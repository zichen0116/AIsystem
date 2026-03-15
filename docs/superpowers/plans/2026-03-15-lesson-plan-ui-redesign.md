# 教案生成页面 UI 重设计 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the lesson plan generation page from a 3-column layout to a Doubao-style dialog/writer dual-mode switching interface.

**Architecture:** Full rewrite of `LessonPrepLessonPlan.vue` and its child components. New component tree with `LessonPlanPage.vue` as root, managing two mutually exclusive modes (dialog/writer) via reactive state. Reuses existing backend APIs and Tiptap editor stack.

**Tech Stack:** Vue 3 Composition API, Tiptap v3 (3.20.1), markdown-it, html2pdf.js, SSE via fetch + ReadableStream

**Spec:** `docs/superpowers/specs/2026-03-15-lesson-plan-ui-redesign.md`

---

## File Structure

### New Files (Create)
| File | Responsibility |
|------|---------------|
| `src/components/lesson-plan-v2/ChatInput.vue` | Shared input component (textarea + action buttons inside + send) |
| `src/components/lesson-plan-v2/ChatMessage.vue` | Single message bubble (user right-aligned blue / AI left-aligned white) |
| `src/components/lesson-plan-v2/DocumentCard.vue` | Special message card triggering writer mode |
| `src/components/lesson-plan-v2/ChatFlow.vue` | Scrollable message list, renders ChatMessage + DocumentCard |
| `src/components/lesson-plan-v2/WelcomePanel.vue` | Phase 1 welcome page (title + 9-grid prompt cards) |
| `src/components/lesson-plan-v2/FloatingToolbar.vue` | Notion-style floating format toolbar on text selection |
| `src/components/lesson-plan-v2/EditorTOC.vue` | Floating table of contents inside editor |
| `src/components/lesson-plan-v2/WriterEditor.vue` | Rich text editor panel (topbar inlined + Tiptap + TOC). Note: spec lists `EditorToolbar.vue` separately but we inline it to reduce file count — the topbar is only ~10 lines of template. |
| `src/components/lesson-plan-v2/WriterChat.vue` | Writer mode left panel (ChatFlow + ChatInput) |
| `src/components/lesson-plan-v2/LessonPlanDialog.vue` | Dialog mode container (WelcomePanel or ChatFlow + ChatInput) |
| `src/components/lesson-plan-v2/LessonPlanWriter.vue` | Writer mode container (WriterChat + WriterEditor) |
| `src/components/lesson-plan-v2/LessonPlanSidebar.vue` | Left history sidebar (UI shell, mock data) |
| `src/views/LessonPlanPage.vue` | Top-level page: mode state, SSE handling, API calls |

### Modified Files
| File | Change |
|------|--------|
| `src/views/LessonPrep.vue:39-49` | Update `currentComponent` map to use `LessonPlanPage` |

### Deleted Files (after integration verified)
| File |
|------|
| `src/views/LessonPrepLessonPlan.vue` |
| `src/components/lesson-plan/LessonPlanChat.vue` |
| `src/components/lesson-plan/LessonPlanEditor.vue` |
| `src/components/lesson-plan/LessonPlanTOC.vue` |

---

## Chunk 1: Shared UI Components

### Task 1: Create ChatInput.vue

**Files:**
- Create: `src/components/lesson-plan-v2/ChatInput.vue`

- [ ] **Step 1: Create ChatInput component**

```vue
<template>
  <div class="chat-input-area">
    <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
    <div class="chat-input-box" :class="{ focused }">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        :placeholder="placeholder"
        rows="2"
        @focus="focused = true"
        @blur="focused = false"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="chat-input-bottom">
        <div class="chat-input-actions">
          <button class="action-btn" @click="triggerUpload">
            <span class="action-icon">📎</span> 上传文件
          </button>
          <button class="action-btn" @click="toggleRecording" :class="{ recording: isRecording }">
            <span class="action-icon">🎙</span> {{ isRecording ? '停止' : '语音输入' }}
          </button>
          <button class="action-btn" @click="showLibPicker = !showLibPicker">
            <span class="action-icon">📚</span> 知识库
          </button>
        </div>
        <button class="send-btn" @click="handleSend" :disabled="!canSend">▶</button>
      </div>

      <!-- Tags for uploaded files and selected libraries -->
      <div v-if="uploadedFiles.length || selectedLibraries.length" class="input-tags">
        <span v-for="f in uploadedFiles" :key="f.file_id" class="tag tag-file">
          {{ f.filename }} <span class="tag-close" @click="removeFile(f.file_id)">&times;</span>
        </span>
        <span v-for="lib in selectedLibraries" :key="lib.id" class="tag tag-lib">
          {{ lib.name }} <span class="tag-close" @click="removeLib(lib.id)">&times;</span>
        </span>
      </div>
    </div>

    <!-- Hidden file input -->
    <input ref="fileInput" type="file" hidden accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" @change="handleFileUpload" />

    <!-- Knowledge base picker dropdown -->
    <div v-if="showLibPicker" class="lib-picker">
      <div class="lib-section">
        <div class="lib-section-title">个人知识库</div>
        <label v-for="lib in personalLibs" :key="lib.id" class="lib-option">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          {{ lib.name }}
        </label>
        <div v-if="!personalLibs.length" class="lib-empty">暂无</div>
      </div>
      <div class="lib-section">
        <div class="lib-section-title">系统知识库</div>
        <label v-for="lib in systemLibs" :key="lib.id" class="lib-option">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          {{ lib.name }}
        </label>
        <div v-if="!systemLibs.length" class="lib-empty">暂无</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { resolveApiUrl, getToken } from '../../api/http.js'
import { useVoiceInput } from '../../composables/useVoiceInput.js'

const props = defineProps({
  placeholder: { type: String, default: '发消息以生成教案...' },
  disabled: { type: Boolean, default: false },
  lessonPlanId: { type: [Number, String], default: null },
})

const emit = defineEmits(['send'])

const inputText = ref('')
const focused = ref(false)
const textareaRef = ref(null)
const fileInput = ref(null)
const uploadedFiles = ref([])
const selectedLibIds = ref([])
const personalLibs = ref([])
const systemLibs = ref([])
const showLibPicker = ref(false)

const uploadError = ref('')

const { isRecording, toggleRecording } = useVoiceInput(inputText)

const selectedLibraries = computed(() => {
  const all = [...personalLibs.value, ...systemLibs.value]
  return all.filter(l => selectedLibIds.value.includes(l.id))
})

const canSend = computed(() => inputText.value.trim() && !props.disabled)

function handleSend() {
  if (!canSend.value) return
  emit('send', {
    text: inputText.value.trim(),
    file_ids: uploadedFiles.value.map(f => f.file_id),
    library_ids: selectedLibIds.value,
  })
  inputText.value = ''
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  if (props.lessonPlanId) formData.append('lesson_plan_id', props.lessonPlanId)
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/upload'), {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    })
    if (!res.ok) throw new Error('上传失败')
    const data = await res.json()
    uploadedFiles.value.push(data)
  } catch (err) {
    console.error('File upload error:', err)
    uploadError.value = '文件上传失败，请重试'
    setTimeout(() => { uploadError.value = '' }, 3000)
  }
  e.target.value = ''
}

function removeFile(fileId) {
  uploadedFiles.value = uploadedFiles.value.filter(f => f.file_id !== fileId)
}

function removeLib(libId) {
  selectedLibIds.value = selectedLibIds.value.filter(id => id !== libId)
}

async function fetchLibraries() {
  try {
    const token = getToken()
    const headers = { Authorization: `Bearer ${token}` }
    const [pRes, sRes] = await Promise.all([
      fetch(resolveApiUrl('/api/v1/libraries?scope=personal'), { headers }),
      fetch(resolveApiUrl('/api/v1/libraries?scope=system'), { headers }),
    ])
    if (pRes.ok) personalLibs.value = (await pRes.json()).items || []
    if (sRes.ok) systemLibs.value = (await sRes.json()).items || []
  } catch (err) {
    console.error('Failed to fetch libraries:', err)
  }
}

function restoreFiles(files) {
  uploadedFiles.value = files || []
}

defineExpose({ restoreFiles })

onMounted(fetchLibraries)
</script>
```

