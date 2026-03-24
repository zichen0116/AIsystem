<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
import linkFileImg from '../assets/链接文件.png'
import voiceImg from '../assets/语音.png'
import sendImg from '../assets/发送.png'
import animationJson from '../assets/animation (1).json'
import todaygamesJson from '../assets/todaygames.json'
import { useVoiceInput } from '../composables/useVoiceInput'

const animationInput = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(animationInput)

const activeMode = ref('animation')
const tabs = [
  { id: 'animation', name: '动画' },
  { id: 'game', name: '小游戏' }
]
const currentLottieData = computed(() =>
  activeMode.value === 'animation' ? animationJson : todaygamesJson
)

const lottieSize = computed(() => {
  // 放大动画展示区域尺寸（小游戏模式稍大一些）
  return activeMode.value === 'game' ? 345 : 230
})

// 发送后布局
const hasSentMessages = ref(false)
const messages = ref([])
const codeTab = ref('content') // 'content' | 'preview'
const isSending = ref(false)
const htmlMode = ref(false) // HTML代码模式开关
const htmlDynamicMode = ref(false) // HTML代码动态模式开关

const fileInput = ref(null)
const uploadResult = ref(null) // { file_id, filename, extracted_length, preview, ... }

function getApiBase() {
  const base = (import.meta.env?.VITE_API_BASE || '').trim()
  return (base || 'http://127.0.0.1:8000').replace(/\/+$/, '')
}

async function postJson(path, body, timeoutMs = 900000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${getApiBase()}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal
    })
    const text = await res.text()
    if (!res.ok) throw new Error(text || res.statusText)
    return text ? JSON.parse(text) : null
  } finally {
    clearTimeout(timer)
  }
}

async function uploadFileToBackend(file, timeoutMs = 180000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${getApiBase()}/api/v1/html/upload`, {
      method: 'POST',
      body: form,
      signal: controller.signal
    })
    const data = await res.json().catch(() => null)
    if (!res.ok) {
      const detail = data?.detail || res.statusText
      throw new Error(detail)
    }
    return data
  } finally {
    clearTimeout(timer)
  }
}

function extractHtml(text) {
  const raw = (text || '').trim()
  if (!raw) return null

  // ```html ... ```（或任意 fenced code block）
  const fence = raw.match(/```([a-zA-Z0-9_-]+)?\s*[\r\n]+([\s\S]*?)```/)
  if (fence) {
    const lang = (fence[1] || '').trim().toLowerCase()
    const code = (fence[2] || '').trim()
    if (lang === 'html') return code
    const upper = code.toUpperCase()
    if (upper.includes('<!DOCTYPE HTML') || upper.includes('<HTML')) return code
  }

  // 直接输出整页 HTML（无 fence）
  const upper = raw.toUpperCase()
  if (upper.includes('<!DOCTYPE HTML') || upper.includes('<HTML')) return raw

  return null
}

function buildPrompt(mode, userText, forceHtml, autoPlay) {
  // 两个开关都关时，按普通对话处理
  if (!forceHtml && !autoPlay) {
    return userText
  }

  const sections = []

  if (forceHtml || autoPlay) {
    sections.push(
      '【HTML代码模式】只返回单文件可运行的 HTML 源代码：不要解释文字、不要 Markdown 代码块标记（```），不要分段说明。'
    )
  }

  const target =
    mode === 'game'
      ? '请生成一个教学互动小游戏（HTML5），包含玩法说明、得分/反馈机制，单文件可运行。'
      : '请生成一个教学互动式动画/演示（HTML5），包含交互控件（按钮/滑块等），单文件可运行。'
  sections.push(target)

  if (autoPlay) {
    sections.push(
      '【动态演示要求】页面加载后应自动开始演示关键交互：例如通过 JavaScript 定时器自动改变滑块/参数并更新图像，' +
        '无需用户点击即可看到函数/图表/动画的变化。演示可循环播放 5~10 秒左右，并保留用户后续手动交互能力。'
    )
  }

  sections.push('以下是具体需求：')
  sections.push(userText)

  return sections.join('\n')
}

