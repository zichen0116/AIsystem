# LightRAG 图检索集成 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Chroma 向量检索基础上集成 LightRAG 图检索，为系统级知识库提供 Neo4j 知识图谱支持。

**Architecture:** 新建 GraphStore 薄封装 LightRAG，通过 workspace 实现 Neo4j Label 隔离。在 tools.py 中新增独立的 `search_knowledge_graph` 工具，由 LangGraph Agent 自主决策调用。图索引通过管理员手动触发的 Celery 任务异步执行。

**Tech Stack:** LightRAG (lightrag-hku), Neo4j Aura (neo4j driver), DashScope/Qwen (LLM+Embedding), Celery, FastAPI

**Spec:** `docs/superpowers/specs/2026-03-10-lightrag-integration-design.md`

---

## Chunk 1: 前置准备与基础设施

### Task 1: 创建功能分支并迁移凭据

**Files:**
- Modify: `backend/.env` (添加 Neo4j 配置)
- Modify: `backend/.env.example` (添加 Neo4j 模板)
- Modify: `ISSUES.md` (移除凭据)

- [ ] **Step 1: 创建功能分支**

```bash
git checkout -b feature/lightrag-integration
```

- [ ] **Step 2: 将 Neo4j 凭据添加到 backend/.env**

在 `backend/.env` 文件末尾（第 59 行 `DEBUG=true` 之后）追加：

```
# ========== Neo4j 图数据库 ==========
NEO4J_URI=neo4j+s://your-neo4j-aura-uri
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

- [ ] **Step 3: 更新 backend/.env.example**

在 `backend/.env.example` 文件末尾（第 53 行 `HTML_UPLOAD_DIR=uploads` 之后）追加：

```
# ========== Neo4j Graph Database ==========
# Neo4j Aura 连接信息（仅系统知识库图检索使用）
NEO4J_URI=neo4j+s://your-neo4j-aura-uri
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# ========== LightRAG ==========
# LightRAG 本地工作目录（默认自动锚定 backend/lightrag_data/，一般无需修改）
# LIGHTRAG_WORKING_DIR=lightrag_data
```

- [ ] **Step 4: 从 ISSUES.md 中移除凭据**

将 ISSUES.md 第 11 行的 Neo4j 连接信息替换为：

```
知识图谱存储使用neo4j Aura，连接信息见 backend/.env
```

- [ ] **Step 5: 提交**

```bash
git add ISSUES.md backend/.env.example
git commit -m "chore: migrate Neo4j credentials to .env"
```

注意：`backend/.env` 不应提交（已在 .gitignore 中）。

---

### Task 2: 添加依赖与配置

**Files:**
- Modify: `backend/requirements.txt:72` (末尾追加)
- Modify: `backend/app/core/config.py:50-51` (Tavily 之后追加)

- [ ] **Step 1: 更新 requirements.txt**

在 `backend/requirements.txt` 末尾（第 72 行 `python-pptx==0.6.23` 之后）追加：

```
# 知识图谱
lightrag-hku
neo4j>=5.0.0
cachetools
```

- [ ] **Step 2: 更新 config.py**

在 `backend/app/core/config.py` 第 4 行 `from functools import lru_cache` 之后追加导入：

```python
from pathlib import Path
```

在第 50 行 `TAVILY_API_KEY: str = ""` 之后、第 52 行 `# 应用` 之前插入：

```python

    # ========== Neo4j 图数据库 ==========
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # ========== LightRAG ==========
    # 动态绝对路径，锚定 backend/ 目录，避免 CWD 差异导致路径分裂
    LIGHTRAG_WORKING_DIR: str = str(
        Path(__file__).resolve().parent.parent.parent / "lightrag_data"
    )
```