Styles: Apply the input box design from the mockup — flex column layout, actions inside the box bottom row, send button right-aligned. See `docs/mockup-lesson-plan.html` `.chat-input-area` / `.chat-input-box` / `.chat-input-bottom` styles.

- [ ] **Step 2: Verify ChatInput renders**

Run: `cd teacher-platform && npm run dev`

Temporarily import in `LessonPrepLessonPlan.vue` to verify it renders. Check:
- Textarea accepts input
- Action buttons visible inside box
- Send button fires event
- File upload works
- Knowledge base dropdown opens

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/ChatInput.vue
git commit -m "feat(lesson-plan): add ChatInput shared input component"
```

---

### Task 2: Create ChatMessage.vue

**Files:**
- Create: `src/components/lesson-plan-v2/ChatMessage.vue`

- [ ] **Step 1: Create ChatMessage component**

```vue
<template>
  <div class="chat-msg" :class="msg.role">
    <div class="msg-bubble">
      <div v-if="msg.role === 'assistant'" v-html="renderedContent" />
      <template v-else>{{ msg.content }}</template>
    </div>
    <div v-if="msg.role === 'assistant'" class="ai-actions">
      <button @click="copyContent">📋 复制</button>
      <button @click="$emit('regenerate')">🔄 重新生成</button>
      <button @click="$emit('like')">👍</button>
      <button @click="$emit('dislike')">👎</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const props = defineProps({
  msg: { type: Object, required: true },
  // msg shape: { role: 'user' | 'assistant', content: string }
})

defineEmits(['regenerate', 'like', 'dislike'])

const renderedContent = computed(() => {
  return md.render(props.msg.content || '')
})

function copyContent() {
  navigator.clipboard.writeText(props.msg.content)
}
</script>
```

Styles: User message right-aligned with `background: #2563eb; color: #fff;` bubble. AI message left-aligned with `background: #fff; border: 1px solid #e8ecf0;` bubble. Action buttons below AI messages. See mockup `.chat-msg`, `.msg-bubble`, `.ai-actions` styles.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/ChatMessage.vue
git commit -m "feat(lesson-plan): add ChatMessage component"
```

---

### Task 3: Create DocumentCard.vue

**Files:**
- Create: `src/components/lesson-plan-v2/DocumentCard.vue`

- [ ] **Step 1: Create DocumentCard component**

```vue
<template>
  <div class="chat-msg ai">
    <div class="document-card" @click="$emit('open')">
      <div class="doc-icon">📄</div>
      <div class="doc-info">
        <div class="doc-title">{{ title || '教案文档' }}</div>
        <div class="doc-hint">点击查看完整教案</div>
      </div>
      <div class="doc-arrow">›</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '教案文档' },
})
defineEmits(['open'])
</script>
```

Styles: Card with white background, light border, rounded corners, flex row layout (icon + text + arrow). Hover: slight shadow + border color change to `#2563eb`. Distinguished from regular AI messages.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/DocumentCard.vue
git commit -m "feat(lesson-plan): add DocumentCard component"
```

---

### Task 4: Create ChatFlow.vue

**Files:**
- Create: `src/components/lesson-plan-v2/ChatFlow.vue`

- [ ] **Step 1: Create ChatFlow component**

```vue
<template>
  <div ref="flowRef" class="chat-flow">
    <template v-for="(msg, i) in messages" :key="i">
      <DocumentCard
        v-if="msg.type === 'document-card'"
        :title="msg.title"
        @open="$emit('open-document')"
      />
      <ChatMessage v-else :msg="msg" @regenerate="$emit('regenerate', i)" />
    </template>

    <!-- Streaming indicator -->
    <div v-if="isStreaming" class="chat-msg ai">
      <div class="msg-bubble">
        <div v-if="streamingText" v-html="renderStreaming(streamingText)" />
        <div v-else class="typing-indicator">
          <span /><span /><span />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import DocumentCard from './DocumentCard.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
})

