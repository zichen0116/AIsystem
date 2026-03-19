<script setup>
/**
 * LessonPrepPpt.vue - PPT生成主页面
 *
 * 阶段：欢迎页 -> 对话+大纲 -> 预览+编辑
 * Stage 3 布局对齐原型：左=对话面板(40%) | resize-handle | 右=预览面板(60%)
 */
import { computed, nextTick, ref, onMounted, onBeforeUnmount } from 'vue'
import WelcomePanel from '../components/ppt/WelcomePanel.vue'
import ChatPanel from '../components/ppt/ChatPanel.vue'
import ChatInput from '../components/ppt/ChatInput.vue'
import TemplateSelector from '../components/ppt/TemplateSelector.vue'
import KnowledgeLibraryModal from '../components/ppt/KnowledgeLibraryModal.vue'
import PptSidebar from '../components/ppt/PptSidebar.vue'
import PptThumbnailList from '../components/ppt/PptThumbnailList.vue'
import PptCanvas from '../components/ppt/PptCanvas.vue'
import {
  createSession, listSessions, getSessionDetail,
  approveOutline, getResultDetail, downloadResult, saveEditSnapshot, modifyPptResult,
  streamPptSSE, deleteSession,
} from '../api/ppt.js'
import { decodePptxProperty } from '../utils/docmee/decodePptxProperty.js'
import { encodePptxProperty } from '../utils/docmee/encodePptxProperty.js'
import { Ppt2Canvas } from '../utils/docmee/ppt2canvas.js'
import { CLARIFICATION_STEPS, buildClarificationRequest, getClarificationQuestion } from '../utils/pptOutlineFlow.js'
import { cloneOutlinePayload, hasRenderableOutlinePayload, markdownToOutlinePayload, resolveSpeakerNotes } from '../utils/pptOutlineCard.js'
import {
  getPdfExportLayerPosition,
  getPptDownloadUrl,
  openPendingPptDownloadWindow,
  triggerPptDownload,
} from '../utils/pptPreview.js'

// ========== 状态 ==========
const stage = ref('welcome') // welcome | chat | preview
const sidebarCollapsed = ref(false)

// 会话
const sessions = ref([])
const currentSessionId = ref(null)
const currentSession = ref(null)

// 消息
const messages = ref([])
const userInput = ref('')
const isStreaming = ref(false)
const streamingText = ref('')
let abortController = null
const clarificationStage = ref('idle')
const pendingTopic = ref('')
const clarificationAnswers = ref({
  audience: '',
  goal: '',
  duration: '',
  focus: '',
  style: '',
})
const clarificationStepIndex = ref(0)

// 大纲
const currentOutline = ref(null)

// 模板 & 知识库
const selectedTemplateId = ref(null)
const selectedKnowledgeIds = ref([])
const showTemplateSelector = ref(false)
const showKnowledgeModal = ref(false)
const knowledgeTriggerEl = ref(null)

// PPT结果
const currentResult = ref(null)
const pptxProperty = ref('')
const pptxDoc = ref(null)
const slides = ref([])
const activeSlideIndex = ref(0)
const isGeneratingPpt = ref(false)
const genCurrentPage = ref(0)
const genTotalPages = ref(0)
const thumbnailDirtySlideIndex = ref(null)
const thumbnailRenderNonce = ref(0)
const isPreviewFullscreen = ref(false)
const isExportingPdf = ref(false)
const exportContainerRef = ref(null)
const exportCanvasRefs = []
const exportPainters = new Map()

// Stage 3 拖拽
const chatPanelWidth = ref(40) // percentage
const thumbWidth = ref(150) // px
const isResizingMain = ref(false)
const isResizingThumb = ref(false)
let resizeStartX = 0
let resizeStartVal = 0
let saveSnapshotTimer = null

// 文件上传
const fileInputRef = ref(null)
const imageInputRef = ref(null)

// 语音
const isRecording = ref(false)

function normalizeImageUrls(imageUrls) {
  if (!imageUrls) return {}
  if (Array.isArray(imageUrls)) {
    return Object.fromEntries(
      imageUrls
        .filter(Boolean)
        .map((value, index) => [String(index), Array.isArray(value) ? value : [value]]),
    )
  }
  if (typeof imageUrls === 'object') return imageUrls
  return {}
}

function normalizeOutlineRecord(outline) {
  if (!outline) return null
  const imageUrls = normalizeImageUrls(outline.image_urls)
  const outlinePayload = hasRenderableOutlinePayload(outline.outline_payload)
    ? cloneOutlinePayload(outline.outline_payload)
    : markdownToOutlinePayload(outline.content || '', imageUrls)
  return {
    ...outline,
    image_urls: imageUrls,
    outline_payload: outlinePayload,
  }
}

function normalizeResultRecord(result) {
  if (!result) return null
  const resultId = result.result_id || result.id || null
  return {
    ...result,
    id: resultId,
    result_id: resultId,
  }
}

const currentSpeakerNotes = computed(() => {
  return resolveSpeakerNotes(currentOutline.value?.outline_payload, activeSlideIndex.value)
})

