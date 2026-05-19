# CLAUDE-CN.md

本文件用于指导 Claude Code (claude.ai/code) 在本仓库工作。

## 项目概述

多模态 AI 互动式教学智能体后端（服务外包大赛 A04 赛题），基于 FastAPI 实现。提供 AI 驱动的课件 / PPT / 教案生成、知识库 RAG、课堂预演、数字人、Excel 数据分析等能力。前端位于同级目录 `../teacher-platform`。

## 常用命令

```powershell
# 安装依赖（Python 3.11+）
pip install -r requirements.txt

# 仅启动 API（需提前准备好 Redis / Postgres）
python run.py

# 一键开发栈：通过 Docker 起 Redis + Postgres，然后启动 FastAPI + Celery Worker
python start_dev.py

# 完整 Docker compose（前端 + 后端 + 数据库 + 缓存 + Worker）
docker compose up

# 测试
pytest tests -q
pytest tests/test_lesson_plan_api.py -q                  # 单文件
pytest tests/test_lesson_plan_api.py::test_name -q       # 单用例

# 数据库迁移
alembic upgrade head
alembic revision --autogenerate -m "describe change"

# Celery Worker（知识资产解析、PPT 导出等异步任务必需）
celery -A app.celery worker --loglevel=info -Q default,celery
```

启动后 API 文档位于 `/doc.html`（Swagger）和 `/redoc.html`。

## 架构

### 请求流转

`run.py` / `app/main.py` 启动 FastAPI，`lifespan` 阶段执行 `init_db()`（按 `Base.metadata` 自动建表）。所有路由在 `app/api/__init__.py` 聚合，统一挂载到 `/api/v1`。PPT 相关路由是例外——位于 `app/generators/ppt/banana_routes.py`，通过 `ppt_router` 重新导出并挂载。

认证经过 `app/core/auth.py::get_current_user`（Bearer JWT），每次请求都会校验 `TokenBlacklist`。新接口请使用 `CurrentUser` 依赖。

### 分层（路由保持轻量）

- `app/api/<feature>.py` —— 只做 HTTP 路由：解析入参、调用服务、返回 Pydantic schema
- `app/schemas/<feature>.py` —— Pydantic 请求/响应模型
- `app/services/<feature>.py`（或子包）—— 业务逻辑，**绝大部分代码放这里**
- `app/models/<feature>.py` —— SQLAlchemy 2.0 异步 ORM 模型；必须在 `app/models/__init__.py` 中导入，否则 `Base.metadata` 看不到
- `app/core/` —— 配置、数据库 Session、JWT、日志、认证依赖
- `app/generators/` —— 输出生成：`ppt/`（banana-slides 集成）、`docx_generator.py`、`game_generator.py`

### 异步数据库

`app/core/database.py` 使用 SQLAlchemy async + asyncpg。Session 通过 `Annotated[AsyncSession, Depends(get_db)]` 注入。`get_db` 在成功时自动 commit，异常时 rollback。在 Windows + asyncpg 下使用 `NullPool`（连接池复用不稳），开发环境**不要**覆盖该行为。Celery Worker 内部使用独立的同步引擎（`app/tasks.py` 中的 `get_sync_db()`）。

### Celery 与长耗时任务

`app/celery.py` 定义单一 `default` 队列。auto-include 两个任务模块：`app.tasks`（知识资产解析 → 切片 → 向量化，见 `KnowledgeAssetProcessor`）和 `app.generators.ppt.celery_tasks`（PPT 生成/导出）。任务硬超时 30 分钟、软超时 25 分钟。Worker 需要与 API 相同的 `.env`。

### AI / RAG 技术栈

- **LLM Provider 抽象**：`app/generators/ppt/banana_providers.py` 定义 `TextProvider` / `ImageProvider`，含 Gemini（`GenAITextProvider`）、OpenAI、Anthropic 实现。当前 Provider 由配置中 `AI_PROVIDER_FORMAT` 决定。请使用 `get_text_provider_singleton()` / `get_image_provider_singleton()`，不要直接 new。
- **阿里云百炼 DashScope**（`app/services/ai/dashscope_service.py`）支撑默认的 LLM / Embedding / Rerank / ASR / TTS / Vision 链路（`qwen-plus`、`tongyi-embedding-vision-flash`、`qwen3-vl-rerank` 等）。
- **LangGraph Agent**（`app/services/ai/graph/`）—— ReAct + Self-RAG 闭环，带大纲确认人机协作。入口：`workflow.py` 中的 `create_agent_graph()`；状态在 `state.py`；节点在 `nodes.py`。
- **RAG**（`app/services/rag/`）—— `hybrid_retriever.py` 组合 BM25 + 向量（Chroma 持久化在 `CHROMA_PERSIST_DIR`）；`reranker.py` 使用 Qwen 重排；`graph_store.py` 接入 Neo4j + LightRAG。
- **解析器**（`app/services/parsers/`）—— `factory.py` 按文件类型分发到 `pdf_parser`、`docx_parser`、`image_parser`、`video_parser`。受 `MAX_VIDEO_KEYFRAMES`、`MAX_PDF_IMAGES_PER_PAGE`、`MAX_WORD_IMAGES` 环境变量约束。

### PPT 子系统（banana-slides）

`app/generators/ppt/` 是自包含的"迷你应用"：自带模型（`banana_models.py`）、schema、路由、Provider、Celery 任务、各种服务（planning、intent、parsing、renovation、export）。其模型通过 Alembic `env.py` 注册到全局 `Base.metadata`，**仍需正常执行** `alembic revision --autogenerate`。路由挂载在 `/api/v1/ppt/`。

### 静态文件与生成资产

`app/main.py` 把 `backend/media/` 挂载到 `/media`。生成的 PPT、图表、解析产物、数字人资产都落在这里。上传文件落在 `uploads/`。ChromaDB 数据持久化在 `chroma_data/`。这些目录都**不应**提交。

## 配置

所有配置由 `app/core/config.py::Settings`（pydantic-settings）从 `backend/.env` 读取。`.env.example` 列出全部必要键，新增配置时需同步更新。主要类别：

- 数据库：`DATABASE_URL`（异步，API 使用）+ `DATABASE_URL_SYNC`（Celery、Alembic 使用）
- AI Provider：`DASHSCOPE_API_KEY`（主）+ 可选 `GOOGLE_API_KEY`、`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`DOUBAO_API_KEY`、`QWEN_API_KEY` 等；`AI_PROVIDER_FORMAT` 决定使用哪种 SDK 形态
- 外部服务：`OSS_*`（阿里云 OSS）、`IFLYTEK_VMS_*` / `IFLYTEK_AVATAR_*`（数字人）、`TAVILY_API_KEY`（网络搜索）、`DIFY_*`（资源推荐）、`NEO4J_*`（图谱 RAG）、`EMAIL_SMTP_*`、`SMS_APPCODE`
- LightRAG 工作目录默认锚定为绝对路径 `backend/lightrag_data/`（避免 CWD 差异）

## 约定

- Python 3.11+、PEP 8、4 空格缩进。模块/函数 `snake_case`、类/模型 `PascalCase`、环境键/常量 `UPPER_SNAKE_CASE`。
- 新增模型必须加入 `app/models/__init__.py` 的导出 —— `app.main` 通过 `from app.models import *` 注册表结构。
- 所有 API 响应通过 `app/schemas/` 中的 Pydantic schema；不要直接返回 ORM 对象。
- 提交信息使用 `feat:` / `bugfix:` / `docs:` 前缀，使用祈使语气。
- 测试位于 `tests/`，命名 `test_*.py`。大改前先跑相关用例，再跑全量。
