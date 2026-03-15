<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import arrowGreenImg from '../assets/arrow-green.png'
import voiceImg from '../assets/语音.png'
import { useVoiceInput } from '../composables/useVoiceInput'

const pptTopic = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(pptTopic)
const pptStyleTab = ref('style')
const selectedStyle = ref('free')

const pptStyles = [
  { id: 'free', name: '自由风格' },
  { id: 'business', name: '商务简约' },
  { id: 'tech', name: '科技质感' },
  { id: 'fresh', name: '清新文艺' },
  { id: 'academic', name: '学术汇报' },
  { id: 'guofeng', name: '国风国潮' },
  { id: 'minimal', name: '极简高级' },
  { id: 'creative', name: '创意插画' }
]

const styleButtonGradients = {
  free: 'linear-gradient(135deg, #FFE0D5 0%,rgb(255, 223, 179) 100%)',
  business: 'linear-gradient(135deg,rgb(206, 225, 246) 0%, #E2E8F0 100%)',
  tech: 'linear-gradient(135deg,rgb(186, 223, 255) 0%,rgb(201, 224, 255) 100%)',
  fresh: 'linear-gradient(135deg,rgb(209, 249, 223) 0%,rgb(207, 255, 233) 100%)',
  academic: 'linear-gradient(135deg,rgb(239, 232, 255) 0%, #D3E2F0 100%)',
  guofeng: 'linear-gradient(135deg, #F9CCD3 0%,rgb(255, 194, 177) 100%)',
  minimal: 'linear-gradient(135deg, #E5E7EB 0%, #F3F4F6 100%)',
  creative: 'linear-gradient(135deg,rgb(253, 214, 255) 0%,rgb(255, 254, 222) 100%)'
}

const currentStyle = computed(() => pptStyles.find(s => s.id === selectedStyle.value) || pptStyles[0])
const styleButtonBackground = computed(() => styleButtonGradients[selectedStyle.value] || styleButtonGradients.free)

// 发送后布局
const hasSentMessages = ref(false)
const messages = ref([])
const isSending = ref(false)

// PPT 展示区：幻灯片缩略图（占位）
const pptSlides = ref([{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }])
const activeSlideIndex = ref(0)
const pptThumbnailsCollapsed = ref(false)
const pptZoom = ref(71)
const pptTitle = ref('中国传统文化PPT')
const speakerNotes = ref('大家好，欢迎来到今天的分享。今天，我们将一同走进华夏文明的长河，探寻中国传统文化的璀璨瑰宝。这份PPT将带您领略从古老的思想哲学到绚丽的传统艺术，从庄重的节日习俗到精致的饮食文化……')

// 文件选择
const fileInput = ref(null)
const uploadResult = ref(null)

function getApiBase() {
  const base = (import.meta.env?.VITE_API_BASE || '').trim()
  return (base || 'http://127.0.0.1:8000').replace(/\/+$/, '')
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
    if (hasSentMessages.value) {
      messages.value.push({
        role: 'assistant',
        content: `已上传「${res.filename}」，已提取 ${res.extracted_length} 字。后续生成会结合该文件内容。`
      })
    }
    await nextTick()
  } catch (err) {
    if (hasSentMessages.value) {
      messages.value.push({
        role: 'assistant',
        content: '上传失败：' + (err?.message || String(err))
      })
    }
  }
  e.target.value = ''
}

function handleSend() {
  const text = pptTopic.value?.trim()
  if (!text || isSending.value) return

  isSending.value = true
  messages.value.push({ role: 'user', content: text })
  pptTopic.value = ''
  hasSentMessages.value = true

  messages.value.push({
    role: 'assistant',
    content: '已收到您的需求，PPT 生成功能正在开发中，请期待后续更新。'
  })
  isSending.value = false
}

const props = defineProps({
  resetKey: {
    type: Number,
    default: 0
  }
})

function resetState() {
  pptTopic.value = ''
  pptStyleTab.value = 'style'
  selectedStyle.value = 'free'
  hasSentMessages.value = false
  messages.value = []
  uploadResult.value = null
  activeSlideIndex.value = 0
  pptTitle.value = '中国传统文化PPT'
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)
</script>