const pdfExportLayerStyle = computed(() => getPdfExportLayerPosition(isExportingPdf.value))

function bumpThumbnailRefresh(dirtySlideIndex = null) {
  thumbnailDirtySlideIndex.value = Number.isInteger(dirtySlideIndex) ? dirtySlideIndex : null
  thumbnailRenderNonce.value += 1
}

function syncFullscreenBodyState() {
  document.body.style.overflow = isPreviewFullscreen.value ? 'hidden' : ''
}

function handleFullscreenKeydown(event) {
  if (event.key === 'Escape' && isPreviewFullscreen.value) {
    isPreviewFullscreen.value = false
    syncFullscreenBodyState()
  }
}

function setExportCanvasRef(el, index) {
  if (el) {
    exportCanvasRefs[index] = el
  }
}

function appendOutlineMessage(outlineId, content, imageUrls, outlinePayload = null) {
  messages.value.push({
    role: 'assistant',
    message_type: 'outline',
    content,
    metadata_: {
      outline_id: outlineId,
      image_urls: imageUrls,
      outline_payload: outlinePayload,
    },
    created_at: new Date().toISOString(),
  })
}

async function handleOutlineEdit(message, editedOutline) {
  const outlineId = message?.metadata_?.outline_id
  if (!outlineId || !currentOutline.value || currentOutline.value.id !== outlineId) return
  const nextContent = typeof editedOutline === 'string' ? editedOutline : editedOutline?.content
  const nextPayload = typeof editedOutline === 'object' ? editedOutline?.outline_payload : null
  const nextImageUrls = typeof editedOutline === 'object' ? editedOutline?.image_urls : null
  currentOutline.value = {
    ...currentOutline.value,
    content: nextContent || currentOutline.value.content,
    outline_payload: nextPayload || currentOutline.value.outline_payload,
    image_urls: nextImageUrls || currentOutline.value.image_urls,
  }
  const target = messages.value.find(msg => msg === message)
  if (target) {
    target.content = nextContent || target.content
    target.metadata_ = {
      ...(target.metadata_ || {}),
      outline_payload: nextPayload || target.metadata_?.outline_payload || null,
      image_urls: nextImageUrls || target.metadata_?.image_urls || null,
    }
  }
  try {
    await approveOutline(
      outlineId,
      nextContent || currentOutline.value.content,
      nextImageUrls || currentOutline.value.image_urls || null,
      nextPayload || currentOutline.value.outline_payload || null,
    )
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      message_type: 'error',
      content: error?.message || '保存大纲修改失败，请稍后重试',
    })
  }
}

async function applyPptxProperty(encoded, options = {}) {
  const {
    keepActiveSlide = false,
    dirtySlideIndex = null,
    forceThumbnailRefresh = true,
  } = options

  pptxProperty.value = encoded || ''

  if (!encoded) {
    activeSlideIndex.value = 0
    pptxDoc.value = null
    slides.value = []
    bumpThumbnailRefresh(null)
    return
  }

  try {
    const doc = await decodePptxProperty(encoded)
    pptxDoc.value = doc
    slides.value = Array.isArray(doc?.pages) ? doc.pages : []
    if (keepActiveSlide) {
      const maxIndex = Math.max(slides.value.length - 1, 0)
      activeSlideIndex.value = Math.min(activeSlideIndex.value, maxIndex)
    } else {
      activeSlideIndex.value = 0
    }
    if (forceThumbnailRefresh || Number.isInteger(dirtySlideIndex)) {
      bumpThumbnailRefresh(dirtySlideIndex)
    }
  } catch (error) {
    console.error('解析 PPT 预览数据失败:', error)
    pptxDoc.value = null
    slides.value = []
    messages.value.push({
      role: 'assistant',
      message_type: 'error',
      content: error?.message || 'PPT 预览数据解析失败',
    })
  }
}

async function persistEditedPpt(doc) {
  if (!currentResult.value?.result_id || !doc) return

  pptxDoc.value = doc
  slides.value = Array.isArray(doc?.pages) ? doc.pages : []
  bumpThumbnailRefresh(activeSlideIndex.value)

  if (saveSnapshotTimer) {
    clearTimeout(saveSnapshotTimer)
  }

  saveSnapshotTimer = setTimeout(async () => {
    try {
      const encoded = await encodePptxProperty(doc)
      pptxProperty.value = encoded
      await saveEditSnapshot(currentResult.value.result_id, encoded)
    } catch (error) {
      console.error('保存 PPT 编辑快照失败:', error)
      messages.value.push({
        role: 'assistant',
        message_type: 'error',
        content: error?.message || '保存 PPT 编辑结果失败',
      })
    }
  }, 300)
}

