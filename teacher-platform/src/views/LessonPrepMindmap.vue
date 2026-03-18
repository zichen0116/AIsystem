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
const hasChat = computed(() => chatMessages.value.length > 0)
const fullscreenMessageId = ref(null)
const markmapRefs = ref({})

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
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)

const finalSource = computed(() => {
  return uploadPreview.value ? `【上传材料提取文本】\n${uploadPreview.value}` : ''
})

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
  generating.value = true
  errorMsg.value = ''
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
  <div class="content-panel knowledge-panel" :class="{ 'has-chat': hasChat }">
    <div v-if="!hasChat" class="knowledge-header">
      <div class="knowledge-lottie">
        <LottiePlayer :animation-data="aiAnimationFlow" />
      </div>
      <p class="knowledge-subtitle">
        借助 AI 驱动的思维导图生成器，只需输入主题与关键要点，就能快速构建清晰直观的知识结构图。
      </p>
    </div>

    <!-- Markmap-only：不提供布局切换按钮 -->

    <section v-if="hasChat" class="chat-section">
      <div ref="chatMessagesRef" class="chat-messages">
        <div v-for="m in chatMessages" :key="m.id" class="chat-row" :class="m.role">
          <div class="chat-bubble" :class="m.role">
            <template v-if="m.type === 'text'">
              <div class="chat-text">{{ m.content }}</div>
            </template>

            <template v-else>
              <div class="mindmap-container" :data-mindmap-container="m.id">
                <div class="mindmap-bubble">
                <div class="mindmap-bubble-header">
                  <div class="mindmap-bubble-meta">
                    <div class="mindmap-bubble-title">{{ m.title || '思维导图' }}</div>
                    <div v-if="m.description" class="mindmap-bubble-desc">{{ m.description }}</div>
                  </div>
                  <div class="mindmap-toolbar">
                    <button
                      type="button"
                      class="tool-btn"
                      title="导出图片"
                      :disabled="exporting"
                      @click="handleExportPng(m.id)"
                    >
                      {{ exporting ? '导出中' : '导出' }}
                    </button>
                    <button type="button" class="tool-btn" title="全屏" @click="handleFullscreen(m.id)">
                      全屏
                    </button>
                    <button
                      v-if="fullscreenMessageId === m.id"
                      type="button"
                      class="tool-btn"
                      title="退出全屏"
                      @click="handleExitFullscreen"
                    >
                      退出全屏
                    </button>
                    <button type="button" class="tool-btn" title="放大" @click="handleZoomInFor(m.id)">
                      +
                    </button>
                    <button type="button" class="tool-btn" title="缩小" @click="handleZoomOutFor(m.id)">
                      -
                    </button>
                    <button type="button" class="tool-btn" title="适配视图" @click="handleFitFor(m.id)">
                      适配
                    </button>
                  </div>
                </div>

                <div v-if="m.loading" class="mindmap-loading">生成中...</div>

                <div v-else class="flow-wrap flow-wrap-in-chat" :data-mindmap-export="m.id">
                  <MarkmapRenderer
                    :ref="(el) => setMarkmapRef(m.id, el)"
                    :markdown="m.markdown"
                  />
                </div>
              </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </section>

    <div class="knowledge-input-wrap">
      <div class="knowledge-input-box">
        <textarea
          v-model="promptText"
          class="knowledge-textarea"
          placeholder="请描述您想创建的内容..."
          rows="4"
        ></textarea>
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
          <button class="generate-btn" :disabled="generating" @click="handleGenerate">
            <span class="generate-icon">✨</span>
            <span>{{ generating ? '生成中...' : 'AI生成' }}</span>
          </button>
        </div>
      </div>
    </div>

    <p v-if="uploadedFilename" class="upload-hint">
      已上传：{{ uploadedFilename }}；提取文本长度：{{ uploadPreview.length }} 字
    </p>
    <p v-if="errorMsg" class="error-text">{{ errorMsg }}</p>
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

