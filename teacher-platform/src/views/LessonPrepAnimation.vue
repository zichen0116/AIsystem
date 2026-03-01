<script setup>
import { ref, computed, watch } from 'vue'
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

const initialGeneratedCode = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>二次函数概念演示</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; }
    body { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  </style>
</head>
<body>
  <h1>二次函数概念演示</h1>
</body>
</html>`

const generatedCode = ref(initialGeneratedCode)

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
  generatedCode.value = initialGeneratedCode
}

function handleSend() {
  const text = animationInput.value?.trim()
  if (!text) return
  messages.value.push({ role: 'user', content: text })
  animationInput.value = ''
  messages.value.push({
    role: 'assistant',
    content: '好的，我已经为您分析了需求。如果是需要生成动画，请点击右侧的预览选项查看效果。'
  })
  hasSentMessages.value = true
}

function copyCode() {
  navigator.clipboard?.writeText(generatedCode.value)
}

function clearCode() {
  generatedCode.value = ''
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
          <textarea
            v-model="animationInput"
            class="animation-input"
            placeholder="请描述您想创建的动画或小游戏..."
            rows="4"
          ></textarea>
          <div class="animation-chatbox-bottom">
            <div class="animation-chatbox-left">
              <img :src="linkFileImg" class="attach-icon" alt="上传文件" title="上传文件" />
              <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
                <img :src="voiceImg" class="voice-icon-img" alt="语音" />
              </button>
            </div>
            <button class="send-btn" @click="handleSend"><img :src="sendImg" class="send-btn-icon" alt="" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- 发送后：左右两栏布局 -->
    <div v-else class="animation-two-column">
      <div class="animation-left">
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
          <textarea
            v-model="animationInput"
            class="animation-input"
            placeholder="输入消息发送..."
            rows="2"
          ></textarea>
          <div class="animation-chatbox-bottom">
            <div class="animation-chatbox-left">
              <img :src="linkFileImg" class="attach-icon" alt="上传文件" title="上传文件" />
              <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
                <img :src="voiceImg" class="voice-icon-img" alt="语音" />
              </button>
            </div>
            <button class="send-btn" @click="handleSend"><img :src="sendImg" class="send-btn-icon" alt="" /></button>
          </div>
        </div>
      </div>
      <div class="animation-right">
        <div class="code-panel-header">
          <h3 class="code-panel-title">代码 (HTML)</h3>
          <div class="code-panel-actions">
            <button class="code-action-btn" @click="copyCode">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </span>
              复制
            </button>
            <button class="code-action-btn">
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
            <button class="code-action-btn">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
              </span>
              全屏
            </button>
            <button class="code-action-btn" @click="clearCode">
              <span class="code-action-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
              </span>
              清空
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
          <pre v-show="codeTab === 'content'" class="code-display"><code>{{ generatedCode }}</code></pre>
          <div v-show="codeTab === 'preview'" class="preview-display">
            <iframe v-if="generatedCode" :srcdoc="generatedCode" class="preview-iframe" sandbox="allow-scripts" title="预览" />
            <div v-else class="preview-empty">暂无内容可预览</div>
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
}

.animation-panel {
  position: relative;
  padding: 20px 32px 18px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
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
  gap: 16px;
}

.animation-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

/* 对话部分单独滚动，整体页面不动 */
.animation-chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 0;
}

.chat-msg {
  margin-bottom: 16px;
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
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
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
  overflow: auto;
  overflow-x: hidden;
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
  min-height: 300px;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  min-height: 300px;
  border: none;
}

.preview-empty {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
}
</style>
