<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { apiRequest, getToken } from '../api/http.js'
import assistantAvatarUrl from '../assets/zhushou.jpg'

/** 用于保存试卷、导出 PDF 文件名等（在成功生成后由接口或 spec 写入） */
const form = ref({
  subject: '',
  difficulty: 'medium' // easy | medium | hard
})

const CLARIFY_INTRO =
  '你好！我们可以一步步确认命题需求：我会每次只问一个问题，你回答后我再问下一项，直到信息齐全后自动生成试题。也可以先随便说说你的想法，我们从缺的那一项开始问。'

const chatMessages = ref([{ role: 'assistant', content: CLARIFY_INTRO }])
const chatInput = ref('')
const clarifyLoading = ref(false)

const hasGenerated = ref(false)
const uploading = ref(false)
const generating = ref(false)
/** 用户粘贴的补充材料（与上传解析结果一并参与追问判断与正式生成） */
const sourceDraft = ref('')
const uploadPreview = ref('')
const uploadedFilename = ref('')
const chatScrollRef = ref(null)
const questions = ref([])
const errorMsg = ref('')
const previewRef = ref(null)
const exporting = ref(false)

/** 左侧：服务端保存的试卷列表（按登录用户隔离） */
const sidebarCollapsed = ref(false)
const savedPapers = ref([])
const activeSavedId = ref(null)
const savedListLoading = ref(false)

/** 保存试卷弹窗 */
const showSaveModal = ref(false)
const saveModalTitle = ref('')
const saveModalSubmitting = ref(false)

/** 从左侧记录加载预览时隐藏「生成新试题」卡片，关闭预览后恢复 */
const hideGenerateCard = ref(false)

/** 单题编辑草稿（按下标），保存后写回 questions 并移除 */
const questionEditDrafts = ref({})

function clearQuestionEditDrafts() {
  questionEditDrafts.value = {}
}

const hasUnsavedQuestionEdits = computed(() => {
  for (const key of Object.keys(questionEditDrafts.value)) {
    const i = Number(key)
    const draft = questionEditDrafts.value[i]
    const orig = questions.value[i]
    if (!draft || !orig) continue
    if (JSON.stringify(draft) !== JSON.stringify(orig)) return true
  }
  return false
})

function startEditQuestion(index) {
  const q = questions.value[index]
  if (!q) return
  if (questionEditDrafts.value[index] != null) return
  const draft = JSON.parse(JSON.stringify(q))
  if (draft.type === 'mc') {
    if (!Array.isArray(draft.options) || !draft.options.length) {
      draft.options = [
        { label: 'A', text: '' },
        { label: 'B', text: '' },
        { label: 'C', text: '' },
        { label: 'D', text: '' }
      ]
    }
    const labels = draft.options.map((o) => o.label)
    if (draft.answer == null || draft.answer === '' || !labels.includes(String(draft.answer))) {
      draft.answer = labels[0] || 'A'
    }
  }
  if (draft.type === 'tf' && (draft.answer == null || draft.answer === '')) {
    draft.answer = 'true'
  }
  if (draft.type === 'sa' || draft.type === 'essay') {
    if (draft.answer == null) draft.answer = ''
    if (draft.analysis == null) draft.analysis = ''
  } else if (draft.type !== 'mc' && draft.type !== 'tf') {
    if (draft.answer == null) draft.answer = ''
    if (draft.analysis == null) draft.analysis = ''
  }
  questionEditDrafts.value = { ...questionEditDrafts.value, [index]: draft }
}

function saveEditQuestion(index) {
  const draft = questionEditDrafts.value[index]
  if (!draft) return
  const next = [...questions.value]
  next[index] = JSON.parse(JSON.stringify(draft))
  questions.value = next
  const { [index]: _, ...rest } = questionEditDrafts.value
  questionEditDrafts.value = rest
}

function cancelEditQuestion(index) {
  const draft = questionEditDrafts.value[index]
  if (!draft) return
  const orig = questions.value[index]
  if (orig && JSON.stringify(draft) !== JSON.stringify(orig)) {
    if (!confirm('放弃对本题的修改？')) return
  }
  const { [index]: _, ...rest } = questionEditDrafts.value
  questionEditDrafts.value = rest
}

/** 关闭记录预览：只保留左侧记录 +「生成新试题」，不再展示右侧试题预览 */
function closePreviewFromRecord() {
  if (hasUnsavedQuestionEdits.value) {
    if (!confirm('尚有未保存的题目修改，关闭预览后将无法恢复。确定关闭？')) return
  }
  sidebarCollapsed.value = false
  startNewPaper()
}

async function fetchSavedPapersList() {
  if (!getToken()) {
    savedPapers.value = []
    return
  }
  savedListLoading.value = true
  try {
    const data = await apiRequest('/api/v1/question-papers')
    savedPapers.value = Array.isArray(data.items) ? data.items : []
  } catch (e) {
    console.error(e)
    savedPapers.value = []
  } finally {
    savedListLoading.value = false
  }
}

onMounted(() => {
  fetchSavedPapersList()
})

