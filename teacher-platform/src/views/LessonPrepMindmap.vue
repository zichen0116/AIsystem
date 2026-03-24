<script setup>
import { ref, watch, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
import linkFileImg from '../assets/链接文件.png'
import voiceImg from '../assets/语音.png'
import aiAnimationFlow from '../assets/ai animation Flow 1.json'
import { useVoiceInput } from '../composables/useVoiceInput'

import { toPng } from 'html-to-image'
import MarkmapRenderer from '../components/MarkmapRenderer.vue'
import { initWasm, Resvg } from '@resvg/resvg-wasm'
import resvgWasmUrl from '@resvg/resvg-wasm/index_bg.wasm?url'

const promptText = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(promptText)
const uploading = ref(false)
const generating = ref(false)
const exporting = ref(false)
const errorMsg = ref('')
const uploadedFilename = ref('')
const uploadPreview = ref('')
const chatMessagesRef = ref(null)

const chatMessages = ref([])
const fullscreenMessageId = ref(null)
const markmapRefs = ref({})
const previewFlowRef = ref(null)

/** 左侧预览区始终展示「最后一条」思维导图助手消息 */
const activeMindmapMessage = computed(() => {
  for (let i = chatMessages.value.length - 1; i >= 0; i--) {
    const m = chatMessages.value[i]
    if (m.role === 'assistant' && m.type === 'mindmap') return m
  }
  return null
})

const isEditingMindmap = ref(false)
const dirtyMindmap = ref(false)
const inlineEditor = ref({
  visible: false,
  oldText: '',
  value: '',
  top: 0,
  left: 0,
  width: 160
})

function newConversation() {
  if (
    chatMessages.value.length &&
    !confirm('确定开始新对话？当前对话与左侧预览将被清空。')
  ) {
    return
  }
  resetState()
}

let resvgInitPromise = null
async function ensureResvgReady() {
  if (!resvgInitPromise) {
    // 明确指定 wasm url，避免打包器找不到 wasm
    resvgInitPromise = initWasm(fetch(resvgWasmUrl))
  }
  await resvgInitPromise
}

function waitFrames(n = 2) {
  return new Promise((resolve) => {
    const step = (k) => {
      if (k <= 0) resolve()
      else requestAnimationFrame(() => step(k - 1))
    }
    step(n)
  })
}

async function toPngFullSvg(el, svg, g) {
  // 临时把“真实 SVG”改成全量 viewBox + 尺寸，再截图，确保文字/样式与页面一致且不裁剪
  const prevElWidth = el.style.width
  const prevElHeight = el.style.height
  const prevSvgWidth = svg.getAttribute('width')
  const prevSvgHeight = svg.getAttribute('height')
  const prevViewBox = svg.getAttribute('viewBox')
  const prevGTransform = g.getAttribute('transform')

  try {
    g.setAttribute('transform', '')
    const bbox = g.getBBox()
    const pad = 24
    const width = Math.ceil(bbox.width + pad * 2)
    const height = Math.ceil(bbox.height + pad * 2)

    svg.setAttribute('width', String(width))
    svg.setAttribute('height', String(height))
    svg.setAttribute(
      'viewBox',
      `${bbox.x - pad} ${bbox.y - pad} ${bbox.width + pad * 2} ${bbox.height + pad * 2}`
    )
    el.style.width = `${width}px`
    el.style.height = `${height}px`

    await waitFrames(1)
    return await toPng(el, {
      cacheBust: true,
      pixelRatio: 2,
      backgroundColor: '#ffffff'
    })
  } finally {
    // restore
    if (prevGTransform == null) g.removeAttribute('transform')
    else g.setAttribute('transform', prevGTransform)
    if (prevSvgWidth == null) svg.removeAttribute('width')
    else svg.setAttribute('width', prevSvgWidth)
    if (prevSvgHeight == null) svg.removeAttribute('height')
    else svg.setAttribute('height', prevSvgHeight)
    if (prevViewBox == null) svg.removeAttribute('viewBox')
    else svg.setAttribute('viewBox', prevViewBox)
    el.style.width = prevElWidth
    el.style.height = prevElHeight
  }
}

const props = defineProps({
  resetKey: {
    type: Number,
    default: 0
  }
})

function resetState() {
  promptText.value = ''
  errorMsg.value = ''
  uploadedFilename.value = ''
  uploadPreview.value = ''
  chatMessages.value = []
  isEditingMindmap.value = false
  dirtyMindmap.value = false
  inlineEditor.value = { visible: false, oldText: '', value: '', top: 0, left: 0, width: 160 }
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)

watch(
  () => activeMindmapMessage.value?.id,
  () => {
    // 切换到另一张导图（或清空）时退出编辑态
    isEditingMindmap.value = false
    dirtyMindmap.value = false
    inlineEditor.value.visible = false
  }
)

const finalSource = computed(() => {
  return uploadPreview.value ? `【上传材料提取文本】\n${uploadPreview.value}` : ''
})

function startEditMindmap() {
  const m = activeMindmapMessage.value
  if (!m || m.loading) return
  isEditingMindmap.value = true
  dirtyMindmap.value = false
}

function cancelEditMindmap() {
  isEditingMindmap.value = false
  dirtyMindmap.value = false
  inlineEditor.value.visible = false
}

async function saveEditMindmap() {
  const m = activeMindmapMessage.value
  if (!m || m.loading) return
  isEditingMindmap.value = false
  inlineEditor.value.visible = false
  await nextTick()
  try {
    handleFitFor(m.id)
  } catch {
    // ignore
  }
}

function getLabelElementFromEventTarget(t) {
  if (!t || !t.closest) return null

  // 1) 常见 SVG 文字：<text>/<tspan>
  const textEl = t.closest('text')
  if (textEl) return textEl

  // 2) 部分 markmap 渲染会落在 foreignObject 的 HTML 容器里
  const htmlLabelEl = t.closest('foreignObject, .markmap-foreign, .markmap-node')
  if (htmlLabelEl) {
    const candidate =
      htmlLabelEl.querySelector?.('text') ||
      htmlLabelEl.querySelector?.('div, span, p') ||
      htmlLabelEl
    return candidate
  }

  return null
}

function getLabelText(el) {
  return (el?.textContent || '').replace(/\s+/g, ' ').trim()
}

function getLabelRectOrFallback(el, flowRect, event) {
  const rect = el?.getBoundingClientRect?.()
  if (rect && rect.width >= 1 && rect.height >= 1) return rect

  // 兜底：若拿不到有效 rect，就按点击坐标放置输入框
  const x = Number(event?.clientX || 0)
  const y = Number(event?.clientY || 0)
  return {
    left: x || flowRect.left + 24,
    top: y || flowRect.top + 24,
    width: 140,
    height: 24
  }
}

function applyLabelChangeInMarkdown(markdown, oldText, newText) {
  const md = markdown || ''
  const oldT = (oldText || '').trim()
  const newT = (newText || '').trim()
  if (!oldT || !newT || oldT === newT) return md

  // 优先替换“列表项行”里的节点文本（- oldText / * oldText / + oldText）
  const escaped = oldT.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const listItemRe = new RegExp(`^(\\s*[-*+]\\s+)${escaped}(\\s*)$`, 'm')
  if (listItemRe.test(md)) {
    return md.replace(listItemRe, `$1${newT}$2`)
  }

  // 其次替换“标题行”里的文本（# oldText）
  const headingRe = new RegExp(`^(\\s*#{1,6}\\s+)${escaped}(\\s*)$`, 'm')
  if (headingRe.test(md)) {
    return md.replace(headingRe, `$1${newT}$2`)
  }

  // 兜底：只替换第一次出现，避免误伤过大
  const idx = md.indexOf(oldT)
  if (idx >= 0) {
    return md.slice(0, idx) + newT + md.slice(idx + oldT.length)
  }
  return md
}

function handleMindmapClick(e) {
  if (!isEditingMindmap.value) return
  const m = activeMindmapMessage.value
  if (!m || m.loading) return

  const labelEl = getLabelElementFromEventTarget(e?.target)
  if (!labelEl) return

  const oldText = getLabelText(labelEl)
  if (!oldText) return

  const flowEl = previewFlowRef.value
  if (!flowEl) return

  const flowRect = flowEl.getBoundingClientRect?.()
  if (!flowRect) return
  const textRect = getLabelRectOrFallback(labelEl, flowRect, e)

  const top = Math.max(8, textRect.top - flowRect.top - 30)
  const left = Math.max(8, Math.min(textRect.left - flowRect.left, flowRect.width - 180))
  const width = Math.max(140, Math.min(320, (textRect.width || 140) + 56))

  inlineEditor.value = {
    visible: true,
    oldText,
    value: oldText,
    top,
    left,
    width
  }

  nextTick(() => {
    try {
      const input = flowEl.querySelector?.('.mindmap-inline-input')
      input?.focus?.()
      input?.select?.()
    } catch {
      // ignore
    }
  })
}

function commitInlineEdit() {
  const m = activeMindmapMessage.value
  if (!m || m.loading) return
  if (!inlineEditor.value.visible) return
  const oldText = inlineEditor.value.oldText
  const newText = inlineEditor.value.value
  const updated = applyLabelChangeInMarkdown(m.markdown || '', oldText, newText)
  if (updated !== (m.markdown || '')) {
    m.markdown = updated
    dirtyMindmap.value = true
  }
  inlineEditor.value.visible = false
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
    const resp = await fetch('/api/v1/html/upload', { method: 'POST', body: formData })
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.detail || '上传失败')
    }
    const data = await resp.json()
    uploadedFilename.value = data.filename || file.name
    uploadPreview.value = data.preview || ''
  } catch (e) {
    console.error(e)
    errorMsg.value = e.message || '上传失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function handleGenerate() {
  const prompt = promptText.value.trim()
  if (!prompt) {
    errorMsg.value = '请先输入要生成思维导图的内容'
    return
  }
  // 点击生成后清空输入框（避免内容残留）
  promptText.value = ''
  errorMsg.value = ''

  generating.value = true
  chatMessages.value.push({
    id: `m_${Date.now()}_${Math.random().toString(16).slice(2)}`,
    role: 'user',
    type: 'text',
    content: prompt
  })
  const assistantMsg = {
    id: `m_${Date.now() + 1}_${Math.random().toString(16).slice(2)}`,
    role: 'assistant',
    type: 'mindmap',
    title: '',
    description: '',
    loading: true,
    markdown: ''
  }
  chatMessages.value.push(assistantMsg)
  await nextTick()
  if (chatMessagesRef.value) chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  try {
    const payload = {
      layout: 'center',
      prompt,
      source: finalSource.value || null
    }
    const resp = await fetch('/api/v1/mindmap/generate_markdown', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      const detail =
        typeof data?.detail === 'string'
          ? data.detail
          : data?.detail
            ? JSON.stringify(data.detail)
            : '生成失败'
      throw new Error(detail)
    }
    const data = await resp.json()
    const md = typeof data?.markdown === 'string' ? data.markdown : ''
    if (!md.trim()) throw new Error('未生成 Markdown 内容')
    assistantMsg.title = '思维导图'
    assistantMsg.description = '已为你生成思维导图，支持导出图片、缩放与适配视图。'
    assistantMsg.loading = false
    assistantMsg.markdown = md
    await nextTick()
    if (chatMessagesRef.value) chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  } catch (e) {
    console.error(e)
    const msg =
      typeof e?.message === 'string'
        ? e.message
        : typeof e === 'string'
          ? e
          : e
            ? JSON.stringify(e)
            : ''
    errorMsg.value = msg || '生成失败，请稍后重试'
    assistantMsg.type = 'text'
    assistantMsg.content = errorMsg.value
    assistantMsg.loading = false
  } finally {
    generating.value = false
  }
}

