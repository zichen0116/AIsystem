"""
PPT生成模块 - FastAPI路由
banana-slides 集成到 AIsystem
"""
import json
import logging
import os
import re
import shutil
import tempfile
import urllib.request
import uuid
import zipfile
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Query, Path, Form
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.services.redis_service import invalidate_ppt_cover, get_ppt_cover, set_ppt_cover
from app.models.user import User
from app.generators.ppt.banana_models import (
    PPTProject, PPTPage, PPTTask, PPTMaterial,
    PPTReferenceFile, PPTSession, UserTemplate, PageImageVersion, PPTProjectIntent
)
from app.generators.ppt.page_utils import (
    extract_page_points,
    get_active_extra_fields_config,
    split_generated_description,
)
from app.generators.ppt.intent_service import (
    DEFAULT_INTENT_PENDING,
    DEFAULT_INTENT_SCORES,
    INTENT_STATUS_CONFIRMED,
    apply_intent_state_to_record,
    build_session_intent_metadata,
    confirm_intent_state,
    create_intent_state,
    merge_intent_state,
    parse_intent_response,
    serialize_intent_record,
)
from app.generators.ppt.banana_schemas import (
    PPTProjectCreate, PPTProjectUpdate, PPTProjectResponse, PPTProjectListItem,
    PPTPageCreate, PPTPageUpdate, PPTPageResponse,
    PPTTaskResponse, PPTMaterialResponse, PPTReferenceFileResponse,
    PPTSessionResponse, ChatMessageRequest, PageReorderRequest,
    ProjectSettingsUpdate, UserTemplateCreate, UserTemplateUpdate,
    UserTemplateResponse, PageImageVersionResponse,
    PPTIntentStateResponse, PPTIntentEnvelopeResponse, PPTIntentConfirmResponse,
    RefineOutlineRequest, RefineDescriptionsRequest, EditImageRequest,
    GenerateOutlineRequest, GenerateOutlineStreamRequest,
    GenerateDescriptionsStreamRequest, ExportRequest, ExportTaskResponse,
    MaterialGenerateRequest,
    FileGenerationResponse,
)
from app.generators.ppt.task_dispatcher import (
    dispatch_file_generation_task,
    dispatch_renovation_parse_task,
    ensure_pending_task_started,
)

router = APIRouter(prefix="/ppt", tags=["PPT生成"])
logger = logging.getLogger(__name__)

DEFAULT_INTENT_PENDING = [
    "受众基础层次",
    "核心教学目标",
    "章节重点和节奏",
    "互动形式与限制条件",
]

DEFAULT_INTENT_SCORES = {
    "goal": 35,
    "audience": 35,
    "structure": 35,
    "interaction": 35,
}

LOCAL_EXPORT_ROUTE_PREFIX = "/api/v1/ppt/exports/local"


def _normalize_file_ext(filename: Optional[str], content_type: Optional[str] = None) -> str:
    """统一提取文件扩展名（不带点）。"""
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    if ext:
        return ext

    mime_to_ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
        "application/pdf": "pdf",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "text/markdown": "md",
        "text/csv": "csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }
    if content_type:
        return mime_to_ext.get(content_type.lower(), "bin")
    return "bin"


def _extract_oss_key(url: str) -> Optional[str]:
    """从 OSS/签名 URL 提取对象 key。"""
    try:
        parsed = urlparse(url)
        key = parsed.path.lstrip("/")
        return key or None
    except Exception:
        return None


def _parse_page_ids_param(page_ids: Optional[str]) -> Optional[list[int]]:
    """解析逗号分隔的 page_ids 查询参数。"""
    if not page_ids:
        return None
    ids = []
    for item in page_ids.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的 page_id: {item}")
    return ids or None


