<script setup>
import { ref, watch } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
import linkFileImg from '../assets/链接文件.png'
import voiceImg from '../assets/语音.png'
import aiAnimationFlow from '../assets/ai animation Flow 1.json'
import { useVoiceInput } from '../composables/useVoiceInput'

const promptText = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(promptText)
const selectedLayout = ref('center')

const props = defineProps({
  resetKey: {
    type: Number,
    default: 0
  }
})

function resetState() {
  promptText.value = ''
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)
</script>

<template>
  <div class="content-panel knowledge-panel">
    <div class="knowledge-header">
      <div class="knowledge-lottie">
        <LottiePlayer :animation-data="aiAnimationFlow" />
      </div>
      <p class="knowledge-subtitle">
        借助 AI 驱动的思维导图生成器，只需输入主题与关键要点，就能快速构建清晰直观的知识结构图。
      </p>
    </div>

    <!-- 模板布局区域 -->
    <section class="layout-section">
      <div class="layout-grid">
        <div class="layout-label-card">选择导图布局</div>
        <button
          type="button"
          class="layout-card"
          :class="{ active: selectedLayout === 'center' }"
          @click="selectedLayout = 'center'"
        >
          <h3 class="layout-name">中心放射</h3>
        </button>
        <button
          type="button"
          class="layout-card"
          :class="{ active: selectedLayout === 'split' }"
          @click="selectedLayout = 'split'"
        >
          <h3 class="layout-name">左右分栏</h3>
        </button>
        <button
          type="button"
          class="layout-card"
          :class="{ active: selectedLayout === 'timeline' }"
          @click="selectedLayout = 'timeline'"
        >
          <h3 class="layout-name">时间轴</h3>
        </button>
      </div>
    </section>

    <div class="knowledge-input-wrap">
      <div class="knowledge-input-box">
        <textarea
          v-model="promptText"
          class="knowledge-textarea"
          placeholder="请描述您想创建的内容..."
          rows="5"
        ></textarea>
        <div class="knowledge-input-footer">
          <div class="knowledge-footer-left">
            <button class="upload-btn" title="上传文件">
              <img :src="linkFileImg" class="upload-icon" alt="" />
            </button>
            <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
              <img :src="voiceImg" class="voice-icon-img" alt="语音" />
            </button>
          </div>
          <button class="generate-btn">
            <span class="generate-icon">✨</span>
            <span>AI生成</span>
          </button>
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

.knowledge-panel {
  padding: 72px 40px 24px;
  background: transparent;
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

.layout-section {
  max-width: 900px;
  margin: 0 auto 28px;
}

.layout-label-card {
  margin: 0;
  padding: 13px 16px;
  border-radius: 999px;
  background: #e5edff;
  color: #1f2933;
  font-size: 0.95rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2933;
  margin: 0 0 12px;
}

.layout-grid {
  display: flex;
  flex-wrap: nowrap;
  gap: 16px;
  align-items: center;
}

.layout-card {
  flex: 0 0 110px;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.layout-name {
  margin: 0 0 6px;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}

.layout-card:hover {
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
  border-color: #bfdbfe;
  transform: translateY(-2px);
}

.layout-card.active {
  border-color: #2563eb;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.25);
  color: #2563eb;
}

@media (max-width: 900px) {
  .layout-grid {
    flex-wrap: wrap;
  }
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
  width: 75%;
  margin: 0 auto;
}

.knowledge-input-box {
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  background: #fdfefe;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 180px;
}

.knowledge-input-box:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.knowledge-textarea {
  flex: 1;
  padding: 20px 20px 12px;
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
  padding: 12px 20px 16px;
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
</style>
