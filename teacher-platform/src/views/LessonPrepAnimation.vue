<script setup>
import { ref, computed } from 'vue'
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

</script>

<template>
  <div class="content-panel animation-panel">
    <!-- 顶部固定高度，保证说明/选项/聊天框位置与动画页一致 -->
    <div class="animation-content">
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
            <button class="send-btn"><img :src="sendImg" class="send-btn-icon" alt="" /></button>
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
  background: #fff;
  margin: 0;
  overflow: hidden;
}

.animation-panel {
  position: relative;
  padding: 48px 32px;
  min-height: 400px;
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
  background: linear-gradient(90deg, #e0e7ff 0%, #d1fae5 100%);
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
}

.animation-tab {
  padding: 10px 28px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
}

.animation-tab:hover {
  color: #475569;
}

.animation-tab.active {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
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
  max-width: 640px;
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
</style>
