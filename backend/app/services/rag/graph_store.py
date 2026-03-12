"""
LightRAG 图存储服务
薄封装 LightRAG，提供知识图谱的插入和检索能力。
每个系统知识库通过 LightRAG workspace 实现 Neo4j Label 隔离。
"""
import os
import logging
import asyncio
from pathlib import Path
from typing import Optional

import numpy as np
import httpx
from cachetools import LRUCache

from app.core.config import settings

logger = logging.getLogger(__name__)


# ==================== DashScope 适配函数 ====================

DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_EMBED_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"


async def dashscope_llm_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict] | None = None,
    keyword_extraction: bool = False,
    stream: bool = False,
    **kwargs,
) -> str:
    """
    DashScope LLM 适配函数（LightRAG 要求的签名）。
    通过 OpenAI 兼容接口调用。
    """
    if history_messages is None:
        history_messages = []

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                DASHSCOPE_CHAT_URL, headers=headers, json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DashScope LLM 调用失败: {e}")
        raise


async def dashscope_embed_func(texts: list[str]) -> np.ndarray:
    """
    DashScope Embedding 适配函数（LightRAG 要求的签名）。
    返回 np.ndarray shape=(len(texts), embedding_dim)。
    """
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": {"texts": texts},
    }

    # 多模态 embedding 模型使用不同的端点
    if settings.EMBEDDING_MODEL.startswith("tongyi-embedding-vision"):
        url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
        payload["input"] = {"contents": [{"text": t} for t in texts]}
    else:
        url = DASHSCOPE_EMBED_URL

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            embeddings = [
                item["embedding"] for item in result["output"]["embeddings"]
            ]
            return np.array(embeddings)
    except Exception as e:
        logger.error(f"DashScope Embedding 调用失败: {e}")
        raise


# 在模块加载时设置 Neo4j 环境变量（LightRAG Neo4JStorage 从 env 读取）
# 仅在已配置时设置，避免覆盖外部配置
if settings.NEO4J_URI:
    os.environ["NEO4J_URI"] = settings.NEO4J_URI
    os.environ["NEO4J_USERNAME"] = settings.NEO4J_USERNAME
    os.environ["NEO4J_PASSWORD"] = settings.NEO4J_PASSWORD


# ==================== GraphStore ====================


class GraphStore:
    """
    LightRAG 图存储封装。

    每个系统知识库对应一个 LightRAG 实例，通过 workspace 实现
    Neo4j Label 隔离。实例按 library_id 缓存。
    """

    _instances: LRUCache = LRUCache(maxsize=16)  # LRU 淘汰，防止内存无限增长
    _init_lock: asyncio.Lock = asyncio.Lock()  # 防止并发初始化同一 library_id

    @classmethod
    async def get_instance(cls, library_id: int):
        """获取指定知识库的 LightRAG 实例（首次访问时初始化）"""
        if library_id in cls._instances:
            return cls._instances[library_id]

        async with cls._init_lock:
            # double-check：另一协程可能在等锁期间已完成初始化
            if library_id in cls._instances:
                return cls._instances[library_id]

            from lightrag import LightRAG
            from lightrag.base import EmbeddingFunc

            workspace = f"library_{library_id}"
            working_dir = str(
                Path(settings.LIGHTRAG_WORKING_DIR) / workspace
            )
            Path(working_dir).mkdir(parents=True, exist_ok=True)

            embedding_func = EmbeddingFunc(
                # DashScope tongyi-embedding-vision-flash 输出 1024 维
                embedding_dim=1024,
                max_token_size=2048,
                func=dashscope_embed_func,
            )

        rag = LightRAG(
            working_dir=working_dir,
            workspace=workspace,
            graph_storage="Neo4JStorage",
            kv_storage="JsonKVStorage",
            vector_storage="NanoVectorDBStorage",
            llm_model_func=dashscope_llm_func,
            embedding_func=embedding_func,
            llm_model_name=settings.LLM_MODEL,
        )

        await rag.initialize_storages()
        cls._instances[library_id] = rag
        logger.info(f"LightRAG 实例初始化: workspace={workspace}")
        return rag

    @classmethod
    async def insert_documents(cls, library_id: int, texts: list[str]) -> str:
        """将文本插入到指定知识库的图谱中"""
        try:
            rag = await cls.get_instance(library_id)
            result = await rag.ainsert(texts)
            logger.info(
                f"图谱插入完成: library_id={library_id}, texts={len(texts)}"
            )
            return result
        except Exception as e:
            logger.error(f"图谱插入失败: library_id={library_id}, error={e}")
            raise

    @classmethod
    async def query(
        cls, library_id: int, query: str, mode: str = "hybrid"
    ) -> str:
        """从指定知识库的图谱中检索"""
        try:
            from lightrag import QueryParam

            rag = await cls.get_instance(library_id)
            result = await rag.aquery(query, param=QueryParam(mode=mode))
            logger.info(
                f"图谱检索完成: library_id={library_id}, mode={mode}"
            )
            return result
        except Exception as e:
            logger.error(f"图谱检索失败: library_id={library_id}, error={e}")
            return f"知识图谱检索失败: {str(e)}"

    @classmethod
    async def delete_library(cls, library_id: int):
        """清理指定知识库的图谱数据"""
        try:
            rag = await cls.get_instance(library_id)
            # LightRAG 的 drop 方法会删除 workspace 下所有 Neo4j 节点
            if hasattr(rag, "chunk_storage"):
                await rag.chunk_storage.drop()
            if hasattr(rag, "entity_storage"):
                await rag.entity_storage.drop()
            if hasattr(rag, "relationship_storage"):
                await rag.relationship_storage.drop()
            if hasattr(rag, "chunk_entity_relation_storage"):
                await rag.chunk_entity_relation_storage.drop()

            # 从缓存中移除
            cls._instances.pop(library_id, None)
            logger.info(f"图谱清理完成: library_id={library_id}")
        except Exception as e:
            logger.error(f"图谱清理失败: library_id={library_id}, error={e}")
            raise
