# PPT Safe Text Editing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make common PPT text edits update existing page text safely without letting the LLM rebuild the whole slide JSON.

**Architecture:** Extend backend slide editing with a deterministic text-targeting path for title, subtitle, and body-like content. Keep the existing LLM JSON rewrite as a fallback only when the instruction cannot be matched safely.

**Tech Stack:** FastAPI backend service helpers, Python `unittest`, existing Docmee page JSON structure

---

## Chunk 1: Safe Target Detection

### Task 1: Add regression tests for safe text updates and fallback

**Files:**
- Modify: `backend/tests/test_ppt_slide_editing.py`
- Test: `backend/tests/test_ppt_slide_editing.py`

- [ ] **Step 1: Write failing tests for subtitle, body, and fallback-to-LLM behavior**
- [ ] **Step 2: Run `python -m unittest tests.test_ppt_slide_editing` in `backend` to verify the new assertions fail**
- [ ] **Step 3: Keep the title regression test green while adding the new failures**
- [ ] **Step 4: Re-run `python -m unittest tests.test_ppt_slide_editing` and confirm only the new behavior is failing**

## Chunk 2: Minimal Safe Editing Implementation

### Task 2: Expand deterministic slide text editing

**Files:**
- Modify: `backend/app/services/ppt/nodes.py`
- Test: `backend/tests/test_ppt_slide_editing.py`

- [ ] **Step 1: Add instruction parsing for subtitle/body style edits**
- [ ] **Step 2: Add text-node targeting helpers that preserve page structure**
- [ ] **Step 3: Keep unmatched instructions on the existing LLM fallback path**
- [ ] **Step 4: Run `python -m unittest tests.test_ppt_slide_editing` and confirm all tests pass**

## Chunk 3: Focused Verification

### Task 3: Run related backend regression tests

**Files:**
- Test: `backend/tests/test_ppt_slide_editing.py`
- Test: `backend/tests/test_ppt_outline_payload.py`
- Test: `backend/tests/test_docmee_client.py`
- Test: `backend/tests/test_core_imports.py`

- [ ] **Step 1: Run `python -m unittest tests.test_ppt_slide_editing tests.test_ppt_outline_payload tests.test_docmee_client tests.test_core_imports` in `backend`**
- [ ] **Step 2: Confirm the safe editing change does not break outline/docmee support**
