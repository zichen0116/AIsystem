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
  return activeMode.value === 'game' ? 280 : 170
})

// 发送后布局
const hasSentMessages = ref(false)
const messages = ref([])
const codeTab = ref('content') // 'content' | 'preview'
const isSending = ref(false)
const htmlMode = ref(false) // HTML代码模式开关

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

function buildPrompt(mode, userText, forceHtml) {
  if (!forceHtml) {
    return userText
  }
  const forceHtmlOnly =
    '【HTML代码模式】你只返回完整可运行的 HTML 源代码：不要解释文字，不要 Markdown 代码块标记，不要分段说明。'
  const target =
    mode === 'game'
      ? '请生成一个教学互动小游戏（HTML5），包含玩法说明、得分/反馈机制，单文件可运行。'
      : '请生成一个教学互动式动画/演示（HTML5），包含交互控件（按钮/滑块等），单文件可运行。'
  return `${forceHtmlOnly}\n${target}\n\n需求：\n${userText}`
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
}

async function handleSend() {
  const text = animationInput.value?.trim()
  if (!text || isSending.value) return

  isSending.value = true
  messages.value.push({ role: 'user', content: text })
  animationInput.value = ''
  hasSentMessages.value = true

  const wantHtml = htmlMode.value
  const prompt = buildPrompt(activeMode.value, text, wantHtml)
  const assistantIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

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
              messages.value[assistantIndex].content = fullText
              await nextTick()
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
                  messages.value[assistantIndex].content = fullText
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
      messages.value[assistantIndex].content =
        fullText.trim() || '已生成 HTML，右侧切换到「预览」即可查看效果。'
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

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

watch(
  () => props.resetKey,
  () => {
    resetState()
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
            class="animation-tab"
            :class="{ active: activeMode === tab.id }"
            @click="activeMode = tab.id"
          >
            {{ tab.name }}
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
            <button class="code-action-btn">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
              </span>
              导出图片
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
  padding: 20px 32px 18px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
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
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 40px;
  margin-bottom: 0px;
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
  margin-bottom: 32px;
}

.animation-tabs-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 40px;
}

.animation-tabs {
  display: inline-flex;
  gap: 8px;
}

.animation-tab {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border: 1px solid transparent;
  background:rgba(255, 255, 255, 0.5);
  font-size: 0.875rem;
  font-weight: 700;
  color:rgb(0, 0, 0);
  cursor: pointer;
  transition: background 0.1s, border 0.1s;
  border-radius: 6px;
}

.animation-tab:hover {
  background:rgba(80, 173, 254, 0.11);
}

.animation-tab.active {
  background:rgba(129, 194, 255, 0.31);
  border-color:rgba(129, 194, 255, 0.51);
}

.animation-header h3 {
  font-size: 1.5rem;
  color: #1e293b;
  margin: 0 0 12px;
}

.animation-header p {
  font-size: 0.95rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
}

.animation-chatbox-wrap {
  max-width: 740px;
  margin: 0 auto;
  width: 80%;
}

.animation-chatbox {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  min-height: 140px;
}

.upload-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 10px;
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
  max-width: 320px;
}

.upload-banner-meta {
  color: #64748b;
  flex-shrink: 0;
}

.upload-banner-remove {
  margin-left: auto;
  width: 22px;
  height: 22px;
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
  margin-bottom: 8px;
}

.animation-chatbox:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.animation-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
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
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.animation-chatbox-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.attach-icon {
  width: 20px;
  height: 20px;
  cursor: pointer;
  opacity: 0.8;
}

.attach-icon:hover {
  opacity: 1;
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
  animation: anim-voice-pulse 1.5s ease-in-out infinite;
}

@keyframes anim-voice-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.voice-icon-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.send-btn {
  width: 40px;
  height: 40px;
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
  width: 20px;
  height: 20px;
  object-fit: contain;
}

/* 发送后：左右两栏布局 */
.animation-two-column {
  display: flex;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  gap: 16px;
  overflow: hidden;
}

.animation-two-column.fullscreen-mode {
  position: fixed;
  inset: 0;
  z-index: 50;
  padding: 24px 32px;
  background: rgba(15, 23, 42, 0.08);
}

.animation-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: calc(100vh - 140px);
  max-height: calc(100vh - 140px);
  overflow: hidden;
}

.animation-left.full-width {
  max-width: 800px;
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
  padding: 12px 0;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.animation-chat-messages::-webkit-scrollbar {
  display: none; /* Chrome/Safari/Opera */
}

.chat-msg {
  margin-bottom: 16px;
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
  padding: 10px 14px;
  border-radius: 12px;
  display: inline-block;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  font-size: 15px;
}

.chat-msg.assistant .chat-msg-content {
  background: #FFFFFF;
  color: #000000;
  padding: 10px 14px;
  border-radius: 12px;
  display: inline-block;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  font-size: 15px;
}

.chat-msg-label {
  font-size: 13px;
  margin-bottom: 4px;
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
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  min-height: 80px;
}

.chatbox-top-bar {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.html-mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
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
  height: calc(100vh - 140px);
  max-height: calc(100vh - 140px);
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
  height: calc(100vh - 220px);
}

.code-panel-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
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
  gap: 8px;
  flex-wrap: wrap;
}

/* 图5：白底、药丸形、细浅灰边框、深灰字、左侧图标 */
.code-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
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
  width: 14px;
  height: 14px;
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
  padding: 8px 16px 12px;
  border-bottom: 1px solid #e2e8f0;
}

.code-panel-tabs {
  display: inline-flex;
  padding: 2px;
  background: #F0F5FA;
  border-radius: 999px;
  gap: 0;
  border: 0.5px solid #D1DAE8;
}

.code-tab {
  padding: 4px 10px;
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
  padding: 16px;
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
  min-height: calc(100vh - 260px);
  border: none;
}

.preview-empty {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
}
</style>
