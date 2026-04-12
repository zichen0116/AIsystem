# Coding Conventions

**Analysis Date:** 2026-04-12

## Naming Patterns

**Files:**
- Python modules in `backend/app/` and `backend/tests/` use snake_case filenames such as `backend/app/services/rehearsal_media_service.py`, `backend/app/core/logging_setup.py`, and `backend/tests/test_rehearsal_media_service.py`.
- Vue SFCs under `teacher-platform/src/views/` and `teacher-platform/src/components/` use PascalCase filenames such as `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`, `teacher-platform/src/views/ppt/PptPreview.vue`, and `teacher-platform/src/components/rehearsal/PlaybackControls.vue`.
- Frontend stores use mixed lowercase and lowerCamel filenames such as `teacher-platform/src/stores/user.js`, `teacher-platform/src/stores/ppt.js`, and `teacher-platform/src/stores/adminDigitalHuman.js`.
- Frontend composables use `useXxx.js` filenames such as `teacher-platform/src/composables/usePlaybackEngine.js`, `teacher-platform/src/composables/useKnowledgeGraph.js`, and `teacher-platform/src/composables/useVoiceInput.js`.
- Frontend colocated tests use the `.test.js` suffix as in `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.

**Functions:**
- Python functions, helpers, and route handlers use snake_case, for example `wait_for_condition` in `backend/start_dev.py`, `build_rehearsal_image_prompt` in `backend/app/services/rehearsal_media_service.py`, and `send_code` in `backend/app/api/auth.py`.
- Frontend functions use camelCase, for example `resolveApiUrl` in `teacher-platform/src/api/http.js`, `syncPages` in `teacher-platform/src/views/ppt/PptPreview.vue`, and `toggleFullscreen` in `teacher-platform/src/components/rehearsal/PlaybackControls.vue`.
- Stores and composables use `use` prefixes, such as `useUserStore` in `teacher-platform/src/stores/user.js`, `useKnowledgeStore` in `teacher-platform/src/stores/knowledge.js`, and `usePlaybackEngine` in `teacher-platform/src/composables/usePlaybackEngine.js`.

**Variables:**
- Python locals and module state use snake_case; constants use UPPER_SNAKE_CASE such as `LOG_FORMAT` in `backend/app/core/logging_setup.py`, `QWEN_IMAGE_ENDPOINT` in `backend/app/services/rehearsal_media_service.py`, and `GREEN` in `backend/start_dev.py`.
- Settings fields in `backend/app/core/config.py` are mostly env-style UPPER_SNAKE_CASE. Lowercase fields such as `siliconflow_api_key` and `docmee_api_key` are exceptions inside the same settings object.
- Frontend locals use camelCase, with boolean flags typically starting with `is`, `has`, or `show`, for example `isExporting`, `hasRenovationFailedPages`, and `showTemplateModal` in `teacher-platform/src/views/ppt/PptPreview.vue`.

**Types:**
- Python classes use PascalCase for configuration, ORM models, schemas, and test suites, for example `Settings` in `backend/app/core/config.py`, `LessonPlan` in `backend/app/models/lesson_plan.py`, and `LessonPlanInfo` in `backend/app/schemas/lesson_plan.py`.
- Python type hints use modern built-in generics and union syntax such as `list[int]`, `dict | None`, and `Mapped[str]` in `backend/app/schemas/lesson_plan.py`, `backend/app/services/rehearsal_media_service.py`, and `backend/app/models/lesson_plan.py`.
- Main frontend app code in `teacher-platform/src/` is JavaScript, not TypeScript. Component contracts are expressed with runtime `defineProps` and `defineEmits` in files such as `teacher-platform/src/components/rehearsal/PlaybackControls.vue`.

## Code Style

**Formatting:**
- No repo-wide formatter config was detected in `.prettierrc*`, `eslint.config.*`, `biome.json`, `backend/pyproject.toml`, or `teacher-platform/package.json`.
- JavaScript and Vue files follow a consistent manual style: 2-space indentation, single quotes, and no semicolons in files such as `teacher-platform/src/main.js`, `teacher-platform/src/api/http.js`, and `teacher-platform/src/stores/ppt.js`.
- Python files follow manual PEP 8 style: 4-space indentation, grouped imports, and triple-quoted module/function docstrings in files such as `backend/app/main.py`, `backend/app/core/config.py`, and `backend/start_dev.py`.
- Multiline literals typically keep trailing commas in both Python and frontend object/array literals, as seen in `backend/app/api/auth.py`, `backend/app/services/rehearsal_media_service.py`, and `teacher-platform/src/stores/user.js`.

**Linting:**
- No lint configuration was detected for the repo-owned backend or frontend applications.
- `backend/app/main.py` uses `from app.models import *  # noqa: F401, F403`, so local suppressions are acceptable when a module intentionally relies on import side effects.
- `teacher-platform/public/libs/avatar-sdk-web_demo/avatar-sdk-web_demo/.eslintrc.cjs` belongs to a vendored demo under `public/`, not to the main `teacher-platform/src/` codebase.

