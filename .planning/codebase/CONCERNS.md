# Codebase Concerns

**Analysis Date:** 2026-04-12

## Tech Debt

**Stubbed core generation/chat paths:**
- Issue: several user-facing backend paths still return placeholder content or write placeholder files instead of invoking real model or document-generation flows.
- Files: `backend/app/api/chat.py`, `backend/app/services/ai/lesson_generator.py`, `backend/app/generators/ppt_generator.py`, `backend/app/generators/docx_generator.py`, `backend/app/generators/game_generator.py`
- Impact: endpoints can report success while producing fake AI replies, text files with `.pptx`/`.docx` extensions, or JSON placeholders that do not match product promises.
- Fix approach: replace placeholder implementations with real provider integrations and generate format-valid outputs; add contract tests that assert MIME type, file structure, and response shape.

**Oversized PPT backend module:**
- Issue: the PPT backend is concentrated in very large multi-responsibility modules that mix parsing helpers, persistence, task orchestration, exports, chat, materials, reference files, and template handling.
- Files: `backend/app/generators/ppt/banana_routes.py`, `backend/app/generators/ppt/celery_tasks.py`
- Impact: small changes have wide regression risk, review cost is high, and test isolation is difficult because routing, business logic, and external I/O are intertwined.
- Fix approach: split by bounded responsibility such as `projects`, `pages`, `materials`, `reference_files`, `exports`, and `tasks`; move non-routing logic behind service boundaries with focused tests.

**Oversized frontend orchestration views/components:**
- Issue: major frontend flows are implemented in single very large files with polling, task handling, DOM wiring, modal control, and view state all in one place.
- Files: `teacher-platform/src/views/ppt/PptPreview.vue`, `teacher-platform/src/views/QuestionGenerate.vue`, `teacher-platform/src/views/rehearsal/RehearsalNew.vue`, `teacher-platform/src/components/DigitalHumanAssistant.vue`
- Impact: behavior is hard to reason about, defects are likely during UI changes, and reuse is minimal because logic is embedded directly in view files.
- Fix approach: extract task polling, export flows, upload handling, and digital-human session control into composables or stores with component-level tests.

## Known Bugs

**`resume_chat` can crash while logging PPT generation results:**
- Symptoms: the recovery path can raise a server error even after PPT generation succeeds or fails internally.
- Files: `backend/app/api/chat.py`, `backend/app/generators/ppt_generator.py`
- Trigger: call `POST /api/v1/chat/resume` with an outline that enters the PPT-generation branch; `backend/app/api/chat.py` references `logger` at lines using `logger.info(...)` and `logger.error(...)`, but no logger is defined in the module.
- Workaround: none in code; the path depends on the outer exception handler and currently returns HTTP 500 on the undefined-name failure.

**Resume flow can produce invalid downloadable artifacts:**
- Symptoms: generated “PPT” downloads can be plain UTF-8 text rather than valid PowerPoint files.
- Files: `backend/app/api/chat.py`, `backend/app/generators/ppt_generator.py`
- Trigger: `resume_chat()` writes to `media/ppt/*.pptx`, but `PPTGenerator.generate()` currently uses `output_path.write_text(...)` instead of creating a real PPT package.
- Workaround: use the newer PPT project pipeline in `backend/app/generators/ppt/banana_routes.py` rather than the legacy `resume_chat` export path.

## Security Considerations

**Insecure backend defaults and permissive CORS:**
- Risk: the backend accepts any origin while allowing credentials, and it ships with development-grade default secrets and database URLs.
- Files: `backend/app/main.py`, `backend/app/core/config.py`
- Current mitigation: environment variables can override defaults, but the code falls back to permissive values such as `allow_origins=["*"]`, `allow_credentials=True`, and `JWT_SECRET_KEY = "dev-secret-key-change-in-production"`.
- Recommendations: require explicit production settings, fail fast when `JWT_SECRET_KEY` or database URLs are left at defaults, and replace wildcard CORS with an allowlist.

**JWT stored in browser `localStorage`:**
- Risk: any XSS bug in the frontend can exfiltrate long-lived bearer tokens.
- Files: `teacher-platform/src/api/http.js`, `teacher-platform/src/stores/user.js`, `teacher-platform/src/router/index.js`
- Current mitigation: logout blacklists the current token in `backend/app/api/auth.py`, and password change bumps `token_version`.
- Recommendations: move auth to `HttpOnly` cookies or a short-lived access token plus refresh-cookie model; keep `localStorage` only for non-sensitive preferences.

