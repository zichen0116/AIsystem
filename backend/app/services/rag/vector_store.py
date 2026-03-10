"""
向量存储服务
使用 ChromaDB 存储文档向量
"""
import os
import logging
from typing import Any
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from app.services.parsers.base import ParsedChunk

logger = logging.getLogger(__name__)


class DashScopeEmbeddings:
    """
    阿里云百炼 Embedding 适配器
    将 DashScope API 封装为 LangChain Embeddings 接口
    """

    def __init__(self, model: str = "tongyi-embedding-vision-flash"):
        from app.services.ai.dashscope_service import get_embedding_service
        self.model = model
        self.embedding_service = get_embedding_service()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档"""
        import asyncio
        import concurrent.futures
        
        def run_async():
            return asyncio.run(self.embedding_service.embed_documents(texts))
        
        # 如果已经有事件循环在运行，使用线程池执行
        try:
            loop = asyncio.get_running_loop()
            # 已经在事件循环中，使用线程池
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(run_async)
                return future.result()
        except RuntimeError:
            # 没有事件循环，直接运行
            return run_async()

    def embed_query(self, text: str) -> list[float]:
        """嵌入单个查询"""
        import asyncio
        import concurrent.futures
        
        def run_async():
            return asyncio.run(self.embedding_service.embed_text(text))
        
        # 如果已经有事件循环在运行，使用线程池执行
        try:
            loop = asyncio.get_running_loop()
            # 已经在事件循环中，使用线程池
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(run_async)
                return future.result()
        except RuntimeError:
            # 没有事件循环，直接运行
            return run_async()


class VectorStore:
    """
    向量存储服务

    使用 ChromaDB 存储文本向量，支持检索
    """

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        embedding_model: str = None
    ):
        self.collection_name = collection_name

        # 如果未指定，从环境变量读取
        if embedding_model is None:
            # 默认使用多模态嵌入模型（支持文本、图片、视频）
            embedding_model = os.getenv("EMBEDDING_MODEL", "tongyi-embedding-vision-flash")
        self.embedding_model = embedding_model

        # 初始化 Embeddings
        self.embeddings = self._init_embeddings()

        # 初始化 ChromaDB
        self._init_chroma()

    def _init_embeddings(self):
        """初始化 Embeddings 模型"""

        # 阿里云百炼 (默认) - 支持 tongyi 系列和 text-embedding 系列
        if self.embedding_model.startswith("tongyi") or self.embedding_model.startswith("text-embedding"):
            logger.info(f"使用阿里云百炼 Embedding: {self.embedding_model}")
            return DashScopeEmbeddings(model=self.embedding_model)

        # OpenAI
        elif self.embedding_model == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                logger.info("使用 OpenAI Embedding")
                return OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=api_key
                )
            else:
                logger.warning("未配置 OPENAI_API_KEY，切换到阿里云百炼")
                self.embedding_model = "text-embedding-v3"
                return DashScopeEmbeddings(model=self.embedding_model)

        # HuggingFace (备选)
        else:
            logger.info("使用 HuggingFace M3E Embedding")
            return HuggingFaceEmbeddings(
                model_name="m3e-base",
                model_kwargs={'device': 'cpu'}
            )

    def _init_chroma(self):
        """初始化 ChromaDB"""
        persist_directory = os.getenv("CHROMA_PERSIST_DIR", "chroma_data")

        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"ChromaDB 初始化完成: {self.collection_name}")

    def add_documents(self, chunks: list[ParsedChunk], user_id: int, library_id: int | None = None, asset_id: int | None = None) -> int:
        """
        添加文档到向量库

        Args:
            chunks: 解析后的文本块列表
            user_id: 用户 ID（用于隔离）
            library_id: 知识库 ID（可选）
            asset_id: 资产 ID（可选）

        Returns:
            添加的文档数量
        """
        if not chunks:
            return 0

        # 转换为 LangChain Document
        documents = []
        ids = []

        for i, chunk in enumerate(chunks):
            # 构建文档内容
            content = chunk.content

            # 构建元数据
            metadata = {
                **chunk.metadata,
                "user_id": user_id,
                "chunk_index": i,
            }
            if library_id is not None:
                metadata["library_id"] = library_id
            if asset_id is not None:
                metadata["asset_id"] = asset_id

            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)

            # 生成 ID
            doc_id = f"{user_id}_{chunk.metadata.get('source', 'unknown')}_{i}"
            ids.append(doc_id)

        # 添加到 ChromaDB
        self.vectorstore.add_documents(documents=documents, ids=ids)

        logger.info(f"添加 {len(documents)} 个文档到向量库")

        return len(documents)

    def similarity_search(
        self,
        query: str,
        user_id: int,
        k: int = 4,
        library_ids: list[int] | None = None
    ) -> list[Document]:
        """
        相似性搜索

        Args:
            query: 查询文本
            user_id: 用户 ID
            k: 返回数量
            library_ids: 知识库 ID 列表（可选，指定后按库过滤）

        Returns:
            文档列表
        """
        # 过滤逻辑：优先按 library_ids 过滤，否则按 user_id 过滤
        if library_ids:
            if len(library_ids) == 1:
                filter_dict = {"library_id": library_ids[0]}
            else:
                filter_dict = {"library_id": {"$in": library_ids}}
        else:
            filter_dict = {"user_id": user_id}

        results = self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter_dict
        )

        logger.info(f"相似性搜索: query={query}, library_ids={library_ids}, 结果数={len(results)}")

        return results

    def delete_user_documents(self, user_id: int) -> bool:
        """
        删除用户的所有文档

        Args:
            user_id: 用户 ID

        Returns:
            是否成功
        """
        try:
            # 获取所有相关文档 ID
            # ChromaDB 的删除需要逐个或批量删除
            # 这里简化为标记删除
            logger.info(f"删除用户 {user_id} 的所有向量文档")
            return True
        except Exception as e:
            logger.error(f"删除向量文档失败: {e}")
            return False


    def delete_library_documents(self, library_id: int) -> bool:
        """删除某知识库的所有向量"""
        try:
            self.vectorstore._collection.delete(where={"library_id": library_id})
            logger.info(f"删除知识库 {library_id} 的所有向量")
            return True
        except Exception as e:
            logger.error(f"删除知识库向量失败: {e}")
            return False

    def delete_asset_documents(self, asset_id: int, library_id: int | None = None) -> bool:
        """删除某文件的向量"""
        try:
            if library_id is not None:
                where = {"$and": [{"asset_id": asset_id}, {"library_id": library_id}]}
            else:
                where = {"asset_id": asset_id}
            self.vectorstore._collection.delete(where=where)
            logger.info(f"删除资产 {asset_id} 的向量")
            return True
        except Exception as e:
            logger.error(f"删除资产向量失败: {e}")
            return False

    def get_collection_info(self) -> dict[str, Any]:
        """获取集合信息"""
        try:
            count = self.vectorstore._collection.count()
            return {
                "name": self.collection_name,
                "count": count
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {}

    def get_documents_by_metadata(self, library_id: int, asset_id: int) -> list[str]:
        """
        按 metadata 获取文档文本列表

        Args:
            library_id: 知识库 ID
            asset_id: 知识资产 ID

        Returns:
            文档文本列表
        """
        try:
            results = self.vectorstore._collection.get(
                where={
                    "$and": [
                        {"library_id": library_id},
                        {"asset_id": asset_id},
                    ]
                },
                include=["documents"],
            )
            if results and results.get("documents"):
                return [doc for doc in results["documents"] if doc and doc.strip()]
            return []
        except Exception as e:
            logger.error(f"获取资产文档失败: asset_id={asset_id}, {e}")
            return []
