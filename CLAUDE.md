# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

多模态 AI 互动式教学智能体 — 全栈智能备课平台。后端 Python/FastAPI，前端 Vue 3/Vite，单 git 仓库。

子项目各自有更详细的 CLAUDE.md / CLAUDE-CN.md，进入对应目录工作前先看一眼：

- `backend/CLAUDE.md` · `backend/CLAUDE-CN.md` — FastAPI 后端（分层、async DB、Celery、AI/RAG 栈、PPT 子系统）
- `teacher-platform/CLAUDE.md` · `teacher-platform/CLAUDE-CN.md` — Vue 3 前端（路由守卫、HTTP 层、Pinia stores、视图组织）

# Rules

- 在进行开发之前需要向用户提问，确保双方完全理解需求或用户要求后再完成开发任务。
- 开发任务要求见ISSUES.md文档,在开发前必须确保当前处在非main分支上
- 注意这是一个小团队竞赛类项目且代码位于私有团队仓库，所以无密钥泄露风险，所以可以把密钥直接放在.env文件里
- 并发量不会太大，所以不用太过于关心并发风险,重点在业务功能的实现上
- 赛题要求可以参见赛题信息.md 
- git提交记录不要包含Co-Authored-By

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# Git Commit Rules

## Behavior
When generating git commit messages:
- **Strictly Forbidden**: Never include text indicating the message was AI-generated (e.g., "Written by Claude", "AI-generated").
- **No Footers**: Do not append "Signed-off-by" or "Co-authored-by" lines unless explicitly told to do so for a specific human user.
- **Direct Output**: Output the commit message immediately without introductory text (e.g., skip "Sure, here is the commit...").

## Format Standard
- Use the Conventional Commits format: `<type>(<scope>): <subject>`
- Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.
- Keep the first line under 72 characters.

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

