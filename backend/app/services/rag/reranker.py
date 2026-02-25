"""
重排序服务
调用阿里云百炼 Rerank API 对检索结果进行二次精排
"""
import logging
from typing import Optional

import httpx
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DashScopeReranker:
    """
    阿里云百炼重排序服务

    调用 qwen3-vl-rerank API 对候选文档进行精排，
    将与用户查询最相关的文档排在前列。
    """

    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

    def __init__(self, api_key: str, model: str = "qwen3-vl-rerank"):
        self.api_key = api_key
        self.model = model

    async def rerank(
        self,
        query: str,
        documents: list[Document],
        top_n: int = 10,
        timeout: float = 10.0,
    ) -> list[Document]:
        """
        对文档列表进行重排序。

        Args:
            query: 用户查询文本
            documents: 待排序的 LangChain Document 列表
            top_n: 返回前 N 条结果
            timeout: API 超时时间（秒）

        Returns:
            按相关性降序排列的 Document 列表，
            每个 document.metadata 中会写入 rerank_score。
            API 失败时回退返回原始文档的前 top_n 条。
        """
        if not documents:
            return []

        # 限制文档数量不超过模型上限（qwen3-vl-rerank 最多 100 条）
        max_docs = 100
        docs_to_rerank = documents[:max_docs]

        # 构造请求体（qwen3-vl-rerank 使用 input 包裹格式）
        request_body = {
            "model": self.model,
            "input": {
                "query": query,
                "documents": [
                    {"text": doc.page_content} for doc in docs_to_rerank
                ],
            },
            "parameters": {
                "return_documents": False,
                "top_n": min(top_n, len(docs_to_rerank)),
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.API_URL,
                    json=request_body,
                    headers=headers,
                )

            if response.status_code != 200:
                logger.error(
                    f"Rerank API 返回错误: status={response.status_code}, "
                    f"body={response.text}"
                )
                return docs_to_rerank[:top_n]

            data = response.json()

            # 检查业务错误码
            if "code" in data and data["code"] != 200 and data["code"] != "200":
                logger.error(
                    f"Rerank API 业务错误: code={data.get('code')}, "
                    f"message={data.get('message')}"
                )
                return docs_to_rerank[:top_n]

            # 解析结果
            results = data.get("output", {}).get("results", [])
            if not results:
                logger.warning("Rerank API 返回空结果，回退到原始排序")
                return docs_to_rerank[:top_n]

            # 按 score 降序排列（API 已排序，但确保一下）
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

            # 构建重排后的文档列表
            reranked_docs = []
            for item in results:
                idx = item["index"]
                score = item.get("relevance_score", 0.0)
                doc = docs_to_rerank[idx]
                doc.metadata["rerank_score"] = score
                reranked_docs.append(doc)

            logger.info(
                f"Rerank 完成: {len(docs_to_rerank)} 篇候选 → {len(reranked_docs)} 篇精排结果"
            )
            return reranked_docs

        except httpx.TimeoutException:
            logger.warning(
                f"Rerank API 超时 ({timeout}s)，回退到原始排序"
            )
            return docs_to_rerank[:top_n]
        except Exception as e:
            logger.error(f"Rerank 调用异常: {e}", exc_info=True)
            return docs_to_rerank[:top_n]
