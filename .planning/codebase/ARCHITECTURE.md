# Architecture

**Analysis Date:** 2026-04-12

## Pattern Overview

**Overall:** Split full-stack repository with a layered FastAPI backend in `backend/` and a route-driven Vue SPA in `teacher-platform/`.

**Key Characteristics:**
- Keep backend HTTP composition in `backend/app/main.py` and `backend/app/api/__init__.py`, then fan requests into domain routers under `backend/app/api/`.
- Keep backend business logic below the route layer in `backend/app/services/` and `backend/app/generators/`, with persistence handled through `backend/app/models/`, `backend/app/schemas/`, and `backend/app/core/database.py`.
- Keep frontend page orchestration at the route and view level in `teacher-platform/src/router/index.js` and `teacher-platform/src/views/`, with shared state centralized in Pinia stores under `teacher-platform/src/stores/`.
- Treat streaming and asynchronous generation as first-class architecture concerns: SSE endpoints live in `backend/app/api/lesson_plan.py`, `backend/app/api/rehearsal.py`, and `backend/app/generators/ppt/banana_routes.py`, while background work runs through `backend/app/celery.py`, `backend/app/tasks.py`, and `backend/app/generators/ppt/celery_tasks.py`.

## Layers

**Frontend SPA Layer:**
- Purpose: Render the teacher-facing application, manage route transitions, and coordinate user workflows across lesson prep, PPT generation, knowledge, courseware, admin, and rehearsal features.
- Location: `teacher-platform/src/`
- Contains: App bootstrap in `teacher-platform/src/main.js`, top-level shell logic in `teacher-platform/src/App.vue`, route definitions in `teacher-platform/src/router/index.js`, page views in `teacher-platform/src/views/`, reusable UI in `teacher-platform/src/components/`, stores in `teacher-platform/src/stores/`, and HTTP wrappers in `teacher-platform/src/api/`.
- Depends on: Backend HTTP APIs under `backend/app/api/`, browser storage via `teacher-platform/src/api/http.js`, and Pinia state via files such as `teacher-platform/src/stores/user.js`, `teacher-platform/src/stores/ppt.js`, and `teacher-platform/src/stores/rehearsal.js`.
- Used by: The Vite application entry point in `teacher-platform/src/main.js`.

**Backend API Layer:**
- Purpose: Expose authenticated HTTP endpoints, validate request payloads, and map transport concerns to domain services.
- Location: `backend/app/api/` and `backend/app/generators/ppt/banana_routes.py`
- Contains: Router modules such as `backend/app/api/auth.py`, `backend/app/api/courseware.py`, `backend/app/api/lesson_plan.py`, `backend/app/api/rehearsal.py`, `backend/app/api/knowledge.py`, and the PPT router exported from `backend/app/generators/ppt/__init__.py`.
- Depends on: FastAPI dependency injection from `backend/app/core/auth.py` and `backend/app/core/database.py`, Pydantic schemas under `backend/app/schemas/`, SQLAlchemy models under `backend/app/models/`, and service modules under `backend/app/services/` and `backend/app/generators/`.
- Used by: `backend/app/api/__init__.py`, which is mounted by `backend/app/main.py` under `/api/v1`.

**Persistence and Core Infrastructure Layer:**
- Purpose: Manage configuration, database sessions, JWT auth, logging, and model metadata shared across domains.
- Location: `backend/app/core/` and `backend/app/models/`
- Contains: Settings in `backend/app/core/config.py`, async session lifecycle in `backend/app/core/database.py`, auth dependencies in `backend/app/core/auth.py`, JWT helpers in `backend/app/core/jwt.py`, and ORM models such as `backend/app/models/user.py`, `backend/app/models/lesson_plan.py`, `backend/app/models/rehearsal.py`, and `backend/app/generators/ppt/banana_models.py`.
- Depends on: Environment configuration from `backend/.env` through `backend/app/core/config.py` and Alembic migrations in `backend/alembic/versions/`.
- Used by: Every router and service that uses `Depends(get_db)`, `CurrentUser`, or SQLAlchemy models.