<template>
  <div class="content-panel ppt-panel" :class="{ 'ppt-panel-two-col': hasSentMessages }">
    <input
      ref="fileInput"
      type="file"
      class="hidden-file-input"
      accept=".pdf,.doc,.docx,.ppt,.pptx,.txt"
      @change="onFileSelect"
    />

    <!-- 初始布局：居中输入区 + 风格选择 -->
    <template v-if="!hasSentMessages">
      <div class="ppt-hero">
        <h1 class="ppt-hero-title">智能PPT生成</h1>
        <p class="ppt-hero-sub">输入主题，AI自动生成专业PPT内容。支持多种风格模板，智能内容填充，让备课更高效</p>
      </div>
      <div class="ppt-chatbox">
        <div class="ppt-chatbox-top">
          <button
            class="style-btn-inline active"
            :style="{ background: styleButtonBackground, color: '#ffffff' }"
          >
            {{ currentStyle.name }}
          </button>
          <input v-model="pptTopic" type="text" class="ppt-topic-input" placeholder="输入你想创作的PPT 主题" />
        </div>
        <div v-if="uploadResult" class="ppt-upload-banner">
          <span class="ppt-upload-title">已选择文件</span>
          <span class="ppt-upload-name">{{ uploadResult.filename }}</span>
          <span class="ppt-upload-meta">提取 {{ uploadResult.extracted_length }} 字</span>
          <button type="button" class="ppt-upload-remove" title="移除附件" @click="clearUpload">×</button>
        </div>
        <div class="ppt-chatbox-bottom">
          <div class="ppt-control-bar">
            <button class="ctrl-btn" type="button" title="选择本地文件" @click="triggerUpload">+</button>
            <button class="ctrl-btn">自动页数 ▼</button>
            <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
              <img :src="voiceImg" class="voice-icon-img" alt="语音" />
            </button>
          </div>
          <button class="ppt-submit-btn" type="button" @click="handleSend"><img :src="arrowGreenImg" class="ppt-submit-btn-icon" alt="发送" /></button>
        </div>
      </div>
      <div class="ppt-tabs">
        <button class="ppt-tab" :class="{ active: pptStyleTab === 'template' }" @click="pptStyleTab = 'template'">选择模版</button>
      </div>
      <div class="ppt-style-grid">
        <div v-for="s in pptStyles" :key="s.id" class="style-card" :class="{ selected: selectedStyle === s.id }" @click="selectedStyle = s.id">
          <div class="style-preview style-free" v-if="s.id === 'free'">
            <span v-if="selectedStyle === 'free'" class="check-mark">✓</span>
            <span v-if="selectedStyle === 'free'" class="selected-tag">已选择</span>
          </div>
          <div class="style-preview style-business" v-else-if="s.id === 'business'">
            <span class="preview-text">季度业绩总结 · 商务路演</span>
          </div>
          <div class="style-preview style-tech" v-else-if="s.id === 'tech'">
            <span class="preview-text">AI 与智能教育 平台方案介绍</span>
          </div>
          <div class="style-preview style-fresh" v-else-if="s.id === 'fresh'">
            <span class="preview-text">阅读分享会 青春校园主题</span>
          </div>
          <div class="style-preview style-academic" v-else-if="s.id === 'academic'">
            <span class="preview-text">教育数据分析 教学效果评估</span>
          </div>
          <div class="style-preview style-guofeng" v-else-if="s.id === 'guofeng'">
            <span class="preview-text">中华传统文化主题 课堂展示</span>
          </div>
          <div class="style-preview style-minimal" v-else-if="s.id === 'minimal'">
            <span class="preview-text">课堂重点梳理 极简信息图表</span>
          </div>
          <div class="style-preview style-creative" v-else>
            <span class="preview-text">科普故事 创意插画课堂</span>
          </div>
          <span class="style-name">{{ s.name }}</span>
        </div>
      </div>
    </template>

    <!-- 发送后：左对话区 + 右展示区（与动游制作一致） -->
    <div v-else class="ppt-two-column">
      <div class="ppt-left">
        <div class="ppt-chat-messages">
          <div v-for="(msg, i) in messages" :key="i" class="ppt-chat-msg" :class="msg.role">
            <span class="ppt-chat-label">{{ msg.role === 'user' ? '我' : '小助手' }}</span>
            <div class="ppt-chat-content">{{ msg.content }}</div>
          </div>
        </div>
        <div class="ppt-chatbox-compact">
          <div v-if="uploadResult" class="ppt-upload-banner ppt-upload-banner-compact">
            <span class="ppt-upload-title">已选择文件</span>
            <span class="ppt-upload-name">{{ uploadResult.filename }}</span>
            <span class="ppt-upload-meta">提取 {{ uploadResult.extracted_length }} 字</span>
            <button type="button" class="ppt-upload-remove" title="移除附件" @click="clearUpload">×</button>
          </div>
          <div class="ppt-compact-top">
            <button
              class="style-btn-inline active"
              :style="{ background: styleButtonBackground, color: '#ffffff' }"
            >
              {{ currentStyle.name }}
            </button>
          </div>
          <input v-model="pptTopic" type="text" class="ppt-topic-input-compact" placeholder="输入消息发送..." />
          <div class="ppt-compact-bottom">
            <div class="ppt-control-bar">
              <button class="ctrl-btn" type="button" title="选择本地文件" @click="triggerUpload">+</button>
              <button class="ctrl-btn">自动页数 ▼</button>
              <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
                <img :src="voiceImg" class="voice-icon-img" alt="语音" />
              </button>
            </div>
            <button class="ppt-submit-btn" type="button" :disabled="isSending" @click="handleSend"><img :src="arrowGreenImg" class="ppt-submit-btn-icon" alt="发送" /></button>
          </div>
        </div>
      </div>
      <div class="ppt-right">
        <!-- 左侧：幻灯片缩略图 -->
        <aside class="ppt-thumbnails" :class="{ collapsed: pptThumbnailsCollapsed }">
          <button type="button" class="ppt-new-slide-btn">+ 新建幻灯片</button>
          <button type="button" class="ppt-collapse-btn" :title="pptThumbnailsCollapsed ? '展开' : '收起'" @click="pptThumbnailsCollapsed = !pptThumbnailsCollapsed">
            {{ pptThumbnailsCollapsed ? '→' : '←' }}
          </button>
          <div class="ppt-thumb-list">
            <div
              v-for="(slide, i) in pptSlides"
              :key="slide.id"
              class="ppt-thumb-item"
              :class="{ active: activeSlideIndex === i }"
              @click="activeSlideIndex = i"
            >
              <span class="ppt-thumb-num">{{ i + 1 }}</span>
              <div class="ppt-thumb-preview" />
            </div>
          </div>
        </aside>
        <!-- 右侧主内容区 -->
        <div class="ppt-main">
          <header class="ppt-main-header">
            <h3 class="ppt-main-title">{{ pptTitle }}</h3>
            <div class="ppt-main-actions">
              <button type="button" class="ppt-action-btn">▷ 放映</button>
              <button type="button" class="ppt-action-btn">分享</button>
              <button type="button" class="ppt-action-btn">下载</button>
              <span class="ppt-action-ellipsis">…</span>
            </div>
          </header>
          <div class="ppt-toolbar">
            <div class="ppt-toolbar-left">
              <span class="ppt-tool-item">文本</span>
              <span class="ppt-tool-item">图形</span>
              <span class="ppt-tool-item">图片</span>
              <span class="ppt-tool-item">表格</span>
              <span class="ppt-tool-item">格式</span>
              <span class="ppt-tool-item">动画</span>
            </div>
            <div class="ppt-toolbar-right">
              <button type="button" class="ppt-zoom-btn">−</button>
              <span class="ppt-zoom-value">{{ pptZoom }}%</span>
              <button type="button" class="ppt-zoom-btn">+</button>
            </div>
          </div>
          <div class="ppt-slide-preview">
            <div class="ppt-slide-canvas">
              <div class="ppt-slide-placeholder">
                <p class="ppt-slide-title">华夏之光：中国传统文化概览</p>
                <p class="ppt-slide-subtitle">探寻千年文明的璀璨瑰宝</p>
                <div class="ppt-slide-btn">传承</div>
                <p class="ppt-slide-credit">由 AI 生成</p>
              </div>
            </div>
          </div>
          <div class="ppt-speaker-notes">
            <div class="ppt-notes-handle">⋮⋮⋮</div>
            <textarea v-model="speakerNotes" class="ppt-notes-input" placeholder="添加演讲者备注…" rows="3"></textarea>
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

