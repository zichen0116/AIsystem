# PPT File Generation Video Support Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing PPT file-generation flow so uploaded videos can be parsed and used to generate outline pages.

**Architecture:** Reuse the current `file-generation` route and async task pipeline. Add video file validation on the route, rely on the existing `ParserFactory -> VideoParser` path for parsing, and update the frontend file picker plus copy so users can discover the feature and understand its limits.

**Tech Stack:** FastAPI, pytest, Vue 3, Pinia

---

## Chunk 1: Backend route support

### Task 1: Add a failing acceptance test for video uploads

**Files:**
- Modify: `backend/tests/test_file_generation.py`
- Test: `backend/tests/test_file_generation.py`

- [ ] **Step 1: Write the failing test**

Add a route test proving `POST /api/v1/ppt/projects/file-generation` accepts `test.mp4` and returns `200` with `status == "processing"`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_file_generation.py -k video_file_returns_processing -q`
Expected: FAIL because the route currently rejects `mp4`.

- [ ] **Step 3: Write minimal implementation**

Update backend file-type validation to include supported video extensions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_file_generation.py -k video_file_returns_processing -q`
Expected: PASS

### Task 2: Preserve unsupported-type rejection

**Files:**
- Modify: `backend/tests/test_file_generation.py`
- Modify: `backend/app/generators/ppt/banana_routes.py`

- [ ] **Step 1: Update the rejection test**

Change the unsupported-type test to use a truly unsupported file type such as `xlsx`.

- [ ] **Step 2: Run test to verify expected behavior**

Run: `pytest backend/tests/test_file_generation.py -k unsupported_file_type_returns_400 -q`
Expected: PASS with `400`

- [ ] **Step 3: Extend MIME normalization**

Add common video MIME-to-extension mappings in `_normalize_file_ext`.

- [ ] **Step 4: Re-run both route tests**

Run: `pytest backend/tests/test_file_generation.py -k "video_file_returns_processing or unsupported_file_type_returns_400" -q`
Expected: both PASS

## Chunk 2: Frontend upload support

### Task 3: Allow video files in file-generation mode

**Files:**
- Modify: `teacher-platform/src/views/ppt/PptHome.vue`

- [ ] **Step 1: Update accept list**

Extend `fileAcceptMap.file` to include `mp4/mov/avi/mkv/flv`.

- [ ] **Step 2: Update drag-and-drop validation**

Ensure drop validation uses the updated list without additional branching.

- [ ] **Step 3: Update mode description and upload hint**

Add concise user-facing text saying video is supported and parsing quality depends on multimodal configuration.

- [ ] **Step 4: Review the rendered strings for consistency**

Check the affected template and script sections for matching copy and no stale wording.

## Chunk 3: Verification

### Task 4: Run focused regression checks

**Files:**
- Verify only

- [ ] **Step 1: Run backend file-generation tests**

Run: `pytest backend/tests/test_file_generation.py -q`
Expected: PASS

- [ ] **Step 2: Run multimodal fallback tests**

Run: `pytest backend/tests/test_multimodal_fallback.py -q`
Expected: PASS

- [ ] **Step 3: Summarize outcomes**

Record which tests passed and whether any environment-dependent quality limitations remain.