**Domain Service Layer:**
- Purpose: Implement feature workflows that are too large or stateful for route handlers.
- Location: `backend/app/services/`
- Contains: Lesson plan generation in `backend/app/services/lesson_plan_service.py`, rehearsal generation in `backend/app/services/rehearsal_generation_service.py`, rehearsal persistence helpers in `backend/app/services/rehearsal_session_service.py`, data analysis services under `backend/app/services/data_analysis/`, AI graph orchestration under `backend/app/services/ai/graph/`, document parsing under `backend/app/services/parsers/`, and retrieval under `backend/app/services/rag/`.
- Depends on: Core config and DB helpers, models and schemas, external AI/storage clients, and occasionally other services.
- Used by: API modules such as `backend/app/api/lesson_plan.py`, `backend/app/api/rehearsal.py`, and `backend/app/api/data_analysis.py`.

**Generator Subsystem Layer:**
- Purpose: Own large content-generation domains whose internal workflow is broader than a single service file.
- Location: `backend/app/generators/` and especially `backend/app/generators/ppt/`
- Contains: Generic generator factory code in `backend/app/generators/factory.py`, legacy generators such as `backend/app/generators/ppt_generator.py`, and the newer PPT subsystem with routes, providers, task dispatch, parsing, export, renovation, and intent handling in `backend/app/generators/ppt/`.
- Depends on: Models in `backend/app/generators/ppt/banana_models.py`, schemas in `backend/app/generators/ppt/banana_schemas.py`, provider abstractions in `backend/app/generators/ppt/banana_providers.py`, Celery tasks in `backend/app/generators/ppt/celery_tasks.py`, and shared services such as `backend/app/services/oss_service.py` and `backend/app/services/redis_service.py`.
- Used by: `backend/app/api/__init__.py` through `ppt_router`, and frontend PPT flows through `teacher-platform/src/stores/ppt.js`.

**Background Processing Layer:**
- Purpose: Run long-running parsing, vectorization, and PPT generation work outside the request path.
- Location: `backend/app/celery.py`, `backend/app/tasks.py`, and `backend/app/generators/ppt/celery_tasks.py`
- Contains: Celery app bootstrap, task routing, retry settings, and feature-specific jobs.
- Depends on: Redis broker/backend from `backend/app/celery.py`, synchronous SQLAlchemy access in `backend/app/tasks.py`, and the same service/generator modules used by synchronous request paths.
- Used by: Upload and generation flows that dispatch background work from router or dispatcher code such as `backend/app/generators/ppt/task_dispatcher.py`.

## Data Flow

**Authenticated SPA Request Flow:**

1. `teacher-platform/src/main.js` mounts the app, Pinia, router, and UI plugins.
2. `teacher-platform/src/router/index.js` applies route guards, restoring user state with `teacher-platform/src/stores/user.js` when a token exists.
3. A view such as `teacher-platform/src/views/LessonPrep.vue` or `teacher-platform/src/views/rehearsal/RehearsalLab.vue` calls a Pinia store like `teacher-platform/src/stores/ppt.js` or `teacher-platform/src/stores/rehearsal.js`.
4. The store issues fetch requests through `teacher-platform/src/api/http.js` or feature-specific wrappers under `teacher-platform/src/api/`.
5. FastAPI routes in files such as `backend/app/api/rehearsal.py` or `backend/app/generators/ppt/banana_routes.py` validate input, resolve `CurrentUser`, and obtain an `AsyncSession` with `Depends(get_db)`.
6. The route persists or fetches models and then delegates feature logic to service or generator modules.
7. The response returns JSON, file output, or an SSE stream that the store maps back into view state.

**Lesson Plan Streaming Flow:**

1. `teacher-platform/src/views/LessonPlanPage.vue` opens an SSE-like fetch stream against `/api/v1/lesson-plan/generate` or `/api/v1/lesson-plan/modify`.
2. `backend/app/api/lesson_plan.py` creates or loads `LessonPlan` rows, writes `ChatHistory`, pulls context via `backend/app/services/lesson_plan_service.py`, and returns `StreamingResponse`.
3. `backend/app/services/lesson_plan_service.py` streams tokens from an OpenAI-compatible endpoint, merges optional RAG context, and saves the final lesson plan through `AsyncSessionLocal`.
4. `teacher-platform/src/views/LessonPlanPage.vue` switches between dialog and writer modes and persists edits back through `/api/v1/lesson-plan/{id}`.

