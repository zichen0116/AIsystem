"""
混合检索服务 (Hybrid RAG)
结合向量检索 (Semantic) 和 BM25 (Keyword) （又融合了jieba分词，对中文支持更好）实现混合搜索
"""
import os
import logging
from typing import Any, Optional
import numpy as np

from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class BM25Index:
    """
    BM25 索引管理器
    为每个用户的文档建立 BM25 索引
    """
    
    def __init__(self):
        # 存储每个用户的 BM25 索引
        # 结构: {user_id: {"bm25": BM25Okapi, "doc_ids": list, "docs": list}}
        # key = library_id
        self._indices: dict[int, dict] = {}
    
    def build_index(self, library_id: int, documents: list[Document]):
        """
        为用户构建 BM25 索引
        
        Args:
            user_id: 用户 ID
            documents: 文档列表
        """
        if not documents:
            return
        
        # Tokenize 文档（中文使用 jieba，英文使用空格分词）
        tokenized_docs = []
        doc_ids = []
        
        for doc in documents:
            # 获取文档内容
            content = doc.page_content
            # 分词
            tokens = self._tokenize(content)
            tokenized_docs.append(tokens)
            # 保存文档 ID
            doc_ids.append(doc.metadata.get("doc_id", str(doc.metadata)))
        
        # 构建 BM25 索引
        bm25 = BM25Okapi(tokenized_docs)
        
        self._indices[library_id] = {
            "bm25": bm25,
            "doc_ids": doc_ids,
            "documents": documents
        }
        
        logger.info(f"为用户 {user_id} 构建 BM25 索引，包含 {len(documents)} 个文档")
    
    def search(self, library_id: int, query: str, top_k: int = 10) -> list[tuple[Document, float]]:
        """
        BM25 搜索
        
        Args:
            user_id: 用户 ID
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            [(文档, BM25分数), ...]
        """
        if library_id not in self._indices:
            logger.warning(f"用户 {user_id} 没有 BM25 索引")
            return []
        
        # Tokenize 查询
        query_tokens = self._tokenize(query)
        
        # 获取 BM25 分数
        index_data = self._indices[library_id]
        bm25 = index_data["bm25"]
        doc_ids = index_data["doc_ids"]
        documents = index_data["documents"]
        
        scores = bm25.get_scores(query_tokens)
        
        # 获取 top_k 结果
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((documents[idx], float(scores[idx])))
        
        return results
    
    def _tokenize(self, text: str) -> list[str]:
        """
        分词
        尝试使用 jieba（中文），否则使用空格分词
        
        Args:
            text: 待分词文本
            
        Returns:
            词列表
        """
        try:
            import jieba
            # 中文分词
            tokens = list(jieba.cut(text))
            # 过滤空字符串和单字符
            tokens = [t.strip() for t in tokens if len(t.strip()) > 1]
            return tokens
        except ImportError:
            # 英文/默认：转小写，按空格和标点分词
            import re
            text = text.lower()
            # 使用正则分词（保留英文和数字）
            tokens = re.findall(r'\w+', text)
            # 过滤太短的词
            tokens = [t for t in tokens if len(t) > 1]
            return tokens
    
    def clear_library_index(self, library_id: int):
        """清除用户的 BM25 索引"""
        if library_id in self._indices:
            del self._indices[library_id]
            logger.info(f"清除用户 {user_id} 的 BM25 索引")


