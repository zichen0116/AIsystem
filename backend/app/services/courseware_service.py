"""Courseware aggregation service — merges PPT projects, lesson plans, and uploaded files."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.courseware import Courseware
from app.models.lesson_plan import LessonPlan
from app.generators.ppt.banana_models import PPTProject, PPTPage
from app.schemas.courseware import CoursewareAggregateItem, CoursewareAggregateResponse
from app.services.redis_service import get_ppt_cover, set_ppt_cover


async def _get_cover_url(db: AsyncSession, project_id: int) -> str:
    """Get PPT cover URL with Redis cache-aside."""
    cached = await get_ppt_cover(project_id)
    if cached is not None:
        return cached  # "" means no cover (cached negative)

    stmt = (
        select(PPTPage.image_url)
        .where(PPTPage.project_id == project_id, PPTPage.image_url.isnot(None))
        .order_by(PPTPage.page_number)
        .limit(1)
    )
    result = await db.execute(stmt)
    url = result.scalar_one_or_none() or ""
    await set_ppt_cover(project_id, url)
    return url


async def _get_page_count(db: AsyncSession, project_id: int) -> int:
    stmt = select(func.count()).select_from(PPTPage).where(PPTPage.project_id == project_id)
    result = await db.execute(stmt)
    return result.scalar_one()


def _apply_date_filter(dt: datetime, date_range: Optional[str]) -> bool:
    if not date_range:
        return True
    now = datetime.now(timezone.utc)
    if date_range == "week":
        return dt >= now - timedelta(days=7)
    elif date_range == "month":
        return dt >= now - timedelta(days=30)
    elif date_range == "year":
        return dt >= now - timedelta(days=365)
    return True


async def get_aggregated_courseware(
    db: AsyncSession,
    user_id: int,
    source_type: Optional[str] = None,
    file_type: Optional[str] = None,
    date_range: Optional[str] = None,
) -> CoursewareAggregateResponse:
    items: list[CoursewareAggregateItem] = []

    # --- PPT Projects ---
    if source_type in (None, "all", "ppt"):
        if file_type in (None, "ppt"):
            stmt = select(PPTProject).where(PPTProject.user_id == user_id)
            result = await db.execute(stmt)
            for p in result.scalars().all():
                updated = p.updated_at or p.created_at
                if not _apply_date_filter(updated, date_range):
                    continue
                cover = await _get_cover_url(db, p.id)
                page_count = await _get_page_count(db, p.id)
                items.append(CoursewareAggregateItem(
                    id=f"ppt_{p.id}",
                    source_type="ppt",
                    name=p.title or p.outline_text or "未命名PPT",
                    file_type="ppt",
                    file_size=None,
                    status=p.status or "DRAFT",
                    cover_image=cover or None,
                    updated_at=updated,
                    source_id=p.id,
                    tags=None,
                    remark=None,
                    file_url=p.exported_file_url,
                    page_count=page_count,
                ))

    # --- Lesson Plans ---
    if source_type in (None, "all", "lesson_plan"):
        if file_type in (None, "word"):
            stmt = select(LessonPlan).where(LessonPlan.user_id == user_id)
            result = await db.execute(stmt)
            for lp in result.scalars().all():
                updated = lp.updated_at or lp.created_at
                if not _apply_date_filter(updated, date_range):
                    continue
                items.append(CoursewareAggregateItem(
                    id=f"lp_{lp.id}",
                    source_type="lesson_plan",
                    name=lp.title or "未命名教案",
                    file_type="word",
                    file_size=None,
                    status=lp.status or "draft",
                    cover_image=None,
                    updated_at=updated,
                    source_id=lp.id,
                    tags=None,
                    remark=None,
                    file_url=None,
                    page_count=None,
                ))

    # --- Uploaded Files (from courseware table) ---
    if source_type in (None, "all", "uploaded"):
        stmt = select(Courseware).where(Courseware.user_id == user_id)
        result = await db.execute(stmt)
        for c in result.scalars().all():
            # Skip courseware linked to PPT projects (those are AI-generated, shown via ppt_projects)
            if c.ppt_project_id is not None:
                continue
            c_file_type = c.file_type or "pdf"
            if file_type and c_file_type != file_type:
                continue
            updated = c.updated_at or c.created_at
            if not _apply_date_filter(updated, date_range):
                continue
            items.append(CoursewareAggregateItem(
                id=f"up_{c.id}",
                source_type="uploaded",
                name=c.title or c.file_name or "未命名文件",
                file_type=c_file_type,
                file_size=c.file_size,
                status=c.status,
                cover_image=None,
                updated_at=updated,
                source_id=c.id,
                tags=c.tags,
                remark=c.remark,
                file_url=c.file_url,
                page_count=None,
            ))

    # Sort all items by updated_at DESC
    items.sort(key=lambda x: x.updated_at, reverse=True)

    return CoursewareAggregateResponse(items=items, total=len(items))
