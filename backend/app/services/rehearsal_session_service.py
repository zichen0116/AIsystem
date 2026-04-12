# backend/app/services/rehearsal_session_service.py
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rehearsal import RehearsalScene, RehearsalSession

logger = logging.getLogger(__name__)


def summarize_session_counts(session: RehearsalSession) -> dict[str, int]:
    return {
        "ready_count": session.ready_count,
        "fallback_count": session.fallback_count,
        "playable_count": session.playable_count,
        "skipped_count": session.skipped_count,
        "failed_count": session.failed_count,
    }


async def list_sessions(db: AsyncSession, user_id: int) -> list[dict]:
    """列出会话，附带上传场景计数汇总。"""
    result = await db.execute(
        select(RehearsalSession)
        .options(selectinload(RehearsalSession.scenes))
        .where(RehearsalSession.user_id == user_id)
        .order_by(RehearsalSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    out = []
    for session in sessions:
        counts = summarize_session_counts(session)
        out.append(
            {
                "id": session.id,
                "title": session.title,
                "topic": session.topic,
                "source": session.source,
                "status": session.status,
                "total_scenes": session.total_scenes,
                "total_pages": session.total_pages,
                "original_file_name": session.original_file_name,
                "language": session.language,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                **counts,
            }
        )
    return out


async def get_session_with_scenes(
    db: AsyncSession, session_id: int, user_id: int
) -> RehearsalSession | None:
    result = await db.execute(
        select(RehearsalSession)
        .options(selectinload(RehearsalSession.scenes))
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_scene(
    db: AsyncSession, session_id: int, scene_order: int, user_id: int
) -> RehearsalScene | None:
    """获取单个场景（校验 user_id 所有权）。"""
    result = await db.execute(
        select(RehearsalScene)
        .join(RehearsalSession)
        .where(
            RehearsalScene.session_id == session_id,
            RehearsalScene.scene_order == scene_order,
            RehearsalSession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_playback_snapshot(
    db: AsyncSession, session_id: int, user_id: int, snapshot: dict
) -> bool:
    result = await db.execute(
        select(RehearsalSession)
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    session.playback_snapshot = snapshot
    await db.flush()
    return True


def compute_session_status(session: RehearsalSession) -> str:
    """根据页级状态汇总计算会话级状态。"""
    if not session.scenes:
        return "failed"

    statuses = [scene.scene_status for scene in session.scenes]
    if any(status in ("pending", "generating") for status in statuses):
        return "processing" if session.source == "upload" else "generating"

    counts = summarize_session_counts(session)
    if counts["playable_count"] == 0:
        return "failed"
    if counts["failed_count"] > 0:
        return "partial"
    return "ready"


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(RehearsalSession)
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    await db.delete(session)
    await db.flush()
    return True