**Unauthenticated public file-processing endpoints:**
- Risk: arbitrary users can upload and process documents without authentication, and the data-analysis pipeline stores artifacts under a shared `"public"` scope.
- Files: `backend/app/api/html_upload.py`, `backend/app/api/data_analysis.py`, `backend/app/services/data_analysis/storage.py`, `teacher-platform/src/views/QuestionGenerate.vue`, `teacher-platform/src/views/LessonPrepMindmap.vue`, `teacher-platform/src/views/LessonPrepPpt.vue`
- Current mitigation: extension and size checks exist, but there is no `CurrentUser` dependency and no per-user ownership boundary in the `"public"` scope.
- Recommendations: require authentication, scope uploads by user ID, add retention cleanup, and rate-limit anonymous upload paths if any anonymous access must remain.

## Performance Bottlenecks

**Whole-file buffering and duplicate reads on uploads:**
- Problem: several upload paths read entire files into memory before validation or forwarding; some flows then hand the same stream to downstream logic that reads it again.
- Files: `backend/app/api/courseware.py`, `backend/app/services/oss_service.py`, `backend/app/api/data_analysis.py`, `backend/app/api/html_upload.py`
- Cause: handlers use `await file.read()` for size checks and content handling instead of streaming validation/upload; `upload_courseware()` reads the whole file and `oss_service.upload_file()` reads it again.
- Improvement path: stream uploads with chunked validation, compute size incrementally, and avoid double-buffering before OSS transfer.

**Aggressive client polling loops for long-running PPT tasks:**
- Problem: PPT preview repeatedly polls backend task endpoints and reloads page/material state on a timer.
- Files: `teacher-platform/src/views/ppt/PptPreview.vue`, `teacher-platform/src/api/ppt.js`, `backend/app/generators/ppt/banana_routes.py`
- Cause: `waitForImageTask()` polls every 2.5 seconds for up to 8 minutes and reloads preview data each cycle; multiple other export/edit/material flows use similar polling functions.
- Improvement path: consolidate task polling into a shared backoff-aware composable or move task progress to SSE/WebSocket updates.

**Sequential rehearsal scene generation limits throughput:**
- Problem: rehearsal generation builds each scene one after another.
- Files: `backend/app/services/rehearsal_generation_service.py`
- Cause: `generate_rehearsal_stream()` loops through outlines and awaits `_generate_scene(...)` sequentially; TTS is decoupled, but scene generation itself is serialized.
- Improvement path: parallelize bounded batches of scene generation with concurrency controls and preserve ordered SSE updates separately.

## Fragile Areas

**Rehearsal generation state is split between SSE store logic and page-level polling logic:**
- Files: `teacher-platform/src/stores/rehearsal.js`, `teacher-platform/src/views/rehearsal/RehearsalNew.vue`, `backend/app/services/rehearsal_generation_service.py`, `backend/app/services/rehearsal_session_service.py`
- Why fragile: the same concepts (`sceneStatuses`, `generatingStatus`, aggregate session status, retries) are maintained in multiple places with different update paths.
- Safe modification: keep a single source of truth in the store and reuse one mapping function for live SSE updates and loaded sessions.
- Test coverage: `backend/tests/test_rehearsal_generation_service.py` covers helper functions only; there is no frontend test covering `RehearsalNew.vue` state transitions, polling, or retry UX.

**PPT preview task handling is highly stateful and DOM-coupled:**
- Files: `teacher-platform/src/views/ppt/PptPreview.vue`
- Why fragile: export polling, image generation, region selection, header button binding, version switching, and material generation all live in one component with shared mutable state.
- Safe modification: extract task runners, header bindings, and region-selection behavior into composables before changing flow logic.
- Test coverage: no automated tests were found for `teacher-platform/src/views/ppt/PptPreview.vue`.

**Vendored avatar SDK in source tree:**
- Files: `teacher-platform/src/libs/avatar-sdk-web_3.1.2.1002/index.js`, `teacher-platform/src/libs/avatar-sdk-web_3.1.2.1002/index-OS7Lza_r.js`, `teacher-platform/src/libs/avatar-sdk-web_3.1.2.1002/webrtc-player--YuOiwFd.js`, `teacher-platform/src/libs/avatar-sdk-web_3.1.2.1002/xrtc-player-BJTnVhG9.js`, `teacher-platform/src/components/DigitalHumanAssistant.vue`
- Why fragile: minified third-party bundles are committed directly into `src/` and loaded by a large hand-written integration component; upgrades and debugging require manual vendor management.
- Safe modification: isolate SDK loading behind a thin adapter module and keep the vendor package outside normal app source where possible.
- Test coverage: no automated tests were found for the digital-human integration path.