defineEmits(['open-document', 'regenerate'])

const flowRef = ref(null)

function renderStreaming(text) {
  return text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (flowRef.value) {
      flowRef.value.scrollTop = flowRef.value.scrollHeight
    }
  })
}

// Auto-scroll when messages change or streaming updates
watch(() => props.messages.length, scrollToBottom)
watch(() => props.streamingText, scrollToBottom)

defineExpose({ scrollToBottom })
</script>
```

Styles: Flex column, `overflow-y: auto`, messages centered with `padding: 24px 15%` (dialog mode) or `padding: 20px 24px` (writer mode, controlled via prop or parent CSS). Typing indicator with 3 dots animation. See mockup `.chat-flow`, `.typing-indicator` styles.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/ChatFlow.vue
git commit -m "feat(lesson-plan): add ChatFlow message list component"
```

---

## Chunk 2: Dialog Mode

### Task 5: Create WelcomePanel.vue

**Files:**
- Create: `src/components/lesson-plan-v2/WelcomePanel.vue`

- [ ] **Step 1: Create WelcomePanel component**

```vue
<template>
  <div class="welcome-area">
    <div class="welcome-icon">📝</div>
    <div class="welcome-title">AI 智能教案生成</div>
    <div class="welcome-desc">告诉我你的教学需求，我来帮你生成专业教案</div>
    <div class="prompt-grid">
      <div
        v-for="(card, i) in promptCards"
        :key="i"
        class="prompt-card"
        @click="$emit('select-prompt', card.prompt)"
      >
        <div class="card-icon">{{ card.icon }}</div>
        <div class="card-title">{{ card.title }}</div>
        <div class="card-desc">{{ card.desc }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['select-prompt'])

// Placeholder prompt cards — content to be provided by user later
const promptCards = [
  { icon: '📐', title: '小学数学教案', desc: '帮我生成一份三年级「分数的初步认识」教案', prompt: '帮我生成一份三年级「分数的初步认识」教案' },
  { icon: '🔬', title: '实验课教案', desc: '设计一节高中化学实验课教案', prompt: '设计一节高中化学实验课教案' },
  { icon: '📖', title: '语文阅读课', desc: '初中语文《背影》精读课教案', prompt: '初中语文《背影》精读课教案' },
  { icon: '🌍', title: '地理探究课', desc: '「地球的运动」探究式教学设计', prompt: '帮我设计「地球的运动」探究式教学' },
  { icon: '🎨', title: '美术鉴赏课', desc: '小学美术色彩基础课教案', prompt: '帮我生成小学美术色彩基础课教案' },
  { icon: '🏃', title: '体育课教案', desc: '初中篮球基础技能训练课', prompt: '帮我设计初中篮球基础技能训练课教案' },
  { icon: '🎵', title: '音乐欣赏课', desc: '小学音乐节奏感培养教案', prompt: '帮我生成小学音乐节奏感培养教案' },
  { icon: '💻', title: '信息技术课', desc: '初中 Python 编程入门教案', prompt: '帮我生成初中 Python 编程入门教案' },
  { icon: '🧪', title: '跨学科融合', desc: 'STEM 项目式学习教案设计', prompt: '帮我设计一份 STEM 项目式学习教案' },
]
</script>
```

Styles: Centered flex column, `prompt-grid` as `grid-template-columns: repeat(3, 1fr)` with `gap: 12px`. Cards: white bg, border, rounded, hover with blue border + shadow + translateY(-1px). See mockup `.welcome-area`, `.prompt-grid`, `.prompt-card` styles.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/WelcomePanel.vue
git commit -m "feat(lesson-plan): add WelcomePanel with prompt cards"
```

---

### Task 6: Create LessonPlanDialog.vue

**Files:**
- Create: `src/components/lesson-plan-v2/LessonPlanDialog.vue`

- [ ] **Step 1: Create LessonPlanDialog component**

```vue
<template>
  <div class="dialog-container">
    <!-- Phase 1: Welcome (no messages yet) -->
    <WelcomePanel
      v-if="!hasMessages"
      @select-prompt="$emit('send-prompt', $event)"
    />

    <!-- Phase 2: Chat flow (has messages) -->
    <ChatFlow
      v-else
      ref="chatFlowRef"
      :messages="messages"
      :is-streaming="isStreaming"
      :streaming-text="streamingText"
      @open-document="$emit('open-document')"
      @regenerate="$emit('regenerate', $event)"
    />

    <!-- Input always at bottom -->
    <ChatInput
      :placeholder="placeholder"
      :disabled="isStreaming"
      :lesson-plan-id="lessonPlanId"
      @send="$emit('send', $event)"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import WelcomePanel from './WelcomePanel.vue'
import ChatFlow from './ChatFlow.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  lessonPlanId: { type: [Number, String], default: null },
})

defineEmits(['send', 'send-prompt', 'open-document', 'regenerate'])

const chatFlowRef = ref(null)

const hasMessages = computed(() => props.messages.length > 0)

const placeholder = computed(() =>
  hasMessages.value ? '继续对话...' : '发消息以生成教案...'
)

function scrollToBottom() {
  chatFlowRef.value?.scrollToBottom()
}