function triggerUpload() {
  fileInput.value?.click()
}

function clearUpload() {
  uploadResult.value = null
  if (fileInput.value) fileInput.value.value = ''
}

async function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const res = await uploadFileToBackend(file)
    uploadResult.value = res
    messages.value.push({
      role: 'assistant',
      content: `已上传「${res.filename}」，已提取 ${res.extracted_length} 字。后续生成会结合该文件内容。`
    })
    await nextTick()
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: '上传失败：' + (err?.message || String(err))
    })
  } finally {
    e.target.value = ''
  }
}

const generatedCode = ref('')
const isFullscreen = ref(false)
const isExportingGif = ref(false)

const props = defineProps({
  resetKey: {
    type: Number,
    default: 0
  }
})

function resetState() {
  activeMode.value = 'animation'
  animationInput.value = ''
  hasSentMessages.value = false
  messages.value = []
  codeTab.value = 'content'
  generatedCode.value = ''
  uploadResult.value = null
  isSending.value = false
  isFullscreen.value = false
   htmlMode.value = false
   htmlDynamicMode.value = false
}

async function handleSend() {
  const text = animationInput.value?.trim()
  if (!text || isSending.value) return

  isSending.value = true
  messages.value.push({ role: 'user', content: text })
  animationInput.value = ''
  hasSentMessages.value = true

  // 动态模式基于 HTML 代码模式：开启动态时也强制返回 HTML
  const wantHtml = htmlMode.value || htmlDynamicMode.value
  const wantAutoPlay = htmlDynamicMode.value
  const prompt = buildPrompt(activeMode.value, text, wantHtml, wantAutoPlay)
  const assistantIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: wantHtml ? '正在生成 HTML 代码，请稍候…' : ''
  })

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 900000)

  try {
    const res = await fetch(`${getApiBase()}/api/v1/html/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: prompt,
        context_file_id: uploadResult.value?.file_id || undefined
      }),
      signal: controller.signal
    })
    if (!res.ok) throw new Error(res.statusText || '请求失败')
    const reader = res.body?.getReader()
    if (!reader) throw new Error('无法读取响应流')
    const decoder = new TextDecoder()
    let fullText = ''
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (value) buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const ev of events) {
        const line = ev.split('\n')[0]
        if (line?.startsWith('data: ')) {
          const raw = line.slice(6).trim()
          if (raw === '[DONE]') continue
          try {
            const obj = JSON.parse(raw)
            const content = obj?.content ?? obj?.text ?? ''
            const err = obj?.error
            if (err) {
              fullText = `错误：${err}`
              break
            }
            if (content) {
              fullText += content
              if (!wantHtml) {
                messages.value[assistantIndex].content = fullText
                await nextTick()
              }
            }
          } catch (_) {}
        }
      }
      if (done) {
        if (buffer) {
          const line = buffer.split('\n')[0]
          if (line?.startsWith('data: ')) {
            const raw = line.slice(6).trim()
            if (raw !== '[DONE]') {
              try {
                const obj = JSON.parse(raw)
                const content = obj?.content ?? obj?.text ?? ''
                if (content) {
                  fullText += content
                  if (!wantHtml) {
                    messages.value[assistantIndex].content = fullText
                  }
                }
              } catch (_) {}
            }
          }
        }
        break
      }
    }
    clearTimeout(timer)
    const html = extractHtml(fullText)
    if (html) {
      generatedCode.value = html
      codeTab.value = 'preview'
      messages.value[assistantIndex].content = wantHtml
        ? '已生成 HTML，已在右侧代码区域展示，可切换「预览」查看效果。'
        : fullText.trim() || '已生成 HTML，右侧切换到「预览」即可查看效果。'
    } else if (!fullText.trim()) {
      messages.value[assistantIndex].content = '生成失败：返回为空'
    }
    await nextTick()
  } catch (err) {
    clearTimeout(timer)
    messages.value[assistantIndex].content =
      '发送失败：' + (err?.message || String(err))
  } finally {
    isSending.value = false
  }
}

const copySuccess = ref(false)

function copyCode() {
  if (!generatedCode.value) return
  navigator.clipboard?.writeText(generatedCode.value).then(() => {
    copySuccess.value = true
    setTimeout(() => { copySuccess.value = false }, 2000)
  })
}

function downloadCode() {
  if (!generatedCode.value) return
  const blob = new Blob([generatedCode.value], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `generated_${Date.now()}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function exportGif() {
  if (!generatedCode.value || isExportingGif.value) return
  isExportingGif.value = true
  try {
    const res = await fetch(`${getApiBase()}/api/v1/html/export/gif`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        html: generatedCode.value,
        width: 960,
        height: 540,
        duration_sec: 6,
        fps: 12,
        start_delay_ms: 300,
        filename: `demo_${Date.now()}.gif`
      })
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      try {
        const obj = JSON.parse(text)
        throw new Error(obj?.detail || text || res.statusText || '导出失败')
      } catch (_) {
        throw new Error(text || res.statusText || '导出失败')
      }
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `demo_${Date.now()}.gif`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: '导出 GIF 失败：' + (err?.message || String(err))
    })
    await nextTick()
  } finally {
    isExportingGif.value = false
  }
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)