## Scaling Limits

**Shared public upload namespace for data analysis:**
- Current capacity: one shared `"public"` scope stores uploaded workbooks and generated outputs under `media/data_analysis/uploads/public` and `media/data_analysis/outputs/public`.
- Limit: storage growth, retention management, and user isolation all degrade as concurrent usage grows because assets are not partitioned by authenticated owner.
- Scaling path: store by user/workspace, add cleanup jobs, and move generated artifacts to object storage with signed URLs.

**Synchronous request/response processing for expensive file extraction:**
- Current capacity: `backend/app/api/html_upload.py` extracts text inline after saving, and `backend/app/api/data_analysis.py` loads Excel profiles inline in request handlers.
- Limit: latency and worker utilization rise with larger files or concurrent uploads because CPU-bound parsing stays on the API path.
- Scaling path: offload extraction/profiling to background tasks with persisted job status endpoints.

## Dependencies at Risk

**Environment-sensitive document conversion stack:**
- Risk: PPT renovation depends on external system tools and large parsing libraries that vary by host environment.
- Impact: `backend/app/generators/ppt/renovation_service.py` can fail when LibreOffice/`soffice`, fonts, or related binary dependencies are missing or misconfigured.
- Migration plan: containerize the conversion runtime, add startup diagnostics for required binaries, and keep the parsing/conversion boundary behind one service API.

**Duplicate and loosely controlled dependency declarations:**
- Risk: `backend/requirements.txt` declares `oss2` twice and mixes wide `>=` ranges with unpinned packages such as `lightrag-hku`.
- Impact: dependency resolution can drift across environments and make production behavior hard to reproduce.
- Migration plan: deduplicate `backend/requirements.txt`, generate a lockfile, and pin packages with known binary/runtime compatibility requirements.

## Missing Critical Features

**Legacy chat-to-PPT path is not production-complete:**
- Problem: the older chat flow still relies on placeholder AI responses and placeholder document generation.
- Blocks: `backend/app/api/chat.py`, `backend/app/services/ai/lesson_generator.py`, `backend/app/generators/ppt_generator.py`, `backend/app/generators/docx_generator.py`, and `backend/app/generators/game_generator.py` cannot serve as a reliable end-to-end teaching-material pipeline.

**Frontend automated testing is effectively absent:**
- Problem: `teacher-platform/package.json` has no test scripts or test runner setup, and only one lightweight test file was found at `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.
- Blocks: safe refactoring of `teacher-platform/src/views/ppt/*`, `teacher-platform/src/views/rehearsal/*`, and `teacher-platform/src/components/DigitalHumanAssistant.vue`.

## Test Coverage Gaps

**Security-sensitive auth and storage paths:**
- What's not tested: browser token persistence in `teacher-platform/src/api/http.js` and `teacher-platform/src/stores/user.js`, plus backend auth flows in `backend/app/api/auth.py` beyond basic endpoint behavior.
- Files: `teacher-platform/src/api/http.js`, `teacher-platform/src/stores/user.js`, `backend/app/api/auth.py`
- Risk: token handling regressions or XSS-hardening changes can silently break login/logout/session recovery behavior.
- Priority: High

**Anonymous/public upload flows:**
- What's not tested: unauthenticated file upload and parsing paths for `html_upload` and `data_analysis`, including retention, ownership, and malformed-file handling.
- Files: `backend/app/api/html_upload.py`, `backend/app/api/data_analysis.py`, `backend/app/services/data_analysis/storage.py`
- Risk: abuse, storage leaks, and parsing failures can go unnoticed until production load.
- Priority: High

**Large PPT and rehearsal UI workflows:**
- What's not tested: task polling, retry flows, export UX, and status synchronization in the main Vue views.
- Files: `teacher-platform/src/views/ppt/PptPreview.vue`, `teacher-platform/src/views/rehearsal/RehearsalNew.vue`, `teacher-platform/src/components/DigitalHumanAssistant.vue`
- Risk: regressions in async UI state are likely because the most complex frontend flows do not have automated coverage.
- Priority: High

---

*Concerns audit: 2026-04-12*