const clarificationQuestions = CLARIFICATION_STEPS || [
  {
    key: 'audience',
    ask: (topic) => `好呀，我们先慢慢来。\n\n这份《${topic}》PPT，你主要想讲给谁听呢？比如高中生、本科生，或者家长、老师都可以。`,
  },
  {
    key: 'goal',
    ask: () => '明白了。\n\n那你希望这份 PPT 最终帮你达到什么教学目标呀？比如让大家建立整体认识、理解重点概念，或者用于课堂汇报。',
  },
  {
    key: 'duration',
    ask: () => '好的，我记下来了。\n\n这次大概准备讲多久呢？如果你心里有预期页数，也可以一起告诉我。',
  },
  {
    key: 'focus',
    ask: () => '收到。\n\n那内容上你最想重点展开哪几部分呢？我可以把篇幅和层次更贴近你的想法。',
  },
  {
    key: 'style',
    ask: () => '最后再帮你确认一个小细节。\n\n你对风格、案例、知识库素材，或者配图方向有没有特别偏好的要求？没有的话我也可以按主题帮你自然处理。',
  },
]

function resetClarification() {
  clarificationStage.value = 'idle'
  pendingTopic.value = ''
  clarificationStepIndex.value = 0
  clarificationAnswers.value = {
    audience: '',
    goal: '',
    duration: '',
    focus: '',
    style: '',
  }
}

function getCurrentClarificationQuestion() {
  const step = clarificationQuestions[clarificationStepIndex.value]
  if (!step) return ''
  return step.ask(pendingTopic.value)
}

function buildOutlineRequest() {
  return [
    `PPT主题：${pendingTopic.value}`,
    '',
    '下面是已经和用户逐轮确认过的真实意图，请严格基于这些信息生成 PPT 大纲：',
    `受众：${clarificationAnswers.value.audience || '未明确'}`,
    `教学目标：${clarificationAnswers.value.goal || '未明确'}`,
    `演讲时长/页数：${clarificationAnswers.value.duration || '未明确'}`,
    `重点展开内容：${clarificationAnswers.value.focus || '未明确'}`,
    `风格/案例/素材偏好：${clarificationAnswers.value.style || '未特别指定'}`,
    '',
    '要求：',
    '1. 直接输出 PPT 大纲内容，不要重复提问，不要输出寒暄。',
    '2. 明确体现受众、教学目标、演讲时长或页数、重点内容和呈现重点。',
    '3. 如果用户没有写全，可以做最小必要补全，但不要偏离用户意图。',
  ].join('\n')
}

function getCurrentClarificationQuestionText() {
  return getClarificationQuestion(pendingTopic.value, clarificationStepIndex.value)
}

function buildOutlineRequestText() {
  return buildClarificationRequest(pendingTopic.value, clarificationAnswers.value)
}

// ========== 生命周期 ==========
onMounted(async () => {
  document.addEventListener('keydown', handleFullscreenKeydown)
  try {
    sessions.value = await listSessions()
  } catch { /* ignore */ }
})

onBeforeUnmount(() => {
  isPreviewFullscreen.value = false
  syncFullscreenBodyState()
  if (saveSnapshotTimer) clearTimeout(saveSnapshotTimer)
  exportPainters.clear()
  document.removeEventListener('keydown', handleFullscreenKeydown)
  document.removeEventListener('mousemove', onResizeMain)
  document.removeEventListener('mouseup', stopResizeMain)
  document.removeEventListener('mousemove', onResizeThumb)
  document.removeEventListener('mouseup', stopResizeThumb)
})

// ========== 会话管理 ==========
async function handleNewSession() {
  try {
    const s = await createSession()
    sessions.value.unshift(s)
    currentSessionId.value = s.id
    currentSession.value = s
    resetState()
    stage.value = 'welcome'
  } catch (e) {
    console.error('创建会话失败:', e)
  }
}