async function handleExportPng(messageId) {
  if (exporting.value) return
  exporting.value = true
  const el = document.querySelector(`[data-mindmap-export=\"${messageId}\"]`)
  if (!el) {
    errorMsg.value = '未找到思维导图元素'
    exporting.value = false
    return
  }
  const markmap = getMarkmap(messageId)
  const prevViewportTransform = (() => {
    try {
      return markmap?.getTransform?.() ?? null
    } catch {
      return null
    }
  })()
  try {
    // 无论导出走哪条路径，都先适配到“刚好都能看见”
    try {
      markmap?.fit?.()
      await nextTick()
      await waitFrames(2)
    } catch {
      // ignore
    }

    const svg = el.querySelector('svg')
    const g = svg?.querySelector('g')

    // Markmap 优先走“真实 SVG 全量截图导出”（文字/样式最稳，也不会被当前视口裁剪）
    if (svg && g) {
      try {
        const dataUrl = await toPngFullSvg(el, svg, g)
        const a = document.createElement('a')
        a.href = dataUrl
        a.download = `mindmap_${Date.now()}.png`
        a.click()
        return
      } catch (e) {
        console.warn('真实 SVG 全量截图导出失败，尝试 resvg 导出:', e)
      }
    }

    // 兜底：截图导出（仍可能只导出可视区域）
    const dataUrl = await toPng(el, {
      cacheBust: true,
      pixelRatio: 2,
      backgroundColor: '#ffffff'
    })
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = `mindmap_${Date.now()}.png`
    a.click()
  } catch (e) {
    console.error('导出失败:', e)
    errorMsg.value = '导出 PNG 失败，请稍后重试'
  } finally {
    // 导出完成后恢复用户视图（避免导出导致画布跳回“适配”状态）
    try {
      markmap?.setTransform?.(prevViewportTransform)
    } catch {
      // ignore
    }
    exporting.value = false
  }
}