## Import Organization

**Order:**
1. Python modules group standard library imports first, third-party imports second, and local `app.*` imports last, with blank lines between groups. Follow the pattern in `backend/app/api/auth.py`, `backend/app/core/config.py`, and `backend/app/services/rehearsal_media_service.py`.
2. Frontend modules import framework/vendor packages first, then app modules via alias or relative path, then side-effect stylesheet imports when needed. See `teacher-platform/src/main.js` and `teacher-platform/src/views/ppt/PptPreview.vue`.
3. Dynamic imports are used for route-level code splitting and optional feature loading in `teacher-platform/src/router/index.js`, `teacher-platform/src/stores/ppt.js`, and `teacher-platform/src/views/ppt/PptHome.vue`.

**Path Aliases:**
- `@` maps to `teacher-platform/src` via `teacher-platform/vite.config.js`.
- The codebase mixes alias imports in the PPT area (`teacher-platform/src/api/ppt.js`, `teacher-platform/src/stores/ppt.js`, `teacher-platform/src/views/ppt/PptPreview.vue`) with relative imports in older modules (`teacher-platform/src/router/index.js`, `teacher-platform/src/stores/user.js`, `teacher-platform/src/stores/rehearsal.js`). Match the style already used in the file you edit.

## Error Handling

**Patterns:**
- FastAPI routes raise `HTTPException` with explicit status codes and localized `detail` messages, as in `backend/app/api/auth.py`.
- Backend helpers and services raise `RuntimeError` or `ValueError` for invalid external responses and unsupported inputs, as in `backend/app/services/rehearsal_media_service.py` and `backend/start_dev.py`.
- Frontend request handling is centralized in `teacher-platform/src/api/http.js`, which parses backend error payloads and throws `Error` objects with normalized messages.
- Frontend stores and views wrap async work in `try/catch/finally`, update reactive state, and either rethrow or log errors, as in `teacher-platform/src/stores/knowledge.js`, `teacher-platform/src/stores/ppt.js`, and `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`.

## Logging

**Framework:** Python `logging` on the backend; browser `console` on the frontend.

**Patterns:**
- Backend modules create a module logger with `logging.getLogger(__name__)`, then log progress, warnings, and failures, as in `backend/app/services/rehearsal_media_service.py` and `backend/app/tasks.py`.
- Root logging is configured centrally in `backend/app/core/logging_setup.py`, and `backend/app/main.py` calls `configure_logging(settings.DEBUG)` during startup.
- CLI/bootstrap scripts still use `print()` for operator-facing output in `backend/start_dev.py`, and `backend/app/main.py` uses `print()` for local static-file mapping notices.
- Frontend code logs recoverable failures with `console.error` or `console.warn` in `teacher-platform/src/stores/rehearsal.js`, `teacher-platform/src/stores/ppt.js`, `teacher-platform/src/composables/useKnowledgeGraph.js`, and `teacher-platform/src/views/LessonPlanPage.vue`.

## Comments