watch(
  () => htmlMode.value,
  (val) => {
    if (!val) {
      htmlDynamicMode.value = false
    }
  }
)
</script>

<template>
  <div class="content-panel animation-panel">
    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.doc,.docx,.ppt,.pptx,.txt"
      style="display:none"
      @change="onFileSelect"
    />
    <!-- 发送前：初始布局 -->
    <div v-if="!hasSentMessages" class="animation-content">
      <div class="animation-top-slot">
        <div class="animation-lottie" :style="{ width: `${lottieSize}px`, height: `${lottieSize}px` }">
          <LottiePlayer :key="activeMode" :animation-data="currentLottieData" />
        </div>
      </div>
      <div class="animation-header">
        <p>{{ activeMode === 'animation' ? '在此创建互动式动画，描述您的需求即可快速生成' : '在此创建教育小游戏，描述您的需求即可快速生成' }}</p>
      </div>
      <div class="animation-tabs-wrap">
        <div class="animation-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="animation-tab"
            :class="{ active: activeMode === tab.id }"
            @click="activeMode = tab.id"
          >
            <span class="animation-tab-icon" aria-hidden="true">
              <!-- 动画：场记板图标 -->
              <svg
                v-if="tab.id === 'animation'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect x="3" y="7" width="18" height="13" rx="2" />
                <path d="M3 11h18" />
                <path d="M5 7l2.5-4L11 7M13 7l2.5-4L21 7" />
              </svg>
              <!-- 小游戏：手柄图标 -->
              <svg
                v-else
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M6 12h4M8 10v4" />
                <path d="M15 13h.01M18 11h.01M17 15h.01M20 10h.01" />
                <path d="M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v4a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8z" />
              </svg>
            </span>
            <span class="animation-tab-label">
              {{ tab.id === 'animation' ? '动画' : '小游戏' }}
            </span>
          </button>
        </div>
      </div>
      <div class="animation-chatbox-wrap">
        <div class="animation-chatbox">
          <div class="chatbox-top-bar">
            <button
              type="button"
              class="html-mode-btn"
              :class="{ active: htmlMode }"
              @click="htmlMode = !htmlMode"
            >
              <span class="html-mode-icon">&lt;/&gt;</span>
              HTML代码模式
            </button>
            <button
              type="button"
              class="html-mode-btn secondary"
              :class="{ active: htmlDynamicMode, disabled: !htmlMode && !htmlDynamicMode }"
              :disabled="!htmlMode && !htmlDynamicMode"
              @click="htmlDynamicMode = !htmlDynamicMode"
            >
              <span class="html-mode-icon">▶</span>
              HTML代码动态模式
            </button>
          </div>
          <div v-if="uploadResult" class="upload-banner" role="status" aria-live="polite">
            <span class="upload-banner-title">已选择文件</span>
            <span class="upload-banner-name">{{ uploadResult.filename }}</span>
            <span class="upload-banner-meta">提取 {{ uploadResult.extracted_length }} 字</span>
            <button type="button" class="upload-banner-remove" title="移除附件" @click="clearUpload">×</button>
          </div>
          <textarea
            v-model="animationInput"
            class="animation-input"
            placeholder="请描述您想创建的动画或小游戏..."
            rows="4"
          ></textarea>
          <div class="animation-chatbox-bottom">
            <div class="animation-chatbox-left">
              <img :src="linkFileImg" class="attach-icon" alt="上传文件" title="上传文件" @click="triggerUpload" />
              <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
                <img :src="voiceImg" class="voice-icon-img" alt="语音" />
              </button>
            </div>
            <button class="send-btn" :disabled="isSending" @click="handleSend"><img :src="sendImg" class="send-btn-icon" alt="" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- 发送后：根据是否有HTML决定布局 -->
    <div
      v-else
      class="animation-two-column"
      :class="{ 'no-code-panel': !generatedCode, 'fullscreen-mode': isFullscreen }"
    >
      <div class="animation-left" :class="{ 'full-width': !generatedCode }">
        <div class="animation-chat-messages">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="chat-msg"
            :class="msg.role"
          >
            <span class="chat-msg-label">{{ msg.role === 'user' ? '我' : '小助手' }}</span>
            <div class="chat-msg-content">{{ msg.content }}</div>
          </div>
        </div>
        <div class="animation-chatbox-compact">
          <div class="chatbox-top-bar">
            <button
              type="button"
              class="html-mode-btn"
              :class="{ active: htmlMode }"
              @click="htmlMode = !htmlMode"
            >
              <span class="html-mode-icon">&lt;/&gt;</span>
              HTML代码模式
            </button>
            <button
              type="button"
              class="html-mode-btn secondary"
              :class="{ active: htmlDynamicMode, disabled: !htmlMode && !htmlDynamicMode }"
              :disabled="!htmlMode && !htmlDynamicMode"
              @click="htmlDynamicMode = !htmlDynamicMode"
            >
              <span class="html-mode-icon">▶</span>
              HTML代码动态模式
            </button>
          </div>
          <div v-if="uploadResult" class="upload-banner upload-banner-compact" role="status" aria-live="polite">
            <span class="upload-banner-title">已选择文件</span>
            <span class="upload-banner-name">{{ uploadResult.filename }}</span>
            <span class="upload-banner-meta">提取 {{ uploadResult.extracted_length }} 字</span>
            <button type="button" class="upload-banner-remove" title="移除附件" @click="clearUpload">×</button>
          </div>
          <textarea
            v-model="animationInput"
            class="animation-input"
            placeholder="输入消息发送..."
            rows="2"
          ></textarea>
          <div class="animation-chatbox-bottom">
            <div class="animation-chatbox-left">
              <img :src="linkFileImg" class="attach-icon" alt="上传文件" title="上传文件" @click="triggerUpload" />
              <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
                <img :src="voiceImg" class="voice-icon-img" alt="语音" />
              </button>
            </div>
            <button class="send-btn" :disabled="isSending" @click="handleSend"><img :src="sendImg" class="send-btn-icon" alt="" /></button>
          </div>
        </div>
      </div>
      <div v-if="generatedCode" class="animation-right" :class="{ fullscreen: isFullscreen }">
        <div class="code-panel-header">
          <h3 class="code-panel-title">代码 (HTML)</h3>
          <div class="code-panel-actions">
            <button class="code-action-btn" :class="{ success: copySuccess }" @click="copyCode">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </span>
              {{ copySuccess ? '已复制' : '复制' }}
            </button>
            <button class="code-action-btn" @click="downloadCode">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              </span>
              下载
            </button>
            <button class="code-action-btn" :disabled="isExportingGif" @click="exportGif">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
              </span>
              {{ isExportingGif ? '导出中…' : '导出GIF' }}
            </button>
            <button class="code-action-btn" @click="toggleFullscreen">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
              </span>
              {{ isFullscreen ? '退出全屏' : '全屏' }}
            </button>
          </div>
        </div>
        <div class="code-panel-tabs-wrap">
          <div class="code-panel-tabs">
            <button class="code-tab" :class="{ active: codeTab === 'content' }" @click="codeTab = 'content'">内容</button>
            <button class="code-tab" :class="{ active: codeTab === 'preview' }" @click="codeTab = 'preview'">预览</button>
          </div>
        </div>
        <div class="code-panel-body">
          <pre v-if="codeTab === 'content'" class="code-display"><code>{{ generatedCode }}</code></pre>
          <div v-else class="preview-display">
            <iframe :srcdoc="generatedCode" class="preview-iframe" sandbox="allow-scripts allow-forms allow-modals allow-same-origin" title="预览" />
          </div>
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
  overflow: hidden;
  height: 100%;
  max-height: 100%;
}

