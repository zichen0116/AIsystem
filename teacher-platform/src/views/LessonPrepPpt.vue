<script setup>
import { ref, watch, computed } from 'vue'
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
  padding: 55px 32px 32px;
  overflow-y: auto;
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

@media (max-width: 900px) {
  .ppt-style-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>