function handleZoomIn() {
  // 兼容旧调用：如果模板未传 messageId，则不处理
}

function handleZoomOut() {
  // 兼容旧调用：如果模板未传 messageId，则不处理
}

function handleFitView() {
  // 兼容旧调用：如果模板未传 messageId，则不处理
}

function handleResetViewport() {
  // Markmap 没有“重置位置”，使用 fit 代替（在新按钮里会传 messageId）
}

function setMarkmapRef(messageId, el) {
  if (!messageId) return
  if (el) markmapRefs.value[messageId] = el
  else delete markmapRefs.value[messageId]
}

function getMarkmap(messageId) {
  return markmapRefs.value[messageId] || null
}

function handleZoomInFor(messageId) {
  try {
    getMarkmap(messageId)?.zoomIn?.()
  } catch {}
}

function handleZoomOutFor(messageId) {
  try {
    getMarkmap(messageId)?.zoomOut?.()
  } catch {}
}

function handleFitFor(messageId) {
  try {
    getMarkmap(messageId)?.fit?.()
  } catch {}
}

async function handleFullscreen(messageId) {
  const container = document.querySelector(`[data-mindmap-container=\"${messageId}\"]`)
  if (!container) return
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await container.requestFullscreen()
    }
  } catch (e) {
    console.error(e)
    errorMsg.value = '全屏失败，请检查浏览器权限或重试'
  }
}

