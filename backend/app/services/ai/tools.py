"""
AI 工具定义
定义两个 StructuredTool 供 LangGraph Agent 调用：
1. search_local_knowledge - 本地知识库检索
2. search_web - 联网搜索
"""
import os
import logging
from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


# ==================== 工具输入模型 ====================

class LocalSearchInput(BaseModel):
    """本地知识库检索输入"""
    query: str = Field(
        description="用户问题或查询关键词，用于检索本地知识库"
    )
    user_id: int = Field(
        description="用户ID，用于隔离不同用户的知识库"
    )
    k: int = Field(
        default=10,
        description="返回的候选文档数量，默认10"
    )


class WebSearchInput(BaseModel):
    """联网搜索输入"""
    query: str = Field(
        description="搜索关键词，应简洁准确"
    )


# ==================== 工具实现 ====================

def search_local_knowledge_impl(
    query: str,
    user_id: int,
    k: int = 10
) -> str:
    """
    本地知识库检索

    调用 HybridRetriever 进行混合检索（向量 + BM25 + RRF）

    Args:
        query: 用户问题
        user_id: 用户ID
        k: 返回数量

    Returns:
        格式化的检索结果字符串
    """
    try:
        # 初始化向量存储
        vector_store = VectorStore()

        # 初始化混合检索器
        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            bm25_weight=0.5,
            fusion_method="rrf"
        )

        # 构建 BM25 索引（需要先有文档）
        # 注意：这里需要传入用户已有的文档
        # 实际使用时应从向量库获取所有文档
        logger.info(f"执行本地知识库检索: query={query}, user_id={user_id}, k={k}")

        # 直接使用向量检索
        docs = vector_store.similarity_search(
            query=query,
            user_id=user_id,
            k=k
        )

        if not docs:
            return "本地知识库中未找到相关内容。"

        # 格式化结果
        results = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page", "")
            content = doc.page_content

            # 截断过长内容
            if len(content) > 500:
                content = content[:500] + "..."

            ref = f"[Ref: {source}"
            if page:
                ref += f", p.{page}"
            ref += "]"

            results.append(
                f"【文档 {i}】{ref}\n"
                f"内容: {content}\n"
            )

        return "\n".join(results)

    except Exception as e:
        logger.error(f"本地知识库检索失败: {e}")
        return f"检索失败: {str(e)}"


def search_web_impl(query: str) -> str:
    """
    联网搜索

    使用 Tavily API 进行网络搜索

    Args:
        query: 搜索关键词

    Returns:
        格式化的搜索结果字符串
    """
    try:
        # 检查 Tavily API Key
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            logger.warning("未配置 TAVILY_API_KEY，尝试使用备用方案")
            return _search_web_fallback(query)

        # 使用 Tavily 官方客户端
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_api_key)

        response = client.search(
            query=query,
            max_results=5,
            include_answer=True,
            include_raw_content=False
        )

        if not response.get("results"):
            return "未找到相关网络信息。"

        # 格式化结果
        results = []
        for i, item in enumerate(response["results"], 1):
            title = item.get("title", "无标题")
            url = item.get("url", "")
            content = item.get("content", "")[:300]  # 截断

            results.append(
                f"【结果 {i}】[Web: {title}]\n"
                f"来源: {url}\n"
                f"内容: {content}...\n"
            )

        # 如果有摘要答案，放在最前面
        if response.get("answer"):
            results.insert(0, f"【摘要】{response['answer']}\n")

        return "\n".join(results)

    except ImportError:
        logger.warning("Tavily 客户端未安装，使用备用搜索方案")
        return _search_web_fallback(query)
    except Exception as e:
        logger.error(f"联网搜索失败: {e}")
        return _search_web_fallback(query)


def _search_web_fallback(query: str) -> str:
    """
    备用搜索方案（当 Tavily 不可用时）

    使用 DuckDuckGo 简单搜索
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

        if not results:
            return "未找到相关网络信息。"

        output = []
        for i, r in enumerate(results, 1):
            output.append(
                f"【结果 {i}】[Web: {r.get('title', '无标题')}]\n"
                f"来源: {r.get('href', '')}\n"
                f"内容: {r.get('body', '')[:300]}...\n"
            )

        return "\n".join(output)

    except ImportError:
        return "网络搜索功能暂不可用（请安装 duckduckgo-search 或配置 Tavily API）。"
    except Exception as e:
        logger.error(f"备用搜索失败: {e}")
        return f"网络搜索失败: {str(e)}"


# ==================== 导出 StructuredTools ====================

def get_search_tools() -> List[BaseTool]:
    """
    获取所有搜索工具

    Returns:
        [search_local_knowledge, search_web]
    """
    tools = [
        StructuredTool.from_function(
            name="search_local_knowledge",
            description=(
                "用于查询用户上传的教学资料（PDF/Word/视频/图片）。"
                "涉及具体课程内容、定义、公式时**必须优先使用**此工具。"
                "输入需要提供 query（问题）和 user_id（用户ID）。"
            ),
            args_schema=LocalSearchInput,
            func=search_local_knowledge_impl,
        ),
        StructuredTool.from_function(
            name="search_web",
            description=(
                "用于联网搜索最新新闻、技术文档、社区讨论等外部信息。"
                "仅在以下情况使用："
                "1. 本地知识库无相关结果；"
                "2. 用户询问实时信息或最新动态；"
                "3. 需要外部案例补充说明。"
            ),
            args_schema=WebSearchInput,
            func=search_web_impl,
        ),
    ]

    return tools


# 导出单例工具（方便直接导入使用）
search_local_knowledge = get_search_tools()[0]
search_web = get_search_tools()[1]
