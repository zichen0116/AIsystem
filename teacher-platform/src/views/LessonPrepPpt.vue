<script setup>
import { ref, watch } from 'vue'
import arrowGreenImg from '../assets/arrow-green.png'
import voiceImg from '../assets/语音.png'
import { useVoiceInput } from '../composables/useVoiceInput'

const pptTopic = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(pptTopic)
const pptStyleTab = ref('style')
const selectedStyle = ref('free')

const pptStyles = [
  { id: 'free', name: '自由风格', selected: true },
  { id: 'academic', name: '学术' },
  { id: 'minimal', name: '极简' },
  { id: 'pro', name: '专业' }
]

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
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)
</script>

<template>
  <div class="content-panel ppt-panel">
    <div class="ppt-hero">
      <h1 class="ppt-hero-title">PPT与教案生成</h1>
      <p class="ppt-hero-sub">输入主题，AI自动生成专业PPT内容。支持多种风格模板，智能内容填充，让备课更高效</p>
    </div>
    <div class="ppt-chatbox">
      <div class="ppt-chatbox-top">
        <button class="style-btn-inline active">自由风格</button>
        <input v-model="pptTopic" type="text" class="ppt-topic-input" placeholder="输入你想创作的PPT 主题" />
      </div>
      <div class="ppt-chatbox-bottom">
        <div class="ppt-control-bar">
          <button class="ctrl-btn">+</button>
          <button class="ctrl-btn">自动页数 ▼</button>
          <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
            <img :src="voiceImg" class="voice-icon-img" alt="语音" />
          </button>
        </div>
        <button class="ppt-submit-btn"><img :src="arrowGreenImg" class="ppt-submit-btn-icon" alt="" /></button>
      </div>
    </div>
    <div class="ppt-tabs">
      <button class="ppt-tab" :class="{ active: pptStyleTab === 'style' }" @click="pptStyleTab = 'style'">选择风格</button>
      <button class="ppt-tab" :class="{ active: pptStyleTab === 'template' }" @click="pptStyleTab = 'template'">选择模版</button>
    </div>
    <div class="ppt-style-grid">
      <div v-for="s in pptStyles" :key="s.id" class="style-card" :class="{ selected: selectedStyle === s.id }" @click="selectedStyle = s.id">
        <div class="style-preview style-free" v-if="s.id === 'free'">
          <span v-if="selectedStyle === 'free'" class="check-mark">✓</span>
          <span v-if="selectedStyle === 'free'" class="selected-tag">已选择</span>
        </div>
        <div class="style-preview style-academic" v-else-if="s.id === 'academic'">
          <span class="preview-text">数字化教育转型 开辟教育发展新赛道</span>
        </div>
        <div class="style-preview style-minimal" v-else-if="s.id === 'minimal'">
          <span class="preview-text">共享经济在出行领域的演进</span>
        </div>
        <div class="style-preview style-pro" v-else>
          <span class="preview-text">全球半导体 产业链格局分析</span>
        </div>
        <span class="style-name">{{ s.name }}</span>
      </div>
      <div class="style-card">
        <div class="style-preview style-green">
          <span class="preview-text">新能源汽车 电池技术路线对比</span>
          <div class="three-dots">
            <span class="dot green"></span>
            <span class="dot orange"></span>
            <span class="dot red"></span>
          </div>
        </div>
        <span class="style-name">技术对比</span>
      </div>
      <div class="style-card">
        <div class="style-preview style-white">
          <span class="preview-text">冥想与正念的神经科学研究进展</span>
        </div>
        <span class="style-name">学术研究</span>
      </div>
      <div class="style-card">
        <div class="style-preview style-memphis">
          <div class="memphis-shapes">
            <span class="shape shape-diamond"></span>
            <span class="shape shape-rect"></span>
            <span class="shape shape-circle"></span>
            <span class="shape shape-dot"></span>
          </div>
          <span class="preview-text">孟菲斯设计运动 与后现代主义</span>
        </div>
        <span class="style-name">设计风格</span>
      </div>
      <div class="style-card">
        <div class="style-preview style-bold">
          <span class="preview-text">颠覆 变革 打破规则</span>
        </div>
        <span class="style-name">创意</span>
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

.ppt-panel {
  padding: 32px;
  overflow-y: auto;
}

.ppt-hero {
  max-width: 960px;
  margin: 12px auto 8px auto;
  text-align: center;
  padding: 24px 12px 8px 12px;
}

.ppt-hero-title {
  font-size: 42px;
  background: linear-gradient(90deg, #2b5496 0%, #4080e8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-fill-color: transparent;
  margin: -28px 0 12px 0;
  font-weight: 700;
}

.ppt-hero-sub {
  color: #6b7f99;
  font-size: 16px;
  margin: -5px;
}

.ppt-chatbox {
  width: 75%;
  aspect-ratio: 7 / 1;
  min-height: 150px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
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
  padding: 10px 18px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 14px;
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
  font-size: 15px;
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
  width: 220px; /* 修复：添加空格，规范书写 */
  height: 130px; /* 修复：添加空格，规范书写 */
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.2s;
}

.style-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.style-card.selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
}

.style-preview {
  width: 100%; /* 修复：添加空格，规范书写 */
  height: 78%; /* 修复：添加空格，规范书写 */
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  position: relative;
}

.style-free {
  background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 30%, #e0e7ff 70%, #c7d2fe 100%);
}

.style-academic {
  background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 30%, #e5e7eb 100%);
}

.style-minimal {
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.style-pro {
  background: #1e293b;
}

.style-green {
  background: #dcfce7;
}

.style-white {
  background: #fff;
}

.style-memphis {
  background: #fff;
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
  background: linear-gradient(135deg, #fff 0%, #fff 55%, #ef4444 55%);
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

@media (max-width: 900px) {
  .ppt-style-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>