- [ ] **Step 3: 在 backend/.gitignore 中添加 lightrag_data/**

在 `backend/.gitignore` 末尾追加：

```
# LightRAG 本地工作目录
lightrag_data/
```

- [ ] **Step 4: 安装依赖**

```bash
cd backend && pip install lightrag-hku "neo4j>=5.0.0" cachetools
```

- [ ] **Step 5: 提交**

```bash
git add backend/requirements.txt backend/app/core/config.py backend/.gitignore
git commit -m "build: add lightrag-hku and neo4j dependencies"
```

---

## Chunk 2: GraphStore 核心模块

### Task 3: 实现 GraphStore

**Files:**
- Create: `backend/app/services/rag/graph_store.py`
- Modify: `backend/app/services/rag/__init__.py`

- [ ] **Step 1: 创建 graph_store.py**

创建 `backend/app/services/rag/graph_store.py`：

```python
"""
LightRAG 图存储服务
薄封装 LightRAG，提供知识图谱的插入和检索能力。
每个系统知识库通过 LightRAG workspace 实现 Neo4j Label 隔离。
"""
import os
import logging
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


# ==================== GraphStore ====================


class GraphStore:
    """
    LightRAG 图存储封装。

    每个系统知识库对应一个 LightRAG 实例，通过 workspace 实现
    Neo4j Label 隔离。实例按 library_id 缓存。
    """

    _instances: LRUCache = LRUCache(maxsize=16)  # LRU 淘汰，防止内存无限增长

    @classmethod
    async def get_instance(cls, library_id: int):
        """获取指定知识库的 LightRAG 实例（首次访问时初始化）"""
        if library_id in cls._instances:
            return cls._instances[library_id]

        from lightrag import LightRAG
        from lightrag.base import EmbeddingFunc

        workspace = f"library_{library_id}"
        working_dir = str(
            Path(settings.LIGHTRAG_WORKING_DIR) / workspace
        )
        Path(working_dir).mkdir(parents=True, exist_ok=True)

        # 设置 Neo4j 环境变量（LightRAG Neo4JStorage 从 env 读取）
        os.environ["NEO4J_URI"] = settings.NEO4J_URI
        os.environ["NEO4J_USERNAME"] = settings.NEO4J_USERNAME
        os.environ["NEO4J_PASSWORD"] = settings.NEO4J_PASSWORD

        embedding_func = EmbeddingFunc(
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
```

- [ ] **Step 2: 更新 RAG 模块 __init__.py**

将 `backend/app/services/rag/__init__.py` 更新为：

```python
"""
RAG 向量存储服务
"""
from app.services.rag.vector_store import VectorStore
from app.services.rag.reranker import DashScopeReranker
from app.services.rag.graph_store import GraphStore

__all__ = ["VectorStore", "DashScopeReranker", "GraphStore"]
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/rag/graph_store.py backend/app/services/rag/__init__.py
git commit -m "feat(rag): add GraphStore with LightRAG/Neo4j integration"
```

---

## Chunk 3: AgentState、工具与节点集成

### Task 4: 更新 AgentState

**Files:**
- Modify: `backend/app/services/ai/graph/state.py:52` (末尾追加)

- [ ] **Step 1: 在 AgentState 中追加 system_library_ids 字段**

在 `backend/app/services/ai/graph/state.py` 第 52 行（`approved: bool` 之后）追加：

```python

    # ====== 知识图谱相关字段 ======

    # 用户选中的系统知识库 ID 列表（非空时绑定图谱搜索工具）
    system_library_ids: Optional[List[int]]
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/ai/graph/state.py
git commit -m "feat(graph): add system_library_ids to AgentState"
```

---

### Task 5: 新增 search_knowledge_graph 工具并改造 get_search_tools

**Files:**
- Modify: `backend/app/services/ai/tools.py`

- [ ] **Step 1: 添加导入和工具输入模型**

在 `backend/app/services/ai/tools.py` 第 16 行（`from app.services.rag.vector_store import VectorStore` 之后）追加：

```python
from app.services.rag.graph_store import GraphStore
```

在第 42 行（`WebSearchInput` 类之后）追加新的输入模型：

```python


class GraphSearchInput(BaseModel):
    """知识图谱检索输入"""
    query: str = Field(
        description="搜索查询，用于从知识图谱中检索全局上下文和实体关系"
    )
    mode: str = Field(
        default="hybrid",
        description="检索模式: local(局部实体), global(全局关系), hybrid(混合)"
    )
```

- [ ] **Step 2: 添加 search_knowledge_graph_impl 函数**

在第 207 行（`_search_web_fallback` 函数之后、`# ==================== 导出 StructuredTools ====================` 之前）插入：

```python


def _create_graph_search_impl(system_library_ids: List[int]):
    """
    创建知识图谱检索实现函数（通过闭包注入 library_ids）

    Args:
        system_library_ids: 当前会话选中的系统知识库 ID 列表
    """

    async def search_knowledge_graph_impl(query: str, mode: str = "hybrid") -> str:
        """
        知识图谱检索（异步实现）

        ToolNode 在异步上下文中调用工具，因此必须使用 async 函数，
        而非 asyncio.run()（会因已有事件循环而崩溃）。

        遍历所有选中的系统知识库，合并图谱检索结果。

        Args:
            query: 搜索查询
            mode: 检索模式 (local/global/hybrid)

        Returns:
            格式化的图谱检索结果字符串
        """
        try:
            logger.info(
                f"执行知识图谱检索: query={query}, mode={mode}, "
                f"libraries={system_library_ids}"
            )

            all_results = []
            for lib_id in system_library_ids:
                try:
                    result = await GraphStore.query(lib_id, query, mode=mode)
                    if result and "检索失败" not in result:
                        all_results.append(
                            f"【知识库 {lib_id}】\n{result}"
                        )
                except Exception as e:
                    logger.warning(f"图谱检索失败 library_id={lib_id}: {e}")

            if not all_results:
                return "知识图谱中未找到相关内容。"

            return "\n\n".join(all_results)

        except Exception as e:
            logger.error(f"知识图谱检索失败: {e}")
            return f"知识图谱检索暂不可用: {str(e)}"

    return search_knowledge_graph_impl
```

- [ ] **Step 3: 改造 get_search_tools 支持动态工具列表**

将 `backend/app/services/ai/tools.py` 中现有的 `get_search_tools` 函数（第 212-244 行）和末尾的单例导出（第 247-249 行）替换为：

```python
def get_search_tools(system_library_ids: Optional[List[int]] = None) -> List[BaseTool]:
    """
    获取搜索工具列表

    Args:
        system_library_ids: 系统知识库 ID 列表。非空时额外绑定知识图谱工具。

    Returns:
        工具列表
    """
    tools = [
        StructuredTool.from_function(
            name="search_local_knowledge",
            description=(
                "用于查询用户上传的教学资料（PDF/Word/视频/图片）。"
                "涉及具体课程内容、定义、公式、原文引用时**必须优先使用**此工具。"
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

    # 当用户选中了系统知识库时，额外绑定图谱工具
    if system_library_ids:
        graph_impl = _create_graph_search_impl(system_library_ids)
        tools.append(
            StructuredTool.from_function(
                name="search_knowledge_graph",
                description=(
                    "搜索系统知识图谱，获取全局上下文、实体关系和知识脉络。"
                    "适用于总结、概述、关系梳理、对比分析等宏观问题。"
                    "当需要全局视角或知识框架时使用此工具。"
                ),
                args_schema=GraphSearchInput,
                coroutine=graph_impl,  # 异步函数，用 coroutine 而非 func
            )
        )

    return tools
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/ai/tools.py
git commit -m "feat(tools): add search_knowledge_graph with dynamic binding"
```

---

### Task 6: 改造 Agent 节点支持动态工具绑定

**Files:**
- Modify: `backend/app/services/ai/graph/nodes.py:24-81`
- Modify: `backend/app/services/ai/graph/workflow.py:124,206` (入口函数传递 system_library_ids)

- [ ] **Step 1: 更新 AGENT_SYSTEM_PROMPT**

在 `backend/app/services/ai/graph/nodes.py` 中，将第 46-50 行的 `## 工具使用策略` 部分替换为：

```python
## 工具使用策略

- **具体细节查询**：涉及定义、公式、原文引用、具体步骤等，使用 search_local_knowledge
- **全局概述查询**：涉及总结、概述、知识脉络、关系梳理或对比分析，使用 search_knowledge_graph（仅当可用时）
- **复杂教学设计**：可同时调用 search_local_knowledge 和 search_knowledge_graph，先获取全局框架再补充具体细节
- **本地无结果时**：搜索网络补充最新信息或外部案例
```

- [ ] **Step 2: 改造 create_agent_node 为按请求动态绑定**

将 `create_agent_node` 函数（第 56-166 行）替换为。

注意：需要在文件顶部导入区新增 `from langchain_core.messages import SystemMessage`（第 13 行 `HumanMessage, AIMessage` 之后追加）。

```python
def create_agent_node():
    """
    创建 Agent 节点

    工具列表根据 state 中 system_library_ids 动态绑定：
    - system_library_ids 非空 → 向量 + 图谱 + 网络搜索
    - system_library_ids 为空 → 向量 + 网络搜索

    Returns:
        agent_node 函数
    """
    from langchain_core.utils.function_calling import convert_to_openai_function

    # 获取 LLM
    llm_service = get_llm_service()

    async def agent_node(state: AgentState) -> AgentState:
        """
        Agent 节点

        根据当前状态决定：
        1. 调用工具
        2. 生成最终答案
        """
        messages = state["messages"]
        user_id = state.get("user_id", 0)
        current_query = state.get("current_query", "")
        system_library_ids = state.get("system_library_ids") or []

        # 如果是第一条消息，提取用户查询
        if not current_query and messages:
            last_msg = messages[-1]
            if isinstance(last_msg, HumanMessage):
                current_query = last_msg.content

        # 动态获取工具列表
        tools = get_search_tools(
            system_library_ids=system_library_ids if system_library_ids else None
        )

        # 动态绑定工具到 LLM（每次请求根据 state 决定工具列表）
        llm = llm_service.llm
        llm_with_tools = llm.bind(
            tools=[convert_to_openai_function(tool) for tool in tools],
            tool_choice="auto"
        )

        # 构造消息列表（SystemMessage 而非 dict，避免混入 BaseMessage 列表后类型不兼容）
        system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
        all_messages = [system_msg] + messages

        logger.info(
            f"Agent 节点执行: user_id={user_id}, 消息数={len(messages)}, "
            f"工具数={len(tools)}, 系统库={system_library_ids}"
        )

        # 调用 LLM（使用绑定了工具的版本）
        response = await llm_with_tools.ainvoke(all_messages)

        # 检查是否需要调用工具
        tool_calls = []
        if hasattr(response, "additional_kwargs") and response.additional_kwargs.get("tool_calls"):
            tool_calls = response.additional_kwargs["tool_calls"]

        if tool_calls:
            # 有工具调用，准备工具调用消息
            ai_msg = AIMessage(
                content=response.content,
                additional_kwargs={"tool_calls": tool_calls}
            )

            # 更新状态
            new_state = {
                "messages": [ai_msg],
                "tool_calls": [tc["function"]["name"] for tc in tool_calls],
                "current_query": current_query,
            }
        else:
            # 无工具调用，生成最终答案
            documents = state.get("documents", [])

            # 构建上下文
            context = ""
            if documents:
                context_parts = []
                for i, doc in enumerate(documents[:5], 1):
                    source = doc.metadata.get("source", "未知")
                    page = doc.metadata.get("page", "")
                    content = doc.page_content[:300]

                    ref = f"[Ref: {source}"
                    if page:
                        ref += f", p.{page}"
                    ref += "]"

                    context_parts.append(f"{i}. {ref}\n{content}")
                context = "\n\n".join(context_parts)

            # 生成最终回复
            final_response = _generate_final_response(
                query=current_query,
                context=context,
                generation=response.content,
                llm_service=llm_service
            )

            new_state = {
                "messages": [response],
                "generation": final_response,
                "documents": documents,
            }

        return new_state

    return agent_node
```

- [ ] **Step 3: 更新 create_tools_node 也使用动态工具**

将 `create_tools_node` 函数（第 203-266 行）中的工具获取改为动态：

在函数体内，将第 214-219 行：

```python
    # 获取工具
    tools = get_search_tools()
    tool_map = {tool.name: tool for tool in tools}

    # 创建 ToolNode
    tool_node = ToolNode(tools)
```

替换为：

```python
    # 注意：ToolNode 需要在调用时根据 state 动态构建
    # 因为工具列表可能包含图谱工具
```

并将 `tools_node` 内部函数改为动态获取工具：

```python
    async def tools_node(state: AgentState) -> AgentState:
        """
        工具执行节点

        执行上一次 Agent 调用的工具，返回结果
        """
        messages = state["messages"]
        user_id = state.get("user_id", 0)
        system_library_ids = state.get("system_library_ids") or []

        # 获取最后一条消息（应该包含 tool_calls）
        last_msg = messages[-1]

        if not hasattr(last_msg, "additional_kwargs") or \
           "tool_calls" not in last_msg.additional_kwargs:
            return {"messages": []}

        # 动态构建 ToolNode
        tools = get_search_tools(
            system_library_ids=system_library_ids if system_library_ids else None
        )
        tool_node = ToolNode(tools)

        logger.info(f"Tools 节点执行: user_id={user_id}")

        tool_messages = await tool_node.ainvoke(last_msg)

        # 收集检索到的文档
        documents = []
        tool_call_results = []

        for msg in tool_messages:
            content = msg.content
            tool_call_results.append(content)

            if "【文档" in content:
                docs = _parse_retrieved_docs(content)
                documents.extend(docs)

        return {
            "messages": tool_messages,
            "documents": documents,
            "tool_calls": [tc.get("name", "") for tc in last_msg.additional_kwargs.get("tool_calls", [])]
        }

    return tools_node
```

- [ ] **Step 4: 修改 workflow.py 将 system_library_ids 传入工作流**

计划只在 AgentState 中加了字段，但入口函数 `run_agent()` 和 `run_agent_with_checkpoint()` 未传递此字段，导致 state 中永远为 None，图谱工具不会被绑定。

在 `backend/app/services/ai/graph/workflow.py` 中：

**4a.** `run_agent` 函数签名（第 124 行）新增参数：

```python
async def run_agent(
    query: str,
    user_id: int,
    chat_history: List = None,
    system_library_ids: List[int] = None,  # 新增
    max_retries: int = 3
) -> dict:
```

在 `initial_state`（第 162 行）中追加：

```python
    initial_state = {
        "messages": messages,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "web_search_needed": False,
        "user_id": user_id,
        "tool_calls": [],
        "current_query": query,
        "system_library_ids": system_library_ids,  # 新增
    }
```

**4b.** `run_agent_with_checkpoint` 函数签名（第 206 行）新增参数：

```python
async def run_agent_with_checkpoint(
    query: str,
    user_id: int,
    thread_id: str = None,
    chat_history: List = None,
    system_library_ids: List[int] = None,  # 新增
    max_retries: int = 3
) -> dict:
```

在 `initial_state`（第 255 行）中追加：

```python
        "system_library_ids": system_library_ids,  # 新增
```

（置于 `"approved": False` 之前即可）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/ai/graph/nodes.py backend/app/services/ai/graph/workflow.py
git commit -m "feat(graph): dynamic tool binding based on system_library_ids"
```

---

## Chunk 4: API 端点与 Celery 任务

### Task 7: 新增图索引 API 端点

**Files:**
- Modify: `backend/app/api/libraries.py:148` (末尾追加)
- Modify: `backend/app/schemas/library.py:40` (末尾追加)

- [ ] **Step 1: 在 schemas/library.py 添加请求/响应模型**

在 `backend/app/schemas/library.py` 末尾（第 40 行之后）追加：

```python


class AddToGraphRequest(BaseModel):
    """添加到知识图谱请求"""
    asset_ids: list[int] = Field(..., min_length=1, description="知识资产 ID 列表")


class AddToGraphResponse(BaseModel):
    """添加到知识图谱响应"""
    task_id: str
    message: str
```

- [ ] **Step 2: 在 libraries.py 添加 add-to-graph 端点**

在 `backend/app/api/libraries.py` 第 10 行（`from app.core.auth import CurrentUser`）修改为：

```python
from app.core.auth import CurrentUser, AdminUser
```

在第 12-16 行的 `from app.schemas.library import (...)` 中追加两个新模型：

```python
from app.schemas.library import (
    KnowledgeLibraryCreate,
    KnowledgeLibraryUpdate,
    KnowledgeLibraryResponse,
    KnowledgeLibraryListResponse,
    AddToGraphRequest,
    AddToGraphResponse,
)
```

在文件末尾（第 148 行 `return None` 之后）追加新端点：

```python


@router.post(
    "/{library_id}/add-to-graph",
    response_model=AddToGraphResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def add_to_graph(
    library_id: int,
    data: AddToGraphRequest,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    将知识资产添加到知识图谱（仅管理员，仅系统知识库）。
    异步执行，返回 Celery task_id。
    """
    # 校验知识库存在且为系统库
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.is_system == True,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系统知识库不存在",
        )

    # 推入 Celery 队列
    from app.tasks import build_graph_index
    task = build_graph_index.delay(library_id, data.asset_ids)

    return AddToGraphResponse(
        task_id=task.id,
        message=f"图索引构建任务已提交，共 {len(data.asset_ids)} 个资产",
    )
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/schemas/library.py backend/app/api/libraries.py
git commit -m "feat(api): add POST /libraries/{id}/add-to-graph endpoint"
```

---

### Task 8: 新增 build_graph_index Celery 任务并集成清理

**Files:**
- Modify: `backend/app/tasks.py:351` (末尾追加任务 + 修改 cleanup_library)

- [ ] **Step 1: 在 tasks.py 末尾追加 build_graph_index 任务**

在 `backend/app/tasks.py` 末尾（第 351 行 `db.close()` 之后）追加：

```python


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.tasks.build_graph_index",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def build_graph_index(self, library_id: int, asset_ids: list[int]):
    """
    为系统知识库构建 LightRAG 图索引。

    从 PostgreSQL 查出指定资产的已解析文本，调用 GraphStore 插入图谱。
    去重由 LightRAG 内部的文档哈希校验自动完成。

    Args:
        library_id: 系统知识库 ID
        asset_ids: 要索引的知识资产 ID 列表
    """
    from app.models.knowledge_asset import KnowledgeAsset
    from app.services.rag.graph_store import GraphStore

    logger.info(
        f"开始构建图索引: library_id={library_id}, "
        f"asset_ids={asset_ids}, retry={self.request.retries}"
    )

    db = get_sync_db()
    try:
        # 查出已完成向量化的资产
        result = db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.id.in_(asset_ids),
                KnowledgeAsset.library_id == library_id,
                KnowledgeAsset.vector_status == "completed",
            )
        )
        assets = result.scalars().all()

        if not assets:
            logger.warning(f"未找到可索引的资产: library_id={library_id}")
            return {"status": "skipped", "message": "无可索引资产"}

        # 收集所有文本内容
        # 直接通过 ChromaDB collection.get() 按 library_id 获取已索引文本
        # 不使用 similarity_search（需要有效 query，且参数签名不匹配）
        from app.services.rag.vector_store import VectorStore

        vs = VectorStore()
        collection = vs.vectorstore._collection
        all_texts = []

        # 按资产逐个获取，确保只拉取 asset_ids 指定的资产
        for asset in assets:
            try:
                chroma_results = collection.get(
                    where={
                        "$and": [
                            {"library_id": library_id},
                            {"asset_id": asset.id},
                        ]
                    },
                    include=["documents"],
                )
                if chroma_results and chroma_results.get("documents"):
                    for doc_text in chroma_results["documents"]:
                        if doc_text and doc_text.strip():
                            all_texts.append(doc_text)
            except Exception as e:
                logger.warning(
                    f"获取资产文本失败 asset_id={asset.id}: {e}"
                )

        if not all_texts:
            logger.warning(f"资产中无文本内容: library_id={library_id}")
            return {"status": "skipped", "message": "资产无文本内容"}

        logger.info(
            f"准备插入图谱: library_id={library_id}, "
            f"texts={len(all_texts)}"
        )

        # 使用 asyncio.run 桥接异步调用
        asyncio.run(GraphStore.insert_documents(library_id, all_texts))

        logger.info(f"图索引构建完成: library_id={library_id}")
        return {
            "status": "success",
            "library_id": library_id,
            "indexed_assets": len(assets),
            "total_texts": len(all_texts),
        }

    except Exception as e:
        logger.error(f"图索引构建失败: {e}", exc_info=True)
        raise

    finally:
        db.close()
```

- [ ] **Step 2: 在 cleanup_library 中追加图谱清理**

在 `backend/app/tasks.py` 的 `cleanup_library` 函数中，在第 321 行（`vs.delete_library_documents(library_id)` 之后）插入：

```python

        # 1.5 清理 Neo4j 图谱数据（如果是系统知识库）
        try:
            from app.models.knowledge_library import KnowledgeLibrary as KLModel
            lib_result = db.execute(
                select(KLModel).where(KLModel.id == library_id)
            )
            lib = lib_result.scalar_one_or_none()
            if lib and lib.is_system:
                from app.services.rag.graph_store import GraphStore
                asyncio.run(GraphStore.delete_library(library_id))
                logger.info(f"Neo4j 图谱数据清理完成: library_id={library_id}")
        except Exception as e:
            logger.warning(f"图谱清理失败（非致命）: library_id={library_id}, {e}")
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/tasks.py
git commit -m "feat(tasks): add build_graph_index task and graph cleanup"
```

---

## Chunk 5: 收尾

### Task 9: 最终验证与提交

- [ ] **Step 1: 检查所有文件的语法正确性**

```bash
cd backend && python -c "
from app.core.config import settings
print('Config OK:', settings.NEO4J_URI[:20] if settings.NEO4J_URI else 'empty')
print('LightRAG dir:', settings.LIGHTRAG_WORKING_DIR)
"
```

Expected: 输出配置值，无 ImportError。

- [ ] **Step 2: 检查模块导入链**

```bash
cd backend && python -c "
from app.services.rag import GraphStore
from app.services.ai.tools import get_search_tools
from app.services.ai.graph.state import AgentState
print('All imports OK')
print('Tools (no graph):', len(get_search_tools()))
print('Tools (with graph):', len(get_search_tools(system_library_ids=[1])))
"
```

Expected:
```
All imports OK
Tools (no graph): 2
Tools (with graph): 3
```

- [ ] **Step 3: 检查所有修改文件的语法（py -m py_compile）**

```bash
cd backend && python -m py_compile app/services/rag/graph_store.py && \
python -m py_compile app/services/ai/tools.py && \
python -m py_compile app/services/ai/graph/state.py && \
python -m py_compile app/services/ai/graph/nodes.py && \
python -m py_compile app/services/ai/graph/workflow.py && \
python -m py_compile app/api/libraries.py && \
python -m py_compile app/tasks.py && \
echo "All files compile OK"
```

Expected: `All files compile OK`，无 SyntaxError。

- [ ] **Step 4: 验证 workflow.py 入口函数接受 system_library_ids**

```bash
cd backend && python -c "
import inspect
from app.services.ai.graph.workflow import run_agent, run_agent_with_checkpoint
sig1 = inspect.signature(run_agent)
sig2 = inspect.signature(run_agent_with_checkpoint)
assert 'system_library_ids' in sig1.parameters, 'run_agent missing system_library_ids'
assert 'system_library_ids' in sig2.parameters, 'run_agent_with_checkpoint missing system_library_ids'
print('Workflow signatures OK')
"
```

Expected: `Workflow signatures OK`

- [ ] **Step 5: 验证 API 端点注册**

```bash
cd backend && python -c "
from app.api.libraries import router
routes = [r.path for r in router.routes]
assert '/{library_id}/add-to-graph' in routes, f'Endpoint not found in {routes}'
print('API endpoint registered OK')
"
```

Expected: `API endpoint registered OK`

- [ ] **Step 6: 最终提交（如有遗漏修改）**

```bash
git status
# 如有未提交的修改，执行：
git add -A && git commit -m "chore: final cleanup for lightrag integration"
```