defineExpose({ scrollToBottom })
</script>
```

Styles: Flex column, `flex: 1`, overflow hidden. Welcome panel centered when no messages; ChatFlow takes remaining space above ChatInput.

- [ ] **Step 2: Verify dialog mode renders**

Run: `npm run dev`

Temporarily mount in `LessonPrepLessonPlan.vue` to verify:
- Welcome page shows when no messages
- Prompt card click triggers send-prompt event
- Chat flow shows when messages array is non-empty
- Input box positioned at bottom with action buttons inside

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/LessonPlanDialog.vue
git commit -m "feat(lesson-plan): add LessonPlanDialog mode container"
```

---

## Chunk 3: Writer Mode — Editor

### Task 7: Create FloatingToolbar.vue

**Files:**
- Create: `src/components/lesson-plan-v2/FloatingToolbar.vue`

- [ ] **Step 1: Create FloatingToolbar component**

Uses Tiptap's `BubbleMenu` extension (already in package.json as `@tiptap/extension-bubble-menu`).

```vue
<template>
  <BubbleMenu v-if="editor" :editor="editor" :tippy-options="{ duration: 150 }">
    <div class="floating-toolbar">
      <button @click="editor.chain().focus().toggleBold().run()" :class="{ active: editor.isActive('bold') }">
        <strong>B</strong>
      </button>
      <button @click="editor.chain().focus().toggleItalic().run()" :class="{ active: editor.isActive('italic') }">
        <em>I</em>
      </button>
      <button @click="editor.chain().focus().toggleUnderline().run()" :class="{ active: editor.isActive('underline') }">
        <u>U</u>
      </button>
      <div class="divider" />
      <button @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" :class="{ active: editor.isActive('heading', { level: 2 }) }">
        H2
      </button>
      <button @click="editor.chain().focus().toggleHeading({ level: 3 }).run()" :class="{ active: editor.isActive('heading', { level: 3 }) }">
        H3
      </button>
      <div class="divider" />
      <button @click="editor.chain().focus().toggleBulletList().run()" :class="{ active: editor.isActive('bulletList') }">
        •
      </button>
      <button @click="editor.chain().focus().toggleOrderedList().run()" :class="{ active: editor.isActive('orderedList') }">
        ≡
      </button>
      <div class="divider" />
      <button @click="editor.chain().focus().toggleHighlight().run()" :class="{ active: editor.isActive('highlight') }">
        🖍
      </button>
    </div>
  </BubbleMenu>
</template>

<script setup>
import { BubbleMenu } from '@tiptap/vue-3'

defineProps({
  editor: { type: Object, default: null },
})
</script>
```

Styles: Dark background (`#1a1a2e`), rounded 8px, flex row, button 30x28px with white text. Active state: `rgba(255,255,255,.15)` background. Divider: 1px vertical `#444`. See mockup `.floating-toolbar` styles.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/FloatingToolbar.vue
git commit -m "feat(lesson-plan): add FloatingToolbar with BubbleMenu"
```

---

### Task 8: Create EditorTOC.vue

**Files:**
- Create: `src/components/lesson-plan-v2/EditorTOC.vue`

- [ ] **Step 1: Create EditorTOC component**

Adapted from existing `LessonPlanTOC.vue` (IntersectionObserver pattern), positioned as floating panel inside editor.

```vue
<template>
  <div v-if="headings.length" class="editor-toc">
    <div class="toc-title">目录</div>
    <div
      v-for="(h, i) in headings"
      :key="i"
      class="toc-item"
      :class="[`level-${h.level}`, { active: activeIndex === i }]"
      @click="$emit('scroll-to', h.pos)"
    >
      {{ h.text }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  headings: { type: Array, default: () => [] },
  editorElement: { type: Object, default: null },
})

defineEmits(['scroll-to'])

const activeIndex = ref(0)
let observer = null

function setupObserver() {
  if (observer) observer.disconnect()
  if (!props.editorElement) return
  const headingEls = props.editorElement.querySelectorAll('h1, h2, h3')
  if (!headingEls.length) return
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const idx = Array.from(headingEls).indexOf(entry.target)
          if (idx >= 0) activeIndex.value = idx
        }
      })
    },
    { root: props.editorElement.closest('.editor-canvas'), rootMargin: '-10% 0px -80% 0px' }
  )
  headingEls.forEach(el => observer.observe(el))
}

watch(() => [props.headings, props.editorElement], () => {
  setTimeout(setupObserver, 100)
}, { deep: true })

onMounted(() => { if (props.editorElement) setupObserver() })
onBeforeUnmount(() => { observer?.disconnect() })
</script>
```

Styles: Positioned `absolute; right: 20px; top: 32px; width: 160px`. White bg, light border, rounded. Items: 12px font, indent by level (`level-2`: 0px, `level-3`: 12px). Active: blue color + font-weight 500. See mockup `.editor-toc` styles. z-index: 40.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/EditorTOC.vue
git commit -m "feat(lesson-plan): add EditorTOC floating navigation"
```

---

### Task 9: Create WriterEditor.vue

**Files:**
- Create: `src/components/lesson-plan-v2/WriterEditor.vue`

- [ ] **Step 1: Create WriterEditor component**

Reuses Tiptap extension config from existing `LessonPlanEditor.vue:88-102`. Integrates FloatingToolbar and EditorTOC.