async function scrollChatToBottom() {
  await nextTick()
  const el = chatScrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(
  chatMessages,
  () => {
    scrollChatToBottom()
  },
  { deep: true }
)

const materialText = computed(() => {
  if (sourceDraft.value && uploadPreview.value) {
    return `${sourceDraft.value}\n\n【以下为上传文档解析内容】\n${uploadPreview.value}`
  }
  return sourceDraft.value || uploadPreview.value || ''
})

function formatSavedTime(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) {
    return `今天 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  if (diffDays === 1) return '昨天'
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function startNewPaper() {
  clearQuestionEditDrafts()
  activeSavedId.value = null
  hasGenerated.value = false
  questions.value = []
  errorMsg.value = ''
  hideGenerateCard.value = false
  chatMessages.value = [{ role: 'assistant', content: CLARIFY_INTRO }]
  chatInput.value = ''
  sourceDraft.value = ''
  uploadPreview.value = ''
  uploadedFilename.value = ''
  form.value.subject = ''
  form.value.difficulty = 'medium'
}

async function loadSavedPaper(p) {
  if (!p?.id || !getToken()) return
  if (hasUnsavedQuestionEdits.value) {
    if (!confirm('尚有未保存的题目修改，加载其他试卷后将丢失。确定继续？')) return
  }
  errorMsg.value = ''
  try {
    const data = await apiRequest(`/api/v1/question-papers/${p.id}`)
    const qs = data.questions
    if (!Array.isArray(qs) || !qs.length) return
    clearQuestionEditDrafts()
    activeSavedId.value = p.id
    questions.value = JSON.parse(JSON.stringify(qs))
    hasGenerated.value = true
    form.value.subject = data.subject || form.value.subject
    if (data.difficulty) form.value.difficulty = data.difficulty
    hideGenerateCard.value = true
  } catch (e) {
    errorMsg.value = e.message || '加载试卷失败'
  }
}

async function deleteSavedPaper(p) {
  if (!getToken()) {
    errorMsg.value = '请先登录后再管理试题记录'
    return
  }
  if (!confirm(`确定删除「${p.title}」？`)) return
  try {
    await apiRequest(`/api/v1/question-papers/${p.id}`, { method: 'DELETE' })
    if (activeSavedId.value === p.id) startNewPaper()
    await fetchSavedPapersList()
  } catch (e) {
    errorMsg.value = e.message || '删除失败'
  }
}

function openSaveModal() {
  errorMsg.value = ''
  if (!getToken()) {
    errorMsg.value = '请先登录后再保存试卷'
    return
  }
  if (hasUnsavedQuestionEdits.value) {
    errorMsg.value = '尚有题目处于编辑中未保存，请先点击该题上的「保存」或「取消」后再保存试卷'
    return
  }
  if (!hasGenerated.value || !questions.value.length) {
    errorMsg.value = '请先生成试题后再保存'
    return
  }
  saveModalTitle.value = `${form.value.subject || '试卷'} ${new Date().toLocaleString('zh-CN', { hour12: false })}`
  showSaveModal.value = true
}

function closeSaveModal() {
  showSaveModal.value = false
  saveModalSubmitting.value = false
}

async function confirmSavePaper() {
  const t = (saveModalTitle.value || '').trim()
  if (!t) {
    errorMsg.value = '请输入试卷名称'
    return
  }
  if (hasUnsavedQuestionEdits.value) {
    errorMsg.value = '尚有题目处于编辑中未保存，请先完成题目上的保存'
    return
  }
  saveModalSubmitting.value = true
  errorMsg.value = ''
  try {
    const payload = {
      title: t,
      subject: form.value.subject || '未命名学科',
      difficulty: form.value.difficulty,
      questions: JSON.parse(JSON.stringify(questions.value))
    }
    const data = await apiRequest('/api/v1/question-papers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const paper = data.paper
    if (paper?.id) activeSavedId.value = paper.id
    closeSaveModal()
    await fetchSavedPapersList()
  } catch (e) {
    errorMsg.value = e.message || '保存失败'
  } finally {
    saveModalSubmitting.value = false
  }
}

function formatTfAnswer(ans) {
  const s = (ans ?? '').toString().trim().toLowerCase()
  if (s === 'true' || s === 't' || s === '1' || s.includes('正确')) return '正确'
  if (s === 'false' || s === 'f' || s === '0' || s.includes('错误')) return '错误'
  return ans ?? ''
}

function isTfTrue(ans) {
  const s = (ans ?? '').toString().trim().toLowerCase()
  return s === 'true' || s === 't' || s === '1' || s.includes('正确')
}

function selectFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pdf,.doc,.docx,.ppt,.pptx,.txt'
  input.onchange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    await handleUpload(file)
  }
  input.click()
}

async function handleUpload(file) {
  uploading.value = true
  errorMsg.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)

    const resp = await fetch('/api/v1/html/upload', {
      method: 'POST',
      body: formData
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.detail || '上传失败')
    }

    const data = await resp.json()
    uploadPreview.value = data.preview || ''
    uploadedFilename.value = data.filename || file.name
  } catch (e) {
    console.error(e)
    errorMsg.value = e.message || '上传失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function runGenerateFromSpec(spec) {
  errorMsg.value = ''
  hideGenerateCard.value = false
  if (hasUnsavedQuestionEdits.value) {
    if (!confirm('尚有未保存的题目修改，重新生成后将丢失。确定继续？')) return
  }
  clearQuestionEditDrafts()
  generating.value = true
  try {
    const extra =
      materialText.value.trim() !== ''
        ? `\n\n【补充材料（用户粘贴或上传解析）】\n${materialText.value}`
        : ''
    const sourceBody = [spec.knowledge_points, extra].filter(Boolean).join('\n')

    const payload = {
      subject: spec.subject || '未指定学科',
      difficulty: spec.difficulty,
      type_counts: spec.counts_per_type,
      source: sourceBody.trim() || null
    }

    const resp = await fetch('/api/v1/question-generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.detail || '生成试题失败')
    }

    const data = await resp.json()

    if (Array.isArray(data.questions) && data.questions.length > 0) {
      questions.value = data.questions
    } else if (data.raw_text) {
      questions.value = [
        {
          type: 'essay',
          stem: '模型未按预期返回结构化题目，以下为原始文本：',
          answer: data.raw_text
        }
      ]
    } else {
      questions.value = []
    }

    form.value.subject = data.subject || spec.subject
    form.value.difficulty = data.difficulty || spec.difficulty
    hasGenerated.value = true
  } catch (e) {
    console.error(e)
    errorMsg.value = e.message || '生成试题失败，请稍后重试'
  } finally {
    generating.value = false
  }
}

async function sendClarifyMessage() {
  const text = (chatInput.value || '').trim()
  if (!text || clarifyLoading.value || generating.value) return

  errorMsg.value = ''
  hideGenerateCard.value = false
  chatInput.value = ''
  chatMessages.value = [...chatMessages.value, { role: 'user', content: text }]
  clarifyLoading.value = true

  try {
    const resp = await fetch('/api/v1/question-generate/clarify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: chatMessages.value.map((m) => ({
          role: m.role,
          content: m.content
        })),
        material_text: materialText.value || null
      })
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.detail || '对话服务暂时不可用')
    }

    const data = await resp.json()
    const reply = (data.assistant_message || '').trim() || '请继续说明您的命题需求。'
    chatMessages.value = [...chatMessages.value, { role: 'assistant', content: reply }]

    if (data.ready && data.spec) {
      await runGenerateFromSpec(data.spec)
      if (!errorMsg.value) {
        chatMessages.value = [
          ...chatMessages.value,
          {
            role: 'assistant',
            content:
              '已根据确认的参数生成试题，请在右侧预览；如需重新命题可在下方输入新要求。'
          }
        ]
      } else {
        const err = errorMsg.value
        chatMessages.value = [
          ...chatMessages.value,
          { role: 'assistant', content: `试题生成未成功：${err}。可修改说明后重试。` }
        ]
      }
    }
  } catch (e) {
    console.error(e)
    const msg = e?.message || String(e) || '发送失败，请稍后重试'
    errorMsg.value = msg
    chatMessages.value = [
      ...chatMessages.value,
      {
        role: 'assistant',
        content: `出错了：${msg}。`
      }
    ]
  } finally {
    clarifyLoading.value = false
  }
}

function onChatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendClarifyMessage()
  }
}

/**
 * html2canvas 对 flex 子项 width:0 的排版与浏览器不一致，导出前需固定宽度。
 * A4 纵向可印宽度 = 210mm − 左右边距；若此处 px 略大于 190mm@96dpi，整图缩进版心时右侧会被裁掉，
 * 表现为「左边框在、右边框没了」。
 * 190mm @ 96dpi ≈ 718px，留 2px 余量避免舍入误差。
 */
const PDF_EXPORT_WIDTH_PX = Math.max(320, Math.floor((190 * 96) / 25.4) - 2)

async function handleExportPdf() {
  if (!hasGenerated.value || !previewRef.value || exporting.value) return
  if (hasUnsavedQuestionEdits.value) {
    errorMsg.value = '请先完成题目编辑处的「保存」，再导出 PDF'
    return
  }
  const element = previewRef.value
  const prev = {
    width: element.style.width,
    minWidth: element.style.minWidth,
    maxWidth: element.style.maxWidth,
    flex: element.style.flex
  }
  try {
    exporting.value = true
    element.style.width = `${PDF_EXPORT_WIDTH_PX}px`
    element.style.minWidth = `${PDF_EXPORT_WIDTH_PX}px`
    element.style.maxWidth = `${PDF_EXPORT_WIDTH_PX}px`
    element.style.flex = 'none'
    await nextTick()

    const { default: html2pdf } = await import('html2pdf.js')

    const opt = {
      margin: [10, 10, 10, 10],
      filename: `${form.value.subject || '试题'}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, logging: false },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    }

    await html2pdf().set(opt).from(element).save()
  } catch (e) {
    console.error(e)
    errorMsg.value = '导出 PDF 失败，请稍后重试'
  } finally {
    element.style.width = prev.width
    element.style.minWidth = prev.minWidth
    element.style.maxWidth = prev.maxWidth
    element.style.flex = prev.flex
    exporting.value = false
  }
}
</script>

