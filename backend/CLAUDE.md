# CLAUDE.md

This file provides guidance to Agents when working with code in this repository.

## Project Overview

FastAPI backend for a multimodal AI interactive teaching agent (服务外包大赛 A04 赛题). Provides AI-powered courseware/PPT/lesson-plan generation, knowledge base RAG, classroom rehearsal, digital human, and Excel-driven data analysis. The frontend lives in a sibling `../teacher-platform` directory.

## Common Commands

```powershell
# Install dependencies (Python 3.11+)
pip install -r requirements.txt

# Run only the API (Redis/Postgres must already be available)
python run.py

# One-shot dev stack: brings up Redis + Postgres via Docker, then FastAPI + Celery worker
python start_dev.py

# Full Docker compose (frontend + backend + db + cache + worker)
docker compose up

# Tests
pytest tests -q
pytest tests/test_lesson_plan_api.py -q                  # single file
pytest tests/test_lesson_plan_api.py::test_name -q       # single test

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "describe change"

# Celery worker (must run for knowledge-asset parsing and PPT export tasks)
celery -A app.celery worker --loglevel=info -Q default,celery
```

API docs available at `/doc.html` (Swagger) and `/redoc.html` once the server is running.

## Architecture

### Request flow

`run.py` / `app/main.py` boots FastAPI with `lifespan` -> `init_db()` (auto-creates tables from `Base.metadata`). All routers are aggregated in `app/api/__init__.py` and mounted under `/api/v1`. PPT routes are an exception — they live in `app/generators/ppt/banana_routes.py` and are included via the `ppt_router` re-export.

Auth flows through `app/core/auth.py::get_current_user` (Bearer JWT), which checks `TokenBlacklist` on every request. Use the `CurrentUser` dependency in new endpoints.

### Layering (keep routers thin)

- `app/api/<feature>.py` — HTTP routing only; parse inputs, call services, return Pydantic schemas
- `app/schemas/<feature>.py` — Pydantic request/response models
- `app/services/<feature>.py` (or subpackages) — business logic; **this is where most code belongs**
- `app/models/<feature>.py` — SQLAlchemy 2.0 async ORM models; all must be imported in `app/models/__init__.py` so `Base.metadata` sees them
- `app/core/` — config, database session, JWT, logging, auth dependency
- `app/generators/` — output generators: `ppt/` (banana-slides integration), `docx_generator.py`, `game_generator.py`

### Async database

`app/core/database.py` uses SQLAlchemy async + asyncpg. Inject sessions via `Annotated[AsyncSession, Depends(get_db)]`. `get_db` auto-commits on success and rolls back on exception. On Windows + asyncpg, `NullPool` is used (pool reuse is unstable); don't add a connection pool size override for Windows dev. A separate sync engine (`get_sync_db()` in `app/tasks.py`) is used inside Celery workers.

### Celery & long-running work

`app/celery.py` defines a single `default` queue. Two task modules are auto-included: `app.tasks` (knowledge-asset parsing → chunking → vectorization, see `KnowledgeAssetProcessor`) and `app.generators.ppt.celery_tasks` (PPT generation/export). Tasks have a 30-min hard limit / 25-min soft limit. Workers need the same `.env` as the API.

### AI / RAG stack

- **LLM provider abstraction**: `app/generators/ppt/banana_providers.py` defines `TextProvider`/`ImageProvider` with implementations for Gemini (`GenAITextProvider`), OpenAI, and Anthropic. The active provider is selected by `AI_PROVIDER_FORMAT` in config. Use `get_text_provider_singleton()` / `get_image_provider_singleton()` rather than constructing providers manually.
- **Aliyun DashScope** (`app/services/ai/dashscope_service.py`) powers the default LLM/embedding/rerank/ASR/TTS/vision flows (`qwen-plus`, `tongyi-embedding-vision-flash`, `qwen3-vl-rerank`, etc).
- **LangGraph agent** (`app/services/ai/graph/`) — ReAct + Self-RAG loop with human-in-the-loop outline approval. Entry: `create_agent_graph()` in `workflow.py`; state in `state.py`; nodes in `nodes.py`.
- **RAG** (`app/services/rag/`) — `hybrid_retriever.py` combines BM25 + vector (Chroma, persisted at `CHROMA_PERSIST_DIR`); `reranker.py` uses Qwen rerank; `graph_store.py` integrates Neo4j + LightRAG.
- **Parsers** (`app/services/parsers/`) — `factory.py` dispatches to `pdf_parser`, `docx_parser`, `image_parser`, `video_parser` based on file type. Honors `MAX_VIDEO_KEYFRAMES`, `MAX_PDF_IMAGES_PER_PAGE`, `MAX_WORD_IMAGES` env vars.

### PPT subsystem (banana-slides)

`app/generators/ppt/` is a self-contained mini-app: its own models (`banana_models.py`), schemas, routes, providers, Celery tasks, and services (planning, intent, parsing, renovation, export). Its models are imported into the global `Base.metadata` via Alembic's `env.py`, so adding a column there still requires a regular `alembic revision --autogenerate`. The router mounts at `/api/v1/ppt/`.

### Static files & generated assets

`app/main.py` mounts `backend/media/` at `/media`. Generated PPTs, charts, parser outputs, and digital-human assets land here. Uploads go to `uploads/`. ChromaDB data persists at `chroma_data/`. None of these should be committed.

## Configuration

All config is read by `app/core/config.py::Settings` (pydantic-settings) from `backend/.env`. `.env.example` lists every required key — keep it in sync when adding new settings. Key categories:

- Database: `DATABASE_URL` (async, used by API) + `DATABASE_URL_SYNC` (used by Celery + Alembic)
- AI providers: `DASHSCOPE_API_KEY` (primary), plus optional `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DOUBAO_API_KEY`, `QWEN_API_KEY`, etc. — `AI_PROVIDER_FORMAT` selects which SDK shape is used
- External services: `OSS_*` (Aliyun OSS), `IFLYTEK_VMS_*` / `IFLYTEK_AVATAR_*` (digital human), `TAVILY_API_KEY` (web search), `DIFY_*` (resource recommendation), `NEO4J_*` (graph RAG), `EMAIL_SMTP_*`, `SMS_APPCODE`
- LightRAG working dir defaults to an absolute path anchored at `backend/lightrag_data/` (don't rely on CWD)

## Conventions

- Python 3.11+, PEP 8, 4-space indent. `snake_case` modules/functions, `PascalCase` classes/models, `UPPER_SNAKE_CASE` env keys/constants.
- Add new models to `app/models/__init__.py` exports — `app.main` does `from app.models import *` to register tables.
- All API responses go through Pydantic schemas in `app/schemas/`; do not return raw ORM objects.
- Commit messages use `feat:` / `bugfix:` / `docs:` prefixes with short imperative subjects.
- Tests live in `tests/` as `test_*.py`. Run a focused test first, then the full suite before larger changes.
