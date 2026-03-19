# PPT Speaker Notes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate, persist, edit, and display per-page `speaker_notes` for PPT outlines so the preview panel always shows the current slide's speaking notes.

**Architecture:** Treat `speaker_notes` as part of `outline_payload.sections[].pages[]`, generated during structured outline creation and saved through the existing outline approval flow. The frontend will render and edit the notes inside the outline card, then resolve preview notes from the current outline payload based on `activeSlideIndex` instead of reading a nonexistent global result field.

**Tech Stack:** FastAPI, SQLAlchemy JSONB persistence via `ppt_outlines.outline_payload`, Vue 3 Composition API, Node `node:test`, Python `unittest`

---

## Chunk 1: Backend Outline Payload Notes

### Task 1: Add failing backend tests for page-level speaker notes

**Files:**
- Modify: `backend/tests/test_ppt_outline_payload.py`
- Test: `backend/tests/test_ppt_outline_payload.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_markdown_to_outline_payload_adds_speaker_notes_per_page(self):
    payload = markdown_to_outline_payload(markdown, image_urls={})
    self.assertTrue(payload["sections"][0]["pages"][0]["speaker_notes"])

def test_payload_to_docmee_markdown_ignores_speaker_notes(self):
    markdown = payload_to_docmee_markdown(payload_with_notes)
    self.assertNotIn("演讲备注", markdown)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_ppt_outline_payload`
Expected: FAIL because `speaker_notes` is missing and markdown export behavior is unverified

- [ ] **Step 3: Write minimal implementation**

```python
def build_speaker_notes_for_page(page_title, blocks):
    return f"本页重点讲 {page_title} ..."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_ppt_outline_payload`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_ppt_outline_payload.py backend/app/services/ppt/outline_payload.py
git commit -m "feat: add speaker notes to outline payload"
```

### Task 2: Generate and preserve speaker notes in backend payload helpers

**Files:**
- Modify: `backend/app/services/ppt/outline_payload.py`
- Modify: `backend/app/api/ppt.py`
- Test: `backend/tests/test_ppt_outline_payload.py`

- [ ] **Step 1: Write the failing test for approval/save round-trip**

```python
def test_outline_payload_round_trip_keeps_speaker_notes(self):
    payload = {..., "speaker_notes": "note text"}
    markdown = payload_to_docmee_markdown(payload)
    self.assertEqual(payload["sections"][0]["pages"][0]["speaker_notes"], "note text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_ppt_outline_payload`
Expected: FAIL if helper rewrites or drops `speaker_notes`

- [ ] **Step 3: Write minimal implementation**

```python
page["speaker_notes"] = page.get("speaker_notes") or build_speaker_notes_for_page(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_ppt_outline_payload`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ppt/outline_payload.py backend/app/api/ppt.py backend/tests/test_ppt_outline_payload.py
git commit -m "feat: preserve speaker notes in outline approval flow"
```

## Chunk 2: Frontend Outline Card Editing

### Task 3: Add failing frontend tests for outline-card speaker notes editing

**Files:**
- Modify: `teacher-platform/tests/ppt-outline-card.test.mjs`
- Modify: `teacher-platform/src/components/ppt/OutlineCard.vue`
- Test: `teacher-platform/tests/ppt-outline-card.test.mjs`

- [ ] **Step 1: Write the failing tests**

```javascript
test('outline payload keeps speaker notes when cloning and editing', () => {
  const payload = cloneOutlinePayload(source)
  assert.equal(payload.sections[0].pages[0].speaker_notes, 'note text')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test teacher-platform/tests/ppt-outline-card.test.mjs`
Expected: FAIL because the card utility/component does not expose notes yet

- [ ] **Step 3: Write minimal implementation**

```vue
<textarea v-if="editing" v-model="page.speaker_notes" class="notes-input" />
<div v-else class="page-notes">{{ page.speaker_notes }}</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test teacher-platform/tests/ppt-outline-card.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add teacher-platform/tests/ppt-outline-card.test.mjs teacher-platform/src/components/ppt/OutlineCard.vue teacher-platform/src/utils/pptOutlineCard.js
git commit -m "feat: edit speaker notes in outline card"
```

### Task 4: Ensure outline payload normalization includes speaker notes

**Files:**
- Modify: `teacher-platform/src/utils/pptOutlineCard.js`
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Test: `teacher-platform/tests/ppt-outline-card.test.mjs`

- [ ] **Step 1: Write the failing test for legacy payload compatibility**

```javascript
test('normalization fills missing speaker notes with empty string', () => {
  const payload = markdownToOutlinePayload(markdown, {})
  assert.equal(typeof payload.sections[0].pages[0].speaker_notes, 'string')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test teacher-platform/tests/ppt-outline-card.test.mjs`
Expected: FAIL because old payloads do not receive normalized note fields

- [ ] **Step 3: Write minimal implementation**

```javascript
speaker_notes: typeof page.speaker_notes === 'string' ? page.speaker_notes : ''
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test teacher-platform/tests/ppt-outline-card.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add teacher-platform/src/utils/pptOutlineCard.js teacher-platform/src/views/LessonPrepPpt.vue teacher-platform/tests/ppt-outline-card.test.mjs
git commit -m "feat: normalize speaker notes in outline payload"
```

## Chunk 3: Preview Panel Notes Resolution

### Task 5: Add failing frontend tests for current-slide notes display

**Files:**
- Modify: `teacher-platform/tests/ppt-preview.test.mjs`
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Test: `teacher-platform/tests/ppt-preview.test.mjs`

- [ ] **Step 1: Write the failing tests**

```javascript
test('preview notes follow active slide index', () => {
  assert.equal(resolveSpeakerNotes(outlinePayload, 1), 'page-2 note')
})

test('preview notes fall back to empty placeholder', () => {
  assert.equal(resolveSpeakerNotes(null, 0), '')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test teacher-platform/tests/ppt-preview.test.mjs`
Expected: FAIL because preview footer still reads `currentResult?.speaker_notes`

- [ ] **Step 3: Write minimal implementation**

```javascript
const currentSpeakerNotes = computed(() => resolveSpeakerNotes(currentOutline.value?.outline_payload, activeSlideIndex.value))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test teacher-platform/tests/ppt-preview.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add teacher-platform/tests/ppt-preview.test.mjs teacher-platform/src/views/LessonPrepPpt.vue
git commit -m "feat: show current slide speaker notes in preview"
```

## Chunk 4: Focused Verification

### Task 6: Run combined verification for notes behavior

**Files:**
- Test: `backend/tests/test_ppt_outline_payload.py`
- Test: `teacher-platform/tests/ppt-outline-card.test.mjs`
- Test: `teacher-platform/tests/ppt-preview.test.mjs`

- [ ] **Step 1: Run backend verification**

Run: `python -m unittest tests.test_ppt_outline_payload`
Expected: PASS

- [ ] **Step 2: Run outline card verification**

Run: `node --test teacher-platform/tests/ppt-outline-card.test.mjs`
Expected: PASS

- [ ] **Step 3: Run preview verification**

Run: `node --test teacher-platform/tests/ppt-preview.test.mjs`
Expected: PASS

- [ ] **Step 4: Run broader regression set**

Run: `python -m unittest tests.test_ppt_slide_editing tests.test_ppt_outline_payload tests.test_docmee_client tests.test_core_imports`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_ppt_outline_payload.py teacher-platform/tests/ppt-outline-card.test.mjs teacher-platform/tests/ppt-preview.test.mjs
git commit -m "test: verify speaker notes flow"
```