.animation-panel {
  position: relative;
  padding: 2% 3% 2%;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
}

/* 选项与聊天框位置与动画页一致 */
.animation-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
}

/* 顶部动画区固定高度，切换选项时说明/选项/聊天框位置不变 */
.animation-top-slot {
  height: 30%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 4%;
  margin-bottom: 0;
  flex-shrink: 0;
}

.animation-lottie {
  flex-shrink: 0;
}

.animation-lottie :deep(.lottie-container) {
  min-height: 0;
  width: 100%;
  height: 100%;
}

.animation-header {
  text-align: center;
  margin-bottom: 3%;
}

.animation-tabs-wrap {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-bottom: 4%;
}

.animation-tabs {
  display: flex;
  width: 18%;
  max-width: 500px;
  margin: 0 auto;
  padding: 0.3%;
  gap: 0;
  background: #e8f1ff;
  border-radius: 999px;
  box-sizing: border-box;
}

.animation-tab {
  display: inline-flex;
  align-items: center;
  gap: 1%;
  padding: 4% 1%;
  flex: 1 1 50%;
  min-width: 0;
  max-width: 50%;
  justify-content: center;
  border: none;
  background: transparent;
  font-size: 1rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-radius: 999px;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.animation-tab:hover {
  color: #2563eb;
}

.animation-tab.active {
  background: #ffffff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}

.animation-tab-icon {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.animation-tab-icon svg {
  width: 100%;
  height: 100%;
}

.animation-tab-label {
  line-height: 1;
}

.animation-header h3 {
  font-size: 1.5rem;
  color: #1e293b;
  margin: 0 0 1.2%;
}

.animation-header p {
  font-size: 1.05rem;
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
}

.animation-chatbox-wrap {
  width: 82%;
  margin: 0 auto;
}

.animation-chatbox {
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  background: #fdfefe;
  padding: 1.6% 2%;
  display: flex;
  flex-direction: column;
  min-height: 14%;
}

.upload-banner {
  display: flex;
  align-items: center;
  gap: 0.8%;
  padding: 0.8% 1%;
  margin-bottom: 1%;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
}

.upload-banner-title {
  font-weight: 600;
  color: #0f172a;
  flex-shrink: 0;
}

.upload-banner-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 36%;
}

.upload-banner-meta {
  color: #64748b;
  flex-shrink: 0;
}

.upload-banner-remove {
  margin-left: auto;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 999px;
  cursor: pointer;
  color: #64748b;
  line-height: 1;
}

.upload-banner-remove:hover {
  color: #dc2626;
  border-color: #fecaca;
  background: #fff5f5;
}

.upload-banner-compact {
  margin-bottom: 0.8%;
}

.animation-chatbox:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.animation-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1rem;
  resize: none;
  padding: 0;
  font-family: inherit;
}

.animation-input::placeholder {
  color: #94a3b8;
}

.animation-chatbox-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.2%;
  margin-top: 1.2%;
  padding-top: 1.2%;
  border-top: 1px solid #f1f5f9;
}