async function handleExitFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
  } catch (e) {
    console.error(e)
    errorMsg.value = '退出全屏失败，请重试'
  }
}

function onFullscreenChange() {
  const el = document.fullscreenElement
  if (el && el.getAttribute) {
    const id = el.getAttribute('data-mindmap-container')
    fullscreenMessageId.value = id || null
  } else {
    fullscreenMessageId.value = null
  }

  // 触发尺寸更新，并自动适配视图
  nextTick(() => {
    try {
      window.dispatchEvent(new Event('resize'))
    } catch {
      // ignore
    }
    // 有些浏览器/组件需要等一帧才能拿到正确尺寸
    setTimeout(() => {
      if (fullscreenMessageId.value) handleFitFor(fullscreenMessageId.value)
    }, 60)
  })
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})
</script>

<template>
  <div class="content-panel knowledge-panel mindmap-split-root">
    <div class="mindmap-workbench">
      <!-- 左侧：思维导图预览区 -->
      <div class="preview-column">
        <div class="preview-toolbar">
          <div class="toolbar-group">
            <span class="toolbar-label">预览</span>
          </div>
          <div class="toolbar-group toolbar-actions">
            <button
              v-if="!isEditingMindmap"
              type="button"
              class="tool-icon-btn"
              title="编辑"
              :disabled="!activeMindmapMessage || activeMindmapMessage.loading"
              @click="startEditMindmap"
            >
              ✎
            </button>
            <button
              v-else
              type="button"
              class="tool-icon-btn tool-icon-btn-primary"
              title="保存"
              @click="saveEditMindmap"
            >
              ✓
            </button>
            <button
              v-if="isEditingMindmap"
              type="button"
              class="tool-icon-btn"
              title="取消编辑"
              @click="cancelEditMindmap"
            >
              ↩
            </button>
            <span class="toolbar-divider" />
            <button
              type="button"
              class="tool-icon-btn"
              title="导出 PNG"
              :disabled="exporting || !activeMindmapMessage || activeMindmapMessage.loading"
              @click="activeMindmapMessage && handleExportPng(activeMindmapMessage.id)"
            >
              ⬇
            </button>
            <button
              type="button"
              class="tool-icon-btn"
              title="全屏"
              :disabled="!activeMindmapMessage || activeMindmapMessage.loading"
              @click="activeMindmapMessage && handleFullscreen(activeMindmapMessage.id)"
            >
              ⛶
            </button>
            <button
              v-if="activeMindmapMessage && fullscreenMessageId === activeMindmapMessage.id"
              type="button"
              class="tool-icon-btn"
              title="退出全屏"
              @click="handleExitFullscreen"
            >
              ✕
            </button>
            <span class="toolbar-divider" />
            <button
              type="button"
              class="tool-icon-btn"
              title="适配画布"
              :disabled="!activeMindmapMessage || activeMindmapMessage.loading"
              @click="activeMindmapMessage && handleFitFor(activeMindmapMessage.id)"
            >
              ⊡
            </button>
            <button
              type="button"
              class="tool-icon-btn"
              title="缩小"
              :disabled="!activeMindmapMessage || activeMindmapMessage.loading"
              @click="activeMindmapMessage && handleZoomOutFor(activeMindmapMessage.id)"
            >
              −
            </button>
            <button
              type="button"
              class="tool-icon-btn"
              title="放大"
              :disabled="!activeMindmapMessage || activeMindmapMessage.loading"
              @click="activeMindmapMessage && handleZoomInFor(activeMindmapMessage.id)"
            >
              +
            </button>
          </div>
        </div>

        <div class="preview-canvas-wrap">
          <div v-if="!activeMindmapMessage" class="preview-empty preview-empty-minimal">
            <p class="preview-empty-hint">发送后将在此展示思维导图</p>
          </div>

          <div
            v-else
            class="mindmap-container preview-mindmap-root"
            :data-mindmap-container="activeMindmapMessage.id"
          >
            <div v-if="activeMindmapMessage.loading" class="mindmap-loading preview-loading">
              正在生成思维导图，请稍候…
            </div>
            <div
              v-else
              class="flow-wrap flow-wrap-preview"
              ref="previewFlowRef"
              :data-mindmap-export="activeMindmapMessage.id"
              :class="{ editing: isEditingMindmap }"
              @click="handleMindmapClick"
            >
              <MarkmapRenderer
                :key="activeMindmapMessage.id"
                :ref="(el) => setMarkmapRef(activeMindmapMessage.id, el)"
                :markdown="activeMindmapMessage.markdown"
              />
              <div v-if="isEditingMindmap" class="mindmap-edit-hint">编辑中：点击节点文字进行修改</div>
              <div
                v-if="isEditingMindmap && inlineEditor.visible"
                class="mindmap-inline-editor"
                :style="{
                  top: inlineEditor.top + 'px',
                  left: inlineEditor.left + 'px',
                  width: inlineEditor.width + 'px'
                }"
                @click.stop
              >
                <input
                  v-model="inlineEditor.value"
                  class="mindmap-inline-input"
                  type="text"
                  @keydown.enter.prevent="commitInlineEdit"
                  @keydown.esc.prevent="inlineEditor.visible = false"
                  @blur="commitInlineEdit"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="preview-status-bar">
          <span class="status-left">思维导图</span>
          <span class="status-center">第 1 页</span>
          <span class="status-right">100%</span>
        </div>
      </div>

      <!-- 右侧：对话区 -->
      <div class="chat-column">
        <div class="chat-column-header">
          <div class="chat-column-title-block">
            <div class="chat-column-title">思维导图助手</div>
            <div class="chat-column-sub">用自然语言描述，AI 生成知识结构图</div>
          </div>
          <button type="button" class="new-chat-btn" title="新对话" @click="newConversation">
            ＋ 新对话
          </button>
        </div>

        <div ref="chatMessagesRef" class="chat-messages-split">
          <div v-if="!chatMessages.length" class="chat-welcome">
            <div class="chat-welcome-lottie">
              <LottiePlayer :animation-data="aiAnimationFlow" />
            </div>
            <p class="chat-welcome-title">开始创作</p>
            <p class="chat-welcome-desc">
              输入课程主题、章节要点或问题链，也可上传材料作为补充上下文。
            </p>
          </div>
          <div
            v-for="m in chatMessages"
            :key="m.id"
            class="chat-row-split"
            :class="m.role"
          >
            <template v-if="m.role === 'user'">
              <div class="chat-bubble-split user">
                <div class="chat-text">{{ m.content }}</div>
              </div>
            </template>
            <template v-else-if="m.type === 'mindmap'">
              <div class="chat-bubble-split assistant mindmap-hint">
                <template v-if="m.loading">
                  <span class="hint-dot" />正在生成思维导图…
                </template>
                <template v-else>
                  ✓ 已生成，请在<strong>左侧预览区</strong>查看、缩放与导出。
                </template>
              </div>
            </template>
            <template v-else>
              <div class="chat-bubble-split assistant error-bubble">
                <div class="chat-text">{{ m.content }}</div>
              </div>
            </template>
          </div>
        </div>

        <div class="chat-input-stack">
          <div class="knowledge-input-box chat-input-box">
            <textarea
              v-model="promptText"
              class="knowledge-textarea"
              placeholder="请描述您想创建的内容..."
              rows="3"
            />
            <div class="knowledge-input-footer">
              <div class="knowledge-footer-left">
                <button class="upload-btn" title="上传文件" :disabled="uploading" @click="selectFile">
                  <img :src="linkFileImg" class="upload-icon" alt="" />
                </button>
                <button
                  v-if="isSupported"
                  class="voice-btn"
                  :class="{ recording: isRecording }"
                  title="语音输入"
                  @click="toggleRecording"
                >
                  <img :src="voiceImg" class="voice-icon-img" alt="语音" />
                </button>
              </div>
              <button class="generate-btn primary-send" :disabled="generating" @click="handleGenerate">
                <span class="generate-icon">✨</span>
                <span>{{ generating ? '生成中...' : '发送' }}</span>
              </button>
            </div>
          </div>
          <p v-if="uploadedFilename" class="upload-hint-split">
            已上传：{{ uploadedFilename }}；提取文本长度：{{ uploadPreview.length }} 字
          </p>
          <p v-if="errorMsg" class="error-text-split">{{ errorMsg }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.content-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
  margin: 0;
  min-height: 0;
  overflow: hidden; /* 交给聊天区滚动，底部输入框 sticky */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge legacy */
}