**Rehearsal Generation Flow:**

1. `teacher-platform/src/views/rehearsal/RehearsalLab.vue` routes into the generation flow, and `teacher-platform/src/stores/rehearsal.js` starts `/api/v1/rehearsal/generate-stream`.
2. `backend/app/api/rehearsal.py` returns an SSE stream from `backend/app/services/rehearsal_generation_service.py`.
3. `backend/app/services/rehearsal_generation_service.py` generates outlines, slide content, actions, media, and optional TTS, then persists page-level progress to `RehearsalSession` and `RehearsalScene` models.
4. The frontend store treats the SSE stream as progress events only, then fetches complete scene payloads from `/api/v1/rehearsal/sessions/{id}` and `/api/v1/rehearsal/sessions/{id}/scenes/{scene_order}`.
5. `teacher-platform/src/views/rehearsal/RehearsalPlay.vue` renders ready scenes and drives playback through `teacher-platform/src/composables/usePlaybackEngine.js` plus overlay components under `teacher-platform/src/components/rehearsal/`.

**PPT Workspace Flow:**

1. `teacher-platform/src/views/ppt/PptIndex.vue` maps store phase to one of `PptHome`, `PptDialog`, `PptOutline`, `PptDescription`, `PptPreview`, or `PptHistory`.
2. `teacher-platform/src/stores/ppt.js` owns the workspace state for projects, pages, descriptions, materials, export tasks, and intent-confirmation status.
3. `backend/app/generators/ppt/banana_routes.py` acts as the main transport surface for the PPT subsystem, backed by provider, task, export, file, and intent modules in the same directory.
4. Long-running file generation and renovation work is dispatched through `backend/app/generators/ppt/task_dispatcher.py` and Celery task modules instead of staying inside a single request.

**State Management:**
- Frontend global state lives in Pinia stores under `teacher-platform/src/stores/`, with routing metadata and query params used to switch modes in `teacher-platform/src/router/index.js`, `teacher-platform/src/views/LessonPrep.vue`, and `teacher-platform/src/views/ppt/PptIndex.vue`.
- Backend durable state lives in PostgreSQL models under `backend/app/models/` and `backend/app/generators/ppt/banana_models.py`, with transient queue state handled by Celery and Redis through `backend/app/celery.py`.
- Retrieval state and generated media also persist outside the database in `backend/chroma_data/` and `backend/media/`.

## Key Abstractions

**API Router Aggregation:**
- Purpose: Keep endpoint registration centralized while leaving domain handlers in separate modules.
- Examples: `backend/app/api/__init__.py`, `backend/app/main.py`, `backend/app/generators/ppt/__init__.py`
- Pattern: Each feature exports a `router`; `backend/app/api/__init__.py` includes them into one `api_router`, and `backend/app/main.py` mounts that aggregate router under `/api/v1`.

**Dependency-Injected Request Context:**
- Purpose: Standardize auth and transaction boundaries.
- Examples: `backend/app/core/auth.py`, `backend/app/core/database.py`, `backend/app/api/auth.py`, `backend/app/api/rehearsal.py`
- Pattern: Route handlers accept `CurrentUser` and `Depends(get_db)` instead of creating auth or DB state inline.

**Store-Owned Frontend Workspaces:**
- Purpose: Keep multi-step feature state out of individual components.
- Examples: `teacher-platform/src/stores/ppt.js`, `teacher-platform/src/stores/rehearsal.js`, `teacher-platform/src/stores/user.js`
- Pattern: Views and components call store actions; stores translate API payloads into UI-ready state and expose derived getters.

**Streaming-First Generation Interfaces:**
- Purpose: Support long-running AI flows without blocking the UI.
- Examples: `backend/app/api/lesson_plan.py`, `backend/app/api/rehearsal.py`, `backend/app/generators/ppt/banana_routes.py`, `teacher-platform/src/views/LessonPlanPage.vue`, `teacher-platform/src/stores/rehearsal.js`
- Pattern: The backend sends metadata and progress over `text/event-stream`; the frontend consumes incremental events and hydrates richer state with follow-up fetches.