async function handleSelectSession(id) {
  currentSessionId.value = id
  try {
    const detail = await getSessionDetail(id)
    currentSession.value = detail
    messages.value = detail.messages || []

    const currentOl = detail.outlines?.find(o => o.is_current)
    currentOutline.value = normalizeOutlineRecord(currentOl)
    resetClarification()
    if (currentOl) clarificationStage.value = 'done'

    const currentRes = detail.results?.find(r => r.is_current)
    currentResult.value = normalizeResultRecord(currentRes)

    if (currentRes && currentRes.status === 'completed') {
      stage.value = 'preview'
      sidebarCollapsed.value = true
      await loadResultDetail(currentRes.id)
    } else if (currentOl) {
      stage.value = 'chat'
    } else {
      stage.value = 'welcome'
    }
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

async function handleDeleteSession(id) {
  if (!confirm('确定删除该会话？')) return
  try {
    await deleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = null
      currentSession.value = null
      resetState()
      stage.value = 'welcome'
    }
  } catch (e) {
    console.error('删除会话失败:', e)
  }
}

function resetState() {
  isPreviewFullscreen.value = false
  syncFullscreenBodyState()
  messages.value = []
  userInput.value = ''
  streamingText.value = ''
  resetClarification()
  currentOutline.value = null
  currentResult.value = null
  pptxProperty.value = ''
  pptxDoc.value = null
  slides.value = []
  activeSlideIndex.value = 0
  bumpThumbnailRefresh(null)
}

// ========== 发送消息 ==========
async function handleSend() {
  const text = userInput.value.trim()
  if (!text || isStreaming.value) return

  if (!currentSessionId.value) {
    await handleNewSession()
  }

  stage.value = 'chat'
  messages.value.push({ role: 'user', message_type: 'text', content: text })
  userInput.value = ''

  if (currentOutline.value) {
    await streamModifyOutline(text)
    return
  }

  if (clarificationStage.value === 'idle') {
    pendingTopic.value = text
    clarificationStage.value = 'awaiting_reply'
    clarificationStepIndex.value = 0
    messages.value.push({
      role: 'assistant',
      message_type: 'text',
      content: getCurrentClarificationQuestionText(),
    })
    return
  }

  if (clarificationStage.value === 'awaiting_reply') {
    const step = clarificationQuestions[clarificationStepIndex.value]
    if (step) {
      clarificationAnswers.value[step.key] = text
    }

    clarificationStepIndex.value += 1

    if (clarificationStepIndex.value < clarificationQuestions.length) {
      messages.value.push({
        role: 'assistant',
        message_type: 'text',
        content: getCurrentClarificationQuestionText(),
      })
      return
    }

    clarificationStage.value = 'generating_outline'
    await streamGenerateOutline(buildOutlineRequestText())
    clarificationStage.value = 'done'
  }
}

// ========== 流式生成大纲 ==========
async function streamGenerateOutline(text) {
  isStreaming.value = true
  streamingText.value = ''
  abortController = new AbortController()

  try {
    await streamPptSSE(
      '/api/v1/ppt/stream/outline',
      {
        session_id: currentSessionId.value,
        user_input: text,
        knowledge_library_ids: selectedKnowledgeIds.value,
        template_id: selectedTemplateId.value,
      },
      {
        onChunk(content) { streamingText.value += content },
        onOutlineReady(data) {
          const imageUrls = normalizeImageUrls(data.image_urls)
          const outlinePayload = data.outline_payload || null
          messages.value.push({
            role: 'assistant',
            message_type: 'text',
            content: '明白了！我已经为你生成了大纲，请查看：',
            created_at: new Date().toISOString(),
          })
          currentOutline.value = {
            id: data.outline_id,
            content: data.content,
            image_urls: imageUrls,
            outline_payload: outlinePayload,
            is_current: true,
          }
          appendOutlineMessage(data.outline_id, data.content, imageUrls, outlinePayload)
          streamingText.value = ''
        },
        onDone() {},
        onError(msg) {
          messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
        },
      },
      abortController.signal,
    )
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
    }
  } finally {
    isStreaming.value = false
    abortController = null
  }
}

// ========== 流式修改大纲 ==========
async function streamModifyOutline(text) {
  if (!currentResult.value) {
    isStreaming.value = true
    streamingText.value = ''
    abortController = new AbortController()

    try {
      await streamPptSSE(
        '/api/v1/ppt/stream/outline',
        {
          session_id: currentSessionId.value,
          user_input: text,
          knowledge_library_ids: selectedKnowledgeIds.value,
          template_id: selectedTemplateId.value,
        },
        {
          onChunk(content) { streamingText.value += content },
          onOutlineReady(data) {
            const imageUrls = normalizeImageUrls(data.image_urls)
            const outlinePayload = data.outline_payload || null
            currentOutline.value = {
              id: data.outline_id,
              content: data.content,
              image_urls: imageUrls,
              outline_payload: outlinePayload,
              is_current: true,
            }
            appendOutlineMessage(data.outline_id, data.content, imageUrls, outlinePayload)
            streamingText.value = ''
          },
          onDone() {},
          onError(msg) {
            messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
          },
        },
        abortController.signal,
      )
    } catch (e) {
      if (e.name !== 'AbortError') {
        messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
      }
    } finally {
      isStreaming.value = false
      abortController = null
    }
    return
  }

  await streamModifyPpt(text)
}

// ========== 审批大纲 -> 生成PPT ==========
async function handleApproveOutline(payload) {
  if (!currentOutline.value) return

  try {
    await approveOutline(
      currentOutline.value.id,
      payload?.content || null,
      payload?.image_urls || null,
      payload?.outline_payload || currentOutline.value.outline_payload || null,
    )

    if (!selectedTemplateId.value) {
      showTemplateSelector.value = true
      return
    }

    await streamGeneratePpt()
  } catch (e) {
    console.error('审批失败:', e)
  }
}

function handleTemplateSelected(t) {
  selectedTemplateId.value = t.id
  showTemplateSelector.value = false
  if (currentOutline.value) {
    streamGeneratePpt()
  }
}