.content-panel::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.knowledge-panel.mindmap-split-root {
  padding: 16px 20px 20px;
  background: transparent;
  height: 100%;
  min-height: 0;
}

.mindmap-workbench {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 16px;
  align-items: stretch;
}

/* ---------- 左侧预览 ---------- */
.preview-column {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  min-height: 520px;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-label {
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
  letter-spacing: 0.02em;
}

.toolbar-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tool-icon-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  color: #374151;
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.tool-icon-btn:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.tool-icon-btn-primary {
  background: #111827;
  border-color: #111827;
  color: #ffffff;
}

.tool-icon-btn-primary:hover:not(:disabled) {
  background: #1f2937;
  border-color: #1f2937;
  color: #ffffff;
}

.tool-icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.toolbar-divider {
  width: 1px;
  height: 22px;
  background: #d1d5db;
  margin: 0 4px;
}

.preview-canvas-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
  background-color: #fafafa;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.04) 1px, transparent 1px);
  background-size: 20px 20px;
}

.preview-empty-minimal {
  height: 100%;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  text-align: center;
}

.preview-empty-hint {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
  line-height: 1.5;
  max-width: 280px;
}

.preview-mindmap-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #ffffff;
}

.preview-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  color: #64748b;
}

.flow-wrap-preview {
  flex: 1;
  min-height: 0;
  height: auto !important;
  border: none;
  border-radius: 0;
  background: #ffffff;
  position: relative;
}

