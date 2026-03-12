<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
import linkFileImg from '../assets/链接文件.png'
import voiceImg from '../assets/语音.png'
import arrowGreenImg from '../assets/arrow-green.png'
import sendImg from '../assets/发送.png'
import dataAnalysisAnimation from '../assets/Data Analysis Animation _ Visualize Insights Effectively.json'
import { useVoiceInput } from '../composables/useVoiceInput'
import { apiRequest, resolveApiUrl } from '../api/http'

const dataInput = ref('')
const { isRecording, isSupported, toggleRecording } = useVoiceInput(dataInput)

const dataExamples = [
  '北京未来七天气温,做个折线图',
  '帮我生成一个二维码,扫码后打开chatglm.cn'
]

const selectedFile = ref(null)
const uploading = ref(false)
const generating = ref(false)
const analyzeResult = ref(null)
const selectedChartIds = ref([])
const combinedImageUrl = ref('')
const errorMsg = ref('')

const combinedImageFullUrl = computed(() => resolveApiUrl(combinedImageUrl.value))

const chatMessages = ref([])
const chatScrollRef = ref(null)
const chatStarted = computed(() => chatMessages.value.length > 0)
const dataInputRef = ref(null)

// 数据分析模式：开启=推荐并生成图表；关闭=纯对话（只回答）
const analysisMode = ref(true)
const chatFileId = ref('') // 纯对话复用的 file_id

