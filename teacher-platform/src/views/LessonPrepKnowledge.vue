<script setup>
import { ref } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
import linkFileImg from '../assets/链接文件.png'
import voiceImg from '../assets/语音.png'
import aiAnimationFlow from '../assets/ai animation Flow 1.json'
import { useVoiceInput } from '../composables/useVoiceInput'

const activeTab = ref('knowledge')
const promptText = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(promptText)

const tabs = [
  { id: 'knowledge', name: '知识图谱' },
  { id: 'flowchart', name: '思维导图' }
]
</script>

<template>
  <div class="content-panel knowledge-panel">
    <div class="knowledge-header">
      <div class="knowledge-lottie">
        <LottiePlayer :animation-data="aiAnimationFlow" />
      </div>
      <p class="knowledge-subtitle">借助 AI 驱动的知识图谱生成器，只需简单几步即可在短时间内创建和部署您的知识图谱、思维导图。</p>
    </div>
    <div class="knowledge-tabs-wrap">
    <div class="knowledge-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="knowledge-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.name }}
      </button>
    </div>
    </div>
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
  background: #fff;
  margin: 0;
  overflow: hidden;
}

.knowledge-panel {
  padding: 48px 32px;
  background-image:
    linear-gradient(rgba(0, 0, 0, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px);
  background-size: 24px 24px;
  background-color: #fff;
}

.knowledge-header {
  text-align: center;
  margin-bottom: 48px;
}

.knowledge-lottie {
  width: 160px;
  height: 160px;
  margin: 0 auto 24px;
}

.knowledge-lottie :deep(.lottie-container) {
  min-height: 0;
  width: 160px;
  height: 160px;
}

.knowledge-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 12px;
  line-height: 1.3;
}

.knowledge-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
}

.knowledge-tabs-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 48px;
}

.knowledge-tabs {
  display: inline-flex;
  background: linear-gradient(90deg, #e0e7ff 0%, #d1fae5 100%);
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
}

.knowledge-tab {
  padding: 10px 24px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
}

.knowledge-tab:hover {
  color: #475569;
}

.knowledge-tab.active {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
}

.knowledge-input-wrap {
  width: 75%;
  margin: 0 auto;
}

.knowledge-input-box {
  border: 2px solid #8b5cf6;
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 160px;
}

.knowledge-textarea {
  flex: 1;
  padding: 20px 20px 12px;
  border: none;
  outline: none;
  font-size: 15px;
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
}
</style>
