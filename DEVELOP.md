# 开发日志

## RAG 系统功能总结

> 记录日期：2026-02-24

### 概述

本项目实现了一套多层次的混合检索增强生成（RAG）系统，服务于多模态 AI 教学平台的智能备课功能。系统由向量检索、关键词检索、混合融合、文本分割、文档摄入和 LangGraph 工作流等模块组成。

---

### 核心模块

#### 1. 向量存储（`services/rag/vector_store.py`）

- **后端**：ChromaDB，持久化目录 `chroma_data/`
- **Embedding 模型**（按优先级）：
  1. 阿里云 DashScope（默认，`tongyi-embedding-vision-flash` 等）
  2. OpenAI `text-embedding-3-small`（可选）
  3. HuggingFace `m3e-base`（兜底）
- **核心功能**：
  - `add_documents()`：将解析结果写入 ChromaDB，带 `user_id` 元数据
  - `similarity_search()`：按 `user_id` 过滤的向量相似度检索
  - `delete_user_documents()`：删除指定用户的文档

#### 2. BM25 关键词检索（`services/rag/hybrid_retriever.py`）

- 使用 `jieba` 分词（中文优化）+ 正则英文分词
- 每个用户独立维护内存中的 BM25 索引（`BM25Okapi`）
- 仅返回得分 > 0 的结果，过滤无关文档

#### 3. 混合检索与重排（`services/rag/hybrid_retriever.py`）

`HybridRetriever` 整合向量检索与 BM25 检索，支持两种融合策略：

| 策略 | 说明 |
|------|------|
| **RRF（倒数排名融合）**（默认） | `score = Σ 1/(rank + 60)`，减少极端值影响 |
| **加权融合** | 独立归一化后按权重合并（默认各 0.5） |

检索流程：向量取 `k*2` 条 → BM25 取 `k*2` 条 → 融合去重 → 返回 top-k（默认 10）。

**用户隔离**：所有向量检索通过 `filter={"user_id": user_id}` 实现多租户隔离。

#### 4. 文本分割（`services/rag/text_splitter.py`）

支持两种分块策略：

| 策略 | 说明 |
|------|------|
| **语义分块**（优先） | `SemanticChunker`，检测语义断点，按含义边界切分；阈值类型 `percentile`，默认 0.95 |
| **递归字符分块**（兜底） | `RecursiveCharacterTextSplitter`，块大小 800 字符，重叠 150 字符；分隔符按段落→句子→词→字符优先级 |

输出格式：`ParsedChunk`（含 `source`、`page`、`chunk_index`、`chunking_method`、`user_id` 等元数据）。

#### 5. 文档摄入流水线（`tasks.py`，Celery 后台任务）

```
上传文件 → 创建 DB 记录（vector_status=False）
    → Celery 任务 process_knowledge_asset()
        → 解析文件（ParserFactory，支持 PDF/DOCX/视频/图片）
        → 语义分块（失败则回退递归分块）
        → 写入 ChromaDB（add_documents）
        → 更新 DB（vector_status=True，记录 chunk_count/image_count）
```

- 重试策略：最多 3 次，指数退避（1s → 2s → 4s，最大 10 min）
- 图片/视频限制：每页最多 2 张图、视频最多 15 帧、Word 最多 10 张图

#### 6. LangGraph 工作流集成（`services/ai/graph/`）

RAG 检索嵌入状态机的 **tools 节点**，由 LLM（agent 节点）自主决策是否调用：

| 节点 | 功能 |
|------|------|
| **agent** | LLM 决策：调用检索工具还是直接生成 |
| **tools** | 执行 `search_local_knowledge`（混合 RAG）或 `search_web`（Tavily/DuckDuckGo） |
| **grader** | Self-RAG 质量评估：相关性 + 事实接地性；不通过则重试 |
| **outline_approval** | 中断点，等待用户确认/修改大纲 |
| **finalize** | 根据知识库扩展大纲，生成最终 JSON |

检索工具：
- `search_local_knowledge(query, user_id, k)`：调用 `HybridRetriever`
- `search_web(query)`：调用 Tavily API（兜底 DuckDuckGo）

#### 7. 知识库 API（`api/knowledge.py`、`api/chat.py`）

- `POST /api/v1/knowledge`：上传文件，触发后台向量化
- `GET/PATCH/DELETE /api/v1/knowledge/{id}`：知识资产的增删改查
- `POST /api/v1/chat/outline`：触发 RAG 检索 + 大纲生成（含断点等待）
- `POST /api/v1/chat/resume`：用户确认大纲后继续生成

---

### 已知问题

| 问题 | 位置 | 说明 |
|------|------|------|
| 缺少导入 | `tasks.py:115` | `split_documents_semantic` 未导入 |
| BM25 索引不持久化 | `hybrid_retriever.py` | 重启后内存索引丢失，首次检索重建 |
| Chat 端点为占位实现 | `api/chat.py` | `/api/v1/chat` 未与 LangGraph 工作流集成 |

---

### 技术栈一览

| 维度 | 实现 |
|------|------|
| 向量数据库 | ChromaDB（本地持久化） |
| Embedding | DashScope / OpenAI / HuggingFace M3E |
| 关键词检索 | BM25Okapi + jieba |
| 融合策略 | RRF（默认）/ 加权融合 |
| 工作流引擎 | LangGraph + MemorySaver 检查点 |
| 质量控制 | Self-RAG（相关性 + 接地性） |
| 异步任务 | Celery + Redis Broker |
| 多租户隔离 | user_id 元数据过滤 |

## 知识库系统开发（2026-02-24）

### 新增功能
- `KnowledgeLibrary` 模型：用户可创建多个知识库，管理员库可公开
- `User` 增加 `is_admin` 字段，管理员由数据库直接写入
- `VectorStatus` 枚举：`pending / processing / completed / failed`
- `library_id` 注入 ChromaDB metadata，实现单 collection 多库隔离
- `GET /api/v1/libraries?scope=personal|system` 分区展示
- `GET /api/v1/knowledge/{id}/status` 轻量轮询端点
- `cleanup_library` Celery 任务：软删除 + 异步清理向量/文件/DB

### 架构决策
- 采用单 ChromaDB collection + metadata `$in` 过滤（非多 collection）：多库联合检索只需一次向量查询，避免跨 collection 合并重排
- 删除知识库用软删除（`is_deleted=True`）立即返回，Celery 异步清理，避免多组件级联删除的部分失败脏数据问题

### 修复
- 修复 `main.py` FastAPI() 构造函数缺少逗号的语法错误
- 修复 `tasks.py` 中 `split_documents_semantic` 未导入的 bug
