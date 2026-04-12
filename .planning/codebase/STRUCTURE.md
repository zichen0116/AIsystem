# Codebase Structure

**Analysis Date:** 2026-04-12

## Directory Layout

```text
AIsystem/
|-- backend/                    # FastAPI backend, async services, Celery tasks, migrations
|   |-- app/                    # Application code grouped by API, core, models, schemas, services, generators
|   |-- alembic/                # Database migration environment and revision files
|   |-- tests/                  # Backend pytest suite
|   |-- media/                  # Runtime media assets and generated files
|   |-- chroma_data/            # Persisted Chroma vector store data
|   |-- run.py                  # API-only local bootstrap
|   `-- start_dev.py            # Full local dev orchestrator
|-- teacher-platform/           # Vue 3 + Vite frontend application
|   |-- src/                    # Views, stores, components, API wrappers, composables
|   |-- public/                 # Static assets, preset previews, bundled third-party SDK demo files
|   |-- package.json            # Frontend scripts and dependencies
|   `-- vite.config.js          # Vite build config
|-- docs/                       # Plans, design notes, and superpowers specs
|-- .planning/                  # Planning artifacts, including generated codebase docs
|-- README.md                   # Project overview
`-- CLAUDE.md                   # Repository-specific agent guidance
```

## Directory Purposes

**`backend/`:**
- Purpose: Backend application, runtime helpers, infrastructure scripts, and tests.
- Contains: `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/run.py`, `backend/start_dev.py`, `backend/requirements.txt`, `backend/pyproject.toml`, `backend/Dockerfile`, and `backend/docker-compose.yml`.
- Key files: `backend/app/main.py`, `backend/run.py`, `backend/start_dev.py`, `backend/app/celery.py`.

**`backend/app/`:**
- Purpose: Main Python package for the backend.
- Contains: Layered subpackages `backend/app/api/`, `backend/app/core/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/generators/`, and `backend/app/utils/`.
- Key files: `backend/app/main.py`, `backend/app/tasks.py`, `backend/app/celery.py`.

**`backend/app/api/`:**
- Purpose: Feature routers and transport-layer request handling.
- Contains: One router per domain, including `backend/app/api/auth.py`, `backend/app/api/courseware.py`, `backend/app/api/lesson_plan.py`, `backend/app/api/rehearsal.py`, `backend/app/api/knowledge.py`, and `backend/app/api/data_analysis.py`.
- Key files: `backend/app/api/__init__.py`, `backend/app/api/lesson_plan.py`, `backend/app/api/rehearsal.py`.

**`backend/app/core/`:**
- Purpose: Shared infrastructure code that the whole backend depends on.
- Contains: Settings, DB session management, auth dependencies, JWT utilities, and logging helpers.
- Key files: `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/auth.py`, `backend/app/core/logging_setup.py`.

**`backend/app/models/`:**
- Purpose: SQLAlchemy ORM models for backend-owned tables outside the PPT subsystem.
- Contains: Files such as `backend/app/models/user.py`, `backend/app/models/lesson_plan.py`, `backend/app/models/rehearsal.py`, `backend/app/models/knowledge_asset.py`, and `backend/app/models/question_paper.py`.
- Key files: `backend/app/models/__init__.py`, `backend/app/models/user.py`, `backend/app/models/rehearsal.py`.

**`backend/app/schemas/`:**
- Purpose: Pydantic request and response contracts for backend routes.
- Contains: Files such as `backend/app/schemas/auth.py`, `backend/app/schemas/lesson_plan.py`, `backend/app/schemas/rehearsal.py`, `backend/app/schemas/library.py`, and `backend/app/schemas/courseware.py`.
- Key files: `backend/app/schemas/rehearsal.py`, `backend/app/schemas/lesson_plan.py`, `backend/app/schemas/auth.py`.

**`backend/app/services/`:**
- Purpose: Business logic and external-system orchestration.
- Contains: Flat service modules like `backend/app/services/lesson_plan_service.py`, `backend/app/services/rehearsal_generation_service.py`, `backend/app/services/rehearsal_media_service.py`, `backend/app/services/oss_service.py`, and grouped subsystems `backend/app/services/ai/`, `backend/app/services/rag/`, `backend/app/services/parsers/`, and `backend/app/services/data_analysis/`.
- Key files: `backend/app/services/lesson_plan_service.py`, `backend/app/services/rehearsal_generation_service.py`, `backend/app/services/ai/graph/workflow.py`, `backend/app/services/rag/hybrid_retriever.py`.

**`backend/app/generators/`:**
- Purpose: Content-generation modules whose workflows are broader than a single service file.
- Contains: Generic generator modules like `backend/app/generators/docx_generator.py`, `backend/app/generators/game_generator.py`, `backend/app/generators/ppt_generator.py`, and the full PPT subsystem in `backend/app/generators/ppt/`.
- Key files: `backend/app/generators/factory.py`, `backend/app/generators/ppt/__init__.py`, `backend/app/generators/ppt/banana_routes.py`.

**`backend/app/generators/ppt/`:**
- Purpose: Self-contained PPT feature slice.
- Contains: Route handlers, provider abstractions, models, schemas, task dispatch, Celery jobs, export helpers, parsing helpers, renovation flows, and intent logic.
- Key files: `backend/app/generators/ppt/banana_routes.py`, `backend/app/generators/ppt/banana_models.py`, `backend/app/generators/ppt/banana_schemas.py`, `backend/app/generators/ppt/task_dispatcher.py`, `backend/app/generators/ppt/celery_tasks.py`.

**`backend/alembic/`:**
- Purpose: Database migration environment for the backend schema.
- Contains: `backend/alembic/env.py`, `backend/alembic/script.py.mako`, and revision files under `backend/alembic/versions/`.
- Key files: `backend/alembic/env.py`, `backend/alembic/versions/20260407_add_renovation_fields.py`.

**`backend/tests/`:**
- Purpose: Backend automated tests.
- Contains: Flat pytest files such as `backend/tests/test_lesson_plan_api.py`, `backend/tests/test_rehearsal_generation_service.py`, `backend/tests/test_ppt_renovation.py`, and `backend/tests/test_hybrid_retriever.py`.
- Key files: `backend/tests/test_lesson_plan_api.py`, `backend/tests/test_rehearsal_generation_service.py`, `backend/tests/test_ppt_template_prompt_regressions.py`.

**`teacher-platform/src/`:**
- Purpose: Frontend application source.
- Contains: `teacher-platform/src/api/`, `teacher-platform/src/components/`, `teacher-platform/src/composables/`, `teacher-platform/src/router/`, `teacher-platform/src/stores/`, `teacher-platform/src/utils/`, and `teacher-platform/src/views/`.
- Key files: `teacher-platform/src/main.js`, `teacher-platform/src/App.vue`, `teacher-platform/src/router/index.js`, `teacher-platform/src/style.css`.

**`teacher-platform/src/views/`:**
- Purpose: Route-level pages and feature workspaces.
- Contains: Top-level screens such as `teacher-platform/src/views/Home.vue`, `teacher-platform/src/views/LessonPrep.vue`, `teacher-platform/src/views/LessonPlanPage.vue`, `teacher-platform/src/views/CoursewareManage.vue`, `teacher-platform/src/views/KnowledgeBase.vue`, plus grouped subdirectories `teacher-platform/src/views/ppt/`, `teacher-platform/src/views/rehearsal/`, and `teacher-platform/src/views/admin/`.
- Key files: `teacher-platform/src/views/LessonPrep.vue`, `teacher-platform/src/views/LessonPlanPage.vue`, `teacher-platform/src/views/ppt/PptIndex.vue`, `teacher-platform/src/views/rehearsal/RehearsalLab.vue`.

**`teacher-platform/src/components/`:**
- Purpose: Reusable UI and feature widgets used by the route views.
- Contains: Shared layout files such as `teacher-platform/src/components/LayoutWithNav.vue` and `teacher-platform/src/components/TopNav.vue`, plus feature directories `teacher-platform/src/components/lesson-plan-v2/`, `teacher-platform/src/components/rehearsal/`, `teacher-platform/src/components/knowledge-graph/`, and `teacher-platform/src/components/BigScreen/`.
- Key files: `teacher-platform/src/components/LayoutWithNav.vue`, `teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue`, `teacher-platform/src/components/rehearsal/SlideRenderer.vue`.

**`teacher-platform/src/stores/`:**
- Purpose: Centralized frontend state management.
- Contains: Domain stores `teacher-platform/src/stores/user.js`, `teacher-platform/src/stores/ppt.js`, `teacher-platform/src/stores/rehearsal.js`, `teacher-platform/src/stores/knowledge.js`, `teacher-platform/src/stores/courseware.js`, and `teacher-platform/src/stores/adminDigitalHuman.js`.
- Key files: `teacher-platform/src/stores/user.js`, `teacher-platform/src/stores/ppt.js`, `teacher-platform/src/stores/rehearsal.js`.

**`teacher-platform/src/api/`:**
- Purpose: Frontend HTTP wrappers for backend endpoints.
- Contains: Shared fetch helpers in `teacher-platform/src/api/http.js` and feature files such as `teacher-platform/src/api/ppt.js`, `teacher-platform/src/api/rehearsal.js`, and `teacher-platform/src/api/courseware.js`.
- Key files: `teacher-platform/src/api/http.js`, `teacher-platform/src/api/rehearsal.js`, `teacher-platform/src/api/ppt.js`.

**`teacher-platform/src/composables/`:**
- Purpose: Reusable frontend behavior that is not purely presentational.
- Contains: Files such as `teacher-platform/src/composables/usePlaybackEngine.js`, `teacher-platform/src/composables/useVoiceInput.js`, `teacher-platform/src/composables/useKnowledgeGraph.js`, and `teacher-platform/src/composables/rehearsalPlaybackEffects.js`.
- Key files: `teacher-platform/src/composables/usePlaybackEngine.js`, `teacher-platform/src/composables/useVoiceInput.js`.

**`teacher-platform/public/`:**
- Purpose: Static assets served directly by the frontend build.
- Contains: Images, template previews, preset previews, and vendor/demo bundles like `teacher-platform/public/libs/avatar-sdk-web_demo/`.
- Key files: `teacher-platform/public/templates/`, `teacher-platform/public/preset-previews/`, `teacher-platform/public/libs/avatar-sdk-web_demo/avatar-sdk-web_demo/README.md`.

**`docs/`:**
- Purpose: Human-authored planning and design materials outside the runtime apps.
- Contains: Implementation plans in `docs/plans/` and design/planning artifacts in `docs/superpowers/plans/` and `docs/superpowers/specs/`.
- Key files: `docs/plans/2026-02-24-knowledge-library-impl.md`, `docs/superpowers/plans/2026-04-09-classroom-rehearsal-mvp.md`.

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI application assembly and lifespan setup.
- `backend/run.py`: Backend local launch script for the API process.
- `backend/start_dev.py`: Backend multi-process local development bootstrap.
- `teacher-platform/src/main.js`: Vue application bootstrap.
- `teacher-platform/src/router/index.js`: Frontend route registry and auth guard.

**Configuration:**
- `backend/app/core/config.py`: Backend settings model and environment loading.
- `backend/app/core/database.py`: Async engine and request-scoped session factory.
- `backend/alembic/env.py`: Alembic migration environment.
- `teacher-platform/vite.config.js`: Frontend build config.
- `teacher-platform/package.json`: Frontend scripts and dependency manifest.

**Core Logic:**
- `backend/app/api/__init__.py`: Backend router aggregation.
- `backend/app/services/lesson_plan_service.py`: Lesson-plan streaming and context retrieval logic.
- `backend/app/services/rehearsal_generation_service.py`: Rehearsal pipeline orchestration.
- `backend/app/services/ai/graph/workflow.py`: LangGraph workflow composition.
- `backend/app/generators/ppt/banana_routes.py`: Main PPT API surface.
- `teacher-platform/src/views/LessonPrep.vue`: Frontend lesson-prep workspace switcher.
- `teacher-platform/src/views/LessonPlanPage.vue`: Lesson-plan dialog and writer workspace.
- `teacher-platform/src/views/ppt/PptIndex.vue`: PPT phase switcher.
- `teacher-platform/src/stores/ppt.js`: PPT workflow state.
- `teacher-platform/src/stores/rehearsal.js`: Rehearsal state and SSE event handling.

**Testing:**
- `backend/tests/`: Backend pytest suite.
- `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`: Frontend test coverage currently lives beside a composable.

## Naming Conventions

**Files:**
- Use `snake_case.py` for backend Python modules such as `backend/app/services/rehearsal_generation_service.py` and `backend/app/models/question_paper.py`.
- Use `PascalCase.vue` for frontend route views and components such as `teacher-platform/src/views/LessonPrep.vue` and `teacher-platform/src/components/PageHeader.vue`.
- Use `camelCase.js` for frontend stores, API wrappers, utils, and composables such as `teacher-platform/src/stores/adminDigitalHuman.js`, `teacher-platform/src/api/courseware.js`, and `teacher-platform/src/composables/usePlaybackEngine.js`.
- Use migration filenames that start with a revision or date prefix in `backend/alembic/versions/`, for example `backend/alembic/versions/20260405_add_ppt_schema.py`.

**Directories:**
- Group backend code by layer under `backend/app/`, then by domain inside those layers, for example `backend/app/services/rag/` and `backend/app/services/data_analysis/`.
- Group frontend code by role under `teacher-platform/src/`, then by feature where the UI surface is large, for example `teacher-platform/src/views/ppt/`, `teacher-platform/src/views/rehearsal/`, `teacher-platform/src/components/lesson-plan-v2/`, and `teacher-platform/src/components/rehearsal/`.

## Where to Add New Code

**New Backend API Feature:**
- Primary code: Add the router to `backend/app/api/` if it is a normal domain endpoint, or to `backend/app/generators/ppt/` if it belongs to the PPT subsystem.
- Supporting contracts: Add or extend Pydantic models in `backend/app/schemas/` or `backend/app/generators/ppt/banana_schemas.py`.
- Persistence: Add SQLAlchemy models in `backend/app/models/` or `backend/app/generators/ppt/banana_models.py`, then add a migration in `backend/alembic/versions/`.
- Service logic: Put business rules in `backend/app/services/` or the owning generator subdirectory instead of expanding route handlers.
- Tests: Add pytest coverage under `backend/tests/`.

**New Frontend Route or Screen:**
- Implementation: Add the route-level page under `teacher-platform/src/views/` or the relevant feature subdirectory such as `teacher-platform/src/views/rehearsal/` or `teacher-platform/src/views/ppt/`.
- Route registration: Wire it into `teacher-platform/src/router/index.js`.
- Shared state: Add or extend a Pinia store in `teacher-platform/src/stores/` when the feature spans multiple components or steps.

**New Reusable Frontend Component:**
- Implementation: Put generic UI in `teacher-platform/src/components/`.
- Feature-specific widgets: Keep them in the closest feature directory such as `teacher-platform/src/components/rehearsal/`, `teacher-platform/src/components/lesson-plan-v2/`, or `teacher-platform/src/components/knowledge-graph/`.

**New Frontend HTTP Client Code:**
- Shared fetch/auth behavior: Keep it in `teacher-platform/src/api/http.js`.
- Feature endpoints: Add a dedicated module under `teacher-platform/src/api/` and call it from a store rather than directly from many components.

**Utilities:**
- Shared backend helpers: Add them under `backend/app/utils/` only when they are genuinely cross-domain.
- Shared frontend helpers: Add them under `teacher-platform/src/utils/`.
- Reusable frontend behavior with lifecycle or reactive state: Add it under `teacher-platform/src/composables/`.

## Special Directories

**`backend/alembic/versions/`:**
- Purpose: Database schema revision history.
- Generated: Yes.
- Committed: Yes.

**`backend/chroma_data/`:**
- Purpose: Persisted Chroma vector database files used by the retrieval subsystem.
- Generated: Yes.
- Committed: Yes.

**`backend/media/`:**
- Purpose: Runtime media tree for generated files and bundled fonts exposed through `/media`.
- Generated: Mixed. Generated outputs live here, and bundled assets such as `backend/media/fonts/SourceHanSansSC-Regular.otf` also live here.
- Committed: Mixed. At least `backend/media/fonts/SourceHanSansSC-Regular.otf` is committed.

**`teacher-platform/public/libs/avatar-sdk-web_demo/`:**
- Purpose: Bundled third-party demo project and SDK assets for the avatar integration.
- Generated: No.
- Committed: Yes.

**`teacher-platform/dist/`:**
- Purpose: Frontend build output directory.
- Generated: Yes.
- Committed: Not detected.

**`.planning/codebase/`:**
- Purpose: Generated codebase reference documents for GSD planning and execution workflows.
- Generated: Yes.
- Committed: Not detected.

---

*Structure analysis: 2026-04-12*