<template>
  <div class="question-page">
    <!-- 左侧：保存记录（风格对齐教案页历史侧栏） -->
    <div class="sidebar-outer" :class="{ 'is-collapsed': sidebarCollapsed }">
      <Transition name="sidebar-slide">
        <aside v-if="!sidebarCollapsed" class="saved-sidebar">
          <div class="sidebar-header">
            <div class="sidebar-title-block">
              <div class="sidebar-title">试题记录</div>
              <p class="sidebar-title-desc">已登录后保存的试卷会同步到云端，点击可加载到右侧预览</p>
            </div>
            <button
              type="button"
              class="collapse-btn"
              title="收起侧栏"
              @click="sidebarCollapsed = true"
            >
              ‹
            </button>
          </div>
          <div class="history-list">
            <div v-if="savedListLoading" class="empty-state">加载中...</div>
            <template v-else-if="!getToken()">
              <div class="empty-state">登录后可保存并查看试题记录</div>
            </template>
            <template v-else-if="!savedPapers.length">
              <div class="empty-state">暂无已保存记录</div>
            </template>
            <template v-else>
              <div
                v-for="p in savedPapers"
                :key="p.id"
                class="history-item"
                :class="{ active: p.id === activeSavedId }"
                @click="loadSavedPaper(p)"
              >
                <div class="item-content">
                  <div class="history-title">{{ p.title }}</div>
                  <div class="history-meta">
                    {{ p.subject }} · {{ p.question_count ?? 0 }} 题 · {{ formatSavedTime(p.created_at) }}
                  </div>
                </div>
                <button
                  type="button"
                  class="delete-btn"
                  title="删除"
                  @click.stop="deleteSavedPaper(p)"
                >
                  ×
                </button>
              </div>
            </template>
          </div>
        </aside>
      </Transition>
      <button
        v-if="sidebarCollapsed"
        type="button"
        class="sidebar-expand"
        title="展开试题记录"
        @click="sidebarCollapsed = false"
      >
        ›
      </button>
    </div>

    <!-- 右侧主区：表单 + 预览 -->
    <div
      class="page-wrap"
      :class="{
        'with-preview': hasGenerated,
        'preview-from-record': hideGenerateCard && hasGenerated
      }"
    >
    <section v-show="!hideGenerateCard" class="config-card">
      <div class="chat-dialog" role="region" aria-label="命题需求对话">
        <div class="chat-dialog__head">
          <img
            class="chat-dialog__head-avatar"
            :src="assistantAvatarUrl"
            width="40"
            height="40"
            alt="命题助手"
          />
          <div class="chat-dialog__head-text">
            <div class="chat-dialog__head-title">命题助手</div>
            <div class="chat-dialog__head-sub">通过对话确认学科、知识点、题型与数量、难度、是否上传材料</div>
          </div>
        </div>

        <div ref="chatScrollRef" class="chat-dialog__body">
          <div
            v-for="(m, i) in chatMessages"
            :key="i"
            class="dialog-msg"
            :class="m.role === 'user' ? 'dialog-msg--user' : 'dialog-msg--assistant'"
          >
            <img
              v-if="m.role === 'assistant'"
              class="dialog-msg__assistant-avatar"
              :src="assistantAvatarUrl"
              width="32"
              height="32"
              alt=""
            />
            <div class="dialog-msg__main">
              <span class="dialog-msg__name">{{
                m.role === 'assistant' ? '命题助手' : '我'
              }}</span>
              <div class="dialog-msg__bubble">{{ m.content }}</div>
            </div>
            <div
              v-if="m.role === 'user'"
              class="dialog-msg__avatar dialog-msg__avatar--user"
              aria-hidden="true"
            >
              <svg
                class="dialog-msg__user-icon"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
          </div>

          <div
            v-if="clarifyLoading && !generating"
            class="dialog-msg dialog-msg--assistant dialog-msg--typing"
            aria-live="polite"
            aria-busy="true"
          >
            <img
              class="dialog-msg__assistant-avatar"
              :src="assistantAvatarUrl"
              width="32"
              height="32"
              alt=""
            />
            <div class="dialog-msg__main">
              <span class="dialog-msg__name">命题助手</span>
              <div class="dialog-msg__bubble dialog-msg__bubble--typing">
                <span class="typing-dot" />
                <span class="typing-dot" />
                <span class="typing-dot" />
              </div>
            </div>
          </div>

          <div
            v-if="generating"
            class="dialog-msg dialog-msg--assistant dialog-msg--typing"
            aria-live="polite"
            aria-busy="true"
          >
            <img
              class="dialog-msg__assistant-avatar"
              :src="assistantAvatarUrl"
              width="32"
              height="32"
              alt=""
            />
            <div class="dialog-msg__main">
              <span class="dialog-msg__name">命题助手</span>
              <div class="dialog-msg__bubble dialog-msg__bubble--typing dialog-msg__bubble--gen">
                <span class="typing-dot" />
                <span class="typing-dot" />
                <span class="typing-dot" />
                <span class="typing-label">正在生成试题…</span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-dialog__footer">
          <textarea
            v-model="chatInput"
            class="chat-dialog__input"
            rows="2"
            placeholder="输入消息…（Enter 发送，Shift+Enter 换行）"
            :disabled="clarifyLoading || generating"
            @keydown="onChatKeydown"
          />
          <button
            type="button"
            class="chat-dialog__send"
            :disabled="clarifyLoading || generating || !chatInput.trim()"
            :title="generating ? '生成中' : clarifyLoading ? '思考中' : '发送'"
            @click="sendClarifyMessage"
          >
            <span class="chat-dialog__send-label">{{
              generating ? '生成中' : clarifyLoading ? '…' : '发送'
            }}</span>
          </button>
        </div>
      </div>

      <div class="field field--source">
        <div class="label-row">
          <label class="label">补充材料（可选）</label>
          <button
            type="button"
            class="link-btn"
            :disabled="uploading"
            @click="selectFile"
          >
            {{ uploading ? '上传中...' : '上传 PDF / 文档' }}
          </button>
        </div>
        <textarea
          v-model="sourceDraft"
          class="source-input"
          placeholder="粘贴教学材料、知识点列表；若打算依据上传文件命题，请先上传或在此粘贴内容。"
          rows="2"
        />
        <p v-if="uploadedFilename || uploadPreview" class="upload-hint">
          已上传：{{ uploadedFilename }}；
          提取文本长度：{{ uploadPreview.length }} 字
        </p>
      </div>

      <p v-if="errorMsg" class="error-text">
        {{ errorMsg }}
      </p>
    </section>

    <!-- 右侧：生成后预览 -->
    <section
      v-if="hasGenerated"
      ref="previewRef"
      class="preview-card"
      :class="{ exporting: exporting }"
    >
      <header class="preview-header">
        <h2 class="preview-title">试题预览</h2>
        <div class="preview-header-actions">
          <button
            v-if="hideGenerateCard"
            type="button"
            class="outline-btn"
            @click.stop="closePreviewFromRecord"
          >
            关闭预览
          </button>
          <button type="button" class="outline-btn" @click="openSaveModal">保存试卷</button>
        </div>
      </header>

      <div class="preview-body">
        <div
          v-for="(q, index) in questions"
          :key="index"
          class="question-block"
          :class="{ 'is-editing-card': questionEditDrafts[index] != null }"
        >
          <div class="question-block-toolbar">
            <div
              class="q-tag"
              :class="{ yellow: q.type === 'essay' || q.type === 'sa' }"
            >
              第 {{ index + 1 }} 题 ·
              {{
                q.type === 'mc'
                  ? '单选题'
                  : q.type === 'tf'
                    ? '判断题'
                    : q.type === 'sa'
                      ? '简答题'
                      : q.type === 'essay'
                        ? '论述题'
                        : '题目'
              }}
            </div>
            <div class="question-toolbar-actions">
              <template v-if="questionEditDrafts[index] == null">
                <button type="button" class="q-edit-btn q-edit-btn-edit" @click="startEditQuestion(index)">
                  <svg
                    class="q-edit-icon"
                    xmlns="http://www.w3.org/2000/svg"
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                  编辑
                </button>
              </template>
              <template v-else>
                <button type="button" class="q-edit-btn q-edit-btn-primary" @click="saveEditQuestion(index)">
                  保存
                </button>
                <button type="button" class="q-edit-btn" @click="cancelEditQuestion(index)">
                  取消
                </button>
              </template>
            </div>
          </div>

          <!-- 只读预览 -->
          <template v-if="questionEditDrafts[index] == null">
            <p class="q-text">
              {{ q.stem }}
            </p>

            <ul v-if="q.type === 'mc' && q.options && q.options.length" class="option-list">
              <li
                v-for="opt in q.options"
                :key="opt.label"
                class="option"
                :class="{ active: opt.label === q.answer }"
              >
                {{ opt.label }}. {{ opt.text }}
              </li>
            </ul>

            <div v-if="q.type === 'tf'" class="tf-wrap">
              <span class="tf-pill" :class="{ active: isTfTrue(q.answer) }">正确</span>
              <span class="tf-pill" :class="{ active: !isTfTrue(q.answer) }">错误</span>
              <span class="tf-answer">答案：{{ formatTfAnswer(q.answer) }}</span>
            </div>

            <div v-if="(q.type === 'sa' || q.type === 'essay') && (q.answer || q.analysis)" class="answer-hint">
              <div class="hint-title">参考答案与解析：</div>
              <div v-if="q.answer" class="hint-text">
                <div class="hint-k">答案</div>
                <div class="hint-v">{{ q.answer }}</div>
              </div>
              <div v-if="q.analysis" class="hint-text">
                <div class="hint-k">解析</div>
                <div class="hint-v">{{ q.analysis }}</div>
              </div>
            </div>

            <div
              v-if="q.type !== 'tf' && q.type !== 'mc' && q.type !== 'sa' && q.type !== 'essay' && (q.answer || q.analysis)"
              class="answer-hint"
            >
              <div class="hint-title">参考答案与解析：</div>
              <ul class="hint-list">
                <li v-if="q.answer">答案：{{ q.answer }}</li>
                <li v-if="q.analysis">解析：{{ q.analysis }}</li>
              </ul>
            </div>
          </template>

          <!-- 编辑表单 -->
          <template v-else>
            <div class="edit-fields">
              <label class="edit-label">题干</label>
              <textarea v-model="questionEditDrafts[index].stem" class="edit-textarea" rows="4" />

              <template v-if="questionEditDrafts[index].type === 'mc'">
                <label class="edit-label">选项（点选「设为答案」标为正确项）</label>
                <div
                  v-for="(opt, oi) in questionEditDrafts[index].options"
                  :key="oi"
                  class="edit-option-row"
                >
                  <span class="edit-opt-label">{{ opt.label }}.</span>
                  <input v-model="opt.text" type="text" class="edit-input" placeholder="选项内容" />
                  <label class="edit-radio">
                    <input
                      v-model="questionEditDrafts[index].answer"
                      type="radio"
                      class="edit-radio-input"
                      :name="'mc-ans-' + index"
                      :value="opt.label"
                    />
                    设为答案
                  </label>
                </div>
              </template>

              <template v-else-if="questionEditDrafts[index].type === 'tf'">
                <label class="edit-label">答案</label>
                <div class="tf-edit-row">
                  <button
                    type="button"
                    class="tf-edit-btn"
                    :class="{ active: isTfTrue(questionEditDrafts[index].answer) }"
                    @click="questionEditDrafts[index].answer = 'true'"
                  >
                    正确
                  </button>
                  <button
                    type="button"
                    class="tf-edit-btn"
                    :class="{ active: !isTfTrue(questionEditDrafts[index].answer) }"
                    @click="questionEditDrafts[index].answer = 'false'"
                  >
                    错误
                  </button>
                </div>
              </template>

              <template v-else-if="questionEditDrafts[index].type === 'sa' || questionEditDrafts[index].type === 'essay'">
                <label class="edit-label">参考答案</label>
                <textarea v-model="questionEditDrafts[index].answer" class="edit-textarea" rows="5" />
                <label class="edit-label">解析（可选）</label>
                <textarea v-model="questionEditDrafts[index].analysis" class="edit-textarea" rows="4" />
              </template>

              <template v-else>
                <label class="edit-label">参考答案</label>
                <textarea v-model="questionEditDrafts[index].answer" class="edit-textarea" rows="4" />
                <label class="edit-label">解析（可选）</label>
                <textarea v-model="questionEditDrafts[index].analysis" class="edit-textarea" rows="3" />
              </template>
            </div>
          </template>
        </div>
      </div>

      <footer class="preview-footer">
        <button type="button" class="outline-btn" @click="handleExportPdf">导出 PDF</button>
      </footer>
    </section>
    </div>

    <!-- 保存试卷：名称弹窗 -->
    <Teleport to="body">
      <div v-if="showSaveModal" class="save-modal-overlay" @click.self="closeSaveModal">
        <div class="save-modal-box" role="dialog" aria-modal="true" aria-labelledby="save-modal-title">
          <h3 id="save-modal-title" class="save-modal-heading">保存试卷</h3>
          <p class="save-modal-tip">将当前试题保存到您的账号，可在左侧「试题记录」中随时打开。</p>
          <label class="save-modal-label">试卷名称</label>
          <input
            v-model="saveModalTitle"
            type="text"
            class="save-modal-input"
            placeholder="例如：期中复习 · 高等数学"
            @keyup.enter="confirmSavePaper"
          />
          <div class="save-modal-actions">
            <button type="button" class="save-modal-btn ghost" :disabled="saveModalSubmitting" @click="closeSaveModal">
              取消
            </button>
            <button type="button" class="save-modal-btn primary" :disabled="saveModalSubmitting" @click="confirmSavePaper">
              {{ saveModalSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.question-page {
  --qp-base: clamp(13px, 1.05vw, 16px);
  font-size: var(--qp-base);
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 100%;
  align-items: stretch;
  overflow-x: hidden;
  box-sizing: border-box;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.sidebar-outer {
  position: relative;
  flex: 0 0 24%;
  min-width: 0;
  max-width: 30%;
  z-index: 2;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
}

.sidebar-outer.is-collapsed {
  flex: 0 0 auto;
  width: auto;
  max-width: none;
}

.saved-sidebar {
  width: 100%;
  min-width: 0;
  flex: 1;
  background: #fff;
  border-right: 1px solid #eaedf0;
  display: flex;
  flex-direction: column;
  padding: 4% 3.5%;
  min-height: 0;
  box-sizing: border-box;
}

.sidebar-header {
  display: flex;
  gap: 4%;
  margin-bottom: 6%;
  align-items: flex-start;
}

.sidebar-title-block {
  flex: 1;
  min-width: 0;
  padding: 0.15em 0.25em 0 0;
}

.sidebar-title {
  font-size: 112.5%;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.sidebar-title-desc {
  margin: 4% 0 0;
  font-size: 81.25%;
  color: #64748b;
  line-height: 1.45;
}

.collapse-btn {
  width: 14%;
  min-width: 32px;
  max-width: 40px;
  aspect-ratio: 1;
  flex-shrink: 0;
  background: #f7f8fa;
  border: 1px solid #e0e3e8;
  border-radius: 8px;
  cursor: pointer;
  color: #999;
  font-size: 112.5%;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.collapse-btn:hover {
  color: #2563eb;
  border-color: #2563eb;
  background: #f0f5ff;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.empty-state {
  padding: 10% 4%;
  text-align: center;
  color: #94a3b8;
  font-size: 87.5%;
}

.history-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 3%;
  padding: 5% 5%;
  border-radius: 8px;
  font-size: 87.5%;
  color: #334155;
  cursor: pointer;
  margin-bottom: 3%;
  transition: background 0.2s;
}

.history-item:hover {
  background: #f0f5ff;
}

.history-item.active {
  background: #e8f0fe;
  color: #1d4ed8;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.history-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-meta {
  font-size: 75%;
  color: #94a3b8;
  margin-top: 3%;
  line-height: 1.35;
}

.history-item.active .history-meta {
  color: #64748b;
}

.delete-btn {
  opacity: 0;
  width: 10%;
  min-width: 28px;
  max-width: 32px;
  aspect-ratio: 1;
  border: none;
  border-radius: 4px;
  background: #e0e7ff;
  color: #6366f1;
  font-size: 100%;
  line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: opacity 0.15s;
}

.history-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #c7d2fe;
  color: #4f46e5;
}

.sidebar-expand {
  position: sticky;
  top: 2%;
  left: 0;
  width: 10%;
  min-width: 26px;
  max-width: 32px;
  height: auto;
  aspect-ratio: 7 / 11;
  margin: 6% 0 0 0;
  background: #fff;
  border: 1px solid #eaedf0;
  border-left: none;
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 87.5%;
  box-shadow: 2px 0 8px rgba(15, 23, 42, 0.06);
}

.sidebar-expand:hover {
  color: #2563eb;
  background: #f0f5ff;
}

.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 0.28s ease, opacity 0.28s ease;
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(-12px);
  opacity: 0;
}

.page-wrap {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  width: 0;
  max-width: 100%;
  /* 纵向用 em，避免侧栏收起后主区变宽时 padding 随「宽度」变大 */
  padding-block: 1.25em;
  padding-inline: 2.5%;
  display: flex;
  gap: 2%;
  align-items: stretch;
  justify-content: center;
  box-sizing: border-box;
}

.page-wrap.with-preview {
  justify-content: flex-start;
}

/* 从左侧记录打开预览时隐藏中间表单，预览区占满剩余宽度 */
.page-wrap.preview-from-record {
  justify-content: flex-start;
}

.page-wrap.preview-from-record .preview-card {
  flex: 1 1 auto;
  max-width: 96%;
  width: 100%;
  min-width: 0;
}

.config-card {
  width: 100%;
  max-width: 78%;
  background: #ffffff;
  border-radius: 1.1em;
  padding-block: 1.75em;
  padding-inline: 4%;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
}

.page-wrap:not(.with-preview) .config-card {
  margin: 0 auto;
  flex: 1 1 0;
  align-self: stretch;
  min-height: 0;
}

.page-wrap.with-preview .config-card {
  width: auto;
  flex: 0 0 40%;
  min-width: 0;
  max-width: 44%;
  align-self: stretch;
}

.config-card > .header,
.config-card > .field:not(.field--source) {
  flex-shrink: 0;
}

.field--source {
  flex: 0 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: auto;
  padding-top: 1.35em;
  margin-bottom: 0;
}

.field--source .label-row,
.field--source .upload-hint {
  flex-shrink: 0;
}

.header {
  margin-bottom: 1.25em;
}

.title {
  margin: 0 0 0.5em;
  font-size: 162.5%;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
  word-break: break-word;
}

.subtitle {
  margin: 0;
  font-size: 93.75%;
  color: #64748b;
  line-height: 1.5;
}

.header--compact {
  margin-bottom: 0.85em;
}

.header--compact .title {
  margin-bottom: 0.35em;
}

/* 独立对话窗口 */
.chat-dialog {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: min(62vh, 30em);
  max-height: min(72vh, 42em);
  margin-bottom: 0.85em;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.chat-dialog__head {
  display: flex;
  align-items: center;
  gap: 0.65em;
  padding: 0.65em 0.85em;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e8ecf1;
  flex-shrink: 0;
}

.chat-dialog__head-avatar {
  width: 2.5em;
  height: 2.5em;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
  display: block;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.chat-dialog__head-text {
  min-width: 0;
}

.chat-dialog__head-title {
  font-weight: 700;
  font-size: 100%;
  color: #0f172a;
  line-height: 1.3;
}

.chat-dialog__head-sub {
  font-size: 75%;
  color: #64748b;
  line-height: 1.4;
  margin-top: 0.15em;
}

.chat-dialog__body {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: 0.75em 0.85em 0.65em;
  background: #f1f5f9;
  background-image: linear-gradient(180deg, #eef2f7 0%, #f8fafc 48%, #f1f5f9 100%);
}

.dialog-msg {
  display: flex;
  align-items: flex-end;
  gap: 0.5em;
  margin-bottom: 0.75em;
}

.dialog-msg--assistant {
  justify-content: flex-start;
}

.dialog-msg--user {
  justify-content: flex-end;
}

/* 助手头像（图片）；用户侧仍用 .dialog-msg__avatar 文字圆底 */
.dialog-msg__assistant-avatar {
  width: 2em;
  height: 2em;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  display: block;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  align-self: flex-end;
}

.dialog-msg__avatar {
  width: 2em;
  height: 2em;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  align-self: flex-end;
}

.dialog-msg__avatar--user {
  background: linear-gradient(160deg, #ffffff 0%, #f0f7ff 45%, #e0edff 100%);
  color: #1d4ed8;
  border: 2px solid rgba(37, 99, 235, 0.28);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.06),
    0 4px 12px rgba(37, 99, 235, 0.14);
}

.dialog-msg__user-icon {
  width: 58%;
  height: 58%;
  flex-shrink: 0;
  opacity: 0.92;
}

.dialog-msg__main {
  display: flex;
  flex-direction: column;
  max-width: min(92%, 28em);
  min-width: 0;
}

.dialog-msg--user .dialog-msg__main {
  align-items: flex-end;
}

.dialog-msg__name {
  font-size: 72%;
  color: #94a3b8;
  margin-bottom: 0.2em;
  padding-inline: 0.25em;
}

.dialog-msg__bubble {
  padding: 0.55em 0.75em;
  border-radius: 14px;
  font-size: 93.75%;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-msg--assistant .dialog-msg__bubble {
  background: #fff;
  color: #1e293b;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 5px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.dialog-msg--user .dialog-msg__bubble {
  background: #2563eb;
  color: #fff;
  border-bottom-right-radius: 5px;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.dialog-msg__bubble--typing {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  padding: 0.65em 0.85em;
  min-height: 2.25em;
}

.dialog-msg__bubble--gen {
  flex-wrap: wrap;
  gap: 0.5em;
}

.typing-dot {
  width: 0.38em;
  height: 0.38em;
  border-radius: 50%;
  background: #94a3b8;
  animation: dialog-typing 1.1s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.3s;
}

.typing-label {
  font-size: 81.25%;
  color: #64748b;
  margin-left: 0.15em;
}

@keyframes dialog-typing {
  0%,
  60%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.chat-dialog__footer {
  display: flex;
  align-items: flex-end;
  gap: 0.5em;
  padding: 0.65em 0.75em;
  background: #fff;
  border-top: 1px solid #e8ecf1;
  flex-shrink: 0;
}

.chat-dialog__input {
  flex: 1 1 0;
  min-width: 0;
  box-sizing: border-box;
  padding: 0.5em 0.75em;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 93.75%;
  font-family: inherit;
  resize: vertical;
  min-height: 2.85em;
  max-height: 9em;
  outline: none;
  line-height: 1.45;
}

.chat-dialog__input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.chat-dialog__input:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

.chat-dialog__send {
  flex-shrink: 0;
  min-width: 4.5em;
  padding: 0.55em 0.85em;
  border: none;
  border-radius: 12px;
  background: #2563eb;
  color: #fff;
  font-size: 93.75%;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
  transition: background 0.15s ease, transform 0.12s ease;
}

.chat-dialog__send:hover:not(:disabled) {
  background: #1d4ed8;
  transform: translateY(-1px);
}

.chat-dialog__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.chat-dialog__send-label {
  display: block;
  line-height: 1.2;
}

.field {
  margin-bottom: 1em;
}

.label {
  display: block;
  margin-bottom: 0.35em;
  font-size: 100%;
  font-weight: 500;
  color: #4b5563;
}

.subject-input {
  display: flex;
  align-items: center;
  padding-block: 0.65em;
  padding-inline: 3%;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f9fafb;
  gap: 2%;
}

.subject-icon {
  font-size: 112.5%;
}

.subject-text {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 106.25%;
  outline: none;
}

.subject-chevron {
  font-size: 62.5%;
  color: #9ca3af;
}

.pill-group {
  display: inline-flex;
  flex-wrap: wrap;
  padding: 0.2em;
  border-radius: 999px;
  background: #eef2ff;
  max-width: 100%;
}

.pill-btn {
  border: none;
  background: transparent;
  padding: 0.4em 1.1em;
  font-size: 93.75%;
  color: #6b7280;
  border-radius: 999px;
  cursor: pointer;
}

.pill-btn.active {
  background: #ffffff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  row-gap: 0.5em;
  column-gap: 2%;
}

.type-btn {
  display: inline-flex;
  align-items: center;
  gap: 2%;
  padding-block: 0.55em;
  padding-inline: 2.5%;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  font-size: 93.75%;
  color: #4b5563;
  cursor: pointer;
}

.type-btn .box {
  width: 1em;
  height: 1em;
  border-radius: 0.25em;
  border: 1px solid #d1d5db;
  background: #ffffff;
  flex-shrink: 0;
}

.type-btn.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.type-btn.active .box {
  border-color: #2563eb;
  background: #2563eb;
}

.label-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5em 3%;
  flex-wrap: wrap;
}

.label-row > div:first-child {
  flex: 1 1 48%;
  min-width: 0;
}

.link-btn {
  border: 1px solid rgba(37, 99, 235, 0.25);
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 87.5%;
  font-weight: 600;
  cursor: pointer;
  padding: 0.45em 0.85em;
  border-radius: 999px;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.link-btn:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.35);
  transform: translateY(-1px);
}

.link-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.source-input {
  width: 100%;
  flex: 0 1 auto;
  min-height: 4.25em;
  margin-top: 0.5em;
  padding-block: 0.65em;
  padding-inline: 3%;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 93.75%;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.upload-hint {
  margin: 0.5em 0 0;
  font-size: 81.25%;
  color: #64748b;
  line-height: 1.45;
}

.error-text {
  margin: 0 0 0.75em;
  font-size: 87.5%;
  color: #dc2626;
  line-height: 1.45;
  flex-shrink: 0;
}

.primary-btn {
  width: 100%;
  margin-top: 0.65em;
  flex-shrink: 0;
  border: none;
  border-radius: 12px;
  background: #2563eb;
  color: #ffffff;
  font-size: 106.25%;
  font-weight: 600;
  padding: 0.65em 1em;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.4);
  box-sizing: border-box;
}

.primary-btn.small {
  width: auto;
  box-shadow: none;
  padding-inline: 1.1em;
}

.count-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
  flex: 0 1 38%;
  margin-left: 0;
}

.label.small-label {
  margin-bottom: 0.25em;
}

.number-input {
  width: 100%;
  max-width: 100%;
  padding: 0.5em 0.75em;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 93.75%;
  outline: none;
  box-sizing: border-box;
}

.preview-card {
  flex: 1 1 56%;
  min-height: 0;
  min-width: 0;
  width: 0;
  max-width: 100%;
  background: #ffffff;
  border-radius: 1.1em;
  padding: 3% 3.5% 3.5%;
  border: 1px solid #e2e8f0;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
  align-self: stretch;
  box-sizing: border-box;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.65em 2%;
  margin-bottom: 3%;
  flex-wrap: nowrap;
  min-width: 0;
}

.preview-header-actions {
  display: inline-flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5em;
  flex-shrink: 0;
  justify-content: flex-end;
}

.preview-header-actions .outline-btn {
  white-space: nowrap;
}

.preview-title {
  margin: 0;
  flex: 1 1 auto;
  min-width: 0;
  font-size: 118.75%;
  font-weight: 600;
  color: #0f172a;
}

.outline-btn {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 87.5%;
  color: #4b5563;
  padding: 0.45em 0.9em;
  cursor: pointer;
}

.preview-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.15em;
  /* 隐藏滚动条但保留滚动能力 */
  scrollbar-width: none; /* Firefox */
}

.preview-body::-webkit-scrollbar {
  display: none; /* Chrome / Edge / Safari */
}

/* 导出 PDF 时，取消高度限制和内部滚动，导出完整内容 */
.preview-card.exporting {
  max-height: none;
}

.preview-card.exporting .preview-body {
  overflow: visible;
  max-height: none;
  scrollbar-width: auto;
}

.question-block {
  position: relative;
  margin-bottom: 4.5%;
  padding: 3% 3.5% 3.5%;
  border-radius: 12px;
  background: #f9fafb;
}

.question-block.is-editing-card {
  background: #f0f7ff;
  border: 1px solid #bfdbfe;
}

.question-block-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 3%;
  margin-bottom: 2.5%;
}

.question-block-toolbar .q-tag {
  margin-bottom: 0;
  min-width: 0;
  flex: 0 1 auto;
}

.question-toolbar-actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5em;
}

.q-edit-btn {
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 87.5%;
  font-weight: 600;
  color: #475569;
  padding: 0.45em 0.95em;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35em;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.25;
  writing-mode: horizontal-tb;
}

.q-edit-btn:hover {
  border-color: #2563eb;
  color: #2563eb;
}

/* 题目卡片上的「编辑」：更醒目（描边 + 浅蓝底 + 图标） */
.q-edit-btn-edit {
  font-size: 87.5%;
  font-weight: 700;
  padding: 0.45em 0.95em;
  border-radius: 10px;
  color: #1d4ed8;
  background: linear-gradient(180deg, #f0f7ff 0%, #e0edff 100%);
  border: 2px solid #93c5fd;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.18);
}

.q-edit-btn-edit:hover {
  color: #1e40af;
  background: linear-gradient(180deg, #e0edff 0%, #dbeafe 100%);
  border-color: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28);
}

.q-edit-icon {
  flex-shrink: 0;
  opacity: 0.95;
}

.q-edit-btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.q-edit-btn-primary:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
}

.edit-fields {
  display: flex;
  flex-direction: column;
  gap: 0.5em;
}

.edit-label {
  font-size: 81.25%;
  font-weight: 600;
  color: #64748b;
  margin-top: 0.25em;
}

.edit-textarea,
.edit-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e2e8f0;
  border-radius: 0.65em;
  padding: 0.5em 0.65em;
  font-size: 93.75%;
  color: #111827;
  background: #fff;
  font-family: inherit;
}

.edit-textarea {
  resize: vertical;
  min-height: 4.5em;
}

.edit-option-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2%;
  margin-bottom: 0.35em;
}

