"""
知识库路由
"""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import CurrentUser, AdminUser
from app.models.knowledge_library import KnowledgeLibrary
from app.schemas.library import (
    KnowledgeLibraryCreate,
    KnowledgeLibraryUpdate,
    KnowledgeLibraryResponse,
    KnowledgeLibraryListResponse,
    AddToGraphRequest,
    AddToGraphResponse,
)

router = APIRouter(prefix="/libraries", tags=["知识库"])


@router.post("", response_model=KnowledgeLibraryResponse, status_code=status.HTTP_201_CREATED)
async def create_library(
    data: KnowledgeLibraryCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """创建知识库。is_system/is_public 仅管理员可设置。"""
    is_system = False
    is_public = False
    if current_user.is_admin:
        is_system = data.is_system
        is_public = data.is_public

    library = KnowledgeLibrary(
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        is_system=is_system,
        is_public=is_public,
    )
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return library


@router.get("", response_model=KnowledgeLibraryListResponse)
async def list_libraries(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Literal["personal", "system"] = Query("personal"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    列出知识库。
    scope=personal: 当前用户自己创建的库
    scope=system: 所有公开的系统级库
    """
    if scope == "personal":
        conditions = [
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        ]
    else:  # system
        conditions = [
            KnowledgeLibrary.is_system == True,
            KnowledgeLibrary.is_public == True,
            KnowledgeLibrary.is_deleted == False,
        ]

    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeLibrary).where(*conditions)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(KnowledgeLibrary).where(*conditions)
        .order_by(KnowledgeLibrary.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return KnowledgeLibraryListResponse(items=items, total=total)


@router.patch("/{library_id}", response_model=KnowledgeLibraryResponse)
async def update_library(
    library_id: int,
    data: KnowledgeLibraryUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新知识库名称/描述。is_public 仅管理员可修改。"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

    if data.name is not None:
        library.name = data.name
    if data.description is not None:
        library.description = data.description
    if data.is_public is not None:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可修改公开状态")
        library.is_public = data.is_public

    await db.commit()
    await db.refresh(library)
    return library


@router.delete("/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(
    library_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """软删除知识库，Celery 异步清理向量和文件。"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

    # 软删除：立即对前端透明，后台异步清理
    library.is_deleted = True
    await db.commit()

    # 触发 Celery 异步清理（延迟导入避免循环依赖）
    from app.tasks import cleanup_library as cleanup_task
    cleanup_task.delay(library_id)

    return None


@router.post(
    "/{library_id}/add-to-graph",
    response_model=AddToGraphResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def add_to_graph(
    library_id: int,
    data: AddToGraphRequest,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    将知识资产添加到知识图谱（仅管理员，仅系统知识库）。
    异步执行，返回 Celery task_id。
    """
    # 校验知识库存在且为系统库
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.is_system == True,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系统知识库不存在",
        )

    # 推入 Celery 队列
    from app.tasks import build_graph_index
    task = build_graph_index.delay(library_id, data.asset_ids)

    return AddToGraphResponse(
        task_id=task.id,
        message=f"图索引构建任务已提交，共 {len(data.asset_ids)} 个资产",
    )