# 运行测试（推荐先跑相关测试，再跑全量）
pytest tests -q
pytest tests/test_lesson_plan_api.py -q                # 单文件
pytest tests/test_lesson_plan_api.py::test_name -q     # 单用例

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
docker compose up           # 启动所有服务：frontend, app, db, cache, worker
docker compose up db cache  # 仅启动基础设施
```

## 架构

### 仓库结构

- `backend/` — FastAPI 后端（Python 3.11+）
- `teacher-platform/` — 前端Vue 3 单页应用

### 后端分层

```
backend/app/
├── api/          # FastAPI 路由（auth, courseware, chat, knowledge, lesson_plan,
│                 #   question_paper, mindmap, resource_search, rehearsal, ...）
├── schemas/      # Pydantic 请求/响应模型
├── services/     # 业务逻辑层
│   ├── ai/       # LLM 集成（DashScope/通义千问）、ASR、视觉理解
│   │   └── graph/  # LangGraph 工作流（ReAct + Self-RAG + 人机交互）
│   ├── parsers/  # 文档解析器（PDF、DOCX、视频、图片），工厂模式
│   ├── rag/      # ChromaDB 向量库、混合检索（BM25 + 语义）、Neo4j/LightRAG 图谱
│   ├── data_analysis/    # Excel → 图表 LLM 链路
│   ├── rehearsal_*.py    # 课堂预演（会话/媒体/生成）
│   └── ...
├── models/       # SQLAlchemy ORM；新模型必须加入 __init__.py 导出
├── generators/   # 内容生成器
│   ├── ppt/      # banana-slides PPT 子系统（自带 model/schema/route/Celery）
│   ├── docx_generator.py
│   └── game_generator.py
├── core/         # 配置（pydantic-settings）、数据库、JWT、认证依赖
└── tasks.py      # Celery 任务（知识资产解析 → 切片 → 向量化）
```

所有 API 路由挂载在 `/api/v1` 下；PPT 路由通过 `app/generators/ppt/banana_routes.py` 单独并入 `/api/v1/ppt`。Swagger 文档地址 `/doc.html`（不是 `/docs`），ReDoc 在 `/redoc.html`。

### LangGraph 工作流

核心 AI 流水线位于 `app/services/ai/graph/`，是一个状态机：

1. **agent** — LLM 决策：调用工具还是直接生成答案
2. **tools** — 执行检索/搜索工具调用
3. **grader** — Self-RAG 质量评估；不通过则回到 agent 重试
4. **outline_approval** — **中断点**，等待用户对大纲的确认/修改
5. **finalize** — 生成最终输出

状态定义在 `AgentState`（TypedDict + `add_messages` reducer）。通过 `MemorySaver` 实现检查点，支持用户确认后恢复执行。

### 核心设计模式

- **全异步**：API 用 `asyncpg` + SQLAlchemy async session；Celery Worker 用独立同步引擎（`app/tasks.py::get_sync_db()`）
- **Windows 连接池**：`app/core/database.py` 在 Windows + asyncpg 下强制 `NullPool`（连接池复用不稳，不要覆盖）
- **依赖注入**：FastAPI `Depends()` 管理认证和数据库会话；新接口用 `CurrentUser` 依赖
- **Celery 异步任务**：解析/向量化/PPT 导出后台执行，硬超时 30 分钟、软超时 25 分钟；带重试 + 指数退避
- **工厂模式**：`services/parsers/factory.py` 和 `generators/factory.py` 按文件类型分发
- **LLM Provider 抽象**：`app/generators/ppt/banana_providers.py` 提供 Gemini/OpenAI/Anthropic 实现，由 `AI_PROVIDER_FORMAT` 选择；用 `get_text_provider_singleton()` 而非直接 new
- **用户隔离**：所有数据查询按 `user_id` 过滤；ChromaDB 元数据带 `user_id` + `library_id`
- **JWT 认证**：Bearer Token + `TokenBlacklist` 检查；bcrypt 密码哈希，24 小时过期

### 前端结构

- Vue Router 带认证守卫（`src/router/index.js`）：首次导航时通过 `userStore.fetchUser()` 恢复登录态，再决定是否放行；`requiresAuth` + `layout: 'nav'` 控制布局
- Pinia store（`stores/user.js` 是登录态唯一来源；`stores/ppt.js` 含意图状态机依赖 `@/utils/pptIntent.js`）
- 备课中心 `views/LessonPrep.vue` 是 tab 壳子，挂载 PPT / 教案 / 动画 / 知识图谱 / 思维导图 / 数据分析
- PPT 子流程在 `views/ppt/`（PptIndex → PptHome → PptDialog → PptDescription → PptOutline → PptPreview）
- 预演播放器在 `views/rehearsal/` + `components/rehearsal/`，引擎是 composable（`usePlaybackEngine`）
- 管理后台 `views/admin/` 在 `LayoutWithNav` 内由 `userStore.userInfo?.is_admin` 控制
- HTTP 层 `src/api/http.js` 是唯一入口：`apiRequest` / `authFetch` 自动附加 Bearer，401（非 auth 路径）自动跳 `/login` —— 不要写裸 `fetch`，也不要手动加 token

### Vite 代理（开发环境）

`teacher-platform/vite.config.js` 转发：`/api` 和 `/media` → `http://localhost:8000`；`/vmss` → 讯飞数字人主机；`/individuation` → 讯飞个性化资源。**前端代码走相对路径**，不要拼绝对后端 URL。

### 基础设施

- **PostgreSQL 15**：主数据库（通过 `asyncpg` 异步访问）
- **Redis 7**：Celery Broker + 缓存
- **ChromaDB**：向量数据库，持久化在 `backend/chroma_data/`
- **AI 服务**：DashScope（阿里云百炼/通义千问）为主要 LLM/Embedding/视觉/语音服务；OpenAI 和 Anthropic 为可选备选

### 配置管理

所有配置通过环境变量加载，来源为 `backend/.env`（模板见 `.env.example`）。由 `pydantic-settings` 在 `app/core/config.py` 中管理，使用 `lru_cache` 实现单例。

关键变量：`DATABASE_URL`（异步，API 用）+ `DATABASE_URL_SYNC`（Celery / Alembic 用）、`REDIS_URL`、`DASHSCOPE_API_KEY`、`AI_PROVIDER_FORMAT`、`LLM_MODEL`、`EMBEDDING_MODEL`、`JWT_SECRET_KEY`、`TAVILY_API_KEY`、`NEO4J_*`、`OSS_*`、`IFLYTEK_VMS_*`。`LIGHTRAG_WORKING_DIR` 默认锚定 `backend/lightrag_data/` 的绝对路径，不依赖 CWD。
