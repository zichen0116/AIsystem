# PPT Preview Polish Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve PPT preview responsiveness and finish the missing fullscreen/PDF/zoom interaction details in the PPT workspace.

**Architecture:** Keep the existing `LessonPrepPpt.vue` + `PptCanvas.vue` split, but move fragile preview behavior into small pure helpers so we can cover them with `node:test` regression tests. Optimize redraws by separating main-slide rendering from thumbnail rendering and only refreshing the affected thumbnail after edit persistence.

**Tech Stack:** Vue 3 Composition API, html2pdf.js, existing Docmee `Ppt2Svg` / `Ppt2Canvas` renderers, Node `node:test`

---

## Chunk 1: Testable Preview Helpers

### Task 1: Add pure preview helper coverage

**Files:**
- Create: `teacher-platform/src/utils/pptPreview.js`
- Create: `teacher-platform/tests/ppt-preview.test.mjs`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal helper implementation**
- [ ] **Step 4: Run test to verify it passes**

### Task 2: Cover zoom edge cases and toast timing helpers

**Files:**
- Modify: `teacher-platform/tests/ppt-preview.test.mjs`
- Modify: `teacher-platform/src/utils/pptPreview.js`

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal helper implementation**
- [ ] **Step 4: Run test to verify it passes**

## Chunk 2: Preview Rendering and Interaction

### Task 3: Refactor main canvas redraw behavior

**Files:**
- Modify: `teacher-platform/src/components/ppt/PptCanvas.vue`
- Modify: `teacher-platform/src/utils/pptPreview.js`
- Test: `teacher-platform/tests/ppt-preview.test.mjs`

- [ ] **Step 1: Write the failing test for redraw-related helper behavior**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Update `PptCanvas.vue` to use the helper-backed zoom and transient toast behavior**
- [ ] **Step 4: Run test to verify it passes**

### Task 4: Refresh only the changed thumbnail

**Files:**
- Modify: `teacher-platform/src/components/ppt/PptThumbnailList.vue`
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Test: `teacher-platform/tests/ppt-preview.test.mjs`

- [ ] **Step 1: Write the failing test for changed slide detection**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement selective thumbnail refresh plumbing**
- [ ] **Step 4: Run test to verify it passes**

## Chunk 3: Fullscreen, PDF, and Layout Polish

### Task 5: Implement preview-only fullscreen mode

**Files:**
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`

- [ ] **Step 1: Add fullscreen state and keyboard/escape handling**
- [ ] **Step 2: Update template and styles to let the preview panel fill the screen**
- [ ] **Step 3: Verify behavior with a production build**

### Task 6: Implement PDF export for all slides

**Files:**
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Modify: `teacher-platform/src/components/ppt/PptCanvas.vue`

- [ ] **Step 1: Add export flow using the existing preview DOM/html2pdf.js**
- [ ] **Step 2: Ensure export renders all slides in order and hides transient UI**
- [ ] **Step 3: Verify behavior with a production build**

### Task 7: Adjust scrollbar/footer placement

**Files:**
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Modify: `teacher-platform/src/components/ppt/PptCanvas.vue`

- [ ] **Step 1: Move the horizontal scroll region flush with the footer boundary**
- [ ] **Step 2: Verify 100% zoom layout and note area spacing visually via build preview**

## Chunk 4: Final Verification

### Task 8: Run regression tests and build

**Files:**
- Test: `teacher-platform/tests/ppt-preview.test.mjs`

- [ ] **Step 1: Run `node --test teacher-platform/tests/ppt-preview.test.mjs`**
- [ ] **Step 2: Run `npm run build` in `teacher-platform`**
- [ ] **Step 3: Confirm outputs before reporting completion**
