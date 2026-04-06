"""
课件路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import CurrentUser
from app.models.courseware import Courseware
from app.models.enums import CoursewareStatus
from app.models.lesson_plan import LessonPlan
from app.schemas.courseware import (
    CoursewareCreate,
    CoursewareUpdate,
    CoursewareResponse,
    CoursewareListResponse,
    CoursewareAggregateResponse,
    CoursewareAggregateItem,
)
from app.services.courseware_service import get_aggregated_courseware
from app.services.oss_service import upload_file as oss_upload, delete_file as oss_delete
from app.generators.ppt.banana_models import PPTProject

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


@router.get("/all", response_model=CoursewareAggregateResponse)
async def list_all_courseware(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    source_type: str | None = None,
    file_type: str | None = None,
    date_range: str | None = None,
):
    """聚合列出用户所有课件：PPT项目 + 教案 + 上传文件"""
    return await get_aggregated_courseware(
        db, current_user.id, source_type, file_type, date_range
    )


@router.post("/upload", status_code=201)
async def upload_courseware(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    remark: str | None = Form(None),
):
    """上传课件文件到OSS并创建记录"""
    ALLOWED_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".mp4"}
    MAX_SIZE = 50 * 1024 * 1024  # 50MB

    # Validate file extension
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型，仅允许: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read file size BEFORE oss_upload (which consumes the stream)
    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_SIZE:
        raise HTTPException(413, "文件过大，最大允许 50MB")
    await file.seek(0)

    oss_result = await oss_upload(file, current_user.id)

    file_type_val = oss_result.get("file_type", "pdf")
    original_name = oss_result.get("file_name", file.filename or "未命名文件")
    display_title = title or original_name.rsplit(".", 1)[0]

    courseware = Courseware(
        user_id=current_user.id,
        title=display_title,
        type="UPLOADED",
        status="COMPLETED",
        file_url=oss_result["url"],
        file_name=original_name,
        file_size=file_size,
        file_type=file_type_val,
        tags=tags,
        remark=remark,
    )
    db.add(courseware)
    await db.commit()
    await db.refresh(courseware)

    return CoursewareAggregateItem(
        id=f"up_{courseware.id}",
        source_type="uploaded",
        name=courseware.title,
        file_type=courseware.file_type or "pdf",
        file_size=courseware.file_size,
        status=courseware.status,
        cover_image=None,
        updated_at=courseware.updated_at or courseware.created_at,
        source_id=courseware.id,
        tags=courseware.tags,
        remark=courseware.remark,
        file_url=courseware.file_url,
        page_count=None,
    )


@router.get("/download")
async def download_courseware(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    source_type: str = Query(...),
    source_id: int = Query(...),
):
    """统一下载入口"""
    if source_type == "uploaded":
        stmt = select(Courseware).where(
            Courseware.id == source_id, Courseware.user_id == current_user.id
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item or not item.file_url:
            raise HTTPException(404, "文件不存在")
        return RedirectResponse(url=item.file_url)

    elif source_type == "ppt":
        stmt = select(PPTProject).where(
            PPTProject.id == source_id, PPTProject.user_id == current_user.id
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(404, "PPT项目不存在")
        if project.exported_file_url:
            return RedirectResponse(url=project.exported_file_url)
        raise HTTPException(400, "该PPT尚未导出，请先在备课页面导出")

    elif source_type == "lesson_plan":
        stmt = select(LessonPlan).where(
            LessonPlan.id == source_id, LessonPlan.user_id == current_user.id
        )
        result = await db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            raise HTTPException(404, "教案不存在")
        from app.api.lesson_plan import _export_docx_from_content
        return _export_docx_from_content(plan.title or "教案", plan.content or "")

    raise HTTPException(400, "无效的 source_type")


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

    # 更新字段（使用 exclude_unset 以区分「未传」和「传了 null」）
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(courseware, field, value)

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

    if courseware.file_url:
        try:
            oss_delete(courseware.file_url)
        except Exception:
            pass  # OSS cleanup is best-effort

    await db.delete(courseware)
    await db.commit()
    return None
