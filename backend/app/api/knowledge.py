"""
知识资产路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import CurrentUser
from app.models.knowledge_asset import KnowledgeAsset
from app.models.knowledge_library import KnowledgeLibrary
from app.schemas.knowledge import (
    KnowledgeAssetCreate,
    KnowledgeAssetResponse,
    KnowledgeAssetStatusResponse,
    KnowledgeAssetListResponse,
)

router = APIRouter(prefix="/knowledge", tags=["知识资产"])


async def _get_owned_library(library_id: int, user_id: int, db: AsyncSession) -> KnowledgeLibrary:
    """校验用户拥有该知识库"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.owner_id == user_id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在或无权限")
    return library


@router.post("", response_model=KnowledgeAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_asset(
    data: KnowledgeAssetCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """上传知识资产，立即返回，Celery 后台向量化。"""
    await _get_owned_library(data.library_id, current_user.id, db)

    asset = KnowledgeAsset(
        user_id=current_user.id,
        library_id=data.library_id,
        file_name=data.file_name,
        file_type=data.file_type,
        file_path=data.file_path,
        vector_status="pending"
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    # 触发 Celery 后台任务
    from app.tasks import process_knowledge_asset
    process_knowledge_asset.delay(asset.id, current_user.id, data.library_id)

    return asset


@router.get("", response_model=KnowledgeAssetListResponse)
async def list_knowledge_assets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    library_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """列出知识资产，可按知识库过滤。"""
    conditions = [KnowledgeAsset.user_id == current_user.id]
    if library_id is not None:
        conditions.append(KnowledgeAsset.library_id == library_id)

    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeAsset).where(*conditions)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(KnowledgeAsset).where(*conditions)
        .order_by(KnowledgeAsset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return KnowledgeAssetListResponse(items=items, total=total)


@router.get("/{asset_id}/status", response_model=KnowledgeAssetStatusResponse)
async def get_asset_status(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """轻量状态查询，前端轮询用。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")
    return asset


@router.get("/{asset_id}", response_model=KnowledgeAssetResponse)
async def get_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取知识资产详情。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """删除知识资产及其 ChromaDB 向量。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")

    # 删除 ChromaDB 中该文件的向量
    try:
        from app.services.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_asset_documents(asset_id=asset_id, library_id=asset.library_id)
    except Exception:
        pass  # 向量删除失败不阻断 DB 删除

    await db.delete(asset)
    await db.commit()
    return None
