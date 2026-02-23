"""
知识资产路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.core.database import get_db
from app.core.auth import CurrentUser
from app.models.knowledge_asset import KnowledgeAsset
from app.schemas.knowledge import (
    KnowledgeAssetCreate,
    KnowledgeAssetUpdate,
    KnowledgeAssetResponse,
    KnowledgeAssetListResponse,
)

router = APIRouter(prefix="/knowledge", tags=["知识资产"])


@router.post("", response_model=KnowledgeAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_asset(
    data: KnowledgeAssetCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """上传知识资产"""
    asset = KnowledgeAsset(
        user_id=current_user.id,
        file_name=data.file_name,
        file_type=data.file_type,
        file_path=data.file_path,
        vector_status=False
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("", response_model=KnowledgeAssetListResponse)
async def list_knowledge_assets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """获取知识资产列表"""
    # 查询总数
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeAsset).where(
            KnowledgeAsset.user_id == current_user.id
        )
    )
    total = count_result.scalar()

    # 查询列表
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.user_id == current_user.id
        ).order_by(KnowledgeAsset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return KnowledgeAssetListResponse(items=items, total=total)


@router.get("/{asset_id}", response_model=KnowledgeAssetResponse)
async def get_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取知识资产详情"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识资产不存在"
        )

    return asset


@router.patch("/{asset_id}", response_model=KnowledgeAssetResponse)
async def update_knowledge_asset(
    asset_id: int,
    data: KnowledgeAssetUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新知识资产"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识资产不存在"
        )

    if data.vector_status is not None:
        asset.vector_status = data.vector_status

    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """删除知识资产"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识资产不存在"
        )

    await db.delete(asset)
    await db.commit()
    return None