```vue
<template>
  <div class="writer-editor">
    <!-- Top toolbar -->
    <div class="editor-topbar">
      <button class="back-btn" @click="$emit('back')">← 返回对话</button>
      <div class="export-group">
        <button @click="copyAll">📋 复制全文</button>
        <button @click="downloadWord">⬇ Word</button>
        <button @click="downloadPDF">⬇ PDF</button>
        <button @click="downloadMarkdown">⬇ Markdown</button>
      </div>
    </div>

    <!-- Editor canvas -->
    <div class="editor-canvas" ref="canvasRef">
      <!-- Streaming preview (when AI is generating) -->
      <div v-if="isStreaming" class="streaming-preview" v-html="streamingHtml" />

      <!-- Tiptap editor (when not streaming) -->
      <EditorContent v-show="!isStreaming" :editor="editor" />

      <!-- Floating format toolbar -->
      <FloatingToolbar v-if="editor && !isStreaming" :editor="editor" />

      <!-- Floating TOC -->
      <EditorTOC
        :headings="headings"
        :editor-element="editorEl"
        @scroll-to="scrollToPos"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Highlight from '@tiptap/extension-highlight'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import CharacterCount from '@tiptap/extension-character-count'
import { Markdown } from 'tiptap-markdown'
import MarkdownIt from 'markdown-it'
import taskListPlugin from 'markdown-it-task-lists'
import FloatingToolbar from './FloatingToolbar.vue'
import EditorTOC from './EditorTOC.vue'
import { resolveApiUrl, getToken } from '../../api/http.js'

const props = defineProps({
  isStreaming: { type: Boolean, default: false },
  streamingMarkdown: { type: String, default: '' },
})

const emit = defineEmits(['back', 'update:markdown', 'blur'])

const canvasRef = ref(null)
const editor = ref(null)
const headings = ref([])

const md = new MarkdownIt().use(taskListPlugin)
const streamingHtml = computed(() => md.render(props.streamingMarkdown || ''))

const editorEl = computed(() =>
  canvasRef.value?.querySelector('.ProseMirror') || null
)

const editorExtensions = [
  StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
  Placeholder.configure({ placeholder: '教案内容将在这里显示...' }),
  Table.configure({ resizable: true }),
  TableRow, TableCell, TableHeader,
  TaskList, TaskItem.configure({ nested: true }),
  Highlight,
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  Underline, CharacterCount, Markdown,
]

function createEditor(content = '') {
  if (editor.value) editor.value.destroy()
  editor.value = new Editor({
    extensions: editorExtensions,
    content,
    editable: true,
    onUpdate: () => {
      const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
      emit('update:markdown', mkdown)
      extractHeadings()
    },
    onBlur: () => emit('blur'),
  })
}

function extractHeadings() {
  if (!editor.value) return
  const h = []
  editor.value.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      h.push({ level: node.attrs.level, text: node.textContent, pos })
    }
  })
  headings.value = h
}

function scrollToPos(pos) {
  if (!editor.value) return
  const domAtPos = editor.value.view.domAtPos(pos)
  domAtPos.node?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
}

function getMarkdown() {
  return editor.value?.storage.markdown.getMarkdown() || ''
}

function loadContent(markdown) {
  if (!editor.value) createEditor(markdown)
  else editor.value.commands.setContent(markdown)
  nextTick(extractHeadings)
}

// When streaming ends, load content into editor
watch(() => props.isStreaming, (streaming, wasStreaming) => {
  if (wasStreaming && !streaming && props.streamingMarkdown) {
    loadContent(props.streamingMarkdown)
  }
})

function copyAll() {
  const text = getMarkdown()
  navigator.clipboard.writeText(text)
}

async function downloadWord() {
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/export/docx'), {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content: getMarkdown(), title: '教案' }),
    })
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = '教案.docx'; a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('DOCX export error:', err)
  }
}

function downloadPDF() {
  import('html2pdf.js').then(({ default: html2pdf }) => {
    const el = canvasRef.value?.querySelector('.ProseMirror')
    if (!el) return
    html2pdf().set({ margin: 10, filename: '教案.pdf' }).from(el).save()
  })
}

function downloadMarkdown() {
  const text = getMarkdown()
  const blob = new Blob([text], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = '教案.md'; a.click()
  URL.revokeObjectURL(url)
}

function destroy() {
  editor.value?.destroy()
  editor.value = null
}

defineExpose({ getMarkdown, loadContent, destroy, createEditor })

onBeforeUnmount(destroy)
</script>
```

Styles: Flex column, full height. Top bar: `#fafbfc` bg with flex justify-between. Canvas: `padding: 32px 48px`, `position: relative` for TOC positioning. Typography follows mockup `.editor-canvas h1/h2/h3/p/table` styles.

- [ ] **Step 2: Verify editor renders with floating toolbar**

Run: `npm run dev`

Test: Create editor with sample markdown, verify:
- Content renders in Tiptap
- Select text → floating toolbar appears
- Toolbar buttons toggle formatting
- TOC shows headings and scrolls on click
- Export buttons work

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/WriterEditor.vue
git commit -m "feat(lesson-plan): add WriterEditor with floating toolbar and TOC"
```

---

### Task 10: Create WriterChat.vue and LessonPlanWriter.vue

**Files:**
- Create: `src/components/lesson-plan-v2/WriterChat.vue`
- Create: `src/components/lesson-plan-v2/LessonPlanWriter.vue`

- [ ] **Step 1: Create WriterChat component**

```vue
<template>
  <div class="writer-chat">
    <ChatFlow
      ref="chatFlowRef"
      :messages="messages"
      :is-streaming="isStreaming"
      :streaming-text="streamingText"
      @open-document="$emit('open-document')"
    />
    <ChatInput
      placeholder="输入修改意见..."
      :disabled="isStreaming"
      :lesson-plan-id="lessonPlanId"
      @send="$emit('send-modify', $event)"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatFlow from './ChatFlow.vue'
import ChatInput from './ChatInput.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  lessonPlanId: { type: [Number, String], default: null },
})

defineEmits(['send-modify', 'open-document'])

const chatFlowRef = ref(null)

function scrollToBottom() {
  chatFlowRef.value?.scrollToBottom()
}

defineExpose({ scrollToBottom })
</script>
```

Styles: `width: 40%`, flex column, `border-right: 1px solid #eaedf0`, `background: #f7f8fa`. ChatFlow fills remaining space above ChatInput.

- [ ] **Step 2: Create LessonPlanWriter component**

