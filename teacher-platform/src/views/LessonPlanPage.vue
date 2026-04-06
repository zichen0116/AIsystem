<template>
  <div class="lesson-plan-page">
    <!-- Sidebar -->
    <LessonPlanSidebar
      ref="sidebarRef"
      :collapsed="sidebarCollapsed"
      :is-overlay="mode === 'writer'"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
      @new-conversation="startNewConversation"
      @select-history="loadHistorySession"
      @delete-history="handleDeleteHistory"
      @toast="showToast"
    />

    <!-- Toast notification -->
    <transition name="fade">
      <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
    </transition>

    <!-- Main content area -->
    <div class="main-area">
      <keep-alive>
        <component
          :is="currentComponent"
          :ref="mode === 'dialog' ? 'dialogRef' : 'writerRef'"
          :messages="messages"
          :is-streaming="isSending"
          :streaming-text="streamingText"
          :streaming-markdown="streamingMarkdown"
          :lesson-plan-id="lessonPlanId"
          @send="handleSend"
          @send-prompt="handleSendPrompt"
          @open-document="enterWriterMode"
          @regenerate="handleRegenerate"
          @send-modify="handleModify"
          @back="exitWriterMode"
          @update:markdown="handleMarkdownUpdate"
          @editor-blur="autoSave"
          @toast="showToast"
        />
      </keep-alive>
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
  initialLessonPlanId: { type: [String, Number], default: null },
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
const sidebarRef = ref(null)
let abortController = null
let saveTimer = null
let isFirstMount = true

// Computed property for dynamic component
const currentComponent = computed(() => {
  return mode.value === 'dialog' ? LessonPlanDialog : LessonPlanWriter
})

// Watch mode changes to load content when entering writer mode
watch(mode, async (newMode) => {
  if (newMode === 'writer') {
    await nextTick()
    writerRef.value?.loadContent(currentMarkdown.value || '')
  }
})
const toastMsg = ref('')

// ----- Reset Key Watch -----
watch(() => props.resetKey, () => startNewConversation())

// ----- Mode Switching -----
function enterWriterMode() {
  mode.value = 'writer'
  sidebarCollapsed.value = true
  // Clear streamingText so document content doesn't appear in chat
  streamingText.value = ''
}

function exitWriterMode() {
  // Preserve editor content
  const md = writerRef.value?.getMarkdown()
  if (typeof md === 'string') currentMarkdown.value = md
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
            // Only accumulate streamingText for chat if in dialog mode
            if (mode.value === 'dialog') {
              streamingText.value += data.content
            }
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
      // Delay clearing streamingMarkdown to allow editor to load first
      nextTick(() => {
        streamingMarkdown.value = ''
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
      // Delay clearing streamingMarkdown to allow editor to load first
      nextTick(() => {
        streamingMarkdown.value = ''
        writerRef.value?.scrollChatToBottom()
      })
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
  // 刷新侧边栏历史列表
  sidebarRef.value?.refresh()
}

// ----- Handle Delete History -----
function handleDeleteHistory(deletedId) {
  if (lessonPlanId.value === deletedId) {
    startNewConversation()
  }
}

// ----- Load History Session -----
async function loadHistorySession(historyItem) {
  try {
    // 并行请求详情和消息
    const [detailRes, messagesRes] = await Promise.all([
      fetch(resolveApiUrl(`/api/v1/lesson-plan/${historyItem.id}`), {
        headers: { Authorization: `Bearer ${getToken()}` },
      }),
      fetch(resolveApiUrl(`/api/v1/lesson-plan/${historyItem.id}/messages`), {
        headers: { Authorization: `Bearer ${getToken()}` },
      }),
    ])

    if (!detailRes.ok || !messagesRes.ok) {
      showToast('加载历史会话失败')
      return
    }

    const detail = await detailRes.json()
    const messagesData = await messagesRes.json()

    // 重置状态
    mode.value = 'dialog'
    lessonPlanId.value = detail.id
    sessionId.value = detail.session_id
    currentMarkdown.value = detail.content || ''
    streamingMarkdown.value = ''
    streamingText.value = ''
    isSending.value = false

    // 过滤消息（去除教案内容）
    messages.value = messagesData.messages
      .map(m => ({ role: m.role, content: m.content }))
      .filter(m => {
        if (m.role === 'user') return true
        const isLessonPlan = m.content.trim().startsWith('#') && m.content.length > 100
        return !isLessonPlan
      })

    // 插入文档卡片
    if (currentMarkdown.value) {
      insertDocumentCard()
    }

    showToast('已加载历史会话')
  } catch (err) {
    console.error('加载历史会话失败:', err)
    showToast('加载失败，请重试')
  }
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
      // Filter out lesson plan content from messages
      messages.value = data.messages
        .map(m => ({ role: m.role, content: m.content }))
        .filter(m => {
          // Keep user messages
          if (m.role === 'user') return true
          // Filter out AI messages that are lesson plans (starts with # and long)
          const isLessonPlan = m.content.trim().startsWith('#') && m.content.length > 100
          return !isLessonPlan
        })

      // Insert document card if we have lesson plan content
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
onMounted(async () => {
  isFirstMount = true
  if (props.initialLessonPlanId) {
    await loadHistorySession({ id: props.initialLessonPlanId })
    // Switch to writer mode to show the editor if content was loaded
    if (currentMarkdown.value) {
      enterWriterMode()
    }
  } else {
    startNewConversation()
  }
})

onActivated(() => {
  if (isFirstMount) { isFirstMount = false; return }
  // 从其他页面返回时也显示欢迎界面
  startNewConversation()
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

<style scoped>
.lesson-plan-page {
  display: flex;
  height: 100%;
  background: #f1f5f9;
  position: relative;
}
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  background: #1a1a2e;
  color: #fff;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  z-index: 200;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

/* Fade transition for mode switching */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 300ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