function pushMessage(msg) {
  chatMessages.value.push({ id: `${Date.now()}_${Math.random().toString(16).slice(2)}`, ...msg })
  nextTick(() => {
    const el = chatScrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function openPreview() {
  if (!combinedImageFullUrl.value) return
  window.open(combinedImageFullUrl.value, '_blank', 'noopener,noreferrer')
}

async function downloadPng() {
  if (!combinedImageFullUrl.value) return
  try {
    const res = await fetch(combinedImageFullUrl.value)
    const blob = await res.blob()
    const a = document.createElement('a')
    const url = URL.createObjectURL(blob)
    a.href = url
    a.download = 'combined.png'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    errorMsg.value = e?.message || '下载失败'
  }
}


const props = defineProps({
  resetKey: {
    type: Number,
    default: 0
  }
})

function resetState() {
  dataInput.value = ''
  selectedFile.value = null
  uploading.value = false
  generating.value = false
  analyzeResult.value = null
  selectedChartIds.value = []
  combinedImageUrl.value = ''
  errorMsg.value = ''
  chatMessages.value = []
  analysisMode.value = true
  chatFileId.value = ''
}

watch(
  () => props.resetKey,
  () => {
    resetState()
  }
)

function onPickFile(e) {
  const f = e.target.files?.[0]
  selectedFile.value = f || null
}

async function sendAndAnalyze() {
  if (!selectedFile.value) {
    errorMsg.value = '请先选择 Excel 文件'
    return
  }
  const requirement = dataInput.value.trim()
  if (!requirement) {
    errorMsg.value = '请先在输入框中填写你的分析需求，再点击发送'
    return
  }
  errorMsg.value = ''
  uploading.value = true
  combinedImageUrl.value = ''
  selectedChartIds.value = []
  pushMessage({
    role: 'user',
    type: 'text',
    text: requirement
  })
  dataInput.value = ''
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('requirement', requirement)
    const data = await apiRequest('/api/v1/data-analysis/upload', {
      method: 'POST',
      body: fd
    })
    analyzeResult.value = data
    pushMessage({
      role: 'assistant',
      type: 'analysis',
      text: data?.assistant_reply || data?.analysis_summary || '已完成分析并生成图表建议。',
      meta: `${data?.filename || ''} · ${data?.sheet_name || ''} · ${data?.rows || 0} 行 / ${data?.columns || 0} 列`
    })
  } catch (e) {
    errorMsg.value = e?.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function sendChatOnly() {
  const msg = dataInput.value.trim()
  if (!msg) return
  errorMsg.value = ''
  uploading.value = true
  pushMessage({ role: 'user', type: 'text', text: msg })
  dataInput.value = ''
  try {
    const fd = new FormData()
    fd.append('message', msg)
    if (chatFileId.value) fd.append('file_id', chatFileId.value)
    else if (selectedFile.value) fd.append('file', selectedFile.value)

    const data = await apiRequest('/api/v1/data-analysis/chat', { method: 'POST', body: fd })
    chatFileId.value = data?.file_id || chatFileId.value
    pushMessage({ role: 'assistant', type: 'analysis', text: data?.assistant_reply || '—' })
  } catch (e) {
    errorMsg.value = e?.message || '发送失败'
  } finally {
    uploading.value = false
  }
}

async function handleSend() {
  if (analysisMode.value) {
    await sendAndAnalyze()
    // 自动生成：取前 8 个推荐图表
    const charts = analyzeResult.value?.suggested_charts || []
    if (charts.length) {
      selectedChartIds.value = charts.slice(0, 8).map(c => c.id)
      await generateCharts()
    }
    chatFileId.value = analyzeResult.value?.file_id || chatFileId.value
  } else {
    await sendChatOnly()
  }
}

function focusInput() {
  if (dataInputRef.value) {
    dataInputRef.value.focus()
  }
}

function toggleAllCharts() {
  if (!analyzeResult.value?.suggested_charts) return
  const allIds = analyzeResult.value.suggested_charts.map(c => c.id)
  if (selectedChartIds.value.length === allIds.length) selectedChartIds.value = []
  else selectedChartIds.value = allIds
}

async function generateCharts() {
  if (!analyzeResult.value?.file_id) return
  if (!selectedChartIds.value.length) return
  errorMsg.value = ''
  generating.value = true
  try {
    const data = await apiRequest('/api/v1/data-analysis/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_id: analyzeResult.value.file_id,
        chart_ids: selectedChartIds.value
      })
    })
    combinedImageUrl.value = data?.combined_image_url || ''
    if (combinedImageUrl.value) {
      pushMessage({
        role: 'assistant',
        type: 'image',
        text: '已为你生成综合图表，可以预览或下载。',
        imageUrl: combinedImageUrl.value
      })
    }
  } catch (e) {
    errorMsg.value = e?.message || '生成失败'
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <div class="content-panel data-panel">
    <div v-if="!chatStarted" class="data-header">
      <div class="data-icon">
        <LottiePlayer :animation-data="dataAnalysisAnimation" />
      </div>
      <p class="data-desc">通过分析用户上传文件或数据说明，帮助用户分析数据并提供图表化的能力。也可通过简单的编码完成文件处理的工作。</p>
    </div>
    <div v-if="!chatStarted" class="data-examples">
      <button v-for="(ex, i) in dataExamples" :key="i" class="example-card">{{ ex }}</button>
    </div>

    <div class="data-input-area">
      <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

      <div ref="chatScrollRef" class="chat-panel">
        <div v-if="chatMessages.length === 0" class="chat-empty"></div>

        <div v-for="m in chatMessages" :key="m.id" class="chat-row" :class="m.role">
          <div class="bubble">
            <div v-if="m.type === 'text' || m.type === 'analysis'" class="bubble-text" style="white-space: pre-wrap;">
              {{ m.text }}
            </div>
            <div v-if="m.meta" class="bubble-meta">{{ m.meta }}</div>

            <div v-if="m.type === 'analysis' && analyzeResult" class="bubble-actions">
              <div class="charts-header">
                <div class="charts-title">可生成图表（多选）</div>
                <button class="ghost-btn" type="button" @click="toggleAllCharts">
                  {{ selectedChartIds.length === (analyzeResult.suggested_charts?.length || 0) ? '全不选' : '全选' }}
                </button>
              </div>

              <div class="chart-list">
                <label v-for="c in analyzeResult.suggested_charts" :key="c.id" class="chart-item">
                  <input v-model="selectedChartIds" type="checkbox" :value="c.id" />
                  <div class="chart-text">
                    <div class="chart-title">{{ c.title }}</div>
                    <div class="chart-desc">{{ c.description }}</div>
                  </div>
                </label>
              </div>

              <button class="primary-btn generate-btn" type="button" :disabled="!selectedChartIds.length || generating" @click="generateCharts">
                {{ generating ? '生成中...' : `生成图表（已选 ${selectedChartIds.length}）` }}
              </button>
            </div>

            <div v-if="m.type === 'image'" class="bubble-image">
              <div class="output-actions">
                <button class="link-btn" type="button" @click="openPreview">打开预览</button>
                <button class="link-btn" type="button" @click="downloadPng">下载 PNG</button>
              </div>
              <img :src="resolveApiUrl(m.imageUrl)" alt="combined chart" />
            </div>
          </div>
        </div>
      </div>

      <div class="composer">
        <div class="upload-row">
          <label class="file-picker">
            <input type="file" accept=".xlsx,.xls,.xlsm" @change="onPickFile" />
            <span class="file-btn">
              <img :src="linkFileImg" class="attach-icon" alt="" />
              选择 Excel
            </span>
          <span class="file-name">
            {{ selectedFile ? selectedFile.name : '选择一个 Excel 文件，然后在下方输入你的分析需求并点击发送。' }}
          </span>
          </label>
        </div>

        <div class="data-chatbox" @click="focusInput">
          <div class="mode-row" @click.stop>
            <button class="mode-btn" type="button" :class="{ active: analysisMode }" @click.stop="analysisMode = !analysisMode">
              数据分析模式
            </button>
            <span class="mode-hint">{{ analysisMode ? '将推荐并生成图表' : '仅对话，不生成图表' }}</span>
          </div>
          <textarea
            ref="dataInputRef"
            v-model="dataInput"
            class="data-input"
            placeholder="输入你的分析需求，例如：重点看各科是否均衡、是否有偏科"
            rows="3"
          ></textarea>
          <div class="chatbox-bottom">
            <div class="chatbox-left">
              <button v-if="isSupported" class="voice-btn" :class="{ recording: isRecording }" title="语音输入" @click="toggleRecording">
                <img :src="voiceImg" class="voice-icon-img" alt="语音" />
              </button>
            </div>
            <button
              class="send-btn"
              type="button"
              :disabled="uploading || (analysisMode && !selectedFile)"
              :title="analysisMode ? '发送并生成图表' : '发送'"
              @click="handleSend"
            >
              <img :src="sendImg" class="send-btn-icon" alt="" />
            </button>
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

.data-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 24px 16px;
  overflow: hidden;
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
  flex: 1;
  min-height: 0;
}

.chat-panel {
  width: 100%;
  border: none;
  background: transparent;
  border-radius: 14px;
  padding: 6px 2px;
  flex: 1;
  min-height: 0;
  overflow: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge legacy */
}

.chat-panel::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.chat-empty {
  color: #94a3b8;
  font-size: 14px;
  padding: 10px 4px;
}

.chat-row {
  display: flex;
  margin: 10px 0;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 82%;
  border-radius: 14px;
  padding: 12px 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.chat-row.user .bubble {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.chat-row.assistant .bubble {
  background: #ffffff;
  color: #0f172a;
}

.bubble-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.chat-row.user .bubble-meta {
  color: rgba(255, 255, 255, 0.85);
}

.bubble-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}

.bubble-image {
  margin-top: 10px;
}

.bubble-image img {
  width: 100%;
  margin-top: 10px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.error-banner {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #b91c1c;
  border-radius: 10px;
  font-size: 14px;
}

.upload-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
}

.composer {
  width: 100%;
  position: sticky;
  bottom: 0;
  background: linear-gradient(180deg, rgba(248,250,252,0) 0%, rgba(248,250,252,0.85) 18%, rgba(248,250,252,1) 100%);
  padding-top: 12px;
  z-index: 1; /* 确保输入区在聊天区之上，可正常点击输入 */
}

.composer .upload-row,
.composer .data-chatbox {
  width: 100%;
}

.composer .upload-row {
  margin-bottom: 14px; /* 增大文件框与输入框间距 */
}

.file-picker {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 12px;
  padding: 6px 10px; /* 降低整体高度 */
}

.file-picker input[type='file'] {
  display: none;
}

.file-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px; /* 降低按钮高度 */
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  font-size: 14px;
  color: #334155;
  white-space: nowrap;
}

.file-name {
  font-size: 14px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.primary-btn {
  height: 40px;
  padding: 0 16px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary {
  width: 100%;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 14px;
  padding: 14px 16px;
}

.summary-title {
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.summary-text {
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
}

.summary-meta {
  margin-top: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.charts-panel {
  width: 100%;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 14px;
  padding: 14px 16px;
}

.charts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.charts-title {
  font-weight: 700;
  color: #0f172a;
}

.ghost-btn {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  border-radius: 10px;
  height: 34px;
  padding: 0 12px;
  cursor: pointer;
  font-size: 13px;
}

.chart-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.chart-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
}

.chart-item input {
  margin-top: 4px;
}

.chart-title {
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
}

.chart-desc {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.generate-btn {
  width: 100%;
}

.output-panel {
  width: 100%;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 14px;
  padding: 14px 16px;
}

.output-title {
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.output-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #0f172a;
  text-decoration: none;
  font-size: 13px;
  cursor: pointer;
}

.output-preview img {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
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
  min-height: 150px;
  height: auto;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  box-sizing: border-box;
  position: relative; /* 确保内部可正常获取焦点 */
}

.mode-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.mode-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  cursor: pointer;
}

.mode-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
  font-weight: 600;
}

.mode-hint {
  font-size: 12px;
  color: #94a3b8;
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
