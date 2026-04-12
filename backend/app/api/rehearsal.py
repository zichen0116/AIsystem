import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.database import get_db
from app.schemas.rehearsal import (
    RehearsalGenerateRequest,
    RehearsalSnapshotUpdate,
    RehearsalSessionSummary,
    RehearsalSessionDetail,
    RehearsalSessionListResponse,
    RehearsalSceneResponse,
    RehearsalUploadResponse,
)
from app.services import rehearsal_session_service as session_svc
from app.services import rehearsal_upload_service as upload_svc
from app.services.rehearsal_generation_service import generate_stream, retry_scene

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rehearsal", tags=["rehearsal"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/generate-stream")
async def generate_rehearsal_stream(req: RehearsalGenerateRequest, user: CurrentUser):
    """SSE 流式生成课堂预演（仅通知进度，完整数据从 sessions/{id} 获取）。"""
    return StreamingResponse(
        generate_stream(
            topic=req.topic, language=req.language, enable_tts=req.enable_tts,
            voice=req.voice, speed=req.speed, user_id=user.id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/upload", response_model=RehearsalUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_rehearsal(user: CurrentUser, db: DbSession, file: UploadFile = File(...)):
    """上传 PDF/PPT/PPTX 文件并创建上传来源的预演会话。"""
    try:
        payload = await upload_svc.create_rehearsal_upload_session(db, user.id, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return RehearsalUploadResponse(**payload)


@router.get("/sessions", response_model=RehearsalSessionListResponse)
async def list_sessions(user: CurrentUser, db: DbSession):
    """获取预演会话列表（含页级状态汇总）。"""
    sessions = await session_svc.list_sessions(db, user.id)
    return RehearsalSessionListResponse(
        sessions=[RehearsalSessionSummary(**s) for s in sessions]
    )


@router.get("/sessions/{session_id}", response_model=RehearsalSessionDetail)
async def get_session(session_id: int, user: CurrentUser, db: DbSession):
    """获取预演会话详情（含所有场景和页级状态）。"""
    session = await session_svc.get_session_with_scenes(db, session_id, user.id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    return RehearsalSessionDetail.model_validate(session)


@router.get("/sessions/{session_id}/scenes/{scene_order}", response_model=RehearsalSceneResponse)
async def get_scene(session_id: int, scene_order: int, user: CurrentUser, db: DbSession):
    """获取单个场景（用于前端增量获取已就绪页面）。"""
    scene = await session_svc.get_scene(db, session_id, scene_order, user.id)
    if not scene:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "场景不存在")
    return RehearsalSceneResponse.model_validate(scene)


@router.post("/sessions/{session_id}/scenes/{scene_order}/retry")
async def retry_scene_endpoint(session_id: int, scene_order: int, user: CurrentUser):
    """重试生成失败的单个场景。"""
    try:
        new_status = await retry_scene(session_id, scene_order, user.id)
        return {"scene_status": new_status}
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: int, req: RehearsalSnapshotUpdate, user: CurrentUser, db: DbSession
):
    """更新播放进度快照。"""
    ok = await session_svc.update_playback_snapshot(db, session_id, user.id, req.playback_snapshot)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    await db.commit()
    return {"success": True}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: int, user: CurrentUser, db: DbSession):
    """删除预演会话。"""
    ok = await session_svc.delete_session(db, session_id, user.id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    return None