.edit-opt-label {
  font-weight: 700;
  color: #1d4ed8;
  min-width: 1.4em;
}

.edit-option-row .edit-input {
  flex: 1 1 40%;
  min-width: 0;
}

.edit-radio {
  display: inline-flex;
  align-items: center;
  gap: 0.25em;
  font-size: 81.25%;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
}

.edit-radio-input {
  margin: 0;
  cursor: pointer;
}

.tf-edit-row {
  display: flex;
  gap: 2.5%;
  flex-wrap: wrap;
}

.tf-edit-btn {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  padding: 0.5em 1.1em;
  font-size: 87.5%;
  font-weight: 600;
  color: #4b5563;
  cursor: pointer;
}

.tf-edit-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.q-tag {
  display: inline-flex;
  padding: 0.15em 0.65em;
  border-radius: 999px;
  background: #e0edff;
  color: #1d4ed8;
  font-size: 75%;
  font-weight: 600;
  margin-bottom: 2%;
}

.q-tag.yellow {
  background: #fef3c7;
  color: #b45309;
}

.q-text {
  margin: 0 0 2%;
  font-size: 93.75%;
  color: #111827;
}

.option-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.option {
  padding: 0.5em 0.65em;
  border-radius: 0.5em;
  background: #ffffff;
  font-size: 87.5%;
  color: #111827;
  margin-bottom: 0.35em;
}