// ========== 流式生成PPT ==========
async function streamGeneratePpt() {
  isGeneratingPpt.value = true
  stage.value = 'preview'
  sidebarCollapsed.value = true
  abortController = new AbortController()

  try {
    await streamPptSSE(
      '/api/v1/ppt/stream/generate',
      {
        session_id: currentSessionId.value,
        outline_id: currentOutline.value.id,
        template_id: selectedTemplateId.value,
      },
      {
        onProgress(data) {
          genCurrentPage.value = data.current || 0
          genTotalPages.value = data.total || 0
        },
        onResultReady(data) {
          currentResult.value = normalizeResultRecord(data)
          genTotalPages.value = data.total_pages || 0
          genCurrentPage.value = data.total_pages || 0
          isGeneratingPpt.value = false
          void applyPptxProperty(data.pptx_property || '')
          messages.value.push({
            role: 'assistant', message_type: 'ppt_result',
            content: `PPT已生成完成，共${data.total_pages}页`,
            pptTitle: currentSession.value?.title || 'PPT文件',
            created_at: new Date().toISOString(),
          })
        },
        onDone() { isGeneratingPpt.value = false },
        onError(msg) {
          isGeneratingPpt.value = false
          messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
        },
      },
      abortController.signal,
    )
  } catch (e) {
    isGeneratingPpt.value = false
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
    }
  } finally {
    abortController = null
  }
}

// ========== 继续修改 ==========
async function handleModifySend() {
  const text = userInput.value.trim()
  if (!text || isStreaming.value) return
  messages.value.push({ role: 'user', message_type: 'text', content: text })
  userInput.value = ''
  await streamModifyPpt(text)
}

async function streamModifyPpt(text) {
  if (!currentResult.value?.result_id) return
  isStreaming.value = true

  try {
    const dirtySlideIndex = activeSlideIndex.value
    const data = await modifyPptResult(
      currentResult.value.result_id,
      text,
      activeSlideIndex.value,
      pptxProperty.value,
    )
    await applyPptxProperty(data.pptx_property || '', {
      keepActiveSlide: true,
      dirtySlideIndex,
      forceThumbnailRefresh: false,
    })
    genTotalPages.value = data.total_pages || slides.value.length
    genCurrentPage.value = Math.min(activeSlideIndex.value + 1, genTotalPages.value)
    messages.value.push({
      role: 'assistant',
      message_type: 'text',
      content: data.message || `已更新第 ${activeSlideIndex.value + 1} 页。`,
      created_at: new Date().toISOString(),
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
  } finally {
    isStreaming.value = false
  }
}

// ========== 下载 ==========
async function handleDownload() {
  let resultId = currentResult.value?.result_id
  if (currentSessionId.value) {
    try {
      const latestSessionDetail = await getSessionDetail(currentSessionId.value)
      const latestResult = latestSessionDetail.results?.find(r => r.is_current)
      if (latestResult?.id && latestResult.id !== currentResult.value?.result_id) {
        currentResult.value = normalizeResultRecord(latestResult)
        await loadResultDetail(latestResult.id)
      }
      resultId = latestResult?.id || resultId
    } catch (error) {
      console.warn('刷新当前PPT结果失败，继续使用页面已有结果:', error)
    }
  }
  if (!resultId) return
  const pendingWindow = openPendingPptDownloadWindow()
  try {
    const data = await downloadResult(resultId)
    const fileUrl = getPptDownloadUrl(data?.file_url, currentResult.value?.file_url)
    if (fileUrl) {
      currentResult.value = {
        ...currentResult.value,
        result_id: resultId,
        id: resultId,
        file_url: fileUrl,
      }
      triggerPptDownload(fileUrl, { presetWindow: pendingWindow })
    } else {
      pendingWindow?.close?.()
    }
  } catch (e) {
    const fallbackUrl = getPptDownloadUrl('', currentResult.value?.file_url)
    if (fallbackUrl) {
      triggerPptDownload(fallbackUrl, { presetWindow: pendingWindow })
      return
    }
    pendingWindow?.close?.()
    console.error('下载失败:', e)
    messages.value.push({
      role: 'assistant',
      message_type: 'error',
      content: e?.message || '下载 PPT 失败，请稍后重试',
    })
  }
}

// ========== 加载结果详情 ==========
async function loadResultDetail(resultId) {
  try {
    const detail = await getResultDetail(resultId)
    currentResult.value = normalizeResultRecord(detail)
    await applyPptxProperty(detail.edited_pptx_property || detail.source_pptx_property || '')
    genTotalPages.value = detail.total_pages || 0
    genCurrentPage.value = detail.total_pages || 0
  } catch (e) {
    console.error('加载结果失败:', e)
  }
}

// ========== 进入预览 ==========
function enterPreview() {
  stage.value = 'preview'
  sidebarCollapsed.value = true
}

// ========== Stage 3 拖拽：对话/预览分割 ==========
function startResizeMain(e) {
  isResizingMain.value = true
  resizeStartX = e.clientX
  resizeStartVal = chatPanelWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onResizeMain)
  document.addEventListener('mouseup', stopResizeMain)
}

function onResizeMain(e) {
  const container = document.querySelector('.preview-layout')
  if (!container) return
  const cw = container.offsetWidth
  const delta = e.clientX - resizeStartX
  const pct = resizeStartVal + (delta / cw) * 100
  chatPanelWidth.value = Math.max(25, Math.min(65, pct))
}

function stopResizeMain() {
  isResizingMain.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResizeMain)
  document.removeEventListener('mouseup', stopResizeMain)
}

