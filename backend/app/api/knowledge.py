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


# ── Mock 知识图谱数据 ──────────────────────────────────────────────
@router.get("/graph")
async def get_knowledge_graph(
    current_user: CurrentUser,
    library_id: str | None = None,
    limit: int = 50,
):
    """返回知识图谱 mock 数据（宋代词人关系网络）"""
    poets = [
        {"id": "1", "name": "苏轼", "category": "豪放派"},
        {"id": "2", "name": "辛弃疾", "category": "豪放派"},
        {"id": "3", "name": "李清照", "category": "婉约派"},
        {"id": "4", "name": "柳永", "category": "婉约派"},
        {"id": "5", "name": "秦观", "category": "婉约派"},
        {"id": "6", "name": "欧阳修", "category": "文学领袖"},
        {"id": "7", "name": "王安石", "category": "文学领袖"},
        {"id": "8", "name": "黄庭坚", "category": "江西诗派"},
        {"id": "9", "name": "晏殊", "category": "婉约派"},
        {"id": "10", "name": "晏几道", "category": "婉约派"},
        {"id": "11", "name": "周邦彦", "category": "格律派"},
        {"id": "12", "name": "姜夔", "category": "格律派"},
        {"id": "13", "name": "吴文英", "category": "格律派"},
        {"id": "14", "name": "陆游", "category": "豪放派"},
        {"id": "15", "name": "范仲淹", "category": "文学领袖"},
        {"id": "16", "name": "司马光", "category": "文学领袖"},
        {"id": "17", "name": "梅尧臣", "category": "江西诗派"},
        {"id": "18", "name": "苏辙", "category": "豪放派"},
        {"id": "19", "name": "苏洵", "category": "文学领袖"},
        {"id": "20", "name": "曾巩", "category": "文学领袖"},
        {"id": "21", "name": "张先", "category": "婉约派"},
        {"id": "22", "name": "贺铸", "category": "婉约派"},
        {"id": "23", "name": "张元干", "category": "豪放派"},
        {"id": "24", "name": "张孝祥", "category": "豪放派"},
        {"id": "25", "name": "陈亮", "category": "豪放派"},
        {"id": "26", "name": "刘克庄", "category": "豪放派"},
        {"id": "27", "name": "史达祖", "category": "格律派"},
        {"id": "28", "name": "王沂孙", "category": "格律派"},
        {"id": "29", "name": "周密", "category": "格律派"},
        {"id": "30", "name": "蒋捷", "category": "格律派"},
        {"id": "31", "name": "文天祥", "category": "豪放派"},
        {"id": "32", "name": "岳飞", "category": "豪放派"},
        {"id": "33", "name": "李煜", "category": "南唐遗韵"},
        {"id": "34", "name": "温庭筠", "category": "南唐遗韵"},
        {"id": "35", "name": "韦庄", "category": "南唐遗韵"},
        {"id": "36", "name": "冯延巳", "category": "南唐遗韵"},
        {"id": "37", "name": "朱敦儒", "category": "婉约派"},
        {"id": "38", "name": "李之仪", "category": "婉约派"},
        {"id": "39", "name": "陈与义", "category": "江西诗派"},
        {"id": "40", "name": "吕本中", "category": "江西诗派"},
        {"id": "41", "name": "郭祥正", "category": "江西诗派"},
        {"id": "42", "name": "范成大", "category": "田园诗派"},
        {"id": "43", "name": "杨万里", "category": "田园诗派"},
        {"id": "44", "name": "刘辰翁", "category": "格律派"},
        {"id": "45", "name": "张炎", "category": "格律派"},
        {"id": "46", "name": "刘过", "category": "豪放派"},
        {"id": "47", "name": "戴复古", "category": "豪放派"},
        {"id": "48", "name": "叶梦得", "category": "豪放派"},
        {"id": "49", "name": "赵佶", "category": "南唐遗韵"},
        {"id": "50", "name": "林逋", "category": "隐逸派"},
    ]

    links = [
        # 苏轼的核心关系网
        {"source": "1", "target": "6", "relation": "受知于"},
        {"source": "1", "target": "7", "relation": "政治对立"},
        {"source": "1", "target": "8", "relation": "师生"},
        {"source": "1", "target": "5", "relation": "师生"},
        {"source": "1", "target": "18", "relation": "兄弟"},
        {"source": "1", "target": "19", "relation": "父子"},
        {"source": "1", "target": "16", "relation": "政治同僚"},
        {"source": "1", "target": "17", "relation": "文学交游"},
        {"source": "1", "target": "9", "relation": "文学传承"},
        {"source": "1", "target": "14", "relation": "风格相近"},
        {"source": "1", "target": "2", "relation": "词风继承"},
        {"source": "1", "target": "41", "relation": "文学交游"},
        # 辛弃疾关系网
        {"source": "2", "target": "25", "relation": "政治同盟"},
        {"source": "2", "target": "14", "relation": "风格相近"},
        {"source": "2", "target": "24", "relation": "词风相近"},
        {"source": "2", "target": "23", "relation": "词风相近"},
        {"source": "2", "target": "26", "relation": "师生"},
        {"source": "2", "target": "46", "relation": "交游"},
        {"source": "2", "target": "32", "relation": "精神继承"},
        # 婉约派关系
        {"source": "3", "target": "4", "relation": "同派"},
        {"source": "3", "target": "5", "relation": "同派"},
        {"source": "3", "target": "9", "relation": "词风传承"},
        {"source": "3", "target": "10", "relation": "词风相近"},
        {"source": "3", "target": "11", "relation": "词风影响"},
        {"source": "4", "target": "11", "relation": "词法影响"},
        {"source": "4", "target": "5", "relation": "同期"},
        {"source": "4", "target": "21", "relation": "词风相近"},
        {"source": "5", "target": "9", "relation": "受知于"},
        {"source": "5", "target": "22", "relation": "同期"},
        # 文学领袖关系
        {"source": "6", "target": "7", "relation": "政治对立"},
        {"source": "6", "target": "9", "relation": "文学交游"},
        {"source": "6", "target": "17", "relation": "诗文革新"},
        {"source": "6", "target": "20", "relation": "师生"},
        {"source": "6", "target": "15", "relation": "政治同僚"},
        {"source": "7", "target": "16", "relation": "政治对立"},
        {"source": "7", "target": "20", "relation": "文学交游"},
        # 格律派关系
        {"source": "11", "target": "12", "relation": "词法传承"},
        {"source": "11", "target": "13", "relation": "词法传承"},
        {"source": "12", "target": "13", "relation": "同派"},
        {"source": "12", "target": "27", "relation": "词风影响"},
        {"source": "12", "target": "28", "relation": "词风影响"},
        {"source": "12", "target": "29", "relation": "交游"},
        {"source": "12", "target": "45", "relation": "词法传承"},
        {"source": "13", "target": "27", "relation": "同派"},
        {"source": "13", "target": "44", "relation": "词风影响"},
        {"source": "28", "target": "29", "relation": "交游"},
        {"source": "29", "target": "30", "relation": "同期"},
        {"source": "45", "target": "30", "relation": "同期"},
        # 晏氏父子
        {"source": "9", "target": "10", "relation": "父子"},
        {"source": "9", "target": "6", "relation": "政治同僚"},
        # 江西诗派
        {"source": "8", "target": "39", "relation": "同派"},
        {"source": "8", "target": "40", "relation": "诗派传承"},
        {"source": "8", "target": "41", "relation": "同派"},
        {"source": "39", "target": "40", "relation": "同派"},
        # 南唐遗韵
        {"source": "33", "target": "34", "relation": "词风影响"},
        {"source": "33", "target": "35", "relation": "同期"},
        {"source": "33", "target": "36", "relation": "同期"},
        {"source": "34", "target": "35", "relation": "同期"},
        # 田园诗派
        {"source": "42", "target": "43", "relation": "同期同派"},
        {"source": "42", "target": "14", "relation": "交游"},
        # 豪放派补充
        {"source": "14", "target": "15", "relation": "精神继承"},
        {"source": "31", "target": "32", "relation": "精神相通"},
        {"source": "31", "target": "2", "relation": "精神传承"},
        {"source": "23", "target": "48", "relation": "同期"},
        {"source": "26", "target": "47", "relation": "同期"},
        # 隐逸派
        {"source": "50", "target": "17", "relation": "文学交游"},
        {"source": "50", "target": "6", "relation": "受知于"},
        # 跨派交流
        {"source": "37", "target": "3", "relation": "同期"},
        {"source": "38", "target": "1", "relation": "文学交游"},
        {"source": "49", "target": "11", "relation": "赏识"},
    ]

    selected_poets = poets[:limit]
    node_ids = {p["id"] for p in selected_poets}
    filtered_links = [
        link for link in links
        if link["source"] in node_ids and link["target"] in node_ids
    ]

    link_count: dict[str, int] = {}
    for link in filtered_links:
        link_count[link["source"]] = link_count.get(link["source"], 0) + 1
        link_count[link["target"]] = link_count.get(link["target"], 0) + 1

    nodes = [
        {**p, "val": link_count.get(p["id"], 1)}
        for p in selected_poets
    ]

    return {"nodes": nodes, "links": filtered_links}


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