**Graph-Orchestrated AI Workflow:**
- Purpose: Encapsulate agent decisioning, tool use, grading, and human approval.
- Examples: `backend/app/services/ai/graph/workflow.py`, `backend/app/services/ai/graph/nodes.py`, `backend/app/services/ai/graph/state.py`
- Pattern: `StateGraph` composes named nodes, conditional edges, checkpoints, and resume behavior rather than embedding all AI orchestration in one route.

**Feature Subsystems with Internal Modules:**
- Purpose: Isolate larger domains that need their own models, schemas, tasks, and service helpers.
- Examples: `backend/app/generators/ppt/`, `backend/app/services/data_analysis/`, `teacher-platform/src/components/rehearsal/`, `teacher-platform/src/components/lesson-plan-v2/`
- Pattern: The route or view layer delegates into a dedicated directory that owns the full vertical slice of a feature.

## Entry Points

**Backend Application Entry Point:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn`, `backend/run.py`, Docker, or any server process that imports `app.main:app`
- Responsibilities: Configure logging, initialize the database in the lifespan hook, mount `/api/v1`, enable CORS, and expose `/media` and `/health`.

**Backend Developer Bootstrap:**
- Location: `backend/run.py`
- Triggers: Direct local execution for API-only development
- Responsibilities: Load environment variables, configure logging, and run `uvicorn` against `app.main:app`.

**Backend Full Dev Orchestration:**
- Location: `backend/start_dev.py`
- Triggers: Local developer workflow that wants database, cache, API, and worker started together
- Responsibilities: Check Docker, start Redis and PostgreSQL containers if needed, boot FastAPI, boot the Celery worker, and watch readiness.

**Frontend Application Entry Point:**
- Location: `teacher-platform/src/main.js`
- Triggers: Vite dev server or production build
- Responsibilities: Create the Vue app and attach Pinia, Vue Router, `@kjgl77/datav-vue3`, and Element Plus.

**Frontend Shell and Layout Switcher:**
- Location: `teacher-platform/src/App.vue`
- Triggers: Every frontend route render
- Responsibilities: Provide top-level navigation actions, choose `LayoutWithNav` when `route.meta.layout === 'nav'`, and host `RouterView`.

**Frontend Router Entry Point:**
- Location: `teacher-platform/src/router/index.js`
- Triggers: Navigation and page refreshes
- Responsibilities: Lazy-load views, enforce auth for protected routes, and restore login state from persisted token storage.

## Error Handling

**Strategy:** Combine FastAPI exception responses, transaction rollback in the DB dependency, explicit frontend fetch error handling, and status/event-based feedback for long-running jobs.

**Patterns:**
- Let `backend/app/core/database.py` own commit-or-rollback behavior for request-scoped async sessions.
- Raise `HTTPException` in router modules such as `backend/app/api/lesson_plan.py` and `backend/app/api/rehearsal.py` when ownership or lookup checks fail.
- Return SSE `error` events or terminal status payloads from streaming endpoints rather than relying on a single final JSON response.
- Centralize client-side auth expiration handling in `teacher-platform/src/api/http.js`, which clears the token and redirects to `/login` on non-auth 401 responses.
- Keep store-level status flags such as `generatingStatus`, `error`, `fileGenerationTaskStatus`, and `renovationTaskStatus` in `teacher-platform/src/stores/rehearsal.js` and `teacher-platform/src/stores/ppt.js` so views do not infer request state ad hoc.

## Cross-Cutting Concerns

**Logging:** Use `backend/app/core/logging_setup.py` to configure root logging once; service and route modules then use `logging.getLogger(__name__)`.
**Validation:** Use Pydantic request and response models in `backend/app/schemas/` and `backend/app/generators/ppt/banana_schemas.py`; frontend validation is lighter and typically happens through view logic or server responses.
**Authentication:** Use JWT bearer auth through `backend/app/core/auth.py` and `backend/app/core/jwt.py`; frontend token persistence and recovery live in `teacher-platform/src/api/http.js` and `teacher-platform/src/stores/user.js`.

---

*Architecture analysis: 2026-04-12*
