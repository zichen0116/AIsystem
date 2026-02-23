"""
文本切片处理器
支持两种模式：
1. 语义分块 (Semantic Chunking) - 使用 Embedding 模型根据语义相似度自动切分
2. 递归字符分块 (Recursive Character) - 按分隔符和字符数切分
"""
import logging
import os
from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document

from app.services.parsers.base import ParsedChunk
from app.services.rag.vector_store import DashScopeEmbeddings

logger = logging.getLogger(__name__)


# 全局缓存 Embeddings 模型（避免重复初始化）
_semantic_chunker_embeddings: Optional[DashScopeEmbeddings] = None


def _get_semantic_embeddings() -> DashScopeEmbeddings:
    """获取语义分块用的 Embeddings 模型（带缓存）"""
    global _semantic_chunker_embeddings
    if _semantic_chunker_embeddings is None:
        embedding_model = os.getenv("EMBEDDING_MODEL", "tongyi-embedding-vision-flash")
        _semantic_chunker_embeddings = DashScopeEmbeddings(model=embedding_model)
        logger.info(f"语义分块初始化 Embedding 模型: {embedding_model}")
    return _semantic_chunker_embeddings


def split_documents_semantic(
    chunks: List[ParsedChunk],
    breakpoint_threshold_type: str = "percentile",
    breakpoint_threshold_amount: float = 0.8,
    min_chunk_size: int = 100
) -> List[ParsedChunk]:
    """
    语义分块 (Semantic Chunking)
    基于 Embedding 模型的语义相似度进行智能切分

    原理：
    1. 将文本按句子/段落分割
    2. 计算相邻句子/段落的 Embedding 相似度
    3. 当相似度低于阈值时（语义突变点），进行切分

    Args:
        chunks: 解析后的文本块列表
        breakpoint_threshold_type: 断点检测方式
            - "percentile": 基于百分位（推荐，默认95%）
            - "standard_deviation": 基于标准差
            - "gradient": 基于梯度变化
        breakpoint_threshold_amount: 阈值参数
            - percentile 模式：0.0-1.0，推荐 0.90-0.95
        min_chunk_size: 最小块大小，防止过度切分

    Returns:
        List[ParsedChunk]: 语义切片后的文本块列表
    """
    if not chunks:
        return []

    # 1. 获取 Embeddings 模型
    embeddings = _get_semantic_embeddings()

    # 2. 初始化 SemanticChunker
    try:
        text_splitter = SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
            min_chunk_size=min_chunk_size,
            add_start_index=True
        )
        logger.info(
            f"初始化语义分块器: threshold_type={breakpoint_threshold_type}, "
            f"threshold={breakpoint_threshold_amount}, min_size={min_chunk_size}"
        )
    except Exception as e:
        logger.error(f"语义分块器初始化失败: {e}，回退到递归分块")
        return split_documents(chunks, chunk_size=800, chunk_overlap=150)

    # 3. 将 ParsedChunk 转换为 LangChain Document
    documents = []
    for i, chunk in enumerate(chunks):
        metadata = dict(chunk.metadata) if chunk.metadata else {}
        metadata["original_chunk_index"] = i

        doc = Document(
            page_content=chunk.content,
            metadata=metadata
        )
        documents.append(doc)

    # 4. 执行语义切片
    logger.info(f"开始语义切片: {len(documents)} 个原始块")
    try:
        split_docs = text_splitter.split_documents(documents)
    except Exception as e:
        logger.warning(f"语义切片失败: {e}，回退到递归分块")
        return split_documents(chunks, chunk_size=800, chunk_overlap=150)

    # 5. 将切片后的 Document 转换回 ParsedChunk
    result_chunks: List[ParsedChunk] = []
    inherited_fields = [
        "source", "page", "type", "user_id",
        "has_image", "image_count", "image_descriptions",
        "timestamp", "frame_number", "time_block",
        "block_start", "block_end", "has_audio",
        "audio_start_time", "audio_end_time"
    ]

    for i, doc in enumerate(split_docs):
        original_metadata = doc.metadata.copy()

        # 继承关键字段
        final_metadata = {}
        for field in inherited_fields:
            if field in original_metadata:
                final_metadata[field] = original_metadata[field]

        # 添加切片信息
        final_metadata["split_index"] = i
        final_metadata["original_chunk_index"] = original_metadata.get("original_chunk_index", 0)
        final_metadata["chunking_method"] = "semantic"

        # 如果有 start_index，记录下来
        if hasattr(doc, 'metadata') and 'start_index' in doc.metadata:
            final_metadata["start_index"] = doc.metadata.get("start_index")

        result_chunk = ParsedChunk(
            content=doc.page_content,
            metadata=final_metadata
        )
        result_chunks.append(result_chunk)

    logger.info(f"语义切片完成: {len(result_chunks)} 个切片")

    return result_chunks


