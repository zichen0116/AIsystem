"""
知识库路由
"""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import sqlalchemy as sa

from app.core.database import get_db
from app.core.auth import CurrentUser, AdminUser
from app.models.knowledge_library import KnowledgeLibrary
from app.models.knowledge_asset import KnowledgeAsset
from app.schemas.library import (
    KnowledgeLibraryCreate,
    KnowledgeLibraryUpdate,
    KnowledgeLibraryResponse,
    KnowledgeLibraryListResponse,
    TagRenameRequest,
    TagRenameResponse,
    AddToGraphRequest,
    AddToGraphResponse,
)

router = APIRouter(prefix="/libraries", tags=["知识库"])


def _library_to_response(library: KnowledgeLibrary, asset_count: int = 0) -> dict:
    """将 ORM 对象转换为响应 dict，附加 asset_count"""
    return {
        "id": library.id,
        "owner_id": library.owner_id,
        "name": library.name,
        "description": library.description,
        "is_system": library.is_system,
        "is_public": library.is_public,
        "tags": library.tags or [],
        "asset_count": asset_count,
        "created_at": library.created_at,
        "updated_at": library.updated_at,
    }


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
        tags=data.tags or [],
        is_system=is_system,
        is_public=is_public,
    )
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return _library_to_response(library, 0)


@router.get("", response_model=KnowledgeLibraryListResponse)
async def list_libraries(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Literal["all", "personal", "system"] = Query("all"),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    列出知识库。
    scope=all: 用户自己的库 + 所有公开系统库
    scope=personal: 当前用户自己创建的库
    scope=system: 所有公开的系统级库
    """
    base_conditions = [KnowledgeLibrary.is_deleted == False]

    if scope == "personal":
        base_conditions.append(KnowledgeLibrary.owner_id == current_user.id)
    elif scope == "system":
        base_conditions.append(KnowledgeLibrary.is_system == True)
        base_conditions.append(KnowledgeLibrary.is_public == True)
    else:  # all
        base_conditions.append(
            or_(
                KnowledgeLibrary.owner_id == current_user.id,
                (KnowledgeLibrary.is_system == True) & (KnowledgeLibrary.is_public == True)
            )
        )

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        base_conditions.append(
            or_(
                KnowledgeLibrary.name.ilike(search_pattern),
                KnowledgeLibrary.description.ilike(search_pattern),
            )
        )

    # Tag filter — use text LIKE as workaround for JSON (not JSONB) column
    if tag:
        base_conditions.append(
            func.cast(KnowledgeLibrary.tags, sa.Text).contains(f'"{tag}"')
        )

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeLibrary).where(*base_conditions)
    )
    total = count_result.scalar()

    # Query libraries
    result = await db.execute(
        select(KnowledgeLibrary).where(*base_conditions)
        .order_by(KnowledgeLibrary.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    libraries = result.scalars().all()

    # Batch load asset counts
    lib_ids = [lib.id for lib in libraries]
    asset_counts: dict[int, int] = {}
    if lib_ids:
        count_rows = await db.execute(
            select(
                KnowledgeAsset.library_id,
                func.count().label("cnt")
            )
            .where(KnowledgeAsset.library_id.in_(lib_ids))
            .group_by(KnowledgeAsset.library_id)
        )
        for row in count_rows:
            asset_counts[row.library_id] = row.cnt

    items = [
        _library_to_response(lib, asset_counts.get(lib.id, 0))
        for lib in libraries
    ]

    return KnowledgeLibraryListResponse(items=items, total=total)


@router.get("/tags")
async def get_user_tags(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取当前用户的标签池（所有库 tags 去重合集）"""
    result = await db.execute(
        select(KnowledgeLibrary.tags).where(
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    all_tags_lists = result.scalars().all()
    tag_set = set()
    for tags in all_tags_lists:
        if tags:
            tag_set.update(tags)
    return sorted(tag_set)


@router.patch("/tags/rename", response_model=TagRenameResponse)
async def rename_tag(
    data: TagRenameRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """全局重命名标签：遍历用户所有库，将 old_name 替换为 new_name"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    libraries = result.scalars().all()

    updated = 0
    for lib in libraries:
        tags = list(lib.tags or [])
        if data.old_name in tags:
            idx = tags.index(data.old_name)
            tags[idx] = data.new_name
            lib.tags = tags
            updated += 1

    await db.commit()
    return TagRenameResponse(updated_count=updated)


@router.patch("/{library_id}", response_model=KnowledgeLibraryResponse)
async def update_library(
    library_id: int,
    data: KnowledgeLibraryUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新知识库名称/描述/标签。is_public 仅管理员可修改。"""
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
    if data.tags is not None:
        library.tags = data.tags
    if data.is_public is not None:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可修改公开状态")
        library.is_public = data.is_public

    await db.commit()
    await db.refresh(library)

    # Get asset count
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeAsset).where(
            KnowledgeAsset.library_id == library_id
        )
    )
    asset_count = count_result.scalar()

    return _library_to_response(library, asset_count)


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

    library.is_deleted = True
    await db.commit()

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
    """将知识资产添加到知识图谱（仅管理员，仅系统知识库）。"""
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

    from app.tasks import build_graph_index
    task = build_graph_index.delay(library_id, data.asset_ids)

    return AddToGraphResponse(
        task_id=task.id,
        message=f"图索引构建任务已提交，共 {len(data.asset_ids)} 个资产",
    )
