"""
课件路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import CurrentUser
from app.models.courseware import Courseware
from app.models.enums import CoursewareStatus
from app.schemas.courseware import (
    CoursewareCreate,
    CoursewareUpdate,
    CoursewareResponse,
    CoursewareListResponse,
)

router = APIRouter(prefix="/courseware", tags=["课件"])


@router.post("", response_model=CoursewareResponse, status_code=status.HTTP_201_CREATED)
async def create_courseware(
    data: CoursewareCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """创建新课件"""
    courseware = Courseware(
        user_id=current_user.id,
        title=data.title,
        type=data.type,
        status=CoursewareStatus.PLANNING
    )
    db.add(courseware)
    await db.commit()
    await db.refresh(courseware)
    return courseware


@router.get("", response_model=CoursewareListResponse)
async def list_courseware(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: CoursewareStatus | None = Query(None, alias="status")
):
    """获取课件列表"""
    # 查询总数
    count_query = select(func.count()).select_from(Courseware).where(
        Courseware.user_id == current_user.id
    )
    if status_filter:
        count_query = count_query.where(Courseware.status == status_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询列表
    query = select(Courseware).where(
        Courseware.user_id == current_user.id
    ).order_by(Courseware.created_at.desc())

    if status_filter:
        query = query.where(Courseware.status == status_filter)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return CoursewareListResponse(items=items, total=total)


@router.get("/{courseware_id}", response_model=CoursewareResponse)
async def get_courseware(
    courseware_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取课件详情"""
    result = await db.execute(
        select(Courseware).where(
            Courseware.id == courseware_id,
            Courseware.user_id == current_user.id
        )
    )
    courseware = result.scalar_one_or_none()

    if not courseware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课件不存在"
        )

    return courseware


@router.patch("/{courseware_id}", response_model=CoursewareResponse)
async def update_courseware(
    courseware_id: int,
    data: CoursewareUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新课件"""
    result = await db.execute(
        select(Courseware).where(
            Courseware.id == courseware_id,
            Courseware.user_id == current_user.id
        )
    )
    courseware = result.scalar_one_or_none()

    if not courseware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课件不存在"
        )

    # 更新字段
    if data.title is not None:
        courseware.title = data.title
    if data.content_json is not None:
        courseware.content_json = data.content_json
    if data.status is not None:
        courseware.status = data.status
    if data.file_url is not None:
        courseware.file_url = data.file_url

    await db.commit()
    await db.refresh(courseware)
    return courseware


@router.delete("/{courseware_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_courseware(
    courseware_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """删除课件"""
    result = await db.execute(
        select(Courseware).where(
            Courseware.id == courseware_id,
            Courseware.user_id == current_user.id
        )
    )
    courseware = result.scalar_one_or_none()

    if not courseware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课件不存在"
        )

    await db.delete(courseware)
    await db.commit()
    return None