.flow-wrap-preview.editing {
  cursor: text;
}

.flow-wrap-preview.editing :deep(text),
.flow-wrap-preview.editing :deep(tspan),
.flow-wrap-preview.editing :deep(foreignObject),
.flow-wrap-preview.editing :deep(.markmap-foreign),
.flow-wrap-preview.editing :deep(.markmap-node) {
  cursor: text;
  pointer-events: auto;
}

.mindmap-edit-hint {
  position: absolute;
  left: 12px;
  top: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #1f2937;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
  z-index: 4;
  user-select: none;
}

.mindmap-inline-editor {
  position: absolute;
  z-index: 6;
}

.mindmap-inline-input {
  width: 100%;
  border: 1px solid #93c5fd;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.35;
  color: #0f172a;
  outline: none;
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.18);
}

.mindmap-inline-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.18), 0 14px 30px rgba(37, 99, 235, 0.18);
}

.preview-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  font-size: 12px;
  color: #6b7280;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.status-left {
  font-weight: 600;
  color: #374151;
}

/* ---------- 右侧对话 ---------- */
.chat-column {
  flex: 0 0 min(360px, 32%);
  max-width: 400px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  min-height: 520px;
}

.chat-column-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 14px 12px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}

.chat-column-title {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.chat-column-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.4;
}

