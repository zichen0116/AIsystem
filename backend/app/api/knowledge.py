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
    limit: int = Query(100, ge=1, le=300),
):
    """返回唐宋元明清诗人 mock 图谱数据（总计 100 节点）"""
    poets_by_dynasty = {
        "唐": [
            "李白", "杜甫", "白居易", "王维", "孟浩然", "李商隐", "杜牧", "王昌龄", "岑参", "高适",
            "韩愈", "柳宗元", "刘禹锡", "元稹", "王勃", "骆宾王", "陈子昂", "贺知章", "张九龄", "李贺",
        ],
        "宋": [
            "苏轼", "辛弃疾", "李清照", "柳永", "秦观", "欧阳修", "王安石", "黄庭坚", "晏殊", "晏几道",
            "周邦彦", "姜夔", "吴文英", "陆游", "范仲淹", "司马光", "梅尧臣", "苏辙", "苏洵", "曾巩",
        ],
        "元": [
            "元好问", "马致远", "白朴", "关汉卿", "郑光祖", "乔吉", "张可久", "虞集", "揭傒斯", "杨载",
            "范梈", "萨都剌", "王冕", "赵孟頫", "倪瓒", "顾瑛", "张养浩", "睢景臣", "张鸣善", "鲜于枢",
        ],
        "明": [
            "高启", "杨慎", "于谦", "唐寅", "文征明", "祝允明", "李梦阳", "何景明", "徐祯卿", "王世贞",
            "李攀龙", "袁宏道", "袁中道", "袁宗道", "归有光", "汤显祖", "戚继光", "刘基", "陈子龙", "杨基",
        ],
        "清": [
            "纳兰性德", "龚自珍", "黄景仁", "袁枚", "郑燮", "王士祯", "查慎行", "纪昀", "赵翼", "蒋士铨",
            "吴伟业", "钱谦益", "陈维崧", "朱彝尊", "厉鹗", "张问陶", "林则徐", "秋瑾", "谭嗣同", "黄遵宪",
        ],
    }

    poets = []
    dynasty_ids: dict[str, list[str]] = {}
    name_to_id: dict[str, str] = {}
    next_id = 1

    for dynasty in ["唐", "宋", "元", "明", "清"]:
        ids = []
        for poet_name in poets_by_dynasty[dynasty]:
            node_id = str(next_id)
            next_id += 1
            poets.append({
                "id": node_id,
                "name": poet_name,
                "category": f"{dynasty}代",
            })
            ids.append(node_id)
            name_to_id[poet_name] = node_id
        dynasty_ids[dynasty] = ids

    links = []
    edge_seen = set()

    def add_link(a: str, b: str, relation: str):
        if a == b:
            return
        key = (a, b) if a < b else (b, a)
        if key in edge_seen:
            return
        edge_seen.add(key)
        links.append({"source": a, "target": b, "relation": relation})

    # 每个朝代内部：中心辐射 + 相邻连接 + 次邻连接
    for dynasty, ids in dynasty_ids.items():
        hub = ids[0]
        for i, node_id in enumerate(ids):
            if i > 0:
                add_link(hub, node_id, "同代诗坛")
            if i + 1 < len(ids):
                add_link(node_id, ids[i + 1], "同代唱和")
            if i + 2 < len(ids):
                add_link(node_id, ids[i + 2], "风格影响")

    # 朝代之间的传承主链
    dynasty_order = ["唐", "宋", "元", "明", "清"]
    for i in range(len(dynasty_order) - 1):
        src_dynasty = dynasty_order[i]
        tgt_dynasty = dynasty_order[i + 1]
        src_ids = dynasty_ids[src_dynasty]
        tgt_ids = dynasty_ids[tgt_dynasty]
        add_link(src_ids[0], tgt_ids[0], "诗学传承")
        for idx in [2, 6, 10, 14, 18]:
            add_link(src_ids[idx], tgt_ids[idx], "跨代影响")

    # 一组明确的跨代名家关系
    explicit_relations = [
        ("李白", "苏轼", "豪放源流"),
        ("杜甫", "黄庭坚", "江西诗派渊源"),
        ("白居易", "袁枚", "性灵诗风"),
        ("王维", "倪瓒", "诗画同源"),
        ("韩愈", "欧阳修", "古文传统"),
        ("柳宗元", "归有光", "散文传承"),
        ("苏轼", "元好问", "诗文兼擅"),
        ("辛弃疾", "陈子龙", "家国词风"),
        ("李清照", "纳兰性德", "婉约传响"),
        ("陆游", "龚自珍", "爱国诗脉"),
    ]
    for src_name, tgt_name, relation in explicit_relations:
        add_link(name_to_id[src_name], name_to_id[tgt_name], relation)

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