```vue
<template>
  <div class="writer-layout">
    <WriterChat
      ref="writerChatRef"
      :messages="messages"
      :is-streaming="isStreaming"
      :streaming-text="streamingText"
      :lesson-plan-id="lessonPlanId"
      @send-modify="$emit('send-modify', $event)"
    />
    <WriterEditor
      ref="writerEditorRef"
      :is-streaming="isStreaming"
      :streaming-markdown="streamingMarkdown"
      @back="$emit('back')"
      @update:markdown="$emit('update:markdown', $event)"
      @blur="$emit('editor-blur')"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import WriterChat from './WriterChat.vue'
import WriterEditor from './WriterEditor.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  streamingMarkdown: { type: String, default: '' },
  lessonPlanId: { type: [Number, String], default: null },
})

defineEmits(['send-modify', 'back', 'update:markdown', 'editor-blur'])

const writerChatRef = ref(null)
const writerEditorRef = ref(null)

defineExpose({
  getMarkdown: () => writerEditorRef.value?.getMarkdown(),
  loadContent: (md) => writerEditorRef.value?.loadContent(md),
  destroyEditor: () => writerEditorRef.value?.destroy(),
  createEditor: (content) => writerEditorRef.value?.createEditor(content),
  scrollChatToBottom: () => writerChatRef.value?.scrollToBottom(),
})
</script>
```

Styles: `display: flex; flex: 1; overflow: hidden`. See mockup `.writer-layout` styles.

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/WriterChat.vue teacher-platform/src/components/lesson-plan-v2/LessonPlanWriter.vue
git commit -m "feat(lesson-plan): add WriterChat and LessonPlanWriter containers"
```

---

## Chunk 4: Page Shell & Sidebar

### Task 11: Create LessonPlanSidebar.vue

**Files:**
- Create: `src/components/lesson-plan-v2/LessonPlanSidebar.vue`

- [ ] **Step 1: Create LessonPlanSidebar component**

```vue
<template>
  <div class="sidebar-wrapper">
    <transition name="sidebar-slide">
      <div v-if="!collapsed" class="lesson-sidebar" :class="{ overlay: isOverlay }">
        <button class="new-btn" @click="$emit('new-conversation')">＋ 新建对话</button>
        <div class="history-list">
          <div
            v-for="item in mockHistory"
            :key="item.id"
            class="history-item"
            :class="{ active: item.id === activeId }"
            @click="activeId = item.id"
          >
            <div class="history-title">{{ item.title }}</div>
            <div class="history-time">{{ item.time }}</div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Expand button (shown when collapsed) -->
    <button v-if="collapsed" class="sidebar-toggle" @click="$emit('toggle')">›</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  collapsed: { type: Boolean, default: false },
  isOverlay: { type: Boolean, default: false },
})

defineEmits(['new-conversation', 'toggle'])

const activeId = ref(1)

const mockHistory = [
  { id: 1, title: '小学数学分数教案', time: '今天 14:30', preview: '三年级分数的初步认识...' },
  { id: 2, title: '高中物理力学教案', time: '昨天 09:15', preview: '牛顿第二定律应用...' },
  { id: 3, title: '初中英语阅读课', time: '3月12日', preview: 'Reading comprehension...' },
  { id: 4, title: '七年级生物细胞结构', time: '3月10日', preview: '动物细胞与植物细胞...' },
]
</script>
```

Styles: `width: 240px; min-width: 240px; background: #fff; border-right: 1px solid #eaedf0`. When `isOverlay`: `position: absolute; z-index: 100; box-shadow`. Transition: `transform 300ms ease`. Toggle button: positioned at left edge. See mockup `.sidebar`, `.sidebar-toggle` styles.

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue
git commit -m "feat(lesson-plan): add LessonPlanSidebar with mock history"
```

---

### Task 12: Create LessonPlanPage.vue (top-level orchestrator)

**Files:**
- Create: `src/views/LessonPlanPage.vue`

- [ ] **Step 1: Create LessonPlanPage component**

This is the core orchestrator. Manages mode state, SSE streaming, API calls, and mode switching logic.

```vue
<template>
  <div class="lesson-plan-page">
    <!-- Sidebar -->
    <LessonPlanSidebar
      :collapsed="sidebarCollapsed"
      :is-overlay="mode === 'writer'"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
      @new-conversation="startNewConversation"
    />

    <!-- Toast notification -->
    <transition name="fade">
      <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
    </transition>

    <!-- Main content area -->
    <div class="main-area">
      <transition name="fade" mode="out-in">
        <!-- Dialog Mode -->
        <LessonPlanDialog
          v-if="mode === 'dialog'"
          key="dialog"
          ref="dialogRef"
          :messages="messages"
          :is-streaming="isSending"
          :streaming-text="streamingText"
          :lesson-plan-id="lessonPlanId"
          @send="handleSend"
          @send-prompt="handleSendPrompt"
          @open-document="enterWriterMode"
          @regenerate="handleRegenerate"
        />

        <!-- Writer Mode -->
        <LessonPlanWriter
          v-else
          key="writer"
          ref="writerRef"
          :messages="messages"
          :is-streaming="isSending"
          :streaming-text="streamingText"
          :streaming-markdown="streamingMarkdown"
          :lesson-plan-id="lessonPlanId"
          @send-modify="handleModify"
          @back="exitWriterMode"
          @update:markdown="handleMarkdownUpdate"
          @editor-blur="autoSave"
        />
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onActivated, onDeactivated, onBeforeUnmount, nextTick } from 'vue'
import { resolveApiUrl, getToken } from '../api/http.js'
import LessonPlanSidebar from '../components/lesson-plan-v2/LessonPlanSidebar.vue'
import LessonPlanDialog from '../components/lesson-plan-v2/LessonPlanDialog.vue'
import LessonPlanWriter from '../components/lesson-plan-v2/LessonPlanWriter.vue'

const props = defineProps({
  resetKey: { type: Number, default: 0 },
})