// ========== Stage 3 拖拽：缩略图宽度 ==========
function startResizeThumb(e) {
  isResizingThumb.value = true
  resizeStartX = e.clientX
  resizeStartVal = thumbWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onResizeThumb)
  document.addEventListener('mouseup', stopResizeThumb)
}

function onResizeThumb(e) {
  const delta = e.clientX - resizeStartX
  thumbWidth.value = Math.max(100, Math.min(280, resizeStartVal + delta))
}

function stopResizeThumb() {
  isResizingThumb.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResizeThumb)
  document.removeEventListener('mouseup', stopResizeThumb)
}

// ========== 工具按钮 ==========
function handleOpenFileUpload() {
  fileInputRef.value?.click()
}

function handleOpenImageUpload() {
  imageInputRef.value?.click()
}

function handleFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  // TODO: upload to backend
  userInput.value += `[已上传文件: ${file.name}] `
  e.target.value = ''
}

function handleImageSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  userInput.value += `[已上传图片: ${file.name}] `
  e.target.value = ''
}

function handleOpenVoice() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('当前浏览器不支持语音识别')
    return
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  const recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = false

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript
    userInput.value += transcript
    isRecording.value = false
  }
  recognition.onerror = () => { isRecording.value = false }
  recognition.onend = () => { isRecording.value = false }

  isRecording.value = true
  recognition.start()
}

function handleOpenKnowledge(e) {
  knowledgeTriggerEl.value = e?.target || null
  showKnowledgeModal.value = true
}

async function renderExportSlides() {
  if (!pptxDoc.value?.pages?.length) return

  await nextTick()

  for (let index = 0; index < slides.value.length; index += 1) {
    const canvasEl = exportCanvasRefs[index]
    if (!canvasEl) continue

    let painter = exportPainters.get(index)
    if (!painter) {
      painter = new Ppt2Canvas(canvasEl, 'anonymous')
      exportPainters.set(index, painter)
    }

    canvasEl.width = pptxDoc.value.width * 2
    canvasEl.height = pptxDoc.value.height * 2
    canvasEl.style.width = `${pptxDoc.value.width}px`
    canvasEl.style.height = `${pptxDoc.value.height}px`

    await painter.drawPptx(pptxDoc.value, index)
  }

  await waitForPdfRender()
}

function handleFullscreen() {
  isPreviewFullscreen.value = !isPreviewFullscreen.value
  syncFullscreenBodyState()
}

async function handleExportPdf() {
  return handleExportPdfDirect()
}

async function handleExportPdfDirect() {
  if (!pptxDoc.value?.pages?.length || isExportingPdf.value) return

  try {
    isExportingPdf.value = true
    await renderExportSlides()

    const { jsPDF } = await import('jspdf')
    const filename = `${currentSession.value?.title || 'PPT棰勮'}.pdf`
    const canvases = exportCanvasRefs
      .slice(0, slides.value.length)
      .filter(canvas => canvas && canvas.width > 0 && canvas.height > 0)

    if (!canvases.length) {
      throw new Error('PDF 瀵煎嚭鐢荤布鏈噯澶囧畬鎴?')
    }

    const pdf = new jsPDF({
      unit: 'pt',
      format: 'a4',
      orientation: 'landscape',
      compress: true,
    })
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const margin = 24
    const contentWidth = pageWidth - margin * 2
    const contentHeight = pageHeight - margin * 2

    canvases.forEach((canvas, index) => {
      if (index > 0) {
        pdf.addPage('a4', 'landscape')
      }

      const canvasRatio = canvas.width / canvas.height
      let renderWidth = contentWidth
      let renderHeight = renderWidth / canvasRatio

      if (renderHeight > contentHeight) {
        renderHeight = contentHeight
        renderWidth = renderHeight * canvasRatio
      }

      const x = (pageWidth - renderWidth) / 2
      const y = (pageHeight - renderHeight) / 2

      pdf.setFillColor(255, 255, 255)
      pdf.rect(0, 0, pageWidth, pageHeight, 'F')
      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', x, y, renderWidth, renderHeight, undefined, 'FAST')
    })

    pdf.save(filename)
  } catch (error) {
    console.error('PDF export failed:', error)
    messages.value.push({
      role: 'assistant',
      message_type: 'error',
      content: error?.message || '瀵煎嚭 PDF 澶辫触锛岃绋嶅悗閲嶈瘯',
    })
  } finally {
    isExportingPdf.value = false
  }
}

async function waitForPdfRender() {
  await nextTick()
  await new Promise(resolve => requestAnimationFrame(() => resolve()))
  await new Promise(resolve => requestAnimationFrame(() => resolve()))
  await new Promise(resolve => setTimeout(resolve, 180))
}
</script>