.option.active {
  background: #2563eb;
  color: #ffffff;
}

.answer-hint {
  margin-top: 2.5%;
  padding: 2.5% 3%;
  border-radius: 0.65em;
  background: #ffffff;
  border: 1px dashed #e5e7eb;
}

.tf-wrap {
  margin-top: 2.5%;
  display: flex;
  align-items: center;
  gap: 2%;
  flex-wrap: wrap;
}

.tf-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.4em 0.75em;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #4b5563;
  font-size: 87.5%;
  font-weight: 600;
}

.tf-pill.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.tf-answer {
  font-size: 87.5%;
  color: #6b7280;
}

.hint-text {
  margin-top: 2%;
}

.hint-k {
  font-size: 81.25%;
  font-weight: 700;
  color: #6b7280;
  margin-bottom: 0.15em;
}

.hint-v {
  font-size: 87.5%;
  color: #111827;
  white-space: pre-wrap;
  line-height: 1.6;
}

.hint-title {
  font-size: 81.25%;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 0.25em;
}

.hint-list {
  margin: 0;
  padding-left: 1.15em;
  font-size: 81.25%;
  color: #4b5563;
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
  gap: 2%;
  margin-top: 2.5%;
}

/* 保存试卷弹窗 */
.save-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5%;
  --qp-base: clamp(13px, 1.05vw, 16px);
  font-size: var(--qp-base);
  box-sizing: border-box;
}