.hidden-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.ppt-panel {
  padding: 55px 32px 32px;
  overflow-y: auto;
}

.ppt-panel.ppt-panel-two-col {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ppt-upload-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 8px;
}

.ppt-upload-title {
  color: #64748b;
}

.ppt-upload-name {
  color: #0f172a;
  font-weight: 500;
}

.ppt-upload-meta {
  color: #94a3b8;
  font-size: 12px;
}

.ppt-upload-remove {
  margin-left: auto;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

.ppt-upload-remove:hover {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}

.ppt-hero {
  max-width: 960px;
  margin: 12px auto 8px auto;
  text-align: center;
  padding: 24px 12px 8px 12px;
}

.ppt-hero-title {
  font-size: 43px;
  background: linear-gradient(90deg, #1f3d7a 0%, #2563eb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-fill-color: transparent;
  margin: -28px 0 12px 0;
  font-weight: 700;
}

.ppt-hero-sub {
  color: #4b5f7a;
  font-size: 17px;
  margin: -5px;
}

.ppt-chatbox {
  width: 78%;
  aspect-ratio: 7 / 1;
  min-height: 150px;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  background: #fdfefe;
  margin: 15px auto 24px auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
}

.ppt-chatbox:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.ppt-chatbox-top {
  display: flex;
  align-items: center;
  gap: 16px;
}

.style-btn-inline {
  padding: 11px 22px;
  border: none;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #fff;
  font-size: 15px;
  cursor: pointer;
  flex-shrink: 0;
  border-radius: 8px;
}

.style-btn-inline:not(.active) {
  background: #e2e8f0;
  color: #64748b;
}

.ppt-topic-input {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 0;
  font-size: 16px;
  outline: none;
  background: transparent;
}

.ppt-topic-input::placeholder {
  color: #94a3b8;
}

.ppt-chatbox-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ppt-control-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ppt-submit-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: #e2e8f0;
  color: #64748b;
  border-radius: 50%;
  font-size: 1.25rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.ppt-submit-btn:hover {
  background: #cbd5e1;
}

.ppt-submit-btn-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.ctrl-btn {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
}

.ctrl-btn.agent {
  border-color: #3b82f6;
  color: #3b82f6;
}

.voice-btn {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-btn:hover {
  background: #f8fafc;
}

.voice-btn.recording {
  background: #fecaca;
  border-color: #fecaca;
  animation: ppt-voice-pulse 1.5s ease-in-out infinite;
}

@keyframes ppt-voice-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.voice-icon-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.ppt-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 15px;
  max-width: 960px;
  margin-left: auto;
  margin-right: auto;
  width: 100%;
}

.ppt-tab {
  padding: 10px 20px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  border-radius: 0;
  border-bottom: 2px solid transparent;
}

.ppt-tab.active {
  color: #3b82f6;
  font-weight: 500;
  border-bottom-color: #3b82f6;
}

.ppt-style-grid {
  display: grid;
  justify-items: center;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  max-width: 960px;
  margin: 0 auto;
}

.style-card {
  width: 220px;
  height: 130px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: radial-gradient(circle at 0 0, rgba(248, 250, 252, 0.9), transparent 55%),
    #ffffff;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.style-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.12);
  border-color: rgba(59, 130, 246, 0.28);
}

.style-card.selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.55), 0 18px 40px rgba(37, 99, 235, 0.25);
}

