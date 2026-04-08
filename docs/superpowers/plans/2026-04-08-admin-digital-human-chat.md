# Admin Digital Human Intro and Chat Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated admin digital human chat flow that can introduce EduPrep, support light admin chat, and speak backend-generated responses instead of repeating recognized speech.

**Architecture:** Backend-first: add admin chat schemas and endpoint, extract intro/chat response service with fixed intro routing and speak-text sanitization, then rewire the admin widget into a single-turn voice loop with short in-memory history and duplicate suppression.

**Tech Stack:** FastAPI, Pydantic, existing DashScope LLM service, Vue 3, Web Speech API, iFlytek Avatar SDK

**Spec:** `docs/superpowers/specs/2026-04-08-admin-digital-human-chat-design.md`

---

## Chunk 1: Backend Admin Chat Contract

### Task 1: Add admin chat schemas

**Files:**
- Modify: `backend/app/schemas/digital_human.py`

- [ ] Add request/response models for admin chat history, request body, and response payload.
- [ ] Keep the API contract fixed at `{ message, history } -> { answer, speak_text, mode }`.

### Task 2: Add admin digital human service

**Files:**
- Create: `backend/app/services/admin_digital_human.py`
- Test: `backend/tests/test_admin_digital_human_api.py`

- [ ] Add intro intent detection for project/system/dashboard introduction queries.
- [ ] Add fixed project intro template for `intro` mode.
- [ ] Add `sanitize_speak_text()` to strip Markdown markers and keep output suitable for speech.
- [ ] Add chat generation wrapper that trims history, injects system prompt, calls the LLM service, and falls back safely on empty/error responses.

### Task 3: Expose the admin chat endpoint

**Files:**
- Modify: `backend/app/api/digital_human.py`
- Test: `backend/tests/test_admin_digital_human_api.py`

- [ ] Register `POST /api/v1/digital-human/admin/chat`.
- [ ] Route intro queries to the fixed intro response and everything else to the LLM-backed chat path.
- [ ] Return validated response models.

## Chunk 2: Admin Widget Voice Loop

### Task 4: Replace repeat-after-ASR behavior

**Files:**
- Modify: `teacher-platform/src/components/BigScreen/AdminDigitalHumanWidget.vue`

- [ ] Remove the old `isDashboardIntroQuery + direct writeText` logic.
- [ ] Submit recognized text to the admin chat endpoint instead of speaking the raw ASR result.

### Task 5: Add short conversation memory and state machine

**Files:**
- Modify: `teacher-platform/src/components/BigScreen/AdminDigitalHumanWidget.vue`

- [ ] Track recent conversation history in component memory only.
- [ ] Add `idle/listening/waiting_reply/speaking` states.
- [ ] Keep only the latest 3 rounds when sending history to the backend.

### Task 6: Add anti-duplication and speech resume control

**Files:**
- Modify: `teacher-platform/src/components/BigScreen/AdminDigitalHumanWidget.vue`

- [ ] Prevent the same recognized text from being submitted repeatedly in a short window.
- [ ] Prevent the same reply from being spoken repeatedly in a short window.
- [ ] While waiting for backend reply or while speaking, ignore new recognition results.
- [ ] Resume listening only after the avatar finishes the current speech.

## Chunk 3: Verification

### Task 7: Backend tests

**Files:**
- Test: `backend/tests/test_admin_digital_human_api.py`

- [ ] Verify intro queries return the fixed EduPrep introduction.
- [ ] Verify chat queries pass history into the LLM path and return sanitized speak text.

### Task 8: Frontend regression verification

**Files:**
- Modify: `teacher-platform/src/components/BigScreen/AdminDigitalHumanWidget.vue`

- [ ] Build the frontend to catch syntax or import regressions.
- [ ] Manually verify intro query, casual chat, repeated speech suppression, and recovery after API failure.

## Assumptions

- V1 keeps voice-only interaction for the admin widget.
- V1 does not integrate knowledge base retrieval or real-time dashboard data lookup.
- V1 does not persist admin chat history to the database.
- Fixed intro copy and system prompt remain backend-owned constants.