// ----- Core State -----
const mode = ref('dialog')
const sidebarCollapsed = ref(false)
const messages = ref([])
const currentMarkdown = ref('')
const lessonPlanId = ref(null)
const sessionId = ref(null)
const isSending = ref(false)
const streamingMarkdown = ref('')
const streamingText = ref('')
const restoredFiles = ref([])

const dialogRef = ref(null)
const writerRef = ref(null)
let abortController = null
let saveTimer = null
let isFirstMount = true
const toastMsg = ref('')

// ----- Reset Key Watch -----
watch(() => props.resetKey, () => startNewConversation())

// ----- Mode Switching -----
function enterWriterMode() {
  mode.value = 'writer'
  sidebarCollapsed.value = true
  nextTick(() => {
    if (currentMarkdown.value) {
      writerRef.value?.createEditor('')
      writerRef.value?.loadContent(currentMarkdown.value)
    }
  })
}

function exitWriterMode() {
  // Preserve editor content
  const md = writerRef.value?.getMarkdown()
  if (md) currentMarkdown.value = md
  writerRef.value?.destroyEditor()
  mode.value = 'dialog'
  sidebarCollapsed.value = false
}

// ----- SSE Streaming -----
async function streamSSE(url, body, onMeta, onContent, onDone, onError) {
  abortController = new AbortController()
  isSending.value = true
  streamingMarkdown.value = ''
  streamingText.value = ''

  try {
    const res = await fetch(resolveApiUrl(url), {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: abortController.signal,
    })

    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let contentStarted = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.replace(/^data:\s*/, '').trim()
        if (!trimmed || trimmed === '[DONE]') continue
        try {
          const data = JSON.parse(trimmed)
          if (data.meta) {
            onMeta(data.meta)
          } else if (data.content) {
            streamingMarkdown.value += data.content
            streamingText.value += data.content
            // Heuristic: if first content starts with #, it's a document
            if (!contentStarted) {
              contentStarted = true
              if (data.content.trimStart().startsWith('#') && mode.value === 'dialog') {
                enterWriterMode()
              }
            }
            onContent(data.content)
          } else if (data.error) {
            onError(data.error)
          }
        } catch { /* skip non-JSON */ }
      }
    }

    onDone()
  } catch (err) {
    if (err.name !== 'AbortError') {
      onError(err.message)
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

// ----- Send (Generate) -----
function handleSend(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  const body = {
    query: payload.text,
    library_ids: payload.library_ids || [],
    file_ids: payload.file_ids || [],
  }
  if (sessionId.value) body.session_id = sessionId.value

  streamSSE(
    '/api/v1/lesson-plan/generate',
    body,
    (meta) => {
      lessonPlanId.value = meta.lesson_plan_id
      sessionId.value = meta.session_id
    },
    () => { /* content accumulated in streamingMarkdown */ },
    () => {
      // Streaming done
      if (mode.value === 'writer') {
        // Document card in chat
        insertDocumentCard()
        currentMarkdown.value = streamingMarkdown.value
        messages.value.push({ role: 'assistant', content: '教案已生成，请在右侧编辑器中查看和编辑。' })
      } else {
        // Regular chat response
        messages.value.push({ role: 'assistant', content: streamingMarkdown.value })
      }
      streamingText.value = ''
      streamingMarkdown.value = ''
      nextTick(() => {
        dialogRef.value?.scrollToBottom()
        writerRef.value?.scrollChatToBottom()
      })
    },
    (errMsg) => {
      messages.value.push({ role: 'assistant', content: `生成失败：${errMsg}` })
      streamingText.value = ''
      streamingMarkdown.value = ''
    },
  )
}

function handleSendPrompt(promptText) {
  handleSend({ text: promptText, file_ids: [], library_ids: [] })
}

// ----- Modify -----
let markdownBackup = ''

function handleModify(payload) {
  markdownBackup = currentMarkdown.value
  messages.value.push({ role: 'user', content: payload.text })

  const body = {
    lesson_plan_id: lessonPlanId.value,
    instruction: payload.text,
    current_content: currentMarkdown.value,
    file_ids: payload.file_ids || [],
    library_ids: payload.library_ids || [],
  }

  streamSSE(
    '/api/v1/lesson-plan/modify',
    body,
    () => { /* meta already set */ },
    () => {},
    () => {
      currentMarkdown.value = streamingMarkdown.value
      messages.value.push({ role: 'assistant', content: '教案已更新。' })
      streamingText.value = ''
      streamingMarkdown.value = ''
      nextTick(() => writerRef.value?.scrollChatToBottom())
    },
    (errMsg) => {
      // Rollback on failure
      currentMarkdown.value = markdownBackup
      writerRef.value?.loadContent(markdownBackup)
      messages.value.push({ role: 'assistant', content: `修改失败：${errMsg}` })
      streamingText.value = ''
      streamingMarkdown.value = ''
    },
  )
}

// ----- Document Card -----
function insertDocumentCard() {
  // Remove existing document cards (only one per session)
  messages.value = messages.value.filter(m => m.type !== 'document-card')
  messages.value.push({ type: 'document-card', title: '教案文档' })
}

// ----- Auto Save -----
function handleMarkdownUpdate(md) {
  currentMarkdown.value = md
  debounceSave()
}

function debounceSave() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(autoSave, 30000)
}

async function autoSave() {
  if (!lessonPlanId.value || !currentMarkdown.value) return
  try {
    await fetch(resolveApiUrl(`/api/v1/lesson-plan/${lessonPlanId.value}`), {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content: currentMarkdown.value }),
    })
  } catch (err) {
    console.error('Auto-save failed:', err)
    showToast('保存失败，请稍后重试')
  }
}

function showToast(msg) {
  toastMsg.value = msg
  setTimeout(() => { toastMsg.value = '' }, 3000)
}