class HybridRetriever:
    """
    混合检索器
    
    结合向量检索 (Semantic) 和 BM25 (Keyword) 实现混合搜索
    支持两种融合策略：
    1. RRF (Reciprocal Rank Fusion) - 倒数排名融合
    2. 加权融合 (Weighted Fusion)
    """
    
    def __init__(
        self,
        vector_store: Any,
        bm25_weight: float = 0.5,
        fusion_method: str = "rrf"
    ):
        """
        初始化混合检索器
        
        Args:
            vector_store: 向量存储实例 (VectorStore)
            bm25_weight: BM25 权重 (0-1)，向量权重 = 1 - bm25_weight
            fusion_method: 融合方法 ("rrf" 或 "weighted")
        """
        self.vector_store = vector_store
        self.bm25_weight = bm25_weight
        self.fusion_method = fusion_method
        
        # BM25 索引
        self.bm25_index = BM25Index()
        
        # 缓存的用户文档
        self._user_docs: dict[int, list[Document]] = {}

        # Reranker
        from app.core.config import settings
        from app.services.rag.reranker import DashScopeReranker
        if settings.DASHSCOPE_API_KEY:
            self.reranker = DashScopeReranker(
                api_key=settings.DASHSCOPE_API_KEY,
                model=settings.RERANK_MODEL,
            )
        else:
            self.reranker = None
            logger.warning("未配置 DASHSCOPE_API_KEY，Rerank 功能不可用")

    def build_bm25_index(self, library_id: int, documents: list[Document]):
        """
        为用户构建 BM25 索引
        
        Args:
            user_id: 用户 ID
            documents: 文档列表
        """
        # 缓存文档
        self._user_docs[library_id] = documents
        
        # 构建 BM25 索引
        self.bm25_index.build_index(library_id, documents)
    
    async def search(
        self,
        query: str,
        user_id: int,
        k: int = 10,
        library_ids: list[int] | None = None,
        vector_k: int = None,
        bm25_k: int = None
    ) -> list[Document]:
        """
        混合检索

        Args:
            query: 查询文本
            user_id: 用户 ID
            k: 最终返回数量
            library_ids: 知识库 ID 列表（可选，支持多库检索）
            vector_k: 向量检索数量 (默认 k*3)
            bm25_k: BM25 检索数量 (默认 k*3)

        Returns:
            排序后的文档列表
        """
        vector_k = vector_k or k * 3
        bm25_k = bm25_k or k * 3

        # 1. 向量检索（支持多库 in 过滤）
        vector_results = self.vector_store.similarity_search(
            query=query,
            user_id=user_id,
            k=vector_k,
            library_ids=library_ids
        )

        # 2. BM25 检索（对每个 library 分别检索，合并）
        bm25_results = []
        if library_ids:
            for lib_id in library_ids:
                bm25_results.extend(
                    self.bm25_index.search(library_id=lib_id, query=query, top_k=bm25_k)
                )
        else:
            bm25_results = self.bm25_index.search(library_id=user_id, query=query, top_k=bm25_k)

        # 3. 融合（不截断，保留所有候选给 reranker）
        candidate_count = len(set(
            self._get_doc_id(doc) for doc in vector_results
        ) | set(
            self._get_doc_id(doc) for doc, _ in bm25_results
        ))
        fusion_k = max(candidate_count, k)

        if self.fusion_method == "rrf":
            fused = self._rrf_fusion(vector_results, bm25_results, fusion_k)
        else:
            fused = self._weighted_fusion(vector_results, bm25_results, fusion_k)

        # 4. Rerank 精排
        if self.reranker and fused:
            reranked = await self.reranker.rerank(
                query=query,
                documents=fused,
                top_n=k,
            )
            return reranked

        # 无 reranker 时回退到截断
        return fused[:k]
    def _rrf_fusion(
        self,
        vector_results: list[Document],
        bm25_results: list[tuple[Document, float]],
        k: int
    ) -> list[Document]:
        """
        RRF (Reciprocal Rank Fusion) 融合
        RRF分数 = Σ 1/(r + k)，其中 r 是排名，k 是常数（通常取 60）
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25 检索结果 [(文档, 分数), ...]
            k: 返回数量
            
        Returns:
            融合后的文档列表
        """
        RRF_K = 60
        
        # 构建文档分数映射
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}
        
        # 向量检索结果打分
        for rank, doc in enumerate(vector_results):
            doc_id = self._get_doc_id(doc)
            rrf_score = 1.0 / (rank + RRF_K)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            doc_map[doc_id] = doc
        
        # BM25 结果打分
        for rank, (doc, bm25_score) in enumerate(bm25_results):
            doc_id = self._get_doc_id(doc)
            rrf_score = 1.0 / (rank + RRF_K)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            doc_map[doc_id] = doc
        
        # 排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 返回 top k
        result = []
        for doc_id, score in sorted_docs[:k]:
            result.append(doc_map[doc_id])
        
        return result
    
    def _weighted_fusion(
        self,
        vector_results: list[Document],
        bm25_results: list[tuple[Document, float]],
        k: int
    ) -> list[Document]:
        """
        加权融合
        归一化向量检索分数和 BM25 分数，加权求和
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25 检索结果 [(文档, 分数), ...]
            k: 返回数量
            
        Returns:
            融合后的文档列表
        """
        vector_weight = 1.0 - self.bm25_weight
        
        # 构建文档分数映射
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}
        
        # 向量检索结果打分
        if vector_results:
            # 归一化分数（使用排名作为近似）
            for rank, doc in enumerate(vector_results):
                doc_id = self._get_doc_id(doc)
                # 归一化分数: (len - rank) / len
                norm_score = (len(vector_results) - rank) / len(vector_results)
                weighted_score = norm_score * vector_weight
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + weighted_score
                doc_map[doc_id] = doc
        
        # BM25 结果打分
        if bm25_results:
            # 归一化 BM25 分数
            max_score = max(score for _, score in bm25_results)
            for doc, bm25_score in bm25_results:
                doc_id = self._get_doc_id(doc)
                norm_score = bm25_score / max_score if max_score > 0 else 0
                weighted_score = norm_score * self.bm25_weight
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + weighted_score
                doc_map[doc_id] = doc
        
        # 排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 返回 top k
        result = []
        for doc_id, score in sorted_docs[:k]:
            result.append(doc_map[doc_id])
        
        return result
    
    def _get_doc_id(self, doc: Document) -> str:
        """获取文档唯一 ID"""
        # 优先使用 metadata 中的 doc_id
        if "doc_id" in doc.metadata:
            return doc.metadata["doc_id"]
        # 否则使用 source + chunk_index
        return f"{doc.metadata.get('source', 'unknown')}_{doc.metadata.get('chunk_index', 0)}"
    
    def add_documents(self, chunks: list, user_id: int, library_id: int | None = None, document_ids: list[str] = None):
        """
        添加文档时同步更新 BM25 索引
        
        Args:
            chunks: 解析后的文本块列表
            user_id: 用户 ID
            document_ids: 文档 ID 列表
        """
        from langchain_core.documents import Document
        
        documents = []
        for i, chunk in enumerate(chunks):
            metadata = {
                **chunk.metadata,
                "user_id": user_id,
                "chunk_index": i,
                "doc_id": document_ids[i] if document_ids else f"{user_id}_{i}"
            }
            doc = Document(
                page_content=chunk.content,
                metadata=metadata
            )
            documents.append(doc)
        
        # 使用 library_id 作为 key（如无则回退到 user_id）
        key = library_id if library_id is not None else user_id
        
        # 缓存文档并重建索引
        if key in self._user_docs:
            self._user_docs[key].extend(documents)
        else:
            self._user_docs[key] = documents
        
        self.bm25_index.build_index(key, self._user_docs[key])
        
        logger.info(f"为键 {key} 更新 BM25 索引，当前共 {len(self._user_docs[key])} 个文档")


# 全局混合检索器实例
_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever(
    collection_name: str = "knowledge_base",
    bm25_weight: float = 0.5,
    fusion_method: str = "rrf"
) -> HybridRetriever:
    """
    获取混合检索器实例
    
    Args:
        collection_name: 向量库 collection 名称
        bm25_weight: BM25 权重
        fusion_method: 融合方法 ("rrf" 或 "weighted")
        
    Returns:
        HybridRetriever 实例
    """
    global _hybrid_retriever
    
    if _hybrid_retriever is None:
        from app.services.rag.vector_store import VectorStore
        vector_store = VectorStore(collection_name=collection_name)
        _hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            bm25_weight=bm25_weight,
            fusion_method=fusion_method
        )
    
    return _hybrid_retriever