.animation-chatbox-left {
  display: flex;
  align-items: center;
  gap: 1.2%;
}

.attach-icon {
  width: 26px;
  height: 26px;
  object-fit: contain;
  flex-shrink: 0;
  cursor: pointer;
  opacity: 0.8;
}

.attach-icon:hover {
  opacity: 1;
}

.voice-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
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
  animation: anim-voice-pulse 1.5s ease-in-out infinite;
}

@keyframes anim-voice-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.voice-icon-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.send-btn {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border: none;
  background: #e2e8f0;
  border-radius: 50%;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:hover {
  background: #cbd5e1;
}

.send-btn-icon {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

/* 发送后：左右两栏布局 */
.animation-two-column {
  display: flex;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  gap: 1.6%;
  overflow: hidden;
}

.animation-two-column.fullscreen-mode {
  position: fixed;
  inset: 0;
  z-index: 50;
  padding: 2.4% 3.2%;
  background: rgba(15, 23, 42, 0.08);
}

.animation-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: auto;
  max-height: none;
  overflow: hidden;
}

.animation-left.full-width {
  width: 92%;
  max-width: none;
  margin: 0 auto;
}

.animation-two-column.no-code-panel {
  justify-content: center;
}

/* 对话部分单独滚动，整体页面不动 */
.animation-chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1.2% 0;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.animation-chat-messages::-webkit-scrollbar {
  display: none; /* Chrome/Safari/Opera */
}

.chat-msg {
  margin-bottom: 1.6%;
  display: flex;
  flex-direction: column;
}

.chat-msg.user {
  align-items: flex-end;
}

.chat-msg.assistant {
  align-items: flex-start;
}

/* 图1：用户与助手均有圆角气泡，用户浅蓝、助手白底，均有轻微阴影；小助手标签蓝色 */
.chat-msg.user .chat-msg-content {
  background: #E0EDFE;
  color: #000000;
  padding: 1% 1.4%;
  border-radius: 12px;
  display: inline-block;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  font-size: 16px;
}

.chat-msg.assistant .chat-msg-content {
  background: #FFFFFF;
  color: #000000;
  padding: 1% 1.4%;
  border-radius: 12px;
  display: inline-block;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  font-size: 16px;
}

.chat-msg-label {
  font-size: 13px;
  margin-bottom: 0.4%;
  display: block;
}

.chat-msg.user .chat-msg-label {
  color: #333333;
}

.chat-msg.assistant .chat-msg-label {
  color: #409EFF;
}

.animation-chatbox-compact {
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 1.2% 1.6%;
  display: flex;
  flex-direction: column;
  min-height: 8%;
}

.chatbox-top-bar {
  display: flex;
  align-items: center;
  margin-bottom: 0.8%;
  width: 100%;
  box-sizing: border-box;
  gap: 1%;
  flex-wrap: nowrap;
}

.html-mode-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.6%;
  flex: 0 0 13%;
  min-width: 0;
  white-space: nowrap;
  padding: 0.6% 1.2%;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.html-mode-btn.secondary {
  flex: 0 0 14%;
  margin-left: 0;
  font-size: 12px;
  padding: 0.4% 1%;
}

.html-mode-btn:hover {
  background: #e2e8f0;
  color: #475569;
}

.html-mode-btn.active {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

.html-mode-btn.disabled,
.html-mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.html-mode-icon {
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
}

.animation-chatbox-compact:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.animation-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: auto;
  max-height: none;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.animation-right.fullscreen {
  height: 100%;
  max-height: none;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
}

.animation-two-column.fullscreen-mode .animation-left {
  display: none;
}

.animation-right.fullscreen .code-panel-body {
  justify-content: center;
  align-items: center;
}

.animation-right.fullscreen .preview-iframe {
  min-height: 0;
  height: calc(100dvh - 220px);
}

.code-panel-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.2% 1.6%;
  border-bottom: 1px solid #e2e8f0;
}

.code-panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.code-panel-actions {
  display: flex;
  gap: 0.8%;
  flex-wrap: wrap;
}

/* 图5：白底、药丸形、细浅灰边框、深灰字、左侧图标 */
.code-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4%;
  padding: 0.5% 1%;
  border: 1px solid #E0E0E0;
  background: #FFFFFF;
  border-radius: 999px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.code-action-btn:hover {
  background: #f8fafc;
  border-color: #DCDCDC;
}

.code-action-btn.success {
  background: #10b981;
  border-color: #10b981;
  color: #fff;
}

.code-action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: inherit;
}

