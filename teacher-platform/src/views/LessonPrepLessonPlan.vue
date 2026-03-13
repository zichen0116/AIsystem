<template>
  <div class="lesson-plan-page">
    <LessonPlanTOC
      :headings="headings"
      :is-streaming="isSending"
      @scroll-to="handleScrollTo"
    />
    <div class="chat-column">
      <LessonPlanChat
        ref="chatRef"
        :messages="messages"
        :is-sending="isSending"
        :has-content="hasEditorContent"
        @send="handleGenerate"
        @send-modify="handleModify"
      />
    </div>
    <div class="editor-column">
      <LessonPlanEditor
        ref="editorRef"
        :is-streaming="isSending"
        :streaming-markdown="streamingMarkdown"
        @update:markdown="handleMarkdownUpdate"
        @update:headings="headings = $event"
        @blur="autoSave"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { resolveApiUrl, getToken } from '../api/http.js'
import LessonPlanChat from '../components/lesson-plan/LessonPlanChat.vue'
import LessonPlanEditor from '../components/lesson-plan/LessonPlanEditor.vue'
import LessonPlanTOC from '../components/lesson-plan/LessonPlanTOC.vue'

const editorRef = ref(null)
const chatRef = ref(null)
const messages = ref([])
const isSending = ref(false)
const streamingMarkdown = ref('')
const currentMarkdown = ref('')
const headings = ref([])
const lessonPlanId = ref(null)
const sessionId = ref(null)

let abortController = null
let saveTimer = null
let isFirstMount = true

const hasEditorContent = computed(() => currentMarkdown.value.trim().length > 0)

// ---------- Data loading (from DB) ----------

async function loadLatestPlan() {
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
      editorRef.value?.loadContent(currentMarkdown.value)
    } else {
      lessonPlanId.value = null
      sessionId.value = null
      currentMarkdown.value = ''
      editorRef.value?.loadContent('')
    }
    messages.value = (data.messages || []).map((m) => ({ role: m.role, content: m.content }))
    chatRef.value?.restoreFiles((data.files || []).map((f) => ({ file_id: f.id, filename: f.filename })))
  } catch (e) {
    console.error('Failed to load latest plan:', e)
  }
}

// ---------- SSE processing ----------

async function processSSEStream(res) {
  if (!res.ok) throw new Error(res.statusText || `HTTP ${res.status}`)

  const reader = res.body?.getReader()
  if (!reader) throw new Error('No reader available')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (value) buffer += decoder.decode(value, { stream: true })

    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const ev of events) {
      const line = ev.split('\n')[0]
      if (!line?.startsWith('data: ')) continue

      const raw = line.slice(6).trim()
      if (raw === '[DONE]') return

      try {
        const data = JSON.parse(raw)
        // Metadata event (first event from generate)
        if (data.meta) {
          lessonPlanId.value = data.meta.lesson_plan_id
          sessionId.value = data.meta.session_id
          continue
        }
        if (data.error) throw new Error(data.error)
        if (data.content) streamingMarkdown.value += data.content
      } catch (parseErr) {
        if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr
      }
    }

    if (done) {
      // Process final buffer
      if (buffer.trim()) {
        const line = buffer.split('\n')[0]
        if (line?.startsWith('data: ')) {
          const raw = line.slice(6).trim()
          if (raw !== '[DONE]') {
            try {
              const data = JSON.parse(raw)
              if (data.content) streamingMarkdown.value += data.content
            } catch (_) {}
          }
        }
      }
      break
    }
  }
}

// ---------- Generate ----------

async function handleGenerate(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  isSending.value = true
  streamingMarkdown.value = ''
  abortController = new AbortController()

  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/generate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({
        query: payload.text,
        library_ids: payload.library_ids || [],
        file_ids: payload.file_ids || [],
        session_id: sessionId.value || undefined,
      }),
      signal: abortController.signal,
    })

    await processSSEStream(res)

    // Determine if response is a lesson plan or clarifying question
    const isLessonPlan = streamingMarkdown.value.trim().startsWith('#')
    if (isLessonPlan) {
      currentMarkdown.value = streamingMarkdown.value
      // Show real AI content in chat (truncated for readability, full content in editor)
      const title = streamingMarkdown.value.match(/^#\s+(.+)/m)?.[1] || '教案'
      messages.value.push({ role: 'assistant', content: `已为您生成「${title}」，请在右侧编辑器中查看和编辑。如需修改，请直接告诉我。` })
    } else {
      // AI asked a clarifying question - show full real content in chat
      messages.value.push({ role: 'assistant', content: streamingMarkdown.value })
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Generate failed:', e)
      messages.value.push({ role: 'assistant', content: `生成失败: ${e.message}` })
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

// ---------- Modify ----------

async function handleModify(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  isSending.value = true
  streamingMarkdown.value = ''
  const backupMarkdown = editorRef.value?.getMarkdown() || ''
  abortController = new AbortController()

  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/modify'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({
        lesson_plan_id: lessonPlanId.value,
        instruction: payload.text,
        current_content: backupMarkdown,
        file_ids: payload.file_ids || [],
        library_ids: payload.library_ids || [],
      }),
      signal: abortController.signal,
    })

    await processSSEStream(res)
    currentMarkdown.value = streamingMarkdown.value
    // Show real content excerpt in chat (full response stored in ChatHistory by backend)
    const excerpt = streamingMarkdown.value.slice(0, 150).trim()
    messages.value.push({ role: 'assistant', content: excerpt + (streamingMarkdown.value.length > 150 ? '...\n\n*已在右侧编辑器中更新*' : '') })
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Modify failed:', e)
      messages.value.push({ role: 'assistant', content: `修改失败: ${e.message}` })
      editorRef.value?.loadContent(backupMarkdown)
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

// ---------- Auto-save ----------

function handleMarkdownUpdate(markdown) {
  currentMarkdown.value = markdown
  scheduleAutoSave()
}

function scheduleAutoSave() {
  if (!lessonPlanId.value || isSending.value) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(autoSave, 30000)
}

async function autoSave() {
  if (!lessonPlanId.value || isSending.value) return
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null }
  try {
    await fetch(resolveApiUrl(`/api/v1/lesson-plan/${lessonPlanId.value}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ content: currentMarkdown.value }),
    })
  } catch (e) {
    console.warn('Auto-save failed:', e)
  }
}

function handleScrollTo(pos) { editorRef.value?.scrollToPos(pos) }

// ---------- Lifecycle ----------

onMounted(async () => {
  isFirstMount = true
  await loadLatestPlan()
})

onActivated(async () => {
  if (isFirstMount) { isFirstMount = false; return }
  await loadLatestPlan()
})

onDeactivated(() => {
  abortController?.abort()
  autoSave()
})

onBeforeUnmount(() => {
  abortController?.abort()
  if (saveTimer) clearTimeout(saveTimer)
})
</script>

<style scoped>
.lesson-plan-page { display: flex; height: calc(100vh - 60px); gap: 0; background: #f1f5f9; padding: 16px; }
.chat-column { width: 33%; min-width: 300px; max-width: 420px; flex-shrink: 0; padding: 0 12px; }
.editor-column { flex: 1; min-width: 0; }
</style>