def split_documents(
    chunks: List[ParsedChunk],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    separators: List[str] = None
) -> List[ParsedChunk]:
    """
    将 ParseResult 的 chunks 进行智能切片

    策略：
    1. 使用 RecursiveCharacterTextSplitter 进行文本分割
    2. 确保每个切片都完整继承原始 chunk 的所有元数据
    3. 添加切片索引和来源信息用于追溯

    Args:
        chunks: 解析后的文本块列表
        chunk_size: 每个切片的最大字符数
        chunk_overlap: 相邻切片之间的重叠字符数
        separators: 自定义分隔符列表

    Returns:
        List[ParsedChunk]: 切片后的文本块列表
    """
    if not chunks:
        return []

    # 默认分隔符（按优先级排列）
    if separators is None:
        separators = [
            "\n\n\n",  # 段落分隔（三个换行）
            "\n\n",    # 段落分隔（两个换行）
            "\n",      # 换行
            "。",      # 中文句子
            ". ",      # 英文句子
            ", ",      # 英文逗号
            "，",      # 中文逗号
            " ",       # 空格
            ""         # 单字符
        ]

    # 创建文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
        keep_separator=False
    )

    # 将 ParsedChunk 转换为 LangChain Document
    documents = []
    for i, chunk in enumerate(chunks):
        # 构建元数据（深拷贝）
        metadata = dict(chunk.metadata) if chunk.metadata else {}
        # 添加原始块索引
        metadata["original_chunk_index"] = i

        doc = Document(
            page_content=chunk.content,
            metadata=metadata
        )
        documents.append(doc)

    # 执行切片
    logger.info(f"开始文本切片: {len(documents)} 个原始块, chunk_size={chunk_size}, overlap={chunk_overlap}")
    split_docs = text_splitter.split_documents(documents)

    # 将切片后的 Document 转换回 ParsedChunk
    result_chunks: List[ParsedChunk] = []
    for i, doc in enumerate(split_docs):
        # 从原始元数据继承关键字段
        original_metadata = doc.metadata.copy()

        # 继承的关键字段（如果存在）
        inherited_fields = [
            "source", "page", "type", "user_id",
            "has_image", "image_count", "image_descriptions",
            "timestamp", "frame_number", "time_block",
            "block_start", "block_end", "has_audio",
            "audio_start_time", "audio_end_time"
        ]

        # 构建最终元数据
        final_metadata = {}
        for field in inherited_fields:
            if field in original_metadata:
                final_metadata[field] = original_metadata[field]

        # 添加切片信息
        final_metadata["split_index"] = i
        final_metadata["original_chunk_index"] = original_metadata.get("original_chunk_index", 0)

        result_chunk = ParsedChunk(
            content=doc.page_content,
            metadata=final_metadata
        )
        result_chunks.append(result_chunk)

    logger.info(f"文本切片完成: {len(result_chunks)} 个切片")

    return result_chunks


def split_text(
    text: str,
    metadata: dict = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[ParsedChunk]:
    """
    简单文本切片（不带解析器）

    Args:
        text: 待切分的文本
        metadata: 元数据字典
        chunk_size: 每个切片的最大字符数
        chunk_overlap: 相邻切片之间的重叠字符数

    Returns:
        List[ParsedChunk]: 切片后的文本块列表
    """
    if not text:
        return []

    separators = [
        "\n\n\n", "\n\n", "\n",
        "。", ". ", ", ", "，", " ", ""
    ]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
        keep_separator=False
    )

    # 切分文本
    texts = text_splitter.split_text(text)

    # 转换为 ParsedChunk
    chunks = []
    for i, content in enumerate(texts):
        chunk_metadata = dict(metadata) if metadata else {}
        chunk_metadata["split_index"] = i
        chunks.append(ParsedChunk(content=content, metadata=chunk_metadata))

    return chunks
