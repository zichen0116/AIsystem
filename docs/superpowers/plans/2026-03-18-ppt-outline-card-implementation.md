# PPT Outline Card Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw markdown outline chat rendering with a persistent structured outline card flow that supports gentle one-by-one clarification, per-page image choice, structured editing, and markdown conversion for Docmee generation.

**Architecture:** Treat `outline_payload` JSON as the single source of truth for outline cards. The backend will generate/store/return both legacy markdown and structured payload during migration, and the frontend will render/edit the structured payload while converting it back to Docmee-compliant markdown only at approval/generation time.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL JSONB, Vue 3 Composition API, existing SSE/fetch reader flow, Node `node:test`

---

## Chunk 1: Backend Outline Payload Foundation

### Task 1: Extend outline persistence and schema

**Files:**
- Modify: `backend/app/models/ppt_outline.py`
- Modify: `backend/app/schemas/ppt.py`
- Create: `backend/alembic/versions/<timestamp>_add_outline_payload_to_ppt_outlines.py`

- [ ] **Step 1: Write the failing backend test for serializing `outline_payload`**
- [ ] **Step 2: Run the backend test to verify it fails**
- [ ] **Step 3: Add `outline_payload` field and schema exposure**
- [ ] **Step 4: Run the backend test to verify it passes**

### Task 2: Add payload/markdown conversion helpers

**Files:**
- Create: `backend/app/services/ppt/outline_payload.py`
- Create: `backend/tests/test_ppt_outline_payload.py`

- [ ] **Step 1: Write failing tests for markdown conversion and image insertion syntax**
- [ ] **Step 2: Run the backend test to verify it fails**
- [ ] **Step 3: Implement minimal payload conversion helpers**
- [ ] **Step 4: Run the backend test to verify it passes**

## Chunk 2: Gentle Clarification and Outline Generation

### Task 3: Replace rigid clarification prompts with gentle single-question flow

**Files:**
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Create: `teacher-platform/src/utils/pptOutlineFlow.js`
- Create: `teacher-platform/tests/ppt-outline-flow.test.mjs`

- [ ] **Step 1: Write failing tests for one-question-at-a-time clarification sequencing**
- [ ] **Step 2: Run the frontend test to verify it fails**
- [ ] **Step 3: Implement the minimal clarification helper logic**
- [ ] **Step 4: Run the frontend test to verify it passes**

### Task 4: Persist assistant lead-in message plus structured outline message

**Files:**
- Modify: `backend/app/api/ppt.py`
- Modify: `backend/app/services/ppt/nodes.py`
- Modify: `teacher-platform/src/api/ppt.js`

- [ ] **Step 1: Write failing backend/frontend tests for `outline_ready` payload shape**
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Emit assistant text message then structured outline card payload**
- [ ] **Step 4: Run tests to verify they pass**

## Chunk 3: Structured Outline Card UI

### Task 5: Replace markdown outline rendering with structured card rendering

**Files:**
- Modify: `teacher-platform/src/components/ppt/OutlineCard.vue`
- Modify: `teacher-platform/src/components/ppt/ChatMessage.vue`
- Modify: `teacher-platform/src/components/ppt/ChatPanel.vue`
- Create: `teacher-platform/src/utils/pptOutlineCard.js`
- Modify: `teacher-platform/tests/ppt-outline-flow.test.mjs`

- [ ] **Step 1: Write failing tests for card mapping and selected-image behavior**
- [ ] **Step 2: Run the frontend test to verify it fails**
- [ ] **Step 3: Implement structured card view/edit state with per-page 2-image choice**
- [ ] **Step 4: Run the frontend test to verify it passes**

### Task 6: Save edits and image selection back to the current outline

**Files:**
- Modify: `backend/app/api/ppt.py`
- Modify: `backend/app/schemas/ppt.py`
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Modify: `teacher-platform/src/api/ppt.js`

- [ ] **Step 1: Write failing tests for approving/saving outline payload mutations**
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement payload save/update handling for text edits and image selection**
- [ ] **Step 4: Run tests to verify they pass**

## Chunk 4: Generation and Rehydration

### Task 7: Generate Docmee markdown from payload at approval/generation time

**Files:**
- Modify: `backend/app/api/ppt.py`
- Modify: `backend/app/services/ppt/outline_payload.py`
- Modify: `backend/tests/test_ppt_outline_payload.py`

- [ ] **Step 1: Write failing tests for Docmee markdown output with selected images**
- [ ] **Step 2: Run the backend test to verify it fails**
- [ ] **Step 3: Use payload-derived markdown in the generation path**
- [ ] **Step 4: Run the backend test to verify it passes**

### Task 8: Rehydrate saved sessions into the same outline card UI

**Files:**
- Modify: `backend/app/api/ppt.py`
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Modify: `teacher-platform/src/components/ppt/ChatMessage.vue`

- [ ] **Step 1: Write failing tests for session reload card reconstruction**
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Return and map saved `outline_payload` for current/history outlines**
- [ ] **Step 4: Run tests to verify they pass**

## Chunk 5: Final Verification

### Task 9: Run focused verification

**Files:**
- Test: `backend/tests/test_ppt_outline_payload.py`
- Test: `teacher-platform/tests/ppt-outline-flow.test.mjs`

- [ ] **Step 1: Run `pytest backend/tests/test_ppt_outline_payload.py -q`**
- [ ] **Step 2: Run `node --test teacher-platform/tests/ppt-outline-flow.test.mjs`**
- [ ] **Step 3: Run `npm.cmd run build` in `teacher-platform`**
- [ ] **Step 4: Confirm outputs before reporting completion**
