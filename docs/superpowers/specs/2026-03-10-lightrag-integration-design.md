# LightRAG 图检索集成设计

## 概述

在现有 LangChain+ChromaDB 向量检索基础上，集成 LightRAG 图检索能力，为系统级知识库提供知识图谱支持。图数据存储于 Neo4j Aura 云端，通过 LightRAG 原生 workspace 机制实现多知识库标签隔离。

## 核心决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 集成方式 | 直接使用 `lightrag-hku` 库 | 利用其 Neo4j 存储、实体抽取、多模式检索能力 |
| 隔离策略 | LightRAG workspace（Neo4j Label） | 原生支持，零改造，每个知识库独立 Label |
| 路由策略 | Agent 自主工具选择 | 利用 LangGraph 的 Agent 节点自主决策 |
| 图索引触发 | 管理员手动触发（HTTP 202 异步） | 控制 token 开销，Celery 后台执行 |
| LLM/Embedding | 复用 DashScope/Qwen | 统一模型配置 |
| 去重机制 | LightRAG 原生哈希校验 | 无需额外数据库字段 |

## 前置条件

Neo4j Aura 凭据必须从 `ISSUES.md` 移至 `backend/.env`，在任何功能代码提交之前完成。

## 架构

### 整体数据流

```
用户查询
  │
  ▼
LangGraph Agent 节点（LLM 决策工具调用）
  │
  ├─ search_local_knowledge  ──► HybridRetriever (Chroma+BM25)
  │                                    │
  ├─ search_knowledge_graph  ──► GraphStore (LightRAG/Neo4j)
  │                                    │
  └─ search_web              ──► Tavily/DuckDuckGo
  │
  ▼
Agent 自然融合多工具结果 → 生成回答
```

### 工具动态绑定

当前的 `create_agent_node()` 在模块加载时绑定工具，需要改为**按请求动态绑定**。

具体实现：
1. 在 `AgentState` 中新增 `system_library_ids: list[int]` 字段，记录用户选中的系统知识库 ID
2. `create_agent_node()` 改为接受 state 参数，根据 `system_library_ids` 是否非空决定工具列表
3. 若 `system_library_ids` 非空 → 绑定三个工具（向量 + 图谱 + 网络搜索）
4. 若 `system_library_ids` 为空 → 绑定两个工具（向量 + 网络搜索）

## 组件设计

### 1. GraphStore（`services/rag/graph_store.py`）

LightRAG 的薄封装，职责：

- **DashScope 适配**：将 DashScope LLM/Embedding API 适配为 LightRAG 要求的函数签名
- **实例管理**：按 `library_id` 缓存 LightRAG 实例，每个实例对应一个 workspace
- **workspace 隔离**：`workspace=f"library_{library_id}"`，LightRAG 自动在 Neo4j 中为该 workspace 的所有节点打上对应 Label
- **错误处理**：Neo4j 不可用或 LightRAG 异常时返回错误字符串，不中断 Agent 流程

```python
class GraphStore:
    _instances: dict[str, LightRAG]  # workspace → LightRAG 实例

    async def get_instance(library_id: int) -> LightRAG
    async def insert_documents(library_id: int, texts: list[str]) -> str
    async def query(library_id: int, query: str, mode: str = "hybrid") -> str
    async def delete_library(library_id: int)
```

**DashScope 适配函数签名**：

LightRAG 要求的 `llm_model_func` 签名：
```python
async def dashscope_llm_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict] = [],
    keyword_extraction: bool = False,
    stream: bool = False,
    **kwargs
) -> str:
    """通过 httpx 调用 DashScope OpenAI 兼容接口，返回文本响应"""
```

LightRAG 要求的 `embedding_func` 签名：
```python
# 包装为 EmbeddingFunc 对象
EmbeddingFunc(
    embedding_dim=1024,  # DashScope embedding 维度
    max_token_size=2048,
    func=async_dashscope_embed  # async (texts: list[str]) -> np.ndarray
)
```

两个适配函数均直接调用 DashScope OpenAI 兼容 API（httpx），不复用现有 LangChain 包装的 `DashScopeService` 类，因为 LightRAG 的接口签名与 LangChain `BaseChatModel` 不兼容。

**LightRAG 配置**：

| 参数 | 值 | 说明 |
|------|----|------|
| graph_storage | `"Neo4JStorage"` | Neo4j Aura 云端 |
| kv_storage | `"JsonKVStorage"` | 本地 JSON，存实体/关系摘要 |
| vector_storage | `"NanoVectorDBStorage"` | LightRAG 内部向量检索 |
| working_dir | `{LIGHTRAG_WORKING_DIR}/library_{id}/` | 绝对路径，锚定 backend/ 目录 |
| workspace | `library_{id}` | Neo4j Label 隔离 |
| llm_model_func | dashscope_llm_func | DashScope 适配 |
| embedding_func | EmbeddingFunc(func=async_dashscope_embed) | DashScope 适配 |

> 注意：`LIGHTRAG_WORKING_DIR` 通过 `Path(__file__).resolve()` 锚定到 `backend/` 目录，无论从哪个 CWD 启动服务或脚本，都指向同一物理路径 `backend/lightrag_data/`。Docker 部署时需将其挂载为持久化 Volume。

### 2. 搜索工具（`services/ai/tools.py`）

新增独立工具，与现有 `search_local_knowledge` 并列：