def _parse_string_list_field(value: object) -> list[str]:
    """Parse JSON/form list fields into a compact string list."""
    if value is None:
        return []

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = [raw]
    elif isinstance(value, (list, tuple, set)):
        parsed = list(value)
    else:
        parsed = [value]

    result: list[str] = []
    for item in parsed:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _parse_bool_field(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_json_object_field(value: object) -> object:
    """Parse JSON object-ish multipart fields, returning raw values if parsing fails."""
    if value is None:
        return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw
    return value


def _extract_page_points(page: PPTPage) -> list[str]:
    return extract_page_points(page)


def _get_active_extra_fields_config(project: PPTProject) -> list[dict]:
    return get_active_extra_fields_config(project.settings or {})

def _extract_project_template_style(project: PPTProject) -> Optional[str]:
    style = str(getattr(project, "template_style", "") or "").strip()
    if style:
        return style
    settings_style = str((project.settings or {}).get("template_style") or "").strip()
    return settings_style or None


def _get_project_style_prompt(project: PPTProject) -> Optional[str]:
    return _extract_project_template_style(project) or project.theme


def _sync_project_template_style_to_settings(project: PPTProject) -> None:
    settings = dict(project.settings or {})
    style = str(getattr(project, "template_style", "") or "").strip()
    if style:
        settings["template_style"] = style
    else:
        settings.pop("template_style", None)
    project.settings = settings



def _sanitize_points(raw_points: list, max_count: int = 3) -> list[str]:
    """将 points 强制转为纯字符串列表，最多保留 max_count 条。"""
    placeholder_terms = (
        "...", "……", "待补充", "待完善", "待确认", "tbd", "todo", "placeholder",
        "[核心概念", "[关键技能", "[实际应用", "[示例", "[要点",
    )
    result = []
    for p in raw_points:
        if isinstance(p, str):
            text = p.strip()
        elif isinstance(p, dict):
            text = p.get("content") or p.get("text") or p.get("title") or json.dumps(p, ensure_ascii=False)
            text = str(text).strip()
        else:
            text = str(p).strip()
        if not text:
            continue
        lowered = text.lower()
        if any(term in lowered for term in placeholder_terms):
            continue
        if text.startswith("[") and text.endswith("]"):
            continue
        if re.fullmatch(r"[\[\](){}\s._\-:：;；,，/\\]+", text):
            continue
        if len(text) < 2:
            continue
        if text:
            result.append(text)
    return result[:max_count]


def _apply_generated_description(page: PPTPage, generated_text: str, extra_fields_config: list[dict]) -> None:
    parsed = split_generated_description(generated_text, extra_fields_config)
    page.description = parsed["description"] or generated_text

    config = dict(page.config or {})
    stored_extra_fields = dict(config.get("extra_fields") or {})
    managed_keys = [
        str(field.get("key") or "").strip()
        for field in extra_fields_config
        if str(field.get("key") or "").strip() and str(field.get("key") or "").strip() != "notes"
    ]
    for key in managed_keys:
        if key in parsed["extra_fields"]:
            stored_extra_fields[key] = parsed["extra_fields"][key]
        else:
            stored_extra_fields.pop(key, None)
    config["extra_fields"] = stored_extra_fields
    page.config = config

    if any(str(field.get("key") or "").strip() == "notes" for field in extra_fields_config):
        page.notes = parsed["notes"] or None


def _download_image_urls_to_local_paths(image_urls: list[str]) -> tuple[str, list[str]]:
    """下载页面图片到临时目录，返回 (tmp_dir, local_paths)。"""
    from app.generators.ppt.file_service import get_oss_service

    tmp_dir = tempfile.mkdtemp(prefix="ppt_export_")
    local_paths: list[str] = []
    try:
        oss_svc = get_oss_service()
    except Exception as e:
        logger.warning("OSS 服务不可用，改用 URL 直接下载: %s", e)
        oss_svc = None

    for idx, image_url in enumerate(image_urls):
        suffix = os.path.splitext(image_url.split("?")[0])[1] or ".png"
        local_path = os.path.join(tmp_dir, f"page_{idx:04d}{suffix}")
        oss_key = _extract_oss_key(image_url)
        try:
            if os.path.isfile(image_url):
                shutil.copyfile(image_url, local_path)
            elif oss_key and oss_svc is not None:
                try:
                    oss_svc.download_file(oss_key, local_path)
                except Exception:
                    urllib.request.urlretrieve(image_url, local_path)
            else:
                urllib.request.urlretrieve(image_url, local_path)
            local_paths.append(local_path)
        except Exception as e:
            logger.warning("下载导出图片失败 url=%s: %s", image_url, e)

    return tmp_dir, local_paths


def _build_export_download_urls(export_url: str, *, is_local: bool, api_base: str) -> dict:
    """Build download URLs for both OSS-hosted and local fallback exports."""
    if is_local:
        filename = os.path.basename(str(export_url).replace("\\", "/"))
        download_url = f"{LOCAL_EXPORT_ROUTE_PREFIX}/{filename}"
        return {
            "download_url": download_url,
            "download_url_absolute": f"{api_base.rstrip('/')}{download_url}",
            "is_local": True,
        }

    return {
        "download_url": export_url,
        "download_url_absolute": export_url,
    }


def _clamp_score(value: object, default: int = 35) -> int:
    """将分值规范到 0-100。"""
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    return max(0, min(100, score))


def _safe_list_text(value: object, fallback: list[str]) -> list[str]:
    """将任意值安全转成字符串列表。"""
    if not isinstance(value, list):
        return fallback
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return result or fallback


def _parse_intent_state(raw_response: str) -> tuple[str, dict]:
    """解析模型返回的结构化意图状态（带降级容错）。"""
    raw_text = (raw_response or "").strip()
    fallback_state = {
        "confirmed": [],
        "pending": DEFAULT_INTENT_PENDING,
        "scores": DEFAULT_INTENT_SCORES.copy(),
        "confidence": 50,
        "ready_for_confirmation": False,
        "summary": "继续澄清中",
    }

    candidates: list[str] = []
    code_blocks = re.findall(r"```json\s*([\s\S]*?)```", raw_text, flags=re.IGNORECASE)
    candidates.extend(code_blocks)

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidates.append(raw_text[start:end + 1])

    parsed: dict | None = None
    for candidate in candidates:
        try:
            parsed_obj = json.loads(candidate)
            if isinstance(parsed_obj, dict):
                parsed = parsed_obj
                break
        except json.JSONDecodeError:
            continue

    if not parsed:
        return raw_text, fallback_state

    # 兼容两种结构: {reply, intent_state:{...}} 或平铺结构
    state_obj = parsed.get("intent_state") if isinstance(parsed.get("intent_state"), dict) else parsed
    reply = str(parsed.get("reply") or parsed.get("message") or "").strip()
    if not reply:
        reply = str(state_obj.get("reply") or raw_text).strip()

    confirmed = _safe_list_text(state_obj.get("confirmed"), [])
    pending = _safe_list_text(state_obj.get("pending"), DEFAULT_INTENT_PENDING)

    scores_obj = state_obj.get("scores") if isinstance(state_obj.get("scores"), dict) else {}
    scores = {
        "goal": _clamp_score(scores_obj.get("goal"), DEFAULT_INTENT_SCORES["goal"]),
        "audience": _clamp_score(scores_obj.get("audience"), DEFAULT_INTENT_SCORES["audience"]),
        "structure": _clamp_score(scores_obj.get("structure"), DEFAULT_INTENT_SCORES["structure"]),
        "interaction": _clamp_score(scores_obj.get("interaction"), DEFAULT_INTENT_SCORES["interaction"]),
    }

    confidence = _clamp_score(state_obj.get("confidence"), 50)
    ready_for_confirmation = bool(state_obj.get("ready_for_confirmation"))

    summary = str(state_obj.get("summary") or "继续澄清中").strip()
    if not summary:
        summary = "继续澄清中"

    # 提取 intent_summary
    intent_summary = parsed.get("intent_summary") if isinstance(parsed.get("intent_summary"), dict) else {}

    # 一致性修正：若模型返回自相矛盾（已确认完整但 pending 仍是默认值），自动纠正
    confirm_text = "\n".join(confirmed)
    covered = {
        "audience": any(k in confirm_text for k in ["受众", "年级", "学生"]),
        "goal": any(k in confirm_text for k in ["目标", "学习目标", "达成"]),
        "structure": any(k in confirm_text for k in ["结构", "章节", "节奏", "课时", "时间线", "页数"]),
        "interaction": any(k in confirm_text for k in ["互动", "约束", "活动", "限制", "形式"]),
    }
    inferred_pending = []
    if not covered["audience"]:
        inferred_pending.append("受众基础层次")
    if not covered["goal"]:
        inferred_pending.append("核心教学目标")
    if not covered["structure"]:
        inferred_pending.append("课时与目标页数")
    if not covered["interaction"]:
        inferred_pending.append("互动与约束条件")

    ready_hint = any(text in f"{reply}\n{summary}" for text in ["确认意图", "确认无误", "可以确认", "请确认"])
    pending_is_default = pending == DEFAULT_INTENT_PENDING

    # 条件触发：明确可确认提示，或已确认项覆盖四类核心信息且有 intent_summary
    if ready_hint or (len(confirmed) >= 4 and not inferred_pending and intent_summary):
        pending = inferred_pending
        ready_for_confirmation = len(pending) == 0

    # 若 pending 仍是默认值但已覆盖大部分核心信息，则用推断结果替换默认值
    if pending_is_default and inferred_pending != pending:
        pending = inferred_pending

    if pending:
        ready_for_confirmation = False

    return reply, {
        "confirmed": confirmed,
        "pending": pending,
        "scores": scores,
        "confidence": confidence,
        "ready_for_confirmation": ready_for_confirmation,
        "summary": summary,
        "intent_summary": intent_summary,
    }


def _project_intent_topic(project: PPTProject) -> str | None:
    return str(project.theme or project.outline_text or "").strip() or None


def _normalize_session_intent_state(raw_state: object, project: PPTProject, round_number: int) -> dict:
    base = create_intent_state(_project_intent_topic(project))
    if not isinstance(raw_state, dict):
        base["round"] = round_number
        return base

    merged = merge_intent_state(base, raw_state, fallback_topic=_project_intent_topic(project))
    merged["round"] = max(int(merged.get("round") or 0), int(round_number or 0))

    confirmed_at = raw_state.get("confirmed_at")
    if isinstance(confirmed_at, str):
        try:
            merged["confirmed_at"] = datetime.fromisoformat(confirmed_at)
        except ValueError:
            merged["confirmed_at"] = None
    return merged


async def _get_or_create_project_intent(
    db: AsyncSession,
    project: PPTProject,
    user_id: int,
    sessions: list[PPTSession] | None = None,
) -> PPTProjectIntent:
    result = await db.execute(
        select(PPTProjectIntent).where(PPTProjectIntent.project_id == project.id)
    )
    intent = result.scalar_one_or_none()
    if intent:
        if not intent.topic and _project_intent_topic(project):
            intent.topic = _project_intent_topic(project)
        should_backfill = bool(
            sessions
            and not any([
                intent.audience,
                intent.goal,
                intent.duration,
                intent.constraints,
                intent.style,
                intent.interaction,
                intent.extra,
            ])
            and not intent.confirmed_points
        )
        if should_backfill:
            intent_state = create_intent_state(_project_intent_topic(project))
            for session in sessions or []:
                if session.role != "assistant" or not session.session_metadata:
                    continue
                session_state = session.session_metadata.get("intent_state")
                if not isinstance(session_state, dict):
                    continue
                intent_state = merge_intent_state(
                    intent_state,
                    _normalize_session_intent_state(session_state, project, session.round),
                    fallback_topic=_project_intent_topic(project),
                )
            if project.status == "INTENT_CONFIRMED" and not intent_state.get("pending"):
                try:
                    intent_state = confirm_intent_state(intent_state)
                except ValueError:
                    pass
            apply_intent_state_to_record(
                intent,
                intent_state,
                round_number=int(intent_state.get("round") or 0),
            )
        return intent

    intent = PPTProjectIntent(project_id=project.id, user_id=user_id)
    intent_state = create_intent_state(_project_intent_topic(project))

    for session in sessions or []:
        if session.role != "assistant" or not session.session_metadata:
            continue
        session_state = session.session_metadata.get("intent_state")
        if not isinstance(session_state, dict):
            continue
        intent_state = merge_intent_state(
            intent_state,
            _normalize_session_intent_state(session_state, project, session.round),
            fallback_topic=_project_intent_topic(project),
        )

    if project.status == "INTENT_CONFIRMED" and not intent_state.get("pending"):
        try:
            intent_state = confirm_intent_state(intent_state)
        except ValueError:
            pass

    apply_intent_state_to_record(
        intent,
        intent_state,
        round_number=int(intent_state.get("round") or 0),
    )
    db.add(intent)
    await db.flush()
    return intent

# ============= Project CRUD =============

@router.post("/projects", response_model=PPTProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: PPTProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建PPT项目"""
    settings = dict(data.settings or {})
    template_style_raw = data.template_style if data.template_style is not None else settings.get("template_style")
    template_style = str(template_style_raw or "").strip() or None

    if has_text:
        parsed_settings["file_generation_source_text"] = source_text.strip()
    else:
        parsed_settings.pop("file_generation_source_text", None)

    project = PPTProject(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        creation_type=data.creation_type,
        theme=data.theme,
        template_style=template_style,
        outline_text=data.outline_text,
        settings=settings,
        knowledge_library_ids=data.knowledge_library_ids or [],
        status="PLANNING"
    )
    _sync_project_template_style_to_settings(project)

    db.add(project)
    await db.flush()
    await _get_or_create_project_intent(db, project, current_user.id)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[PPTProjectListItem])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """列出当前用户的所有PPT项目（含页数和封面图）"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.user_id == current_user.id)
        .order_by(PPTProject.updated_at.desc())
    )
    projects = result.scalars().all()

    items = []
    for project in projects:
        # 使用 Redis 缓存封面图
        cover_url = await get_ppt_cover(project.id)
        if cover_url is None:
            page_result = await db.execute(
                select(PPTPage.image_url)
                .where(PPTPage.project_id == project.id, PPTPage.image_url.isnot(None))
                .order_by(PPTPage.page_number)
                .limit(1)
            )
            cover_url = page_result.scalar_one_or_none() or ""
            await set_ppt_cover(project.id, cover_url)

        # 查询页数
        page_count_result = await db.execute(
            select(func.count()).select_from(PPTPage).where(PPTPage.project_id == project.id)
        )
        page_count = page_count_result.scalar_one()

        items.append(PPTProjectListItem(
            id=project.id,
            user_id=project.user_id,
            title=project.title or project.outline_text or "未命名项目",
            description=project.description,
            creation_type=project.creation_type or "dialog",
            status=project.status or "DRAFT",
            template_style=project.template_style,
            created_at=project.created_at,
            updated_at=project.updated_at,
            page_count=page_count,
            cover_image_url=cover_url or None,
        ))
    return items


@router.get("/projects/{project_id}", response_model=PPTProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目详情"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/projects/{project_id}", response_model=PPTProjectResponse)
async def update_project(
    project_id: int,
    data: PPTProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = data.model_dump(exclude_unset=True)

    incoming_settings = dict(update_data.get("settings") or {}) if isinstance(update_data.get("settings"), dict) else None
    has_template_style_update = "template_style" in update_data or (incoming_settings is not None and "template_style" in incoming_settings)

    if incoming_settings is not None:
        incoming_settings.pop("template_style", None)
        update_data["settings"] = incoming_settings

    if has_template_style_update:
        incoming_template_style = update_data.get("template_style")
        if incoming_template_style is None and isinstance(data.settings, dict):
            incoming_template_style = data.settings.get("template_style")
        update_data["template_style"] = str(incoming_template_style or "").strip() or None

    for field, value in update_data.items():
        setattr(project, field, value)

    _sync_project_template_style_to_settings(project)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除项目"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await invalidate_ppt_cover(project_id)
    await db.delete(project)
    await db.commit()


@router.post("/projects/batch-delete")
async def batch_delete_projects(
    project_ids: list[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量删除项目"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id.in_(project_ids), PPTProject.user_id == current_user.id)
    )
    projects = result.scalars().all()
    for project in projects:
        await invalidate_ppt_cover(project.id)
        await db.delete(project)
    await db.commit()
    return {"deleted": len(projects)}


# ============= Project Settings =============

@router.put("/projects/{project_id}/settings", response_model=PPTProjectResponse)
async def update_project_settings(
    project_id: int,
    data: ProjectSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新项目设置"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    from app.generators.ppt.template_settings import merge_project_settings

    update_data = data.model_dump(exclude_unset=True)
    if "template_style" in update_data:
        project.template_style = str(update_data.pop("template_style") or "").strip() or None

    project.settings = merge_project_settings(project.settings, update_data)
    _sync_project_template_style_to_settings(project)

    await db.commit()
    await db.refresh(project)
    return project


# ============= Pages =============

@router.post("/projects/{project_id}/pages", response_model=PPTPageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    project_id: int,
    data: PPTPageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建页面"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    description = data.description

    config = dict(data.config or {})
    if data.points is not None:
        config["points"] = data.points
    if data.part is not None:
        config["part"] = data.part

    page = PPTPage(
        project_id=project_id,
        page_number=data.page_number,
        title=data.title,
        description=description,
        image_prompt=data.image_prompt,
        notes=data.notes,
        config=config,
        description_mode=data.description_mode
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return page


@router.get("/projects/{project_id}/pages", response_model=list[PPTPageResponse])
async def list_pages(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """列出项目所有页面"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.project_id == project_id)
        .order_by(PPTPage.page_number)
    )
    return result.scalars().all()


@router.put("/projects/{project_id}/pages/{page_id}", response_model=PPTPageResponse)
async def update_page(
    project_id: int,
    page_id: int,
    data: PPTPageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新页面"""
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    update_data = data.model_dump(exclude_unset=True)

    if "points" in update_data:
        points = update_data.pop("points")
        config = dict(update_data.get("config") or page.config or {})
        if points is not None:
            config["points"] = points
        else:
            config.pop("points", None)
        update_data["config"] = config

    if "part" in update_data:
        part = update_data.pop("part")
        config = dict(update_data.get("config") or page.config or {})
        if part is not None:
            config["part"] = part
        else:
            config.pop("part", None)
        update_data["config"] = config

    for field, value in update_data.items():
        setattr(page, field, value)

    await db.commit()
    await db.refresh(page)
    return page


@router.delete("/projects/{project_id}/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    project_id: int,
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除页面"""
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    await db.delete(page)
    await db.commit()
    await invalidate_ppt_cover(project_id)


@router.post("/projects/{project_id}/pages/reorder")
async def reorder_pages(
    project_id: int,
    data: PageReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量重排序页面"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    for idx, page_id in enumerate(data.page_ids):
        result = await db.execute(
            select(PPTPage).where(PPTPage.id == page_id, PPTPage.project_id == project_id)
        )
        page = result.scalar_one_or_none()
        if page:
            page.page_number = idx + 1

    await db.commit()
    await invalidate_ppt_cover(project_id)
    return {"status": "ok"}


# ============= Outline Generation =============

@router.post("/projects/{project_id}/outline/generate")
async def generate_outline(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成大纲（非流式）"""
    from app.generators.ppt.banana_service import get_banana_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    banana_svc = get_banana_service()
    language = "zh" if project.settings.get("language") != "en" else "en"

    # 获取项目的大纲文本
    outline_text = project.outline_text or ""

    try:
        result_data = await banana_svc.parse_outline_text(
            outline_text,
            theme=_get_project_style_prompt(project),
            language=language
        )

        # 更新项目的大纲
        project.outline_text = json.dumps(result_data, ensure_ascii=False)
        await db.commit()

        return {"status": "completed", "data": result_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"大纲生成失败: {str(e)}")


@router.post("/projects/{project_id}/outline/generate/stream")
async def generate_outline_stream(
    project_id: int,
    data: GenerateOutlineStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """流式生成大纲（SSE）"""
    from app.generators.ppt.banana_service import get_banana_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    banana_svc = get_banana_service()
    language = data.language or "zh"

    async def event_generator():
        try:
            # 如果有 idea_prompt，先用它来生成大纲文本
            idea_prompt = data.idea_prompt or project.outline_text or ""

            if idea_prompt:
                # 构建生成大纲的提示（JSON格式，便于直接创建页面）
                style_prompt = _get_project_style_prompt(project)
                theme_hint = f"\nStyle: {style_prompt}" if style_prompt else ""

                # 从 idea_prompt 中提取页数约束（如"8页"、"10页以内"）
                import re
                page_match = re.search(r'页数[：:]\s*([0-9]+页(?:以内)?)', idea_prompt)
                page_hint = f"\n重要：必须生成恰好 {page_match.group(1)}，不要多也不要少。" if page_match else ""

                prompt = f"""You are a helpful assistant that generates an outline for a PPT.

User request:
{idea_prompt}{theme_hint}{page_hint}

Output the outline as a JSON array. Choose the format that best fits the content:

1. Simple format (no major sections):
[{{"title": "封面标题", "points": ["副标题或演讲者信息"]}}, {{"title": "第二页标题", "points": ["核心要点一", "核心要点二", "核心要点三"]}}]

2. Part-based format (with major sections):
[{{"part": "第一部分", "pages": [{{"title": "页面标题", "points": ["核心要点一", "核心要点二"]}}]}}]

Constraints:
- First page should be simple (title, subtitle, presenter only)
- No page number in title
- 必须恰好生成指定页数，不要多也不要少
- 每页 points 最多3条，只保留最核心的要点
- **points 必须是纯字符串数组**，每个元素都是一段简短的中文文本
- **严禁**在 points 中返回对象、字典、JSON嵌套结构
- 错误示例（禁止）："points": [{{"type": "summary", "content": "xxx"}}]
- 正确示例（必须）："points": ["核心要点一", "核心要点二", "核心要点三"]
- Output only the JSON array, no other text
- 请使用全中文输出。"""

                # 调用 AI 生成大纲（Gemini text provider）
                from app.generators.ppt.banana_providers import get_text_provider_singleton
                response = await get_text_provider_singleton().agenerate_text(prompt)

                # 解析 AI 响应
                outline_content = banana_svc._extract_description(response)

                # 保存到项目
                project.outline_text = outline_content
                await db.commit()

                # 分段发送（模拟流式）
                chunks = outline_content.split('\n')
                for chunk in chunks:
                    if chunk.strip():
                        event_data = json.dumps({
                            "type": "outline_chunk",
                            "content": chunk
                        })
                        yield f"event: message\ndata: {event_data}\n\n"

                # 解析 JSON 结构化数据并创建页面
                try:
                    parsed = banana_svc._parse_json_response(outline_content)
                    # 支持两种格式: simple list 或 part-based list
                    pages_data = []
                    if isinstance(parsed, list):
                        for item in parsed:
                            if "pages" in item and "part" in item:
                                # part-based format
                                for p in item["pages"]:
                                    p["part"] = item["part"]
                                    pages_data.append(p)
                            else:
                                pages_data.append(item)
                    elif isinstance(parsed, dict) and "pages" in parsed:
                        pages_data = parsed["pages"]

                    if pages_data:
                        # 删除该项目现有页面，避免重复
                        existing = await db.execute(select(PPTPage).where(PPTPage.project_id == project_id))
                        for ep in existing.scalars().all():
                            await db.delete(ep)
                        await db.commit()
                        yield f"event: message\ndata: {json.dumps({'type': 'reset_pages'})}\n\n"

                        total_pages = len(pages_data)
                        for i, page_data in enumerate(pages_data):
                            cfg = {}
                            if page_data.get("part"):
                                cfg["part"] = page_data["part"]
                            if page_data.get("points") is not None:
                                raw_points = page_data.get("points", [])
                                cfg["points"] = _sanitize_points(raw_points)

                            page = PPTPage(
                                project_id=project_id,
                                page_number=i + 1,
                                title=page_data.get("title", f"第{i+1}页"),
                                config=cfg
                            )
                            db.add(page)
                            await db.commit()
                            await db.refresh(page)

                            page_event = {
                                "type": "page",
                                "page": {
                                    "id": page.id,
                                    "page_number": page.page_number,
                                    "title": page.title,
                                    "points": cfg.get("points", []),
                                    "part": cfg.get("part", "")
                                }
                            }
                            yield f"event: message\ndata: {json.dumps(page_event, ensure_ascii=False)}\n\n"

                            progress_event = {
                                "type": "progress",
                                "current": i + 1,
                                "total": total_pages
                            }
                            yield f"event: message\ndata: {json.dumps(progress_event)}\n\n"
                    else:
                        error_data = json.dumps({"type": "error", "message": "AI返回的大纲格式无法解析，请重试"})
                        yield f"event: message\ndata: {error_data}\n\n"
                        return
                except Exception as parse_err:
                    logger.warning("大纲JSON解析失败: %s\n内容: %s", parse_err, outline_content[:500])
                    error_data = json.dumps({"type": "error", "message": f"大纲解析失败: {str(parse_err)}"})
                    yield f"event: message\ndata: {error_data}\n\n"
                    return

            yield f"event: message\ndata: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"event: message\ndata: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============= Description Generation =============

@router.post("/projects/{project_id}/descriptions/generate")
async def generate_descriptions(
    project_id: int,
    page_ids: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """生成描述（非流式）"""
    from app.generators.ppt.banana_service import get_banana_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    banana_svc = get_banana_service()
    language = "zh"
    parsed_page_ids = _parse_page_ids_param(page_ids)
    extra_fields_config = _get_active_extra_fields_config(project)

    query = (
        select(PPTPage)
        .where(PPTPage.project_id == project_id)
        .order_by(PPTPage.page_number)
    )
    if parsed_page_ids:
        query = query.where(PPTPage.id.in_(parsed_page_ids))

    result = await db.execute(query)
    pages = result.scalars().all()

    for page in pages:
        page.is_description_generating = True
    await db.commit()

    for page in pages:
        try:
            page_data = {
                "id": page.id,
                "title": page.title or "",
                "points": _extract_page_points(page),
            }
            description = await banana_svc.generate_description(
                page_data,
                theme=_get_project_style_prompt(project),
                language=language,
                extra_fields_config=extra_fields_config,
            )
            _apply_generated_description(page, description, extra_fields_config)
        except Exception as e:
            page.description = f"描述生成失败: {str(e)}"
        finally:
            page.is_description_generating = False

    await db.commit()
    return {"status": "completed", "pages": len(pages)}


@router.post("/projects/{project_id}/descriptions/generate/stream")
async def generate_descriptions_stream(
    project_id: int,
    data: GenerateDescriptionsStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """流式生成描述（SSE）"""
    from app.generators.ppt.banana_service import get_banana_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    banana_svc = get_banana_service()
    language = data.language or "zh"
    detail_level = data.detail_level or "default"
    page_ids = data.page_ids or []
    extra_fields_config = _get_active_extra_fields_config(project)

    async def event_generator():
        query = (
            select(PPTPage)
            .where(PPTPage.project_id == project_id)
            .order_by(PPTPage.page_number)
        )
        if page_ids:
            query = query.where(PPTPage.id.in_(page_ids))

        result = await db.execute(query)
        pages = result.scalars().all()
        total = len(pages)

        for page in pages:
            page.is_description_generating = True
        await db.commit()

        for idx, page in enumerate(pages):
            try:
                page_data = {
                    "id": page.id,
                    "title": page.title or "",
                    "points": _extract_page_points(page)
                }

                description = await banana_svc.generate_description(
                    page_data,
                    theme=_get_project_style_prompt(project),
                    language=language,
                    detail_level=detail_level,
                    extra_fields_config=extra_fields_config,
                )

                _apply_generated_description(page, description, extra_fields_config)
                page.is_description_generating = False
                await db.commit()

                event_data = json.dumps({
                    "type": "page",
                    "page_id": page.id,
                    "content": description,
                    "progress": idx + 1,
                    "total": total
                })
                yield f"event: message\ndata: {event_data}\n\n"

            except Exception as e:
                page.is_description_generating = False
                await db.commit()
                event_data = json.dumps({
                    "type": "error",
                    "page_id": page.id,
                    "message": str(e)
                })
                yield f"event: message\ndata: {event_data}\n\n"

        yield f"event: message\ndata: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============= Image Generation =============

@router.post("/projects/{project_id}/images/generate")
async def generate_images(
    project_id: int,
    page_ids: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量生成页面图片"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    parsed_page_ids = _parse_page_ids_param(page_ids)
    task_id = str(uuid.uuid4())
    task = PPTTask(
        project_id=project_id,
        task_id=task_id,
        task_type="generate_image",
        status="PENDING",
    )
    db.add(task)
    await db.commit()

    from app.generators.ppt.celery_tasks import generate_images_async
    import asyncio
    asyncio.create_task(generate_images_async(project_id=project_id, page_ids=parsed_page_ids, task_id_str=task_id))

    return {"task_id": task_id, "status": "processing"}


# ============= Refine (Natural Language Editing) =============

@router.post("/projects/{project_id}/refine/outline")
async def refine_outline(
    project_id: int,
    data: RefineOutlineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """自然语言修改大纲"""
    from app.generators.ppt.banana_service import get_banana_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    banana_svc = get_banana_service()
    language = data.language or "zh"

    # 获取当前页面列表
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.project_id == project_id)
        .order_by(PPTPage.page_number)
    )
    pages = result.scalars().all()

    outline_pages = []
    for p in pages:
        outline_pages.append({
            "id": p.id,
            "title": p.title or "",
            "points": _extract_page_points(p),
        })

    try:
        # 调用 AI 修改大纲
        refined_pages = await banana_svc.refine_outline(
            outline_pages,
            data.user_requirement,
            language=language
        )

        # 更新页面
        for refined in refined_pages:
            for page in pages:
                if page.id == refined.get("id"):
                    page.title = refined.get("title", page.title)
                    if "points" in refined:
                        config = dict(page.config or {})
                        config["points"] = refined["points"] or []
                        page.config = config
                    break

        await db.commit()
        return {"status": "completed", "pages": refined_pages}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"大纲修改失败: {str(e)}")


@router.post("/projects/{project_id}/refine/descriptions")
async def refine_descriptions(
    project_id: int,
    data: RefineDescriptionsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """自然语言修改描述"""
    from app.generators.ppt.banana_service import get_banana_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    banana_svc = get_banana_service()
    language = data.language or "zh"

    # 获取当前页面描述
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.project_id == project_id)
        .order_by(PPTPage.page_number)
    )
    pages = result.scalars().all()

    descriptions = [
        {"id": p.id, "title": p.title, "description": p.description or ""}
        for p in pages
    ]

    try:
        # 调用 AI 修改描述
        refined = await banana_svc.refine_descriptions(
            descriptions,
            data.user_requirement,
            language=language
        )

        # 更新页面描述
        for ref_desc in refined:
            for page in pages:
                if page.id == ref_desc.get("id"):
                    page.description = str(ref_desc.get("description", page.description or ""))
                    break

        await db.commit()
        return {"status": "completed", "descriptions": refined}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"描述修改失败: {str(e)}")


@router.post("/projects/{project_id}/pages/{page_id}/edit/image")
async def edit_page_image(
    project_id: int,
    page_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """单页图片自然语言编辑（异步）"""
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    content_type = request.headers.get("content-type", "")
    uploaded_context_images: list[UploadFile] = []
    if "multipart/form-data" in content_type.lower():
        form = await request.form()
        uploaded_context_images = [
            item
            for item in form.getlist("context_images")
            if isinstance(item, UploadFile)
        ]
        try:
            data = EditImageRequest.model_validate({
                "edit_instruction": form.get("edit_instruction"),
                "context_images": {
                    "use_template": _parse_bool_field(form.get("use_template")),
                    "desc_image_urls": _parse_string_list_field(form.get("desc_image_urls")),
                    "uploaded_image_ids": _parse_string_list_field(form.get("uploaded_image_ids")),
                    "selection_bbox": _parse_json_object_field(form.get("selection_bbox")),
                },
            })
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    else:
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid edit request: {exc}") from exc
        try:
            data = EditImageRequest.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    task_id = str(uuid.uuid4())

    task = PPTTask(
        project_id=project_id,
        task_id=task_id,
        task_type="edit_page_image",
        page_id=page_id,
        status="PENDING"
    )
    db.add(task)
    page.is_image_generating = True
    await db.commit()

    context_images_dict = None
    if data.context_images:
        context_images_dict = data.context_images.model_dump()

    from app.generators.ppt.celery_tasks import edit_page_image_async
    import asyncio

    asyncio.create_task(
        edit_page_image_async(
            project_id=project_id,
            page_id=page_id,
            edit_instruction=data.edit_instruction,
            task_id_str=task_id,
            context_images=context_images_dict,
            uploaded_context_images=uploaded_context_images,
        )
    )

    return {"task_id": task_id}


# ============= Export =============

@router.get("/projects/{project_id}/export/{format}")
async def export_project(
    request: Request,
    project_id: int,
    format: str = Path(..., pattern="^(pptx|pdf|images)$"),
    page_ids: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出项目（同步）"""
    from app.generators.ppt.ppt_export_service import get_ppt_export_service
    from app.generators.ppt.celery_tasks import (
        _download_image_bytes,
        _get_oss_service_safe,
        _update_project_export,
        _upload_or_save_local,
    )

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取页面列表
    query = select(PPTPage).where(PPTPage.project_id == project_id).order_by(PPTPage.page_number)
    selected_page_ids = _parse_page_ids_param(page_ids)
    if selected_page_ids:
        query = query.where(PPTPage.id.in_(selected_page_ids))

    result = await db.execute(query)
    pages = result.scalars().all()

    if not pages:
        raise HTTPException(status_code=400, detail="没有可导出的页面")

    # 收集图片路径（如果有 image_url）
    image_paths = []
    for page in pages:
        if page.image_url:
            # image_url 可能是 URL 或本地路径
            image_paths.append(page.image_url)
    image_paths = [page.image_url for page in pages if page.image_url]

    if not image_paths:
        raise HTTPException(status_code=400, detail="没有生成的图片，请先生成页面图片")

    export_service = get_ppt_export_service()
    aspect_ratio = project.settings.get("aspect_ratio", "16:9") if project.settings else "16:9"
    tmp_dir, local_paths = _download_image_urls_to_local_paths(image_paths)

    if not local_paths:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="没有可用图片，请先生成页面图片")

    try:
        if format == "pptx":
            content = export_service.create_pptx_from_images(local_paths, aspect_ratio=aspect_ratio)
            return StreamingResponse(
                iter([content]),
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": f"attachment; filename={project.title}.pptx"}
            )
        elif format == "pdf":
            content = export_service.create_pdf_from_images(local_paths, aspect_ratio=aspect_ratio)
            return StreamingResponse(
                iter([content]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={project.title}.pdf"}
            )
        else:
            # images 导出走异步任务接口：POST /api/v1/ppt/projects/{id}/export/images
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "USE_ASYNC_EXPORT",
                    "message": "图片导出为异步任务，请使用 POST /api/v1/ppt/projects/{project_id}/export/images 获取任务ID后轮询进度",
                    "async_endpoint": f"/api/v1/ppt/projects/{project_id}/export/images"
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/projects/{project_id}/export/images")
async def export_images_async(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出图片集（异步，ZIP打包，返回任务ID）"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    task_id = str(uuid.uuid4())
    task = PPTTask(
        project_id=project_id,
        task_id=task_id,
        task_type="export_images",
        status="PENDING"
    )
    db.add(task)
    await db.commit()

    from app.generators.ppt.celery_tasks import export_images_task
    export_images_task.delay(project_id=project_id, task_id_str=task_id)

    return {"task_id": task_id, "status": "processing"}


@router.post("/projects/{project_id}/export/editable-pptx")
async def export_editable_pptx(
    project_id: int,
    page_ids: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """导出可编辑PPTX（异步）"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    task_id = str(uuid.uuid4())

    task = PPTTask(
        project_id=project_id,
        task_id=task_id,
        task_type="export_editable_pptx",
        status="PENDING"
    )
    db.add(task)
    await db.commit()

    from app.generators.ppt.celery_tasks import export_editable_pptx_task
    export_editable_pptx_task.delay(project_id=project_id, task_id_str=task_id)

    return {"task_id": task_id, "status": "processing"}


# ============= Export Tasks =============

@router.get("/projects/{project_id}/export-tasks", response_model=list[PPTTaskResponse])
async def list_export_tasks(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取导出任务列表"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(PPTTask)
        .where(PPTTask.project_id == project_id)
        .order_by(PPTTask.created_at.desc())
    )
    return result.scalars().all()


@router.get("/export-tasks/{task_id}", response_model=PPTTaskResponse)
async def get_export_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取导出任务状态"""
    result = await db.execute(
        select(PPTTask)
        .where(PPTTask.task_id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "PENDING":
        await ensure_pending_task_started(db, task)
    return task


# ============= Materials =============

@router.get("/projects/{project_id}/materials", response_model=list[PPTMaterialResponse])
async def list_materials(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目素材列表"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(PPTMaterial)
        .where(PPTMaterial.project_id == project_id)
        .order_by(PPTMaterial.created_at.desc())
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/materials/upload", response_model=PPTMaterialResponse)
async def upload_material(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传素材"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    file_ext = _normalize_file_ext(file.filename, file.content_type)
    material_type = "image" if file_ext in ("png", "jpg", "jpeg", "webp", "gif") else "reference"

    material = PPTMaterial(
        user_id=current_user.id,
        project_id=project_id,
        filename=file.filename,
        oss_path=f"ppt/{project_id}/materials/{uuid.uuid4()}/{file.filename}",
        url=f"https://example.com/oss/{file.filename}",
        file_type=file_ext,
        material_type=material_type
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


@router.delete("/projects/{project_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    project_id: int,
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除素材"""
    result = await db.execute(
        select(PPTMaterial)
        .where(PPTMaterial.id == material_id, PPTMaterial.project_id == project_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")

    await db.delete(material)
    await db.commit()


@router.get("/materials", response_model=list[PPTMaterialResponse])
async def list_all_materials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取全局素材中心列表"""
    result = await db.execute(
        select(PPTMaterial)
        .order_by(PPTMaterial.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()


# ============= Material Generate =============

@router.post("/projects/{project_id}/materials/generate")
async def generate_material(
    project_id: int,
    data: MaterialGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI生成素材图片（异步，返回任务ID）"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    task_id = str(uuid.uuid4())
    task = PPTTask(
        project_id=project_id,
        task_id=task_id,
        task_type="material_generate",
        status="PENDING"
    )
    db.add(task)
    await db.commit()

    from app.generators.ppt.celery_tasks import generate_material_task
    generate_material_task.delay(
        project_id=project_id,
        user_id=current_user.id,
        prompt=data.prompt,
        aspect_ratio=data.aspect_ratio,
        task_id_str=task_id,
    )

    return {"task_id": task_id, "status": "processing"}


# ============= File Generation =============

@router.post("/projects/file-generation", response_model=FileGenerationResponse)
async def file_generation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    file: Optional[UploadFile] = File(None),
    source_text: Optional[str] = Form(None),
    title: str = Form("未命名PPT"),
    theme: Optional[str] = Form(None),
    template_style: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
):
    """
    文件生成一站式入口。

    支持三种输入方式：
    - 仅上传文件（pdf/doc/docx）
    - 仅粘贴文本
    - 文件 + 文本组合
    """
    # 校验：至少提供一种输入
    has_file = file is not None and file.filename
    has_text = bool(source_text and source_text.strip())
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="请上传文件或输入文本内容")

    # 校验文件类型
    ALLOWED_FILE_EXTS = {"pdf", "doc", "docx"}
    file_ext = None
    if has_file:
        file_ext = _normalize_file_ext(file.filename, file.content_type)
        if file_ext not in ALLOWED_FILE_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，仅支持 pdf/doc/docx",
            )

    # 解析 settings JSON
    parsed_settings = {}
    if settings:
        try:
            parsed_settings = json.loads(settings)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="settings 格式错误，需要有效的JSON")

    # 1. 创建项目
    project = PPTProject(
        user_id=current_user.id,
        title=title,
        creation_type="file",
        theme=theme,
        template_style=template_style or parsed_settings.get("template_style"),
        settings=parsed_settings,
        knowledge_library_ids=[],
        status="GENERATING",
    )
    _sync_project_template_style_to_settings(project)
    db.add(project)
    await db.flush()

    # 2. 保存参考文件（如有）
    ref_file_id = None
    if has_file:
        content = await file.read()
        oss_key = f"ppt/{project.id}/reference/{uuid.uuid4()}/{file.filename}"

        # 上传到 OSS
        from app.generators.ppt.file_service import get_oss_service
        try:
            oss_svc = get_oss_service()
            file_url = oss_svc.upload_bytes(content, oss_key)
        except Exception:
            # OSS 不可用时保存到本地
            local_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "exports", "uploads"
            )
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, f"{uuid.uuid4()}_{file.filename}")
            with open(local_path, "wb") as f:
                f.write(content)
            file_url = local_path
            oss_key = local_path

        ref_file = PPTReferenceFile(
            project_id=project.id,
            user_id=current_user.id,
            filename=file.filename,
            oss_path=oss_key,
            url=file_url,
            file_type=file_ext,
            file_size=len(content),
            parse_status="pending",
        )
        db.add(ref_file)
        await db.flush()
        ref_file_id = ref_file.id

    # 3. 创建任务记录
    task_id = str(uuid.uuid4())
    task = PPTTask(
        project_id=project.id,
        task_id=task_id,
        task_type="file_generation",
        status="PENDING",
        progress=0,
    )
    db.add(task)
    await db.commit()

    # 4. 启动 Celery 任务
    dispatch_file_generation_task(
        project_id=project.id,
        file_id=ref_file_id,
        source_text=source_text if has_text else None,
        task_id_str=task_id,
    )

    return FileGenerationResponse(
        project_id=project.id,
        task_id=task_id,
        status="processing",
        reference_file_id=ref_file_id,
    )


# ============= Reference Files =============

@router.post("/projects/{project_id}/reference-files", response_model=PPTReferenceFileResponse)
async def upload_reference_file(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传参考文件"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    file_ext = _normalize_file_ext(file.filename, file.content_type)

    ref_file = PPTReferenceFile(
        project_id=project_id,
        user_id=current_user.id,
        filename=file.filename,
        oss_path=f"ppt/{project_id}/reference/{uuid.uuid4()}/{file.filename}",
        url=f"https://example.com/oss/{file.filename}",
        file_type=file_ext,
        parse_status="pending"
    )
    db.add(ref_file)
    await db.commit()
    await db.refresh(ref_file)
    return ref_file


@router.post("/projects/{project_id}/reference-files/{file_id}/parse")
async def parse_reference_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """触发参考文件解析（异步）"""
    result = await db.execute(
        select(PPTReferenceFile)
        .where(
            PPTReferenceFile.id == file_id,
            PPTReferenceFile.project_id == project_id,
            PPTReferenceFile.user_id == current_user.id,
        )
    )
    ref_file = result.scalar_one_or_none()
    if not ref_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    task_id = str(uuid.uuid4())
    task = PPTTask(
        project_id=project_id,
        task_id=task_id,
        task_type="file_generation",
        status="PENDING",
    )
    db.add(task)

    ref_file.parse_status = "processing"
    ref_file.parse_error = None
    await db.commit()

    dispatch_file_generation_task(
        project_id=project_id,
        file_id=file_id,
        source_text=None,
        task_id_str=task_id,
    )

    return {"status": "processing", "file_id": file_id, "task_id": task_id}


@router.get("/projects/{project_id}/reference-files/{file_id}", response_model=PPTReferenceFileResponse)
async def get_reference_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取参考文件详情"""
    result = await db.execute(
        select(PPTReferenceFile)
        .where(PPTReferenceFile.id == file_id, PPTReferenceFile.project_id == project_id)
    )
    ref_file = result.scalar_one_or_none()
    if not ref_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return ref_file


@router.post("/projects/{project_id}/reference-files/{file_id}/confirm")
async def confirm_reference_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """确认参考文件解析完成"""
    result = await db.execute(
        select(PPTReferenceFile)
        .where(PPTReferenceFile.id == file_id, PPTReferenceFile.project_id == project_id)
    )
    ref_file = result.scalar_one_or_none()
    if not ref_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    ref_file.parse_status = "completed"
    await db.commit()
    return {"status": "confirmed"}


@router.get("/reference-files/{file_id}")
async def get_reference_file_preview(
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取参考文件预览URL（全局）"""
    result = await db.execute(
        select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
    )
    ref_file = result.scalar_one_or_none()
    if not ref_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"url": ref_file.url, "filename": ref_file.filename}


# ============= Sessions (Dialog) =============

@router.get("/projects/{project_id}/sessions", response_model=list[PPTSessionResponse])
async def list_sessions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目对话历史"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(PPTSession)
        .where(PPTSession.project_id == project_id)
        .order_by(PPTSession.created_at)
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/sessions", response_model=PPTSessionResponse)
async def create_session(
    project_id: int,
    data: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建对话消息"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取当前最大轮次
    result = await db.execute(
        select(func.max(PPTSession.round))
        .where(PPTSession.project_id == project_id)
    )
    max_round = result.scalar_one_or_none() or 0

    session = PPTSession(
        project_id=project_id,
        user_id=current_user.id,
        role="user",
        content=data.content,
        session_metadata=data.metadata,
        round=max_round + 1
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/projects/{project_id}/chat")
async def chat(
    project_id: int,
    data: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送对话消息并获取AI回复"""
    from app.services.ai.dashscope_service import get_dashscope_service

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 保存用户消息
    result = await db.execute(
        select(func.max(PPTSession.round))
        .where(PPTSession.project_id == project_id)
    )
    max_round = result.scalar_one_or_none() or 0

    user_session = PPTSession(
        project_id=project_id,
        user_id=current_user.id,
        role="user",
        content=data.content,
        session_metadata=data.metadata,
        round=max_round + 1
    )
    db.add(user_session)
    await db.commit()

    # 构建对话上下文
    dashscope = get_dashscope_service()

    # 获取对话历史
    result = await db.execute(
        select(PPTSession)
        .where(PPTSession.project_id == project_id)
        .order_by(PPTSession.created_at)
    )
    sessions = result.scalars().all()
    project_intent = await _get_or_create_project_intent(db, project, current_user.id, sessions)
    current_intent_state = serialize_intent_record(project_intent)

    # 构建消息历史
    messages = []
    for s in sessions[-10:]:  # 最近 10 条
        messages.append({"role": s.role, "content": s.content})

    try:
        # 调用 AI 服务
        intent_system_prompt = """你是教学意图澄清智能体，风格温柔有耐心，像一位耐心的教学顾问。通过多轮对话引导用户完善教学意图，等待用户确认后再交接给大纲生成。

语气要求：
- 绝对不要使用任何 Markdown 语法（如 **加粗**、*斜体*、- 列表、1. 序号列表等），全部用纯自然文字
- 绝对不要用一整段文字来提问！必须把问题分行列出，每行只问一个明确的点
- 格式示例（不要用 Markdown 序号，用纯数字+句号）：
  1. 学生情况：你的学生是哪个年级/什么专业？他们基础如何？
  2. 课时安排：这节课计划多长时间？（如45分钟、90分钟、2节课）
  3. 页数规划：PPT大概计划多少页？（如8页、10页以内）
  4. 教学风格：你喜欢严谨一点还是轻松活泼的？
- 不用”必须”、”应该”等命令式语气，多用”我们来...”、”你觉得...”等柔和表达
- 用户回答后先肯定再补充，给出正向反馈
- 当用户犹豫时，给台阶下，比如”没关系，我们可以先跳过这个”

提问维度（每轮选 2-3 个相关问题）：
1. 受众：年级/专业/基础水平
2. 目标：学完学生应掌握什么
3. 课时：课堂时长（如45分钟、90分钟、2节课）
4. 页数：PPT目标页数（如8页、10页以内）
5. 风格：严谨学术 or 轻松活泼
6. 重点难点：哪些要重点讲/学生易错在哪
7. 先备知识：需不需要先复习
8. 互动：提问/讨论/小测次数
9. 内容限制：必须包含/避免的内容
10. 素材：是否需要配图/案例

执行规则：
- 前几轮：先建立基础（受众+课时+风格），再明确目标（目标+重点），最后细化（互动+约束+素材）
- 每轮先肯定用户说的，再抛出 2-3 个下一个话题的问题
- 当受众、目标、课时、风格都基本清晰时（confidence >= 70），整理结构化摘要并置 ready_for_confirmation=true
- ready_for_confirmation=true 时，reply 改为整理好的意图摘要文本，语气温暖，询问用户是否确认
- 输出必须是 JSON，不要输出任何 JSON 之外的文字

JSON Schema:
{
    “reply”: “给用户的自然语言回复”,
    “intent_state”: {
        “confirmed”: [“已确认要点1”, “已确认要点2”],
        “pending”: [“待确认要点1”, “待确认要点2”],
        “scores”: {
            “goal”: 0-100,
            “audience”: 0-100,
            “structure”: 0-100,
            “interaction”: 0-100
        },
        “confidence”: 0-100,
        “ready_for_confirmation”: false,
        “summary”: “本轮摘要”
    },
    “intent_summary”: {
        “topic”: “主题（从对话中提取）”,
        “audience”: “受众描述”,
        “goal”: “学习目标”,
        “duration”: “课时时长（如'45分钟'、'2节课'），不能写页数”,
        “constraints”: “约束条件，包含目标页数（如'8页'、'10页以内'）、语言风格要求等”,
        “style”: “风格偏好”,
        “interaction”: “互动安排”,
        “extra”: “其他补充”
    }
}

约束：
- scores 和 confidence 取值 0-100
- pending 非空时 ready_for_confirmation 必须为 false
- 当 ready_for_confirmation=true 时，intent_summary 字段必须完整填写
- 当 ready_for_confirmation=true 时，你的 reply 最后一句必须是：请点击右侧按钮「确认意图，进入大纲页」，进一步生成大纲。"""

        # 注入历史已确认要点到 system prompt
        hist_confirmed = set()
        for s in sessions:
            if s.role == 'assistant' and s.session_metadata:
                old_state = s.session_metadata.get('intent_state', {})
                for item in old_state.get('confirmed', []):
                    if isinstance(item, str) and item.strip():
                        hist_confirmed.add(item.strip())
        if hist_confirmed:
            intent_system_prompt += f"\n\n之前轮次已确认的要点：{', '.join(hist_confirmed)}。请在你的回复中保留这些已确认要点，不要丢弃。"

        initial_topic = _project_intent_topic(project)
        if initial_topic:
            intent_system_prompt += (
                f"\n\n当前项目在欢迎页已经记录的主题/初始需求是：{initial_topic}。"
                "这部分应视为已知前提，除非用户主动推翻，否则不要再次追问主题本身。"
            )

        existing_summary = current_intent_state.get("intent_summary", {})
        summary_lines = [
            f"{field}: {value}"
            for field, value in existing_summary.items()
            if isinstance(value, str) and value.strip()
        ]
        if summary_lines:
            intent_system_prompt += "\n\n当前项目级意图状态摘要：\n" + "\n".join(summary_lines)

        response = await dashscope.chat_with_history(
            messages=messages,
            system_prompt=intent_system_prompt
        )
        raw_content = response if isinstance(response, str) else response.get("content", "")
        ai_content, parsed_intent_state = parse_intent_response(raw_content, _project_intent_topic(project))
        parsed_intent_state["round"] = max_round + 1
        intent_state = merge_intent_state(
            current_intent_state,
            parsed_intent_state,
            fallback_topic=_project_intent_topic(project),
        )
        intent_state["round"] = max_round + 1

    except Exception as e:
        ai_content = f"抱歉，发生了错误: {str(e)}"
        intent_state = current_intent_state or create_intent_state(_project_intent_topic(project))
        intent_state["confidence"] = 40
        intent_state["summary"] = "调用异常，建议重试"
        intent_state["round"] = max_round + 1

    # 保存 AI 回复
    ai_session = PPTSession(
        project_id=project_id,
        user_id=current_user.id,
        role="assistant",
        content=ai_content,
        session_metadata=build_session_intent_metadata(intent_state),
        round=max_round + 1
    )
    db.add(ai_session)
    await db.flush()

    apply_intent_state_to_record(
        project_intent,
        intent_state,
        round_number=ai_session.round,
        source_session_id=ai_session.id,
    )
    if project_intent.status == INTENT_STATUS_CONFIRMED:
        project.status = "INTENT_CONFIRMED"

    await db.commit()
    await db.refresh(ai_session)

    return {
        "message": ai_content,
        "round": ai_session.round,
        "intent_state": serialize_intent_record(project_intent),
        "intent_summary": intent_state.get("intent_summary", {}),
    }


@router.post("/projects/{project_id}/intent/confirm", response_model=PPTIntentConfirmResponse)
async def confirm_intent(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """确认教学意图，更新项目状态后可进入大纲生成"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(PPTProjectIntent).where(PPTProjectIntent.project_id == project_id)
    )
    project_intent = result.scalar_one_or_none()
    if not project_intent:
        project_intent = await _get_or_create_project_intent(db, project, current_user.id)

    try:
        intent_state = confirm_intent_state(serialize_intent_record(project_intent))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    apply_intent_state_to_record(
        project_intent,
        intent_state,
        round_number=project_intent.clarification_round,
        source_session_id=project_intent.last_source_session_id,
    )
    project.status = "INTENT_CONFIRMED"
    await db.commit()

    return {
        "status": "ok",
        "intent": serialize_intent_record(project_intent),
        "intent_summary": serialize_intent_record(project_intent)["intent_summary"],
    }


@router.get("/projects/{project_id}/intent", response_model=PPTIntentEnvelopeResponse)
async def get_intent(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目已确认的教学意图"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    sessions_result = await db.execute(
        select(PPTSession)
        .where(PPTSession.project_id == project_id)
        .order_by(PPTSession.created_at)
    )
    sessions = sessions_result.scalars().all()
    project_intent = await _get_or_create_project_intent(db, project, current_user.id, sessions)
    await db.commit()

    intent = serialize_intent_record(project_intent)
    return {"intent": intent, "intent_summary": intent["intent_summary"]}


@router.post("/projects/{project_id}/dialog/generate-outline")
async def generate_outline_from_dialog(
    project_id: int,
    data: GenerateOutlineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """从对话历史生成结构化大纲"""
    from app.generators.ppt.banana_providers import get_text_provider_singleton

    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取对话历史
    result = await db.execute(
        select(PPTSession)
        .where(PPTSession.project_id == project_id)
        .order_by(PPTSession.created_at)
    )
    sessions = result.scalars().all()

    # 构建对话内容
    conversation = "\n".join([f"{s.role}: {s.content}" for s in sessions])

    # 构建提示词
    prompt = f"""根据以下对话内容，生成一个PPT大纲：

{conversation}

请生成一个结构清晰的PPT大纲，包含：
1. 封面页标题
2. 目录页（可选）
3. 内容页（根据对话主题适当分段，每页一个主题）
4. 总结页（可选）

请以JSON格式返回，格式如下：
{{
  "pages": [
    {{"title": "页面标题", "points": ["核心要点一", "核心要点二", "核心要点三"]}}
  ]
}}

格式强制要求：
- 每页 points 最多3条，只写最核心的内容
- **points 必须是纯字符串数组**，每个元素是一段简短的中文文本
- **严禁**返回对象或嵌套结构，如 {{"type": "summary", "content": "xxx"}} 是错误格式
- 正确示例："points": ["时间跨度：自2025年10月至今", "主要内容概述", "核心收获总结"]
- 只返回JSON，不要其他任何内容。"""

    try:
        response = await get_text_provider_singleton().agenerate_text(prompt)

        # 解析 JSON 响应
        import re
        # 尝试提取 JSON
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            outline_data = json.loads(match.group())
        else:
            outline_data = {"pages": []}

        # 删除该项目现有页面，避免重复累加
        existing = await db.execute(select(PPTPage).where(PPTPage.project_id == project_id))
        for ep in existing.scalars().all():
            await db.delete(ep)
        await db.flush()

        # 创建页面
        pages = outline_data.get("pages", [])
        for i, page_data in enumerate(pages):
            config = {}
            if page_data.get("points") is not None:
                config["points"] = _sanitize_points(page_data.get("points", []))
            page = PPTPage(
                project_id=project_id,
                page_number=i + 1,
                title=page_data.get("title", f"第{i+1}页"),
                config=config
            )
            db.add(page)

        # 更新项目
        project.outline_text = json.dumps(outline_data, ensure_ascii=False)
        project.status = "PLANNING"
        await db.commit()

        return {"outline": outline_data, "pages": pages}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成大纲失败: {str(e)}")


# ============= Templates =============

@router.get("/templates/presets", response_model=list[dict])
async def get_preset_templates():
    """获取预设模板列表"""
    # 返回预设模板数据
    templates = [
        {"id": "1", "name": "经典蓝", "thumbnail": "/templates/template_b.png", "category": "商务"},
        {"id": "2", "name": "简约灰", "thumbnail": "/templates/template_s.png", "category": "简约"},
        {"id": "3", "name": "学术蓝", "thumbnail": "/templates/template_academic.jpg", "category": "学术"},
        {"id": "4", "name": "玻璃感", "thumbnail": "/templates/template_glass.png", "category": "创意"},
        {"id": "5", "name": "清新绿", "thumbnail": "/templates/template_green.png", "category": "清新"},
    ]
    return templates


@router.get("/templates/user", response_model=list[UserTemplateResponse])
async def list_user_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户模板列表"""
    result = await db.execute(
        select(UserTemplate)
        .where(UserTemplate.user_id == current_user.id)
        .order_by(UserTemplate.created_at.desc())
    )
    return result.scalars().all()


@router.post("/user-templates/upload")
async def upload_user_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传用户模板图片到 OSS，返回访问 URL"""
    try:
        from app.generators.ppt.file_service import get_oss_service
        oss = get_oss_service()

        # 读取文件内容
        content = await file.read()
        ext = file.filename.split(".")[-1] if "." in file.filename else "png"
        oss_key = f"ppt/templates/{current_user.id}/{uuid.uuid4().hex}.{ext}"

        url = oss.upload_bytes(content, oss_key)
        logger.info(f"用户模板上传成功: {file.filename} -> {url}")
        return {"url": url, "filename": file.filename}
    except Exception as e:
        logger.error(f"用户模板上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/user-templates", response_model=UserTemplateResponse)
async def create_user_template(
    data: UserTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建用户模板"""
    template = UserTemplate(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        template_data=data.template_data,
        cover_url=data.cover_url,
        source="user"
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/user-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除用户模板"""
    result = await db.execute(
        select(UserTemplate)
        .where(UserTemplate.id == template_id, UserTemplate.user_id == current_user.id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    await db.delete(template)
    await db.commit()


# ============= Image Versions =============

@router.get("/projects/{project_id}/pages/{page_id}/versions", response_model=list[PageImageVersionResponse])
async def list_image_versions(
    project_id: int,
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取页面图片版本历史"""
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    result = await db.execute(
        select(PageImageVersion)
        .where(PageImageVersion.page_id == page_id)
        .order_by(PageImageVersion.version.desc())
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/pages/{page_id}/versions", response_model=PageImageVersionResponse)
async def create_image_version(
    project_id: int,
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新版本（重新生成时）"""
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    # 获取最大版本号
    result = await db.execute(
        select(func.max(PageImageVersion.version))
        .where(PageImageVersion.page_id == page_id)
    )
    max_version = result.scalar_one_or_none() or 0

    version = PageImageVersion(
        page_id=page_id,
        user_id=current_user.id,
        version=max_version + 1,
        image_url=page.image_url or "",
        operation="generate",
        is_active=False
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


@router.post("/projects/{project_id}/pages/{page_id}/versions/{version_id}/set-current")
async def set_current_version(
    project_id: int,
    page_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """切换页面当前图片版本"""
    result = await db.execute(
        select(PPTPage)
        .where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    # 取消所有版本的 active
    result = await db.execute(
        select(PageImageVersion)
        .where(PageImageVersion.page_id == page_id)
    )
    versions = result.scalars().all()
    for v in versions:
        v.is_active = False

    # 设置指定版本为 active
    result = await db.execute(
        select(PageImageVersion)
        .where(PageImageVersion.id == version_id, PageImageVersion.page_id == page_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    version.is_active = True
    page.image_url = version.image_url
    page.image_version = version.version

    await db.commit()
    return {"status": "ok"}


# ============= Tasks =============

@router.get("/projects/{project_id}/tasks", response_model=list[PPTTaskResponse])
async def list_tasks(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目任务列表"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(PPTTask)
        .where(PPTTask.project_id == project_id)
        .order_by(PPTTask.created_at.desc())
    )
    return result.scalars().all()


@router.get("/projects/{project_id}/tasks/{task_id}", response_model=PPTTaskResponse)
async def get_task(
    project_id: int,
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取任务状态"""
    result = await db.execute(
        select(PPTTask)
        .where(PPTTask.task_id == task_id, PPTTask.project_id == project_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


# ============= Project Template =============

@router.post("/projects/{project_id}/template")
async def upload_project_template(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传项目模板图片"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    from app.generators.ppt.file_service import get_oss_service
    import tempfile as _tempfile
    import os as _os

    allowed_exts = {"png", "jpg", "jpeg", "webp"}
    file_ext = _normalize_file_ext(file.filename, file.content_type)
    if file_ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的模板文件格式: {file_ext}，仅支持 png/jpg/webp")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="模板图片不能超过 10MB")

    tmp_path = None
    try:
        with _tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        oss = get_oss_service()
        oss_key = f"ppt/templates/{current_user.id}/{project_id}/{uuid.uuid4().hex}.{file_ext}"
        template_url = oss.upload_file(tmp_path, oss_key)

        settings = dict(project.settings) if project.settings else {}
        settings["template_image_url"] = template_url
        settings["template_oss_key"] = oss_key
        project.settings = settings
        await db.commit()
        await db.refresh(project)

        return {"template_url": template_url, "oss_key": oss_key}
    finally:
        if tmp_path and _os.path.exists(tmp_path):
            _os.unlink(tmp_path)


# ============= Renovation =============

@router.post("/projects/renovation")
async def create_renovation_project(
    file: UploadFile = File(...),
    keep_layout: bool = Form(False),
    template_style: Optional[str] = Form(None),
    language: str = Form("zh"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建PPT翻新项目（上传文件 → 转换 → 渲染页面 → 异步解析）"""
    from app.generators.ppt.file_service import get_oss_service
    from app.generators.ppt.renovation_service import get_renovation_service
    import tempfile
    import os

    # 校验文件类型
    file_ext = _normalize_file_ext(file.filename, file.content_type)
    if file_ext not in ("pdf", "ppt", "pptx"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}，仅支持 pdf/ppt/pptx")

    # 保存上传文件到临时目录
    tmp_dir = tempfile.mkdtemp(prefix="ppt_renovation_")
    tmp_path = os.path.join(tmp_dir, file.filename)
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        oss = get_oss_service()
        renovation_svc = get_renovation_service()
        oss_prefix = f"ppt/renovation/{current_user.id}/{uuid.uuid4()}"

        # 上传原始文件到 OSS
        original_oss_key = f"{oss_prefix}/original.{file_ext}"
        original_url = oss.upload_file(tmp_path, original_oss_key)

        # 创建项目
        project = PPTProject(
            user_id=current_user.id,
            title=f"翻新项目_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            creation_type="renovation",
            status="PARSE",
            settings={
                "keep_layout": keep_layout,
                "language": language,
                "oss_prefix": oss_prefix,
                "aspect_ratio": "16:9",
            },
            template_style=template_style,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # 创建参考文件记录
        ref_file = PPTReferenceFile(
            project_id=project.id,
            user_id=current_user.id,
            filename=file.filename,
            oss_path=original_oss_key,
            url=original_url,
            file_type=file_ext,
            file_size=len(content),
            parse_status="pending",
        )
        db.add(ref_file)
        await db.commit()
        await db.refresh(ref_file)

        # 如果是 PPT/PPTX → LibreOffice 转 PDF
        pdf_path = tmp_path
        if file_ext in ("ppt", "pptx"):
            try:
                pdf_path = renovation_svc.convert_to_pdf(tmp_path, file_ext)
            except (FileNotFoundError, RuntimeError) as e:
                project.status = "FAILED"
                await db.commit()
                raise HTTPException(status_code=500, detail=str(e))

            # 上传转换后的 PDF 到 OSS
            pdf_oss_key = f"{oss_prefix}/converted.pdf"
            oss.upload_file(pdf_path, pdf_oss_key)

        # 渲染 PDF 逐页 PNG
        images_dir = os.path.join(tmp_dir, "pages")
        os.makedirs(images_dir, exist_ok=True)
        image_paths = renovation_svc.render_pdf_to_images(pdf_path, images_dir)

        if not any(p is not None for p in image_paths):
            project.status = "FAILED"
            await db.commit()
            raise HTTPException(status_code=500, detail="PDF 无法渲染出任何页面")

        # 提取宽高比
        aspect_ratio = renovation_svc.get_pdf_aspect_ratio(pdf_path)
        project.settings = {**project.settings, "aspect_ratio": aspect_ratio}

        # 为每页创建 PPTPage + PageImageVersion
        for i, img_path in enumerate(image_paths):
            page = PPTPage(
                project_id=project.id,
                page_number=i + 1,
                title=f"第 {i + 1} 页",
                config={"points": []},
                renovation_status="pending",
            )
            db.add(page)
            await db.flush()

            if img_path:
                # 上传页面图片到 OSS
                img_oss_key = f"{oss_prefix}/pages/page_{i + 1}.png"
                img_url = oss.upload_file(img_path, img_oss_key)
                page.image_url = img_url

                # 创建初始图片版本
                img_version = PageImageVersion(
                    page_id=page.id,
                    user_id=current_user.id,
                    version=1,
                    image_url=img_url,
                    operation="renovation_upload",
                    is_active=True,
                )
                db.add(img_version)

        await db.commit()

        # 创建翻新解析任务
        task_id = str(uuid.uuid4())
        task = PPTTask(
            project_id=project.id,
            task_id=task_id,
            task_type="renovation_parse",
            status="PENDING",
        )
        db.add(task)
        await db.commit()

        dispatch_renovation_parse_task(
            project_id=project.id,
            file_id=ref_file.id,
            task_id_str=task_id,
        )

        page_count = len(image_paths)
        return {
            "project_id": project.id,
            "task_id": task_id,
            "file_id": ref_file.id,
            "page_count": page_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("翻新项目创建失败")
        raise HTTPException(status_code=500, detail=f"翻新项目创建失败: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ============= Pages - Regenerate for Renovation =============

@router.post("/projects/{project_id}/pages/{page_id}/regenerate-renovation")
async def regenerate_page_renovation(
    project_id: int,
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """翻新模式单页重新解析（基于原始单页 PDF）"""
    from app.generators.ppt.renovation_service import get_renovation_service
    from app.generators.ppt.file_service import get_oss_service
    import tempfile
    import os

    # 获取项目
    result = await db.execute(
        select(PPTProject).where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.creation_type != "renovation":
        raise HTTPException(status_code=400, detail="仅翻新项目支持此操作")

    # 获取页面
    result = await db.execute(
        select(PPTPage).where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    # 从 project.settings 获取参数
    settings = project.settings or {}
    oss_prefix = settings.get("oss_prefix", "")
    keep_layout = settings.get("keep_layout", False)
    language = settings.get("language", "zh")

    if not oss_prefix:
        raise HTTPException(status_code=500, detail="项目配置缺少 oss_prefix")

    # 下载单页 PDF
    split_pdf_oss_key = f"{oss_prefix}/split_pages/page_{page.page_number}.pdf"
    oss = get_oss_service()
    renovation_svc = get_renovation_service()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name

        if not oss.file_exists(split_pdf_oss_key):
            raise HTTPException(status_code=500, detail=f"单页 PDF 不存在: page_{page.page_number}.pdf")

        oss.download_file(split_pdf_oss_key, tmp_path)

        # 重新解析
        content = await renovation_svc.process_single_page(
            tmp_path, page.image_url, keep_layout, language,
        )

        # 写回页面
        page.title = content.get("title", "")
        page.description = content.get("description", "")
        page.config = {**(page.config or {}), "points": content.get("points", [])}
        page.renovation_status = "completed"
        page.renovation_error = None
        await db.commit()

        # 重新聚合项目级 outline_text / description_text
        result = await db.execute(
            select(PPTPage)
            .where(PPTPage.project_id == project_id)
            .order_by(PPTPage.page_number)
        )
        all_pages = list(result.scalars().all())

        outline_parts = []
        desc_parts = []
        for p in all_pages:
            if p.renovation_status == "completed":
                points = (p.config or {}).get("points", [])
                points_text = "\n".join(f"- {pt}" for pt in points)
                outline_parts.append(f"第{p.page_number}页：{p.title or ''}\n{points_text}")
                desc_parts.append(f"--- 第{p.page_number}页 ---\n{p.description or ''}")

        project.outline_text = "\n\n".join(outline_parts)
        project.description_text = "\n\n".join(desc_parts)

        # 如果之前 project 是 FAILED 且现在有成功页，更新为 COMPLETED
        success_count = sum(1 for p in all_pages if p.renovation_status == "completed")
        if success_count > 0 and project.status == "FAILED":
            project.status = "COMPLETED"

        await db.commit()
        await db.refresh(page)

        return {
            "status": "completed",
            "page": {
                "id": page.id,
                "page_number": page.page_number,
                "title": page.title,
                "description": page.description,
                "renovation_status": page.renovation_status,
                "renovation_error": page.renovation_error,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("单页翻新重试失败 page_id=%s", page_id)
        page.renovation_status = "failed"
        page.renovation_error = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"单页重试失败: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ============= Local Export Serving (OSS fallback) =============

@router.get("/exports/local/{filename}")
async def serve_local_export(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    服务本地导出文件（OSS不可达时的降级方案）。
    filename 只允许安全文件名，不含路径分隔符。
    """
    import os
    from fastapi.responses import FileResponse
    from app.generators.ppt.celery_tasks import _LOCAL_EXPORTS_DIR

    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    local_path = os.path.join(_LOCAL_EXPORTS_DIR, safe_name)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    media_types = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
        "zip": "application/zip",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(local_path, media_type=media_type, filename=safe_name)


# ============= Extract Style from Image =============

@router.post("/extract-style")
async def extract_style(
    image: UploadFile = File(...),
):
    """
    POST /ppt/extract-style - 从图片中提取风格描述

    Content-Type: multipart/form-data
    Form:
        image: Image file (required)

    Returns:
        {style_description: "..."}
    """
    import base64
    import requests
    from PIL import Image as PILImage
    import io

    settings = get_settings()

    if not image:
        raise HTTPException(status_code=400, detail="没有上传图片")

    # 读取图片
    image_bytes = await image.read()

    # 验证图片
    try:
        pil_img = PILImage.open(io.BytesIO(image_bytes))
        if pil_img.mode not in ('RGB', 'RGBA'):
            pil_img = pil_img.convert('RGB')
    except Exception:
        raise HTTPException(status_code=400, detail="无效的图片文件")

    # 构建风格提取提示词
    style_prompt = """\
You are a professional PPT design analyst. Analyze this image and extract a detailed style description that can be used to generate PPT slides with a similar visual style.

Focus on:
1. **Color palette**: Primary colors, secondary colors, accent colors, background colors
2. **Typography style**: Font style impression (serif/sans-serif, weight, size hierarchy)
3. **Design elements**: Decorative patterns, shapes, icons style, borders, shadows
4. **Overall mood**: Professional, playful, minimalist, corporate, creative, etc.
5. **Layout tendencies**: How content is typically arranged, spacing preferences

Output a concise style description in Chinese that can be directly used as a style prompt for PPT generation. Write it as a single paragraph, not a list. Example:

"采用深蓝色渐变背景，搭配白色和金色文字。整体风格简约商务，使用无衬线字体，标题加粗突出。页面装饰以几何线条和半透明色块为主，配色统一协调。内容区域留白充足，视觉层次分明。"

Only output the style description text, no other content.
"""

    # 调用 Gemini API (使用 HTTP 请求)
    try:
        api_base = settings.GOOGLE_API_BASE or "https://generativelanguage.googleapis.com"
        api_key = settings.GOOGLE_API_KEY

        # 构建请求 URL
        url = f"{api_base}/v1beta/models/gemini-2.0-flash:generateContent"

        # 将图片转为 base64
        b64_image = base64.b64encode(image_bytes).decode('utf-8')

        payload = {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}},
                        {"text": style_prompt}
                    ]
                }
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        result = response.json()

        # 提取风格描述
        style_description = ""
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        style_description = part["text"].strip()
                        break

        if not style_description:
            raise HTTPException(status_code=500, detail="风格提取返回为空")

        return {"style_description": style_description}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"extract_style failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"风格提取失败: {str(e)}")