.new-chat-btn {
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
}

.new-chat-btn:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.chat-messages-split {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 10px 12px;
  text-align: center;
  min-height: 0;
}

.chat-welcome-lottie {
  width: 140px;
  height: 140px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.chat-welcome-lottie :deep(.lottie-container) {
  width: 140px;
  height: 140px;
  min-height: 0;
}

.chat-welcome-title {
  margin: 0 0 8px;
  font-size: 1.05rem;
  font-weight: 800;
  color: #111827;
}

.chat-welcome-desc {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.55;
  max-width: 100%;
}

.chat-row-split {
  display: flex;
}

.chat-row-split.user {
  justify-content: flex-end;
}

.chat-row-split.assistant {
  justify-content: flex-start;
}

.chat-bubble-split {
  max-width: 100%;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.55;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.chat-bubble-split.user {
  background: #2563eb;
  color: #ffffff;
}

.chat-bubble-split.assistant {
  background: #f8fafc;
  color: #334155;
  border: 1px solid #eef2f7;
}

.chat-bubble-split.mindmap-hint {
  background: #f5f3ff;
  border-color: #ddd6fe;
  color: #5b21b6;
  font-size: 12px;
}

.hint-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #7c3aed;
  margin-right: 6px;
  vertical-align: middle;
  animation: hint-pulse 1s ease-in-out infinite;
}

@keyframes hint-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.error-bubble {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}

.chat-input-stack {
  flex-shrink: 0;
  padding: 10px 12px 12px;
  border-top: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}

.chat-input-box {
  height: auto !important;
  min-height: 120px;
}

.primary-send {
  background: #111827 !important;
  color: #ffffff !important;
}

.primary-send:hover:not(:disabled) {
  background: #1f2937 !important;
  color: #ffffff !important;
}

.upload-hint-split,
.error-text-split {
  margin: 8px 2px 0;
  font-size: 11px;
  line-height: 1.45;
}

.upload-hint-split {
  color: #6b7280;
}

.error-text-split {
  color: #dc2626;
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.mindmap-container:fullscreen {
  width: 100vw;
  height: 100vh;
  background: #ffffff;
  padding: 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mindmap-container:fullscreen .flow-wrap-preview {
  flex: 1;
  height: auto;
  min-height: 0;
  background: #ffffff;
}

.mindmap-container:fullscreen .preview-loading {
  flex: 1;
  min-height: 0;
}

.mindmap-loading {
  padding: 18px 12px;
  color: #64748b;
  font-weight: 600;
}

.knowledge-input-box {
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  background: #fdfefe;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 160px;
}

.knowledge-input-box:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.knowledge-textarea {
  flex: 1;
  padding: 14px 18px 10px;
  border: none;
  outline: none;
  font-size: 16px;
  line-height: 1.6;
  resize: none;
  font-family: inherit;
}

.knowledge-textarea::placeholder {
  color: #94a3b8;
}

.knowledge-input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px 12px;
}

.knowledge-footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-btn {
  padding: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-btn:hover {
  opacity: 0.8;
}

.voice-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.voice-btn:hover {
  background: #f1f5f9;
}

.voice-btn.recording {
  background: #fecaca;
  animation: voice-pulse 1.5s ease-in-out infinite;
}

@keyframes voice-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.voice-icon-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.upload-icon {
  width: 20px;
  height: 20px;
  opacity: 0.7;
}

.auto-btn {
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
}

.auto-btn:hover {
  color: #64748b;
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  background: #e2e8f0;
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
}

.generate-btn:hover {
  background: #cbd5e1;
  color: #1e293b;
}

.generate-icon {
  font-size: 1rem;
  color: #a3e635;
}

.examples {
  margin-top: 18px;
}

.examples-title {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #111827;
}

.examples-list {
  margin: 0;
  padding-left: 18px;
  font-size: 0.88rem;
  color: #4b5563;
  line-height: 1.6;
}

.upload-hint {
  width: 75%;
  margin: 10px auto 0;
  font-size: 13px;
  color: #6b7280;
}

.error-text {
  width: 75%;
  margin: 8px auto 0;
  font-size: 13px;
  color: #dc2626;
}

.upload-btn:disabled,
.generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.mindmap-section {
  width: 75%;
  margin: 18px auto 0;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 16px;
  padding: 14px 14px 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.mindmap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.mindmap-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
}

.mindmap-badge {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: #e5edff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 800;
}

.flow-wrap {
  height: 620px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(248, 251, 255, 0.55);
}

.flow-node {
  padding: 2px 6px;
  border-radius: 10px;
  background: transparent;
  border: none;
  font-weight: 700;
  font-size: 13px;
  line-height: 1.35;
  box-shadow: none;
  width: auto;
  max-width: 320px;
  white-space: normal;
  overflow: hidden;
  line-clamp: 2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}
</style>