.code-action-icon svg {
  width: 100%;
  height: 100%;
}

/* 图2：药丸形分段，边框小一点 */
.code-panel-tabs-wrap {
  flex-shrink: 0;
  padding: 0.8% 1.6% 1.2%;
  border-bottom: 1px solid #e2e8f0;
}

.code-panel-tabs {
  display: inline-flex;
  padding: 0.2%;
  background: #F0F5FA;
  border-radius: 999px;
  gap: 0;
  border: 0.5px solid #D1DAE8;
}

.code-tab {
  padding: 0.4% 1%;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #8C8C8C;
  cursor: pointer;
  border-radius: 999px;
  transition: background 0.2s, color 0.2s;
}

.code-tab:hover {
  color: #6B778C;
}

.code-tab.active {
  color: #1890FF;
  font-weight: 500;
  background: #fff;
  border: 0.1px solid #ADCDE0;
  box-shadow: none;
}

/* 代码和预览部分单独滚动，不影响整页 */
.code-panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.code-panel-body::-webkit-scrollbar {
  display: none;
}

.code-display {
  margin: 0;
  padding: 1.6%;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  word-break: break-all;
}

.code-display code {
  color: inherit;
}

.preview-display {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  min-height: 55%;
  border: none;
}

.preview-empty {
  padding: 4%;
  text-align: center;
  color: #94a3b8;
}

@media (max-width: 960px) {
  .animation-two-column { flex-direction: column; }
  .animation-left { max-height: 48%; }
  .animation-right { min-height: 52%; }
  .animation-two-column.fullscreen-mode { padding: 1.6%; }
  .animation-chatbox-wrap { width: 97%; }
}

@media (max-width: 720px) {
  .animation-panel {
    padding: 1.2%;
  }
  .animation-tabs {
    width: 86%;
    max-width: none;
    min-width: 0;
  }
  .animation-tab {
    padding: 0.8% 1.4%;
    font-size: 0.92rem;
  }
  .animation-chatbox {
    padding: 1.2%;
  }
  .animation-chatbox-bottom {
    gap: 0.8%;
    flex-wrap: wrap;
  }
  .animation-right {
    min-height: 56%;
  }
  .preview-iframe {
    min-height: 52%;
  }
  .animation-chatbox-wrap {
    width: 98%;
  }
  .html-mode-btn {
    flex: 0 0 34%;
    font-size: 12px;
  }
  .html-mode-btn.secondary {
    flex: 0 0 64%;
    font-size: 11px;
  }
  .animation-two-column.fullscreen-mode { padding: 1.2%; }
}
</style>