.knowledge-panel {
  padding: 72px 40px 24px;
  background: transparent;
  height: 100%;
}

.knowledge-panel.has-chat {
  /* 进入对话模式后减少顶部留白，让聊天区更靠上 */
  padding-top: 18px;
}

.chat-section {
  max-width: 1060px;
  margin: 24px auto 0;
  width: 100%;
  min-height: 320px;
  flex: 1;
  min-height: 0;
}

.knowledge-panel.has-chat .chat-section {
  margin-top: 10px;
}

.chat-messages {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
  min-height: 320px;
  height: 100%;
  overflow: auto;
  /* 给底部输入框留空间，避免贴得太近 */
  padding-bottom: 240px;
}

.chat-empty {
  color: #64748b;
  font-size: 0.95rem;
  line-height: 1.6;
  padding: 32px 8px;
}

.chat-row {
  display: flex;
  margin-bottom: 14px;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-row.assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: 900px;
  border-radius: 16px;
  padding: 12px 14px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.chat-bubble.user {
  background: #2563eb;
  color: #ffffff;
}

.chat-bubble.assistant {
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.mindmap-bubble {
  width: 900px;
  max-width: 100%;
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

.mindmap-container:fullscreen .mindmap-bubble {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.mindmap-container:fullscreen .mindmap-bubble-header {
  flex: 0 0 auto;
}

.mindmap-container:fullscreen .flow-wrap {
  flex: 1;
  height: auto;
  min-height: 0;
  background: #ffffff;
}

.mindmap-container:fullscreen .flow-wrap-in-chat {
  flex: 1;
  height: auto;
}

.mindmap-container:fullscreen .mindmap-toolbar {
  background: rgba(255, 255, 255, 0.95);
}

.mindmap-bubble-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 10px;
}

.mindmap-bubble-title {
  font-weight: 800;
  font-size: 1.1rem;
  color: #0f172a;
  margin-bottom: 4px;
}

.mindmap-bubble-desc {
  color: #475569;
  font-size: 0.95rem;
  line-height: 1.5;
}

.mindmap-toolbar {
  display: inline-flex;
  gap: 8px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 999px;
  padding: 8px 10px;
  flex-shrink: 0;
}

.tool-btn {
  border: none;
  background: transparent;
  color: #0f172a;
  font-weight: 700;
  font-size: 0.9rem;
  padding: 6px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.tool-btn:hover {
  background: rgba(37, 99, 235, 0.1);
}

.mindmap-loading {
  padding: 18px 12px;
  color: #64748b;
  font-weight: 600;
}

.flow-wrap-in-chat {
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  overflow: hidden;
  background: #ffffff;
}

.knowledge-header {
  text-align: center;
  margin-bottom: 48px;
}

.knowledge-lottie {
  width: 190px;
  height: 190px;
  margin: 0 auto 24px;
}

.knowledge-lottie :deep(.lottie-container) {
  min-height: 0;
  width: 190px;
  height: 190px;
}

.knowledge-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 12px;
  line-height: 1.3;
}

.knowledge-subtitle {
  font-size: 1.05rem;
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
}


.knowledge-tabs-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 40px;
}

.knowledge-tabs {
  display: inline-flex;
  padding: 3px;
  gap: 0;
  background: #e8f1ff;
  border-radius: 999px;
}

.knowledge-tab {
  display: inline-flex;
  align-items: center;
  padding: 9px 24px;
  border: none;
  background: transparent;
  font-size: 1rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
  border-radius: 999px;
}

.knowledge-tab:hover {
  color: #2563eb;
}

.knowledge-tab.active {
  background: #ffffff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}

.knowledge-input-wrap {
  width: min(1060px, 75%);
  margin: 16px auto 0;
  position: sticky;
  bottom: 18px;
  z-index: 10;
  /* 底部磨砂遮罩，让输入框更像固定栏 */
  padding: 12px 0 0;
  background: linear-gradient(to top, rgba(241, 245, 249, 0.96), rgba(241, 245, 249, 0));
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
