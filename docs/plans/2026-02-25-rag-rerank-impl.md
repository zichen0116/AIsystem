# RAG Rerank 重排序集成 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 HybridRetriever 内部集成阿里云百炼 qwen3-vl-rerank 重排序模型，提升 RAG 检索精度。

**Architecture:** 新建 `DashScopeReranker` 类封装 rerank API 调用，在 `HybridRetriever.search()` 的 RRF 融合之后调用 reranker 精排，对上层 tools.py/graph 完全透明。

**Tech Stack:** Python 3.11+, httpx (async HTTP), 阿里云百炼 qwen3-vl-rerank API, LangChain Document

---

### Task 1: 添加 RERANK_MODEL 配置项

**Files:**
- Modify: `backend/app/core/config.py:29-30`
- Modify: `backend/.env.example:25-26`

**Step 1: 在 config.py 的百炼 API 区域添加 RERANK_MODEL**

在 `config.py` 第 30 行 `EMBEDDING_MODEL` 之后添加：

```python
    RERANK_MODEL: str = "qwen3-vl-rerank"
```

**Step 2: 在 .env.example 添加 RERANK_MODEL 说明**

在 `EMBEDDING_MODEL=tongyi-embedding-vision-flash` 之后添加：

```
# Rerank 重排序模型选择
# 可选: qwen3-vl-rerank (多模态), qwen3-rerank (纯文本)
RERANK_MODEL=qwen3-vl-rerank
```

**Step 3: Commit**

```bash
git add backend/app/core/config.py backend/.env.example
git commit -m "feat: add RERANK_MODEL config for reranking support"
```

---

### Task 2: 创建 DashScopeReranker 类

**Files:**
- Create: `backend/app/services/rag/reranker.py`

**Step 1: 创建 reranker.py 文件**

```python
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
```

**Step 2: Commit**

```bash
git add backend/app/services/rag/reranker.py
git commit -m "feat: add DashScopeReranker for qwen3-vl-rerank API integration"
```

---

### Task 3: 在 HybridRetriever 中集成 Reranker

**Files:**
- Modify: `backend/app/services/rag/hybrid_retriever.py:145-231`

**Step 1: 修改 HybridRetriever.__init__() 初始化 reranker**

在 `hybrid_retriever.py` 的 `HybridRetriever.__init__()` 方法中，在 `self._user_docs` 之后添加 reranker 初始化：

```python
    def __init__(
        self,
        vector_store: Any,
        bm25_weight: float = 0.5,
        fusion_method: str = "rrf"
    ):
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
```

**Step 2: 将 search() 改为 async，末尾调用 reranker**

将 `def search(...)` 改为 `async def search(...)`，并修改召回数量默认值和添加 rerank 调用：

```python
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
        if self.fusion_method == "rrf":
            fused = self._rrf_fusion(vector_results, bm25_results, k=len(vector_results) + len(bm25_results))
        else:
            fused = self._weighted_fusion(vector_results, bm25_results, k=len(vector_results) + len(bm25_results))

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
```

**Step 3: 更新上层调用点 tools.py**

`tools.py` 中 `search_local_knowledge_impl` 目前是同步函数，直接调用 `vector_store.similarity_search()`。search 改 async 后，如果未来需要切换到 HybridRetriever，需确保调用方式兼容。

但实际看代码，**tools.py 当前并未使用 HybridRetriever**（第 81 行直接调 `vector_store.similarity_search`）。所以 tools.py 不需要改动——HybridRetriever 的 async search 只影响直接调用它的代码。

查看项目中 `HybridRetriever.search` 的所有调用点确认影响范围（在 Step 4 验证）。

**Step 4: Commit**

```bash
git add backend/app/services/rag/hybrid_retriever.py
git commit -m "feat: integrate DashScopeReranker into HybridRetriever search pipeline"
```

---

### Task 4: 更新 __init__.py 导出

**Files:**
- Modify: `backend/app/services/rag/__init__.py`

**Step 1: 在 __init__.py 中导出 DashScopeReranker**

```python
"""
RAG 向量存储服务
"""
from app.services.rag.vector_store import VectorStore
from app.services.rag.reranker import DashScopeReranker

__all__ = ["VectorStore", "DashScopeReranker"]
```

**Step 2: Commit**

```bash
git add backend/app/services/rag/__init__.py
git commit -m "feat: export DashScopeReranker from rag package"
```

---

### Task 5: 验证所有调用点兼容性

**Files:**
- Check: 所有调用 `HybridRetriever.search()` 的代码
- Check: 所有调用 `get_hybrid_retriever()` 的代码

**Step 1: 搜索 HybridRetriever.search 和 get_hybrid_retriever 的调用点**

```bash
cd backend && grep -rn "\.search(" app/services/rag/hybrid_retriever.py app/services/ai/tools.py app/services/ai/graph/ app/tasks.py --include="*.py" | grep -v "def search"
grep -rn "get_hybrid_retriever\|HybridRetriever" app/ --include="*.py" | grep -v "__pycache__"
```

确认：
- `tools.py` 当前不调用 `HybridRetriever.search()`（直接调 `VectorStore.similarity_search`）
- 如果有其他地方同步调用了 `HybridRetriever.search()`，需要加 `await`

**Step 2: 如发现同步调用点，添加 await 关键字**

根据实际搜索结果修改。预计只有 `tools.py` 和 `tasks.py` 可能涉及，但它们目前都不直接调用 `HybridRetriever.search()`。

**Step 3: Commit（如有改动）**

```bash
git add -u
git commit -m "fix: update HybridRetriever.search callers to use async/await"
```

---

### Task 6: 端到端冒烟验证

**Step 1: 确认 Python 导入无误**

```bash
cd backend && python -c "
from app.services.rag.reranker import DashScopeReranker
from app.services.rag.hybrid_retriever import HybridRetriever, get_hybrid_retriever
from app.core.config import settings
print(f'RERANK_MODEL={settings.RERANK_MODEL}')
print('DashScopeReranker loaded OK')
print('HybridRetriever loaded OK')
"
```

Expected: 无 ImportError，打印 `RERANK_MODEL=qwen3-vl-rerank`

**Step 2: 确认 FastAPI 应用可正常启动（不报错）**

```bash
cd backend && python -c "from app.main import app; print('App loaded OK')"
```

Expected: 无报错

**Step 3: 如有问题，修复后重新提交**
