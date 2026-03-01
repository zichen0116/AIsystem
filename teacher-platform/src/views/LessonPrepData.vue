<script setup>
import { ref, watch } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
import linkFileImg from '../assets/链接文件.png'
import voiceImg from '../assets/语音.png'
import arrowGreenImg from '../assets/arrow-green.png'
import sendImg from '../assets/发送.png'
import dataAnalysisAnimation from '../assets/Data Analysis Animation _ Visualize Insights Effectively.json'
import { useVoiceInput } from '../composables/useVoiceInput'

const dataInput = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(dataInput)

const dataExamples = [
  '北京未来七天气温,做个折线图',
  '帮我生成一个二维码,扫码后打开chatglm.cn'
]

const props = defineProps({
  resetKey: {
    type: Number,
    default: 0
  }
})

function resetState() {
  dataInput.value = ''
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)
</script>

<template>
  <div class="content-panel data-panel">
    <div class="data-header">
      <div class="data-icon">
        <LottiePlayer :animation-data="dataAnalysisAnimation" />
      </div>
      <p class="data-desc">通过分析用户上传文件或数据说明，帮助用户分析数据并提供图表化的能力。也可通过简单的编码完成文件处理的工作。</p>
    </div>
    <div class="data-examples">
      <button v-for="(ex, i) in dataExamples" :key="i" class="example-card">{{ ex }}</button>
    </div>
    <div class="data-input-area">
      <div class="data-actions-row">
        <button class="new-chat-btn">+ 新建对话</button>
      </div>
      <div class="data-chatbox">
        <textarea v-model="dataInput" class="data-input" placeholder="输入你的问题或需求" rows="3"></textarea>
        <div class="chatbox-bottom">
          <div class="chatbox-left">
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

.data-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 24px 24px;
  overflow-y: auto;
}

.data-header {
  text-align: center;
  max-width: 560px;
  margin-bottom: 16px;
}

.data-icon {
  width: 200px;
  height: 200px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.data-icon :deep(.lottie-container) {
  min-height: 0;
  width: 200px;
  height: 200px;
}

.data-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 12px;
}

.data-desc {
  font-size: 0.95rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 16px;
  margin-top: -22px;
}

.data-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 0.875rem;
  color: #64748b;
}

.meta-icon {
  font-size: 1rem;
}

.meta-num {
  color: #94a3b8;
}

.data-examples {
  display: flex;
  gap: 16px;
  margin-bottom: 48px;
  flex-wrap: wrap;
  justify-content: center;
}

.example-card {
  padding: 16px 24px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 12px;
  font-size: 0.95rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}

.example-card:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.data-input-area {
  width: 70%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.data-actions-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 10px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
}

.new-chat-btn:hover {
  background: #f8fafc;
}

.likes-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 10px;
  font-size: 14px;
  color: #475569;
}

.heart-icon {
  color: #ef4444;
}

.arrow-btn {
  width: 36px;
  height: 36px;
  margin-left: auto;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 50%;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.arrow-btn:hover {
  background: #f8fafc;
}

.arrow-btn-icon {
  width: 18px;
  height: 18px;
  object-fit: contain;
}

.data-chatbox {
  width: 100%;
  height: 130px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  box-sizing: border-box;
}

.data-chatbox:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.data-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  resize: none;
  padding: 0;
  font-family: inherit;
}

.data-input::placeholder {
  color: #94a3b8;
}

.chatbox-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
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
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.chatbox-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.voice-icon-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
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