```python
search_knowledge_graph:
    描述: "搜索系统知识图谱，获取全局上下文、实体关系和知识脉络。
          适用于总结、概述、关系梳理、对比分析等宏观问题。
          仅可用于系统级知识库。"
    参数:
      - query: str       # 搜索查询
      - mode: str        # 检索模式 (local/global/hybrid)，默认 hybrid
```

**`library_id` 注入方式**：`search_knowledge_graph` 不暴露 `library_id` 参数给 LLM。在工具构造时，通过闭包/partial 将当前会话的 `system_library_ids` 注入。工具实现内部遍历所有选中的系统知识库进行查询，合并结果返回。模式与现有 `search_local_knowledge` 注入 `user_id` 相同。

**错误处理**：与现有工具一致，异常时返回错误字符串（如"图谱检索暂不可用"），Agent 可回退到向量检索。

**Agent system prompt 新增工具选择指导**（追加到现有 prompt 的规则部分）：

```
- 当需要查找具体定义、公式、原文引用等细节时，使用 search_local_knowledge
- 当需要全局概述、知识脉络、关系梳理或对比分析时，使用 search_knowledge_graph
- 对于复杂的教学设计任务，可同时调用两个工具：先获取全局知识框架，再补充具体细节
```

### 3. 图索引 API（`api/libraries.py`）

```
POST /api/v1/libraries/{id}/add-to-graph

请求体: { "asset_ids": [1, 2, 3] }
响应:   HTTP 202 Accepted, { "task_id": "celery-task-uuid" }

权限: 仅管理员，仅 is_system=True 的知识库
```

流程：
1. 校验权限和知识库类型
2. 将 asset_ids 推入 Celery 队列
3. 立即返回 HTTP 202 + task_id

任务状态可通过 Celery 的 Redis result backend 查询（使用 `AsyncResult(task_id).state`），无需在数据库模型中新增状态字段。

### 4. Celery 图索引任务（`tasks.py`）

```python
@celery_app.task(bind=True, base=CallbackTask, max_retries=3,
                 default_retry_delay=60, retry_backoff=True)
def build_graph_index(self, library_id: int, asset_ids: list[int]):
    # 1. 从 PostgreSQL 查出指定资产的已解析文本
    # 2. 使用 asyncio.run() 桥接异步调用（与现有 process_knowledge_asset 模式一致）
    # 3. 调用 GraphStore.insert_documents(library_id, texts)
    # 4. LightRAG 内部处理：实体抽取 → 关系构建 → 写入 Neo4j
    # 5. 去重由 LightRAG doc_status_storage 的哈希校验自动完成
```

### 5. 清理集成（`tasks.py` 现有 `cleanup_library` 任务）

在现有的 `cleanup_library` Celery 任务中追加图谱清理步骤：

```python
# 现有流程：删除 ChromaDB 向量 → 删除文件 → 删除 DB 记录
# 新增：若该库为系统库，调用 GraphStore.delete_library(library_id) 清理 Neo4j 数据
```

## 配置变更

### `backend/app/core/config.py` 新增

```python
# ========== Neo4j 图数据库 ==========
NEO4J_URI: str = ""
NEO4J_USERNAME: str = "neo4j"
NEO4J_PASSWORD: str = ""

# ========== LightRAG ==========
# 动态计算绝对路径，锚定到 backend/ 目录，避免 CWD 不同导致路径分裂
LIGHTRAG_WORKING_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "lightrag_data")
```

### `backend/.env.example` 新增

```bash
# ========== Neo4j Graph Database ==========
NEO4J_URI=neo4j+s://your-neo4j-aura-uri
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# ========== LightRAG ==========
LIGHTRAG_WORKING_DIR=lightrag_data
```

### `backend/requirements.txt` 新增

```
lightrag-hku
neo4j>=5.0.0
```

### `.gitignore` 确认包含

```
lightrag_data/
```

## AgentState 变更

在 `backend/app/services/ai/graph/state.py` 的 `AgentState` TypedDict 中新增：

```python
system_library_ids: list[int]  # 用户选中的系统知识库 ID 列表，为空则不绑定图谱工具
```

## 变更清单

| 组件 | 文件 | 变更类型 |
|------|------|---------|
| GraphStore | `backend/app/services/rag/graph_store.py` | 新增 |
| RAG 模块导出 | `backend/app/services/rag/__init__.py` | 修改 |
| 图谱搜索工具 | `backend/app/services/ai/tools.py` | 修改 |
| Agent 状态 | `backend/app/services/ai/graph/state.py` | 修改 |
| Agent 节点 | `backend/app/services/ai/graph/nodes.py` | 修改 |
| 图索引 API | `backend/app/api/libraries.py` | 修改 |
| Celery 任务 | `backend/app/tasks.py` | 修改（新增任务 + 清理集成） |
| 配置 | `backend/app/core/config.py` | 修改 |
| 环境变量 | `backend/.env` | 修改 |
| 环境模板 | `backend/.env.example` | 修改 |
| 依赖 | `backend/requirements.txt` | 修改 |
| 凭据清理 | `ISSUES.md` | 修改（移除凭据） |

## 不变更的内容

- 数据库 ORM 模型无变更（不新增字段）
- 现有向量检索逻辑不变
- 现有 HybridRetriever 不变
- 前端暂不在本次变更范围内
