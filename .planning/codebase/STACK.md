# Technology Stack

**Analysis Date:** 2026-04-12

## Languages

**Primary:**
- Python `>=3.11` - backend API, async workers, RAG, and media generation in `backend/app/`, declared in `backend/pyproject.toml` and built from `python:3.11-slim-bookworm` in `backend/Dockerfile`.
- JavaScript ES modules - frontend SPA and browser-side integrations in `teacher-platform/src/`, declared with `"type": "module"` in `teacher-platform/package.json`.

**Secondary:**
- Vue Single-File Components - UI composition in `teacher-platform/src/**/*.vue`, built with Vite from `teacher-platform/vite.config.js`.
- CSS - global and component styling in `teacher-platform/src/style.css` and `<style scoped>` blocks such as `teacher-platform/src/components/DigitalHumanAssistant.vue`.
- TypeScript/TSX (vendored SDK/demo only) - present in the bundled iFlytek Avatar demo under `teacher-platform/public/libs/avatar-sdk-web_demo/avatar-sdk-web_demo/` and not used as the main app framework.

## Runtime

**Environment:**
- Python `3.11` - backend runtime in `backend/Dockerfile`.
- Node.js `20` - frontend container runtime in `teacher-platform/Dockerfile`.
- PostgreSQL `15-alpine` - local/dev database service in `backend/docker-compose.yml`.
- Redis `7-alpine` - cache and Celery broker/backend in `backend/docker-compose.yml`.

**Package Manager:**
- `npm` - frontend install flow uses `npm install` in `teacher-platform/Dockerfile`.
- Lockfile: present for frontend at `teacher-platform/package-lock.json`.
- `pip` + `setuptools` - backend install flow uses `backend/requirements.txt` and project metadata from `backend/pyproject.toml`.
- Lockfile: not detected for Python dependencies in `backend/`.

## Frameworks

**Core:**
- FastAPI `>=0.109.0` - HTTP API in `backend/app/main.py`, routers in `backend/app/api/`.
- SQLAlchemy asyncio `>=2.0.25` - ORM/session layer in `backend/app/core/database.py` and models in `backend/app/models/`.
- Celery `>=5.3.0` - async task execution in `backend/app/celery.py`, `backend/app/tasks.py`, and `backend/app/generators/ppt/celery_tasks.py`.
- Vue `^3.5.25` - SPA framework in `teacher-platform/package.json`, bootstrapped from `teacher-platform/src/main.js`.
- Pinia `^3.0.4` - frontend state stores in `teacher-platform/src/stores/`.
- Vue Router `^4.6.4` - client routing in `teacher-platform/src/router/index.js`.
- Element Plus `^2.13.6` - primary UI component library in `teacher-platform/src/main.js` and many `teacher-platform/src/views/**/*.vue`.

**Testing:**
- `pytest` - backend tests are present in `backend/tests/`; explicit config file is not detected.
- Frontend test support is minimal; a direct test file exists at `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`, but no dedicated JS test runner config is detected in `teacher-platform/`.

**Build/Dev:**
- Vite `^7.3.1` - frontend dev server/build tool in `teacher-platform/package.json` and `teacher-platform/vite.config.js`.
- `@vitejs/plugin-vue` `^6.0.2` - Vue compilation in `teacher-platform/package.json`.
- Docker / Docker Compose - local multi-service environment in `backend/Dockerfile`, `teacher-platform/Dockerfile`, and `backend/docker-compose.yml`.
- Alembic `>=1.13.0` - database migrations in `backend/alembic/` and `backend/alembic/env.py`.

## Key Dependencies

**Critical:**
- `fastapi`, `uvicorn[standard]` - API serving in `backend/app/main.py` and `backend/requirements.txt`.
- `sqlalchemy[asyncio]`, `asyncpg` - PostgreSQL access in `backend/app/core/database.py`.
- `redis`, `celery[redis]` - broker/cache/result backend in `backend/app/celery.py`, `backend/app/services/email.py`, and `backend/app/services/sms.py`.
- `pydantic`, `pydantic-settings` - runtime config and schema validation in `backend/app/core/config.py` and `backend/app/schemas/`.
- `langchain`, `langchain-chroma`, `langchain-huggingface`, `langchain-openai`, `langgraph` - retrieval and agent orchestration in `backend/app/services/rag/` and `backend/app/services/ai/graph/`.
- `oss2` - Alibaba OSS file storage in `backend/app/services/oss_service.py` and `backend/app/generators/ppt/file_service.py`.
- `google-genai` - Gemini-backed PPT generation paths in `backend/app/generators/ppt/banana_providers.py`.

**Infrastructure:**
- `playwright>=1.45.0` - browser rendering/export support in `backend/app/services/html_gif_export.py`.
- `python-jose[cryptography]`, `passlib[bcrypt]` - JWT auth and password hashing in `backend/app/core/jwt.py`, `backend/app/core/auth.py`, and `backend/app/core/security.py`.
- `aiofiles`, `python-multipart` - upload/file handling across `backend/app/api/`.
- `PyMuPDF`, `python-docx`, `opencv-python-headless`, `ffmpeg-python`, `Pillow`, `imagehash` - document/video/image parsing pipelines in `backend/app/services/parsers/`.
- `echarts`, `markmap-lib`, `markmap-view`, `@tiptap/*`, `three`, `@vue-flow/*`, `lottie-web` - specialized frontend visualization/editor features in `teacher-platform/src/components/` and `teacher-platform/src/views/`.

## Configuration

**Environment:**
- Backend runtime settings are centralized in `backend/app/core/config.py` and loaded from `backend/.env` if present; `backend/.env.example` is present for template values.
- Frontend API base configuration comes from `import.meta.env.VITE_API_BASE` in `teacher-platform/src/api/http.js`; `teacher-platform/.env.development` is present.
- Core required backend settings include database/Redis/JWT plus service-specific API keys such as `DASHSCOPE_API_KEY`, `OSS_*`, `IFLYTEK_*`, `DIFY_*`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `NEO4J_*`, all declared in `backend/app/core/config.py`.

**Build:**
- Frontend build config: `teacher-platform/vite.config.js`.
- Backend packaging config: `backend/pyproject.toml`, `backend/requirements.txt`.
- Container build config: `backend/Dockerfile`, `teacher-platform/Dockerfile`, `backend/docker-compose.yml`.
- Migration config: `backend/alembic/` and `backend/alembic.ini`.

## Platform Requirements

**Development:**
- Python `3.11` environment or the backend container defined by `backend/Dockerfile`.
- Node `20` and `npm`, or the frontend container defined by `teacher-platform/Dockerfile`.
- PostgreSQL and Redis, typically via `backend/docker-compose.yml`.
- Optional browser runtime dependencies for Playwright/Chromium are baked into `backend/Dockerfile` when `INSTALL_PLAYWRIGHT=true`.

**Production:**
- Containerized deployment is the only explicit target detected: `backend/Dockerfile` runs Uvicorn, `teacher-platform/Dockerfile` runs the Vite dev server, and `backend/docker-compose.yml` composes frontend, backend, worker, PostgreSQL, and Redis.
- No separate cloud-hosting manifest or CI/CD pipeline is detected outside the Docker artifacts above.

---

*Stack analysis: 2026-04-12*