**When to Comment:**
- Comments are used to label sections, workflow phases, and UI regions rather than to narrate obvious assignments. Examples include `# ========== ... ==========` blocks in `backend/app/core/config.py` and `// ============ ... ============` blocks in `teacher-platform/src/api/ppt.js`.
- Vue templates use short structural comments such as `<!-- 加载状态 -->`, `<!-- Subtitle -->`, and `<!-- Controls -->` in `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`.
- Large view and store files include targeted comments for polling, stream handling, and state restoration in `teacher-platform/src/router/index.js`, `teacher-platform/src/stores/rehearsal.js`, and `teacher-platform/src/views/ppt/PptPreview.vue`.

**JSDoc/TSDoc:**
- Python favors docstrings over external documentation. Module and function docstrings appear in `backend/app/main.py`, `backend/start_dev.py`, and many backend test files.
- JSDoc-style block comments are selective and mainly used for public helpers or API wrappers in `teacher-platform/src/api/http.js`, `teacher-platform/src/api/ppt.js`, and `teacher-platform/src/stores/user.js`.
- Full TSDoc is not used because the main frontend app under `teacher-platform/src/` is JavaScript rather than TypeScript.

## Function Design

**Size:** 
- Backend helpers are usually small to medium and focused on one transformation or boundary concern, as in `backend/app/services/rehearsal_media_service.py` and `backend/start_dev.py`.
- Backend route files group many related handlers in one module, for example `backend/app/api/auth.py`.
- Frontend `script setup` blocks can become large view-level orchestrators, especially `teacher-platform/src/views/ppt/PptPreview.vue`.

**Parameters:** 
- Backend service functions often use keyword-only parameters for multi-input operations, such as `generate_qwen_image` and `populate_slide_media` in `backend/app/services/rehearsal_media_service.py`.
- FastAPI handlers annotate dependencies explicitly with `Annotated[..., Depends(...)]`, as in `backend/app/api/auth.py`.
- Frontend helpers usually accept plain objects or primitives, then serialize payloads immediately through `apiRequest`, as in `teacher-platform/src/api/ppt.js` and `teacher-platform/src/stores/knowledge.js`.

**Return Values:** 
- Backend routes return plain dicts or Pydantic response models from files such as `backend/app/api/auth.py` and `backend/app/schemas/lesson_plan.py`.
- Backend helpers return explicit structured values such as tuples or normalized dicts, for example `download_generated_media` in `backend/app/services/rehearsal_media_service.py`.
- Frontend API helpers return parsed JSON/text or `null` for empty success responses, following the contract in `teacher-platform/src/api/http.js`.

## Module Design

**Exports:** 
- Backend route modules export a module-level `router`, as in `backend/app/api/auth.py`, `backend/app/api/rehearsal.py`, and `backend/app/generators/ppt/banana_routes.py`.
- Backend service modules export named functions or service classes, while model/schema modules export named classes, as seen in `backend/app/services/rehearsal_media_service.py`, `backend/app/models/lesson_plan.py`, and `backend/app/schemas/lesson_plan.py`.
- Frontend utilities, APIs, and stores use named exports by default, for example `teacher-platform/src/api/http.js`, `teacher-platform/src/api/ppt.js`, `teacher-platform/src/stores/user.js`, and `teacher-platform/src/stores/knowledge.js`.
- `teacher-platform/src/router/index.js` is a typical frontend exception with a default-exported router instance.

**Barrel Files:** 
- Backend package initializers aggregate modules for startup and router registration, notably `backend/app/api/__init__.py` and `backend/app/models/__init__.py`.
- No frontend barrel-file pattern was detected under `teacher-platform/src/`; modules generally import concrete file paths directly.
- Pinia store style is mixed: object-style stores appear in `teacher-platform/src/stores/user.js`, `teacher-platform/src/stores/rehearsal.js`, and `teacher-platform/src/stores/ppt.js`, while setup-style stores appear in `teacher-platform/src/stores/knowledge.js`. Keep the existing store style of the file you touch.

---

*Convention analysis: 2026-04-12*