// ----- Regenerate -----
function handleRegenerate(msgIndex) {
  // Find the user message before this AI message and resend
  for (let i = msgIndex - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      const text = messages.value[i].content
      messages.value = messages.value.slice(0, msgIndex) // remove the AI response
      handleSend({ text, file_ids: [], library_ids: [] })
      break
    }
  }
}

// ----- New Conversation -----
function startNewConversation() {
  abortController?.abort()
  clearTimeout(saveTimer)
  if (mode.value === 'writer') writerRef.value?.destroyEditor()
  mode.value = 'dialog'
  sidebarCollapsed.value = false
  messages.value = []
  currentMarkdown.value = ''
  streamingMarkdown.value = ''
  streamingText.value = ''
  lessonPlanId.value = null
  sessionId.value = null
  isSending.value = false
}

// ----- Load Latest -----
async function loadLatest() {
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/latest'), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) return
    const data = await res.json()
    if (data.lesson_plan) {
      lessonPlanId.value = data.lesson_plan.id
      sessionId.value = data.lesson_plan.session_id
      currentMarkdown.value = data.lesson_plan.content || ''
    }
    if (data.messages?.length) {
      messages.value = data.messages.map(m => ({ role: m.role, content: m.content }))
      if (currentMarkdown.value) {
        insertDocumentCard()
      }
    }
    if (data.files?.length) {
      restoredFiles.value = data.files
    }
  } catch (err) {
    console.error('Failed to load latest:', err)
  }
}

// ----- Lifecycle -----
onMounted(() => {
  isFirstMount = true
  loadLatest()
})

onActivated(() => {
  if (isFirstMount) { isFirstMount = false; return }
  loadLatest()
})

onDeactivated(() => {
  abortController?.abort()
  autoSave()
  if (mode.value === 'writer') writerRef.value?.destroyEditor()
})

onBeforeUnmount(() => {
  abortController?.abort()
  clearTimeout(saveTimer)
  if (mode.value === 'writer') writerRef.value?.destroyEditor()
})
</script>
```

Styles: `display: flex; height: calc(100vh - 60px); background: #f1f5f9; position: relative`. `.main-area`: `flex: 1; display: flex; flex-direction: column; overflow: hidden`. Fade transition: `opacity 0→1 / 1→0, 300ms`. See mockup `.layout` styles.

- [ ] **Step 2: Verify full page flow**

Run: `npm run dev`

Temporarily import in `LessonPrepLessonPlan.vue` (replace its template with `<LessonPlanPage />`). Test:
- Initial load shows welcome page or restores history
- Sending a message starts SSE stream
- Content starting with `#` triggers writer mode switch
- Writer mode: left chat + right editor
- Back button returns to dialog mode
- Sidebar collapses in writer mode, expands as overlay

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/views/LessonPlanPage.vue
git commit -m "feat(lesson-plan): add LessonPlanPage orchestrator with mode switching"
```

---

## Chunk 5: Integration & Cleanup

### Task 13: Update LessonPrep.vue and delete old files

**Files:**
- Modify: `src/views/LessonPrep.vue:2,39-49`
- Delete: `src/views/LessonPrepLessonPlan.vue`
- Delete: `src/components/lesson-plan/LessonPlanChat.vue`
- Delete: `src/components/lesson-plan/LessonPlanEditor.vue`
- Delete: `src/components/lesson-plan/LessonPlanTOC.vue`

- [ ] **Step 1: Update LessonPrep.vue component mapping**

In `src/views/LessonPrep.vue`, change the import and mapping:

Replace line 2:
```javascript
import LessonPrepLessonPlan from './LessonPrepLessonPlan.vue'
```
With:
```javascript
import LessonPlanPage from './LessonPlanPage.vue'
```

Replace in the `currentComponent` map (line 42):
```javascript
'lesson-plan': LessonPrepLessonPlan,
```
With:
```javascript
'lesson-plan': LessonPlanPage,
```

- [ ] **Step 2: Full end-to-end verification**

Run: `npm run dev`

Navigate to `/lesson-prep?tab=lesson-plan`. Test complete flow:
1. Welcome page with 9 prompt cards
2. Click a prompt card → sends message → AI responds
3. AI generates document → auto-switches to writer mode
4. Editor shows content with floating toolbar + TOC
5. Send modification from writer chat → editor updates
6. Click "返回对话" → back to dialog mode, document card visible
7. Click document card → back to writer mode with content
8. Switch tabs (e.g., to PPT) and back → state preserved via keep-alive
9. Sidebar collapse/expand works in both modes
10. Export buttons (Word, PDF, Markdown) work

- [ ] **Step 3: Delete old component files**

```bash
git rm teacher-platform/src/views/LessonPrepLessonPlan.vue
git rm teacher-platform/src/components/lesson-plan/LessonPlanChat.vue
git rm teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue
git rm teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue
```

- [ ] **Step 4: Verify no broken imports**

Run: `npm run build`

Expected: Build completes with no errors. Check for any remaining imports of deleted files.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(lesson-plan): integrate LessonPlanPage, remove old components"
```

---

### Task 14: Polish styles and animations

**Files:**
- Modify: All `lesson-plan-v2/*.vue` components (scoped styles)

- [ ] **Step 1: Add transition animations**

In each component, ensure:
- Mode switch uses `<transition name="fade">` with `opacity` animation (300ms)
- Sidebar uses `<transition name="sidebar-slide">` with `transform: translateX` (300ms)
- Buttons have `transition: all 0.2s` with hover scale + shadow
- Typing indicator has blink animation

- [ ] **Step 2: Verify visual match with mockup**

Open `docs/mockup-lesson-plan.html` and the live app side by side. Check:
- Color consistency (blues, backgrounds, borders)
- Spacing and padding
- Font sizes and weights
- Border radius
- Hover effects

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/ teacher-platform/src/views/LessonPlanPage.vue
git commit -m "style(lesson-plan): polish animations and visual consistency"
```