.save-modal-box {
  width: 100%;
  max-width: min(92%, 26em);
  background: #fff;
  border-radius: 1em;
  padding: 1.4em 1.5em 1.25em;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.2);
  border: 1px solid #e2e8f0;
  box-sizing: border-box;
}

.save-modal-heading {
  margin: 0 0 0.5em;
  font-size: 118.75%;
  font-weight: 700;
  color: #0f172a;
}

.save-modal-tip {
  margin: 0 0 1em;
  font-size: 87.5%;
  color: #64748b;
  line-height: 1.5;
}

.save-modal-label {
  display: block;
  font-size: 87.5%;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.35em;
}

.save-modal-input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.65em 0.75em;
  border-radius: 0.65em;
  border: 1px solid #e2e8f0;
  font-size: 93.75%;
  outline: none;
  margin-bottom: 1.25em;
}

.save-modal-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.save-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 2.5%;
}

.save-modal-btn {
  padding: 0.55em 1.1em;
  border-radius: 0.65em;
  font-size: 93.75%;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.save-modal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-modal-btn.ghost {
  background: #f1f5f9;
  color: #475569;
}

.save-modal-btn.primary {
  background: #2563eb;
  color: #fff;
}

@media (max-width: 1200px) {
  .page-wrap.with-preview .config-card {
    flex: 0 1 42%;
    min-width: 0;
    max-width: 48%;
  }
}

@media (max-width: 900px) {
  .question-page {
    flex-direction: column;
  }

  .saved-sidebar {
    width: 100%;
    min-width: 0;
    min-height: auto;
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid #eaedf0;
  }

  .sidebar-expand {
    position: fixed;
    top: max(12px, env(safe-area-inset-top, 0px));
    left: 0;
    z-index: 20;
    margin: 0;
  }

  .page-wrap {
    flex-direction: column;
    align-items: stretch;
    padding-left: max(12px, env(safe-area-inset-left, 0px));
    padding-right: max(12px, env(safe-area-inset-right, 0px));
  }

  .chat-dialog {
    min-height: 20em;
    max-height: min(56vh, 34em);
  }

  .page-wrap.with-preview .config-card {
    flex: none;
    width: 100%;
    max-width: none;
    min-width: 0;
  }

  .config-card {
    flex: none;
    width: 100%;
    max-width: none;
  }

  .page-wrap:not(.with-preview) .config-card {
    flex: 1 1 0;
    min-height: 0;
  }

  .preview-card {
    flex: 1 1 auto;
    width: 100%;
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .label-row {
    flex-direction: column;
    align-items: stretch;
  }

  .count-wrap {
    width: 100%;
  }

  .number-input {
    max-width: none;
    width: 100%;
  }

  .type-grid {
    grid-template-columns: 1fr;
  }

  .pill-btn {
    padding: 0.45em 0.9em;
    font-size: 87.5%;
  }
}
</style>

