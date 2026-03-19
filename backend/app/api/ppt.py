"""
PPT API 路由

提供会话管理、流式大纲生成、PPT生成、编辑快照、版本管理等接口。
所有接口校验JWT，按user_id鉴权。
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.ppt_session import PptSession
from app.models.ppt_outline import PptOutline
from app.models.ppt_message import PptMessage
from app.models.ppt_result import PptResult
from app.schemas.ppt import (
    PptSessionCreate, PptSessionBrief, PptSessionDetail,
    PptOutlineBrief, PptResultBrief, PptResultDetail,
    OutlineStreamRequest, OutlineApproveRequest,
    PptGenerateRequest, PptModifyRequest,
    EditSnapshotRequest, VersionSummary, PptTemplate,
)
from app.services.ppt.docmee_client import describe_exception, docmee_client
from app.services.ppt.nodes import (
    generate_outline_streaming, modify_slide_json,
)
from app.services.ppt.image_search import auto_assign_images
from app.services.ppt.outline_payload import (
    markdown_to_outline_payload,
    outline_payload_has_renderable_content,
    payload_to_docmee_markdown,
)
from app.services.ppt.state import PptAgentState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ppt", tags=["ppt"])


# ========== 辅助函数 ==========

def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _get_session_or_404(
    session_id: int, user_id: int, db: AsyncSession
) -> PptSession:
    result = await db.execute(
        select(PptSession).where(
            PptSession.id == session_id,
            PptSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


# ========== 模板 ==========

@router.get("/templates")
async def get_templates(
    page: int = 1,
    size: int = 20,
    user: User = Depends(get_current_user),
):
    """获取Docmee模板列表"""
    try:
        data = await docmee_client.get_templates(page=page, size=size)
        token = await docmee_client._ensure_token()
        templates = []
        for t in data.get("data", []):
            cover = t.get("coverUrl", "")
            if cover and "?" not in cover:
                cover = f"{cover}?token={token}"
            templates.append(PptTemplate(
                id=str(t.get("id", "")),
                title=t.get("subject"),
                cover_url=cover,
                category=t.get("category"),
            ))
        return {"total": data.get("total", 0), "templates": templates}
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=502, detail=f"获取模板失败: {e}")


# ========== 会话管理 ==========

@router.post("/sessions", response_model=PptSessionBrief)
async def create_session(
    body: PptSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = PptSession(user_id=user.id, title=body.title)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[PptSessionBrief])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PptSession)
        .where(PptSession.user_id == user.id)
        .order_by(PptSession.updated_at.desc())
    )
    return result.scalars().all()


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除PPT会话及其关联数据"""
    session = await _get_session_or_404(session_id, user.id, db)
    await db.delete(session)
    await db.commit()
    return {"detail": "已删除"}


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PptSession)
        .options(
            selectinload(PptSession.messages),
            selectinload(PptSession.outlines),
            selectinload(PptSession.results),
        )
        .where(PptSession.id == session_id, PptSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    results_brief = []
    for r in session.results:
        results_brief.append(PptResultBrief(
            id=r.id, version=r.version, is_current=r.is_current,
            template_id=r.template_id, docmee_ppt_id=r.docmee_ppt_id,
            file_url=r.file_url, status=r.status,
            current_page=r.current_page, total_pages=r.total_pages,
            has_edit_snapshot=bool(r.edited_pptx_property),
            created_at=r.created_at, completed_at=r.completed_at,
        ))

    return PptSessionDetail(
        id=session.id, title=session.title, status=session.status,
        current_outline_id=session.current_outline_id,
        current_result_id=session.current_result_id,
        messages=session.messages,
        outlines=session.outlines,
        results=results_brief,
        created_at=session.created_at, updated_at=session.updated_at,
    )


# ========== 大纲生成与审批 ==========

@router.post("/stream/outline")
async def stream_outline(
    body: OutlineStreamRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """流式生成大纲"""
    session = await _get_session_or_404(body.session_id, user.id, db)

    # 保存用户消息
    user_msg = PptMessage(
        session_id=session.id, role="user",
        message_type="text", content=body.user_input,
    )
    db.add(user_msg)
    session.status = "generating_outline"
    await db.flush()

    # 构建状态
    state: PptAgentState = {
        "session_id": session.id,
        "user_id": user.id,
        "messages": [],
        "user_input": body.user_input,
        "selected_library_ids": body.knowledge_library_ids,
        "retrieved_context": "",
        "template_id": body.template_id,
        "outline_markdown": "",
        "outline_id": None,
        "outline_approved": False,
        "image_urls": {},
        "result_id": None,
        "docmee_task_id": None,
        "next_action": "generate_outline",
        "error_message": "",
    }

    # 如果有知识库，先检索
    if body.knowledge_library_ids:
        from app.services.ppt.nodes import retrieve_knowledge
        retrieval_result = await retrieve_knowledge(state)
        state["retrieved_context"] = retrieval_result.get("retrieved_context", "")

    async def event_generator():
        try:
            yield sse_event({"type": "meta", "session_id": session.id})

            # 流式生成大纲
            full_outline = ""
            async for chunk in generate_outline_streaming(state):
                full_outline += chunk
                yield sse_event({"type": "outline_chunk", "content": chunk})

            # 自动配图（不阻塞）
            image_urls = await auto_assign_images(full_outline)
            outline_payload = markdown_to_outline_payload(full_outline, image_urls=image_urls)

            # 计算版本号
            version_result = await db.execute(
                select(PptOutline)
                .where(PptOutline.session_id == session.id)
                .order_by(PptOutline.version.desc())
            )
            last_outline = version_result.scalars().first()
            new_version = (last_outline.version + 1) if last_outline else 1

            # 将旧大纲标记为非当前
            if last_outline:
                await db.execute(
                    update(PptOutline)
                    .where(PptOutline.session_id == session.id)
                    .values(is_current=False)
                )

            # 保存大纲
            outline = PptOutline(
                session_id=session.id,
                version=new_version,
                content=full_outline,
                image_urls=image_urls,
                outline_payload=outline_payload,
                template_id=body.template_id,
                knowledge_library_ids=body.knowledge_library_ids,
                is_current=True,
            )
            db.add(outline)
            await db.flush()
            await db.refresh(outline)

            # 更新会话
            session.current_outline_id = outline.id
            session.status = "outline_ready"

            # 保存助手消息
            intro_msg = PptMessage(
                session_id=session.id,
                role="assistant",
                message_type="text",
                content="明白了！我已经为你生成了大纲，请查看：",
            )
            db.add(intro_msg)

            ai_msg = PptMessage(
                session_id=session.id, role="assistant",
                message_type="outline", content=full_outline,
                metadata_={
                    "outline_id": outline.id,
                    "image_urls": image_urls,
                    "outline_payload": outline_payload,
                },
            )
            db.add(ai_msg)
            await db.flush()

            yield sse_event({
                "type": "outline_ready",
                "outline_id": outline.id,
                "content": full_outline,
                "image_urls": image_urls,
                "outline_payload": outline_payload,
            })
            yield sse_event({"type": "done"})

        except Exception as e:
            logger.error(f"大纲生成失败: {e}")
            session.status = "failed"
            yield sse_event({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/outlines/{outline_id}/approve")
async def approve_outline(
    outline_id: int,
    body: OutlineApproveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """审批大纲，可带修改后的内容"""
    result = await db.execute(
        select(PptOutline)
        .join(PptSession, PptOutline.session_id == PptSession.id)
        .where(PptOutline.id == outline_id, PptSession.user_id == user.id)
    )
    outline = result.scalar_one_or_none()
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")

    next_image_urls = body.image_urls if body.image_urls is not None else outline.image_urls

    if body.content:
        outline.content = body.content
    if body.image_urls is not None:
        outline.image_urls = body.image_urls
    if body.outline_payload is not None:
        if outline_payload_has_renderable_content(body.outline_payload):
            outline.outline_payload = body.outline_payload
            outline.content = payload_to_docmee_markdown(body.outline_payload)
        else:
            outline.outline_payload = markdown_to_outline_payload(
                body.content or outline.content,
                image_urls=next_image_urls,
            )
            outline.content = payload_to_docmee_markdown(outline.outline_payload)

    session = await _get_session_or_404(outline.session_id, user.id, db)
    session.status = "outline_ready"
    session.current_outline_id = outline.id
    await db.flush()

    return {"message": "大纲已审批", "outline_id": outline.id}


# ========== PPT生成 ==========

@router.post("/stream/generate")
async def stream_generate_ppt(
    body: PptGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """流式生成PPT"""
    session = await _get_session_or_404(body.session_id, user.id, db)

    # 获取大纲
    outline_result = await db.execute(
        select(PptOutline).where(PptOutline.id == body.outline_id)
    )
    outline = outline_result.scalar_one_or_none()
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")

    template_id = body.template_id or outline.template_id
    if not template_id:
        raise HTTPException(status_code=400, detail="请选择模板")

    session.status = "generating_ppt"
    await db.flush()

    async def event_generator():
        try:
            # 创建Docmee任务
            if outline_payload_has_renderable_content(outline.outline_payload):
                outline_markdown = payload_to_docmee_markdown(outline.outline_payload or {})
            else:
                outline_markdown = outline.content

            if not outline_markdown.strip() or outline_markdown.strip() == f"# {(outline.outline_payload or {}).get('title', '').strip()}":
                outline_markdown = outline.content
            logger.info(
                "Generating PPT session=%s outline=%s template=%s markdown_len=%s",
                session.id,
                outline.id,
                template_id,
                len(outline_markdown or ""),
            )
            task_id = await docmee_client.create_task(
                content=outline_markdown, task_type=7
            )
            logger.info("Docmee task created session=%s task_id=%s", session.id, task_id)

            # 计算版本号
            ver_result = await db.execute(
                select(PptResult)
                .where(PptResult.session_id == session.id)
                .order_by(PptResult.version.desc())
            )
            last_result = ver_result.scalars().first()
            new_version = (last_result.version + 1) if last_result else 1

            # 将旧结果标记为非当前
            if last_result:
                await db.execute(
                    update(PptResult)
                    .where(PptResult.session_id == session.id)
                    .values(is_current=False)
                )

            # 创建结果记录
            ppt_result = PptResult(
                session_id=session.id,
                outline_id=outline.id,
                version=new_version,
                is_current=True,
                template_id=template_id,
                status="generating",
            )
            db.add(ppt_result)
            await db.flush()
            await db.refresh(ppt_result)

            yield sse_event({
                "type": "progress",
                "current": 0, "total": 0,
                "result_id": ppt_result.id,
            })

            # 调用Docmee生成PPT
            ppt_info = await docmee_client.generate_pptx(
                task_id=task_id,
                template_id=template_id,
                markdown=outline_markdown,
            )
            logger.info(
                "Docmee generatePptx returned session=%s task_id=%s keys=%s",
                session.id,
                task_id,
                sorted((ppt_info or {}).keys()),
            )

            ppt_info = await docmee_client.finalize_ppt_info(ppt_info)
            ppt_id = ppt_info.get("id", "")
            pptx_property = ppt_info.get("pptxProperty") or ""
            logger.info(
                "Docmee finalized session=%s ppt_id=%s has_pptx=%s has_file_url=%s",
                session.id,
                ppt_id or "<empty>",
                bool(pptx_property),
                bool(ppt_info.get("fileUrl")),
            )

            if not ppt_id:
                raise RuntimeError("PPT 生成失败：未获取到文多多 PPT ID")

            if not pptx_property:
                raise RuntimeError("PPT 生成失败：预览数据尚未就绪，请稍后重试")

            # 更新结果
            ppt_result.docmee_ppt_id = ppt_id
            ppt_result.source_pptx_property = pptx_property
            ppt_result.status = "completed"
            ppt_result.completed_at = datetime.now(timezone.utc)

            page_count = docmee_client.get_page_count(pptx_property)
            ppt_result.total_pages = page_count
            ppt_result.current_page = page_count

            file_url = ppt_info.get("fileUrl") or ""
            if not file_url:
                try:
                    file_url = await docmee_client.download_pptx(ppt_id)
                except Exception:
                    file_url = ""
            ppt_result.file_url = file_url or None

            session.current_result_id = ppt_result.id
            session.status = "preview_ready"

            # 保存消息
            result_msg = PptMessage(
                session_id=session.id, role="assistant",
                message_type="ppt_result",
                content=f"PPT已生成完成，共{ppt_result.total_pages}页",
                metadata_={"result_id": ppt_result.id},
            )
            db.add(result_msg)
            await db.flush()

            yield sse_event({
                "type": "result_ready",
                "result_id": ppt_result.id,
                "ppt_id": ppt_id,
                "file_url": ppt_result.file_url or "",
                "total_pages": ppt_result.total_pages,
                "pptx_property": pptx_property,
            })
            yield sse_event({"type": "done"})

        except Exception as e:
            logger.exception(
                "PPT generation failed session=%s outline=%s error=%s",
                session.id,
                outline.id,
                describe_exception(e),
            )
            session.status = "failed"
            yield sse_event({"type": "error", "message": describe_exception(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ========== 继续修改PPT ==========

@router.post("/results/{result_id}/modify")
async def modify_ppt(
    result_id: int,
    body: PptModifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """直接修改当前 PPT JSON，并返回新的预览结构。"""
    result = await db.execute(
        select(PptResult)
        .join(PptSession, PptResult.session_id == PptSession.id)
        .where(PptResult.id == result_id, PptSession.user_id == user.id)
    )
    ppt_result = result.scalar_one_or_none()
    if not ppt_result:
        raise HTTPException(status_code=404, detail="PPT结果不存在")

    session = await _get_session_or_404(ppt_result.session_id, user.id, db)
    user_msg = PptMessage(
        session_id=session.id, role="user",
        message_type="text", content=body.instruction,
    )
    db.add(user_msg)
    session.status = "editing_ppt"
    await db.flush()
    encoded = (
        body.current_pptx_property
        or ppt_result.edited_pptx_property
        or ppt_result.source_pptx_property
    )
    if not encoded:
        raise HTTPException(status_code=400, detail="当前 PPT 预览数据不存在")

    pptx_obj = docmee_client.decompress_pptx_property(encoded)
    pages = pptx_obj.get("pages") or []
    if body.slide_index >= len(pages):
        raise HTTPException(status_code=400, detail="页码超出范围")

    updated_page = await modify_slide_json(
        instruction=body.instruction,
        pptx_obj=pptx_obj,
        slide_index=body.slide_index,
    )
    pages[body.slide_index] = updated_page
    pptx_obj["pages"] = pages

    edited_pptx_property = docmee_client.compress_pptx_property(pptx_obj)
    ppt_result.edited_pptx_property = edited_pptx_property
    ppt_result.current_page = min(body.slide_index + 1, len(pages))
    ppt_result.total_pages = len(pages)
    session.status = "preview_ready"

    assistant_msg = PptMessage(
        session_id=session.id,
        role="assistant",
        message_type="text",
        content=f"已根据你的要求更新第 {body.slide_index + 1} 页内容。",
        metadata_={"result_id": ppt_result.id, "slide_index": body.slide_index},
    )
    db.add(assistant_msg)
    await db.flush()

    return {
        "result_id": ppt_result.id,
        "slide_index": body.slide_index,
        "pptx_property": edited_pptx_property,
        "total_pages": len(pages),
        "message": assistant_msg.content,
    }


# ========== 编辑快照与结果 ==========

@router.post("/results/{result_id}/edit-snapshot")
async def save_edit_snapshot(
    result_id: int,
    body: EditSnapshotRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保存编辑后的pptx_property快照"""
    result = await db.execute(
        select(PptResult)
        .join(PptSession, PptResult.session_id == PptSession.id)
        .where(PptResult.id == result_id, PptSession.user_id == user.id)
    )
    ppt_result = result.scalar_one_or_none()
    if not ppt_result:
        raise HTTPException(status_code=404, detail="PPT结果不存在")
    ppt_result.edited_pptx_property = body.edited_pptx_property
    await db.flush()
    return {"message": "编辑快照已保存", "result_id": result_id}


@router.get("/results/{result_id}", response_model=PptResultDetail)
async def get_result_detail(
    result_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取PPT结果详情"""
    result = await db.execute(
        select(PptResult)
        .join(PptSession, PptResult.session_id == PptSession.id)
        .where(PptResult.id == result_id, PptSession.user_id == user.id)
    )
    ppt_result = result.scalar_one_or_none()
    if not ppt_result:
        raise HTTPException(status_code=404, detail="PPT结果不存在")
    return PptResultDetail(
        id=ppt_result.id, version=ppt_result.version,
        is_current=ppt_result.is_current, template_id=ppt_result.template_id,
        docmee_ppt_id=ppt_result.docmee_ppt_id,
        file_url=ppt_result.file_url, status=ppt_result.status,
        current_page=ppt_result.current_page, total_pages=ppt_result.total_pages,
        has_edit_snapshot=bool(ppt_result.edited_pptx_property),
        created_at=ppt_result.created_at, completed_at=ppt_result.completed_at,
        source_pptx_property=ppt_result.source_pptx_property,
        edited_pptx_property=ppt_result.edited_pptx_property,
        outline_id=ppt_result.outline_id,
    )


@router.post("/results/{result_id}/download")
async def download_result(
    result_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取PPT下载地址"""
    result = await db.execute(
        select(PptResult)
        .join(PptSession, PptResult.session_id == PptSession.id)
        .where(PptResult.id == result_id, PptSession.user_id == user.id)
    )
    ppt_result = result.scalar_one_or_none()
    if not ppt_result:
        raise HTTPException(status_code=404, detail="PPT结果不存在")
    if not ppt_result.docmee_ppt_id:
        raise HTTPException(status_code=400, detail="PPT尚未生成完成")
    try:
        file_url = await docmee_client.download_pptx(ppt_result.docmee_ppt_id, refresh=True)
        ppt_result.file_url = file_url
        await db.flush()
        return {"file_url": file_url}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取下载地址失败: {e}")


# ========== 版本管理 ==========

@router.get("/sessions/{session_id}/versions", response_model=VersionSummary)
async def get_versions(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话的大纲版本和PPT结果版本"""
    await _get_session_or_404(session_id, user.id, db)
    outlines_result = await db.execute(
        select(PptOutline).where(PptOutline.session_id == session_id).order_by(PptOutline.version)
    )
    results_result = await db.execute(
        select(PptResult).where(PptResult.session_id == session_id).order_by(PptResult.version)
    )
    outline_briefs = [PptOutlineBrief.model_validate(o) for o in outlines_result.scalars().all()]
    result_briefs = []
    for r in results_result.scalars().all():
        result_briefs.append(PptResultBrief(
            id=r.id, version=r.version, is_current=r.is_current,
            template_id=r.template_id, docmee_ppt_id=r.docmee_ppt_id,
            file_url=r.file_url, status=r.status,
            current_page=r.current_page, total_pages=r.total_pages,
            has_edit_snapshot=bool(r.edited_pptx_property),
            created_at=r.created_at, completed_at=r.completed_at,
        ))
    return VersionSummary(outline_versions=outline_briefs, result_versions=result_briefs)


# ========== 文件上传 ==========

@router.post("/sessions/{session_id}/upload")
async def upload_session_file(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """上传参考文件到PPT会话，解析内容后存储"""
    await _get_session_or_404(session_id, user.id, db)

    upload_dir = Path("uploads/ppt")
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix
    dest = upload_dir / f"{uuid.uuid4()}{suffix}"
    content_bytes = await file.read()
    dest.write_bytes(content_bytes)

    parsed = ""
    try:
        from app.services.parsers.factory import ParserFactory
        result = await ParserFactory.parse_file(str(dest))
        if result and result.chunks:
            parsed = "\n\n".join(c.content for c in result.chunks)
    except Exception as e:
        logger.warning(f"Parse failed for {file.filename}: {e}")
        parsed = content_bytes.decode("utf-8", errors="ignore")[:2000]

    # 将解析内容作为消息存入会话
    msg = PptMessage(
        session_id=session_id,
        role="user",
        message_type="file",
        content=f"[上传文件: {file.filename}]",
        metadata_={"filename": file.filename, "file_path": str(dest), "parsed_preview": parsed[:500]},
    )
    db.add(msg)
    await db.commit()

    return {
        "filename": file.filename,
        "file_path": str(dest),
        "parsed_length": len(parsed),
    }