<template>
  <div class="ppt-page">
    <!-- 隐藏的文件输入 -->
    <input ref="fileInputRef" type="file" style="display:none" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt" @change="handleFileSelected" />
    <input ref="imageInputRef" type="file" style="display:none" accept="image/*" @change="handleImageSelected" />

    <!-- 侧边栏 -->
    <PptSidebar
      :sessions="sessions"
      :active-id="currentSessionId"
      :collapsed="sidebarCollapsed"
      @new-session="handleNewSession"
      @select="handleSelectSession"
      @delete="handleDeleteSession"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <!-- 主区域 -->
    <div class="ppt-main">
      <!-- Stage 1: 欢迎页 -->
      <template v-if="stage === 'welcome'">
        <WelcomePanel
          v-model="userInput"
          :selected-template-id="selectedTemplateId"
          @send="handleSend"
          @update:template-id="selectedTemplateId = $event"
          @select-template="handleTemplateSelected"
          @open-file-upload="handleOpenFileUpload"
          @open-image-upload="handleOpenImageUpload"
          @open-voice="handleOpenVoice"
          @open-knowledge="handleOpenKnowledge"
        />
      </template>

      <!-- Stage 2: 对话+大纲 -->
      <template v-else-if="stage === 'chat'">
        <div class="chat-layout">
          <div class="chat-left">
            <ChatPanel
              :messages="messages"
              :streaming-text="streamingText"
              :is-streaming="isStreaming"
              :active-outline-id="currentOutline?.id || null"
              :can-approve-outline="!currentResult"
              @preview="enterPreview"
              @outline-approve="handleApproveOutline"
              @outline-edit="handleOutlineEdit"
              @outline-regenerate="streamGenerateOutline(currentOutline.content)"
            />

            <ChatInput
              v-model="userInput"
              :disabled="isStreaming"
              :loading="isStreaming"
              :placeholder="currentOutline ? '继续对话或修改大纲...' : '描述你的PPT主题...'"
              @send="handleSend"
              @open-file-upload="handleOpenFileUpload"
              @open-image-upload="handleOpenImageUpload"
              @open-voice="handleOpenVoice"
              @open-knowledge="handleOpenKnowledge"
            />
          </div>

          <div v-if="showTemplateSelector" class="chat-right">
            <TemplateSelector
              v-model="selectedTemplateId"
              @select="handleTemplateSelected"
              @close="showTemplateSelector = false"
            />
          </div>
        </div>
      </template>

      <!-- Stage 3: 预览+编辑 (原型布局: 左=对话 | 右=预览) -->
      <template v-else-if="stage === 'preview'">
        <div class="preview-layout" :class="{ 'preview-layout-fullscreen': isPreviewFullscreen }">
          <!-- 左侧对话面板 -->
          <div class="chat-panel-wrap" :style="{ width: chatPanelWidth + '%' }">
            <ChatPanel
              :messages="messages"
              :streaming-text="streamingText"
              :is-streaming="isStreaming"
              :active-outline-id="currentOutline?.id || null"
              :can-approve-outline="!currentResult"
              @outline-approve="handleApproveOutline"
              @outline-edit="handleOutlineEdit"
              @outline-regenerate="streamGenerateOutline(currentOutline.content)"
            />

            <ChatInput
              v-model="userInput"
              :disabled="isStreaming"
              :loading="isStreaming"
              placeholder="告诉我你想修改什么..."
              @send="handleModifySend"
              @open-file-upload="handleOpenFileUpload"
              @open-image-upload="handleOpenImageUpload"
              @open-voice="handleOpenVoice"
              @open-knowledge="handleOpenKnowledge"
            />
          </div>

          <!-- 拖拽分割线 -->
          <div
            class="resize-handle"
            :class="{ dragging: isResizingMain }"
            @mousedown.prevent="startResizeMain"
          />

          <!-- 右侧预览面板 -->
          <div class="preview-panel" :style="{ width: isPreviewFullscreen ? '100%' : (100 - chatPanelWidth) + '%' }">
            <div class="preview-toolbar">
              <div class="toolbar-title">{{ currentSession?.title || 'PPT预览' }}.pptx</div>
              <div class="toolbar-actions">
                <button class="toolbar-btn" @click="handleFullscreen">{{ isPreviewFullscreen ? '退出全屏' : '全屏预览' }}</button>
                <button class="toolbar-btn" @click="handleDownload">下载PPT</button>
                <button class="toolbar-btn" :disabled="isExportingPdf" @click="handleExportPdf">
                  {{ isExportingPdf ? '导出中...' : '导出PDF' }}
                </button>
              </div>
            </div>

            <div class="preview-content">
              <div class="preview-thumbnails" :style="{ width: thumbWidth + 'px' }">
                <PptThumbnailList
                  :slides="slides"
                  :active-index="activeSlideIndex"
                  :pptx-doc="pptxDoc"
                  :dirty-slide-index="thumbnailDirtySlideIndex"
                  :render-nonce="thumbnailRenderNonce"
                  @select="activeSlideIndex = $event"
                />
              </div>
              <div
                class="thumb-resize-handle"
                :class="{ dragging: isResizingThumb }"
                @mousedown.prevent="startResizeThumb"
              />

              <div class="preview-workspace">
                <div class="preview-canvas-area">
                  <PptCanvas
                    :pptx-doc="pptxDoc"
                    :slide-index="activeSlideIndex"
                    :generating="isGeneratingPpt"
                    :current-page="genCurrentPage"
                    :total-pages="genTotalPages"
                    @change="persistEditedPpt"
                  />
                </div>

                <div class="preview-footer">
                  <div class="footer-section">
                    <div class="footer-label">演讲备注</div>
                    <div class="footer-content">{{ currentSpeakerNotes || '暂无演讲备注' }}</div>
                  </div>
                  <div class="footer-section">
                    <div class="footer-label">知识来源</div>
                    <div class="footer-content">
                      <span v-if="!currentResult?.sources?.length" class="source-item">暂无来源</span>
                      <span v-for="(src, i) in (currentResult?.sources || [])" :key="i" class="source-item">{{ src }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 知识库弹窗 -->
    <KnowledgeLibraryModal
      v-if="showKnowledgeModal"
      v-model="selectedKnowledgeIds"
      :trigger-el="knowledgeTriggerEl"
      @close="showKnowledgeModal = false"
    />

    <div ref="exportContainerRef" class="pdf-export-layer" :style="pdfExportLayerStyle">
      <div
        v-for="(_, index) in slides"
        :key="`pdf-slide-${index}`"
        class="pdf-export-slide"
      >
        <div class="pdf-export-slide-inner">
          <canvas :ref="(el) => setExportCanvasRef(el, index)" class="pdf-export-canvas" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ppt-page {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #f5f5f5;
  overflow: hidden;
}
.ppt-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ========== Stage 2: Chat layout ========== */
.chat-layout {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}
.chat-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.chat-right {
  width: 360px;
  border-left: 1px solid #e5e5e5;
  background: #fff;
  flex-shrink: 0;
  min-height: 0;
}

/* ========== Stage 3: Preview layout ========== */
.preview-layout {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}
.preview-layout-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: #f5f5f5;
}
.preview-layout-fullscreen .chat-panel-wrap,
.preview-layout-fullscreen .resize-handle {
  display: none;
}
.preview-layout-fullscreen .preview-panel {
  width: 100% !important;
  height: 100%;
}
.chat-panel-wrap {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e5e5;
  background: #fafafa;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

/* Resize handle (chat/preview split) */
.resize-handle {
  width: 4px;
  background: transparent;
  cursor: col-resize;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}
.resize-handle:hover,
.resize-handle.dragging {
  background: #3a61ea;
}

/* Preview panel */
.preview-panel {
  display: flex;
  flex-direction: column;
  background: #fff;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.preview-toolbar {
  padding: 16px 24px;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.toolbar-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
}
.toolbar-actions {
  display: flex;
  gap: 12px;
}
.toolbar-btn {
  padding: 8px 16px;
  border: 1px solid #e5e5e5;
  background: #fff;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.toolbar-btn:hover {
  background: #f9f9f9;
}
.toolbar-btn:disabled {
  cursor: wait;
  color: #98a2b3;
  background: #f8fafc;
}

/* Preview content area */
.preview-content {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}
.preview-thumbnails {
  padding: 16px 12px;
  background: #f9f9f9;
  border-right: 1px solid #e5e5e5;
  overflow-y: auto;
  flex-shrink: 0;
  min-height: 0;
}

/* Thumb resize handle */
.thumb-resize-handle {
  width: 4px;
  flex-shrink: 0;
  background: #e8e8e8;
  cursor: col-resize;
  transition: background 0.2s;
}
.thumb-resize-handle:hover,
.thumb-resize-handle.dragging {
  background: #3a61ea;
}

/* Preview workspace */
.preview-workspace {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.preview-canvas-area {
  flex: 1;
  padding: 24px 24px 0;
  display: flex;
  align-items: stretch;
  justify-content: stretch;
  background: #f5f5f5;
  min-height: 0;
  overflow: hidden;
}

/* Preview footer */
.preview-footer {
  padding: 20px 24px;
  border-top: 1px solid #e5e5e5;
  background: #fff;
  flex-shrink: 0;
}
.footer-section {
  margin-bottom: 16px;
}
.footer-section:last-child {
  margin-bottom: 0;
}
.footer-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
  font-weight: 500;
}
.footer-content {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}
.source-item {
  display: inline-block;
  padding: 4px 12px;
  background: #f0f0f0;
  border-radius: 4px;
  margin-right: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}
.pdf-export-layer {
  position: fixed;
  left: -99999px;
  top: 0;
  width: 1120px;
  pointer-events: none;
  background: #fff;
}
.pdf-export-slide {
  break-after: page;
  page-break-after: always;
  padding: 0;
}
.pdf-export-slide:last-child {
  break-after: auto;
  page-break-after: auto;
}
.pdf-export-slide-inner {
  width: 1120px;
  min-height: 630px;
  padding: 16px;
  background: #fff;
  box-sizing: border-box;
}
.pdf-export-canvas {
  width: 100%;
  height: auto;
  display: block;
  background: #fff;
}

@media (max-width: 900px) {
  .preview-layout { flex-direction: column; }
  .chat-panel-wrap { width: 100% !important; height: 40%; }
  .preview-panel { width: 100% !important; }
  .preview-thumbnails { width: 100% !important; height: 80px; flex-direction: row; overflow-x: auto; }
}
</style>
