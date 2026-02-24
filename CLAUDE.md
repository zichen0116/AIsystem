# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

多模态 AI 互动式教学智能体 — 全栈智能备课平台。后端 Python/FastAPI，前端 Vue 3/Vite。

在进行开发之前需要向用户提问，确保双方完全理解需求或用户要求后再完成开发任务。

开发任务要求见ISSUES.md文档,在开发前必须确保在处在非main分支上

赛题要求可以参见赛题信息.md

## 开发命令

### 后端（在 `backend/` 目录下执行）

```bash
# 一键启动开发环境（自动拉起 Docker 容器 + FastAPI + Celery）
python start_dev.py

# 仅启动 FastAPI（需提前运行 PostgreSQL + Redis）
python run.py

# 启动 Celery Worker
python -m celery -A app.celery worker --loglevel=info

# 数据库迁移
alembic revision --autogenerate -m "迁移描述"
alembic upgrade head

# 运行测试（无全局 pytest 配置，按文件执行）
python -m pytest tests/test_all_parsers.py
python -m pytest tests/test_hybrid_retriever.py

# 安装依赖
pip install -r requirements.txt
```

### 前端（在 `teacher-platform/` 目录下执行）

```bash
npm install
npm run dev      # Vite 开发服务器
npm run build    # 生产构建
npm run preview  # 预览生产构建
```

### Docker（在 `backend/` 目录下执行）

```bash
docker-compose up           # 启动所有服务：app, db, cache, worker
docker-compose up db cache  # 仅启动基础设施
```

## 架构

### 仓库结构

- `backend/` — FastAPI 后端（Python 3.11+）
- `teacher-platform/` — 前端Vue 3 单页应用

### 后端分层

```
backend/app/
├── api/          # FastAPI 路由（auth, courseware, chat, knowledge）
├── schemas/      # Pydantic 请求/响应模型
├── services/     # 业务逻辑层
│   ├── ai/       # LLM 集成（DashScope/通义千问）、语音识别、视觉理解
│   │   └── graph/  # LangGraph 工作流（ReAct + Self-RAG + 人机交互）
│   ├── parsers/  # 文档解析器（PDF、DOCX、视频、图片），工厂模式
│   └── rag/      # 向量库（ChromaDB）、混合检索（BM25 + 语义）、文本分割
├── models/       # SQLAlchemy ORM（users, courseware, chat_history, knowledge_assets）
├── generators/   # 内容生成器（PPT、DOCX、小游戏），工厂模式
├── core/         # 配置（pydantic-settings）、数据库、认证/安全、依赖注入
└── utils/        # 公共工具
```

所有 API 路由挂载在 `/api/v1` 下，Swagger 文档地址 `/docs`。

### LangGraph 工作流

核心 AI 流水线位于 `app/services/ai/graph/`，是一个状态机：

1. **agent** — LLM 决策：调用工具还是直接生成答案
2. **tools** — 执行检索/搜索工具调用
3. **grader** — Self-RAG 质量评估；不通过则回到 agent 重试
4. **outline_approval** — **中断点**，等待用户对大纲的确认/修改
5. **finalize** — 生成最终输出

状态定义在 `AgentState`（TypedDict + `add_messages` reducer）。通过 `MemorySaver` 实现检查点，支持用户确认后恢复执行。

### 核心设计模式

- **全异步**：数据库操作使用 `asyncpg` + SQLAlchemy async session
- **依赖注入**：FastAPI `Depends()` 管理认证和数据库会话
- **Celery 异步任务**：文档解析/向量化在后台执行，带重试 + 指数退避（`app/tasks.py`）
- **工厂模式**：`services/parsers/factory.py` 和 `generators/factory.py` 按文件类型选择实现
- **用户隔离**：所有数据查询按 `user_id` 过滤，实现多租户
- **JWT 认证**：Bearer Token（`python-jose`），bcrypt 密码哈希，24 小时过期

### 前端结构

- Vue Router 带认证守卫；未登录显示 `LoginView`，已登录进入仪表盘
- Pinia store（`stores/user.js`）管理认证状态
- 页面：Home、LessonPrep、CoursewareManage、KnowledgeBase、PersonalCenter
- 所有未匹配路由回退到 `/`

### 基础设施

- **PostgreSQL 15**：主数据库（通过 `asyncpg` 异步访问）
- **Redis 7**：Celery Broker + 缓存
- **ChromaDB**：向量数据库，持久化在 `backend/chroma_data/`
- **AI 服务**：DashScope（阿里云百炼/通义千问）为主要 LLM/Embedding/视觉/语音服务；OpenAI 和 Anthropic 为可选备选

### 配置管理

所有配置通过环境变量加载，来源为 `backend/.env`（模板见 `.env.example`）。由 `pydantic-settings` 在 `app/core/config.py` 中管理，使用 `lru_cache` 实现单例。

关键变量：`DATABASE_URL`、`REDIS_URL`、`DASHSCOPE_API_KEY`、`LLM_MODEL`、`EMBEDDING_MODEL`、`JWT_SECRET_KEY`、`TAVILY_API_KEY`。