.style-preview {
  width: 100%;
  height: 78%;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  position: relative;
  border-radius: 16px 16px 0 0;
  overflow: hidden;
}

.style-free {
  background: linear-gradient(135deg, #FFE0D5 0%,rgb(255, 223, 179) 100%);
}

.style-business {
  background: linear-gradient(135deg,rgb(206, 225, 246) 0%, #E2E8F0 100%);
}

.style-tech {
  background: linear-gradient(135deg,rgb(186, 223, 255) 0%,rgb(201, 224, 255) 100%);
}

.style-fresh {
  background: linear-gradient(135deg,rgb(209, 249, 223) 0%,rgb(207, 255, 233) 100%);
}

.style-academic {
  background: linear-gradient(135deg,rgb(239, 232, 255) 0%, #D3E2F0 100%);
}

.style-minimal {
  background: linear-gradient(135deg, #E5E7EB 0%, #F3F4F6 100%);
  border-bottom: 1px solid #e2e8f0;
}

.style-guofeng {
  background: linear-gradient(135deg, #F9CCD3 0%,rgb(255, 194, 177) 100%);
}

.style-creative {
  background: linear-gradient(135deg,rgb(253, 214, 255) 0%,rgb(255, 254, 222) 100%);
}

.memphis-shapes {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.shape {
  display: inline-block;
}

.shape-diamond {
  width: 16px;
  height: 16px;
  background: #eab308;
  transform: rotate(45deg);
}

.shape-rect {
  width: 20px;
  height: 12px;
  background: #ec4899;
}

.shape-circle {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #3b82f6;
}

.shape-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.style-bold {
  background: linear-gradient(135deg, #ffffff 0%, #fee2e2 40%,rgb(220, 91, 91) 40%,rgb(206, 77, 77) 100%);
}

.style-bold .preview-text {
  color: #1e293b;
  font-weight: 700;
}

.three-dots {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.green { background: #22c55e; }
.dot.orange { background: #f97316; }
.dot.red { background: #ef4444; }

.check-mark {
  position: absolute;
  top: 12px;
  left: 12px;
  font-size: 1.2rem;
  color: #22c55e;
}

.selected-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  font-size: 0.75rem;
  color: #64748b;
}

.preview-text {
  font-size: 0.85rem;
  color: #1e293b;
  font-weight: 500;
}

.style-pro .preview-text {
  color: #fff;
}

.style-name {
  padding: 10px 16px;
  font-size: 0.875rem;
  color: #475569;
  background: #fff;
  border-top: 1px solid #f1f5f9;
  display: block; /* 修复：span 标签添加块级显示，确保样式生效 */
}

/* 发送后：左对话区 + 右展示区（与动游制作一致） */
.ppt-two-column {
  display: flex;
  flex: 1;
  min-height: 0;
  max-height: 100%;
  gap: 16px;
  overflow: hidden;
  padding: 20px 32px;
}

.ppt-left {
  flex: 0 0 380px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.ppt-chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 0;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ppt-chat-messages::-webkit-scrollbar {
  display: none;
}

.ppt-chat-msg {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
}

.ppt-chat-msg.user {
  align-items: flex-end;
}

.ppt-chat-msg.assistant {
  align-items: flex-start;
}

.ppt-chat-label {
  font-size: 13px;
  margin-bottom: 4px;
  display: block;
  color: #64748b;
}

.ppt-chat-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.ppt-chat-msg.user .ppt-chat-content {
  background: #E0EDFE;
  color: #000;
}

.ppt-chat-msg.assistant .ppt-chat-content {
  background: #fff;
  color: #000;
}

.ppt-chatbox-compact {
  flex-shrink: 0;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  background: #fdfefe;
  padding: 12px 16px;
}

.ppt-chatbox-compact:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.ppt-upload-banner-compact {
  margin-bottom: 8px;
}

.ppt-compact-top {
  margin-bottom: 8px;
}

.ppt-topic-input-compact {
  width: 100%;
  border: none;
  outline: none;
  font-size: 15px;
  padding: 8px 0;
  background: transparent;
}

.ppt-topic-input-compact::placeholder {
  color: #94a3b8;
}

.ppt-compact-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.ppt-right {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

/* 左侧幻灯片缩略图栏 */
.ppt-thumbnails {
  width: 160px;
  min-width: 160px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e2e8f0;
  background: #f8fafc;
  transition: width 0.2s, min-width 0.2s;
}

.ppt-thumbnails.collapsed {
  width: 48px;
  min-width: 48px;
}

.ppt-thumbnails.collapsed .ppt-new-slide-btn,
.ppt-thumbnails.collapsed .ppt-thumb-list {
  display: none;
}

.ppt-new-slide-btn {
  margin: 12px 10px 8px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  text-align: left;
}

.ppt-new-slide-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.ppt-collapse-btn {
  align-self: flex-start;
  margin: 4px 8px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
}

.ppt-collapse-btn:hover {
  color: #0f172a;
}

.ppt-thumb-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ppt-thumb-item {
  position: relative;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 16/9;
  background: #fff;
}

.ppt-thumb-item:hover {
  border-color: #cbd5e1;
}

.ppt-thumb-item.active {
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
}

.ppt-thumb-num {
  position: absolute;
  top: 4px;
  left: 6px;
  font-size: 11px;
  color: #64748b;
  z-index: 1;
}

.ppt-thumb-preview {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}

.ppt-thumb-item.active .ppt-thumb-preview {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
}

/* 右侧主内容区 */
.ppt-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ppt-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.ppt-main-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.ppt-main-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ppt-action-btn {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
}

.ppt-action-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.ppt-action-ellipsis {
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 4px;
}

.ppt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.ppt-toolbar-left {
  display: flex;
  gap: 12px;
}

.ppt-tool-item {
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.ppt-tool-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.ppt-toolbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ppt-zoom-btn {
  width: 24px;
  height: 24px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 4px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.ppt-zoom-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.ppt-zoom-value {
  font-size: 13px;
  color: #64748b;
  min-width: 40px;
  text-align: center;
}

.ppt-slide-preview {
  flex: 1;
  min-height: 0;
  padding: 24px;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ppt-slide-canvas {
  width: 100%;
  max-width: 720px;
  aspect-ratio: 16/9;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 20%, #fef9c3 100%);
  border: 1px solid #fcd34d;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}

.ppt-slide-placeholder {
  text-align: center;
  padding: 24px;
}

.ppt-slide-title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 700;
  color: #c2410c;
}

.ppt-slide-subtitle {
  margin: 0 0 16px;
  font-size: 14px;
  color: #64748b;
}

.ppt-slide-btn {
  display: inline-block;
  padding: 10px 24px;
  background: #dc2626;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  margin-bottom: 20px;
}

.ppt-slide-credit {
  margin: 0;
  font-size: 11px;
  color: #94a3b8;
}

.ppt-speaker-notes {
  flex-shrink: 0;
  border-top: 1px solid #e2e8f0;
  padding: 12px 16px 16px;
  position: relative;
}

.ppt-notes-handle {
  text-align: center;
  font-size: 12px;
  color: #cbd5e1;
  margin-bottom: 6px;
  letter-spacing: 2px;
}

.ppt-notes-input {
  width: 100%;
  min-height: 70px;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  color: #334155;
  resize: vertical;
  font-family: inherit;
}

.ppt-notes-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.ppt-notes-input::placeholder {
  color: #94a3b8;
}

@media (max-width: 900px) {
  .ppt-style-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .ppt-two-column {
    flex-direction: column;
    padding: 16px;
  }
  .ppt-left {
    flex: 0 0 auto;
    max-height: 45vh;
  }
  .ppt-right {
    min-height: 400px;
  }
  .ppt-thumbnails {
    width: 120px;
    min-width: 120px;
  }
  .ppt-slide-canvas {
    max-width: 100%;
  }
}
</style>