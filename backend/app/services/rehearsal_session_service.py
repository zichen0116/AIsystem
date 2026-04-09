# backend/app/services/rehearsal_session_service.py
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rehearsal import RehearsalSession, RehearsalScene

logger = logging.getLogger(__name__)


async def list_sessions(db: AsyncSession, user_id: int) -> list[dict]:
    """列出会话，附带 ready_count 和 failed_count 汇总。"""
    result = await db.execute(
        select(RehearsalSession)
        .options(selectinload(RehearsalSession.scenes))
        .where(RehearsalSession.user_id == user_id)
        .order_by(RehearsalSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        ready = sum(1 for sc in s.scenes if sc.scene_status == "ready")
        failed = sum(1 for sc in s.scenes if sc.scene_status == "failed")
        out.append({
            "id": s.id, "title": s.title, "topic": s.topic,
            "status": s.status, "total_scenes": s.total_scenes,
            "language": s.language,
            "created_at": s.created_at, "updated_at": s.updated_at,
            "ready_count": ready, "failed_count": failed,
        })
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
    statuses = [s.scene_status for s in session.scenes]
    if any(st in ("pending", "generating") for st in statuses):
        return "generating"
    if all(st == "ready" for st in statuses):
        return "ready"
    if all(st == "failed" for st in statuses):
        return "failed"
    return "partial"


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(RehearsalSession)
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True
