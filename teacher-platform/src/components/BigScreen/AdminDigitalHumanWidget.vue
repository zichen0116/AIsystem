<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { apiRequest } from '@/api/http'
import {
  getRecognitionSnapshot,
  normalizeText
} from './adminDigitalHumanSpeech'

const props = defineProps({
  visible: { type: Boolean, default: false },
  voiceMode: { type: Boolean, default: false }
})

const STREAM_DOM_ID = 'admin-iflytek-avatar-stream'
const ADMIN_AVATAR_ID = '111188001'
const MAX_HISTORY_ITEMS = 6
const DUPLICATE_WINDOW_MS = 4000

const statusText = ref('数字人未启动')
const errorText = ref('')
const recognitionText = ref('')
const running = ref(false)
const voiceRecording = ref(false)
const voiceTurnState = ref('idle') // idle | listening | waiting_reply | speaking
const conversationHistory = ref([])

let avatarSdkModule = null
let avatarSdkInstance = null
let speechRec = null
let iflytekConfig = null
let shouldResumeListening = false
let recognitionHandled = false
let restartTimer = null
let activeRequestId = 0
let lastSubmittedText = ''
let lastSubmittedAt = 0
let lastSpokenText = ''
let lastSpokenAt = 0
let pendingRecognitionFinalText = ''
let pendingRecognitionMergedText = ''

function normalizeIflytekConfig(raw) {
  const sceneId = raw?.sceneId ?? raw?.scene_id ?? raw?.serviceId ?? raw?.service_id ?? ''
  return {
    ...raw,
    sceneId: String(sceneId || '').trim(),
    avatarServerUrl:
      raw?.avatarServerUrl ??
      raw?.avatar_server_url ??
      'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact',
    appId: raw?.appId ?? raw?.app_id,
    apiKey: raw?.apiKey ?? raw?.api_key,
    apiSecret: raw?.apiSecret ?? raw?.api_secret,
    defaultAvatarId: raw?.defaultAvatarId ?? raw?.default_avatar_id,
    defaultWidth: raw?.defaultWidth ?? raw?.default_width ?? 1280,
    defaultHeight: raw?.defaultHeight ?? raw?.default_height ?? 720,
    defaultTtsVcn: raw?.defaultTtsVcn ?? raw?.default_tts_vcn ?? 'x4_xiaoxuan',
    streamProtocol: raw?.streamProtocol ?? raw?.stream_protocol ?? 'xrtc'
  }
}

function isRecentDuplicate(text, lastText, lastAt) {
  return !!text && text === lastText && Date.now() - lastAt < DUPLICATE_WINDOW_MS
}

function trimHistory(items) {
  return items.slice(-MAX_HISTORY_ITEMS)
}

function appendHistory(role, content) {
  const normalized = normalizeText(content)
  if (!normalized) return
  conversationHistory.value = trimHistory([
    ...conversationHistory.value,
    { role, content: normalized }
  ])
}

function resetRecognitionBuffer() {
  recognitionText.value = ''
  pendingRecognitionFinalText = ''
  pendingRecognitionMergedText = ''
}

function resetConversationState() {
  conversationHistory.value = []
  resetRecognitionBuffer()
  voiceTurnState.value = 'idle'
  voiceRecording.value = false
  shouldResumeListening = false
  recognitionHandled = false
  lastSubmittedText = ''
  lastSubmittedAt = 0
  lastSpokenText = ''
  lastSpokenAt = 0
  activeRequestId += 1
  if (restartTimer) {
    clearTimeout(restartTimer)
    restartTimer = null
  }
}

async function loadConfig() {
  if (iflytekConfig) return iflytekConfig
  const data = await apiRequest('/api/v1/digital-human/iflytek/web-sdk-config')
  iflytekConfig = normalizeIflytekConfig(data)
  return iflytekConfig
}

async function loadSdk() {
  if (avatarSdkModule) return avatarSdkModule
  avatarSdkModule = await import('@/libs/avatar-sdk-web_3.1.2.1002/index.js')
  return avatarSdkModule
}

function scheduleListeningResume(delay = 300) {
  if (restartTimer) clearTimeout(restartTimer)
  if (!props.voiceMode || !props.visible || !running.value || !shouldResumeListening) {
    voiceTurnState.value = 'idle'
    return
  }
  restartTimer = setTimeout(() => {
    restartTimer = null
    void startRecognitionCycle()
  }, delay)
}

function handleSpeechFinished() {
  if (voiceTurnState.value === 'speaking') {
    statusText.value = '本轮对话结束'
  }
  voiceTurnState.value = 'idle'
  voiceRecording.value = false
  scheduleListeningResume()
}

function attachIflytekSdkListeners(inst, SDKEvents) {
  if (!SDKEvents || !inst?.on) return

  inst.on(SDKEvents.connected, () => {
    statusText.value = '数字人连接成功'
  })

  inst.on(SDKEvents.stream_start, () => {
    statusText.value = '数字人已就绪'
  })

  inst.on(SDKEvents.tts_duration, () => {
    voiceTurnState.value = 'speaking'
    statusText.value = '数字人回复中'
  })

  inst.on(SDKEvents.frame_start, () => {
    voiceTurnState.value = 'speaking'
    statusText.value = '数字人回复中'
  })

  inst.on(SDKEvents.frame_stop, () => {
    handleSpeechFinished()
  })

  inst.on(SDKEvents.disconnected, (event) => {
    running.value = false
    voiceRecording.value = false
    shouldResumeListening = false
    voiceTurnState.value = 'idle'
    errorText.value = event?.message || '数字人连接已断开'
  })

  inst.on(SDKEvents.error, (event) => {
    errorText.value = event?.message || event?.code || '数字人播报失败'
    if (voiceTurnState.value === 'speaking') {
      handleSpeechFinished()
    }
  })
}

async function startDigitalHuman() {
  if (running.value) return
  errorText.value = ''
  statusText.value = '正在启动数字人...'

  try {
    const cfg = await loadConfig()
    if (!cfg.sceneId) throw new Error('缺少 sceneId，请检查后端数字人配置')

    const mod = await loadSdk()
    const AvatarPlatform = mod.default
    const wrapper = document.getElementById(STREAM_DOM_ID)
    if (!wrapper) throw new Error('找不到数字人渲染容器')

    avatarSdkInstance = new AvatarPlatform({ useInlinePlayer: true })
    attachIflytekSdkListeners(avatarSdkInstance, mod.SDKEvents)

    avatarSdkInstance.setApiInfo({
      serverUrl: cfg.avatarServerUrl,
      appId: cfg.appId,
      apiKey: cfg.apiKey,
      apiSecret: cfg.apiSecret,
      sceneId: cfg.sceneId
    })

    avatarSdkInstance.setGlobalParams({
      avatar_dispatch: { interactive_mode: 0, content_analysis: 0 },
      stream: { protocol: 'xrtc', alpha: 1, bitrate: 1000000, fps: 25 },
      avatar: {
        avatar_id: ADMIN_AVATAR_ID || String(cfg.defaultAvatarId || ''),
        width: 720,
        height: 1280,
        scale: 1,
        move_h: 0,
        move_v: 0,
        audio_format: 1
      },
      tts: {
        vcn: cfg.defaultTtsVcn,
        speed: 50,
        pitch: 50,
        volume: 100
      }
    })

    await avatarSdkInstance.start({ wrapper })
    running.value = true
    statusText.value = '数字人已就绪'

    if (props.voiceMode) {
      await startVoice()
    }
  } catch (e) {
    errorText.value = e?.message || '数字人启动失败'
    statusText.value = '启动失败'
    running.value = false
  }
}

async function stopRecognitionCycle() {
  shouldResumeListening = false
  recognitionHandled = true
  resetRecognitionBuffer()

  if (restartTimer) {
    clearTimeout(restartTimer)
    restartTimer = null
  }

  try {
    speechRec?.stop?.()
  } catch {
    // ignore
  } finally {
    voiceRecording.value = false
    if (voiceTurnState.value !== 'waiting_reply' && voiceTurnState.value !== 'speaking') {
      voiceTurnState.value = 'idle'
    }
  }
}

async function stopVoice() {
  shouldResumeListening = false
  activeRequestId += 1
  await stopRecognitionCycle()

  if (voiceTurnState.value === 'speaking') {
    try {
      await avatarSdkInstance?.interrupt?.()
    } catch {
      // ignore
    }
  }

  voiceTurnState.value = 'idle'
  if (running.value) statusText.value = '语音模式已关闭'
}

async function stopDigitalHuman() {
  try {
    await stopVoice()
    await avatarSdkInstance?.stop?.()
    await avatarSdkInstance?.destroy?.()
  } catch {
    // ignore
  } finally {
    avatarSdkInstance = null
    running.value = false
    resetConversationState()
    statusText.value = '数字人已关闭'
  }
}

function ensureRecognition() {
  if (speechRec) return speechRec

  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Ctor) {
    throw new Error('当前浏览器不支持语音识别，请使用 Edge 或 Chrome')
  }

  const rec = new Ctor()
  rec.lang = 'zh-CN'
  rec.continuous = false
  rec.interimResults = true
  rec.maxAlternatives = 1

  rec.onstart = () => {
    voiceRecording.value = true
    if (voiceTurnState.value === 'idle') {
      voiceTurnState.value = 'listening'
    }
  }

  rec.onresult = (event) => {
    if (voiceTurnState.value !== 'listening' || recognitionHandled) return

    const snapshot = getRecognitionSnapshot(event, pendingRecognitionFinalText)
    pendingRecognitionFinalText = snapshot.finalText
    pendingRecognitionMergedText = snapshot.mergedText
    recognitionText.value = snapshot.mergedText

    if (snapshot.mergedText) {
      statusText.value = snapshot.finalText
        ? '语音识别完成，准备提交'
        : '正在识别管理员提问...'
    }
  }

  rec.onerror = (event) => {
    voiceRecording.value = false
    if (event?.error !== 'no-speech') {
      errorText.value = `语音识别错误: ${event?.error || 'unknown'}`
    }
    if (voiceTurnState.value === 'listening') {
      scheduleListeningResume(400)
    }
  }

  rec.onend = () => {
    voiceRecording.value = false
    const capturedText = normalizeText(pendingRecognitionMergedText)

    if (
      props.voiceMode &&
      props.visible &&
      running.value &&
      shouldResumeListening &&
      voiceTurnState.value === 'listening' &&
      !recognitionHandled &&
      capturedText
    ) {
      recognitionHandled = true
      resetRecognitionBuffer()
      void submitRecognizedText(capturedText)
      return
    }

    if (
      props.voiceMode &&
      props.visible &&
      running.value &&
      shouldResumeListening &&
      voiceTurnState.value === 'listening'
    ) {
      scheduleListeningResume(250)
    }
  }

  speechRec = rec
  return rec
}

async function startRecognitionCycle() {
  if (!props.voiceMode || !props.visible || !running.value || !avatarSdkInstance) return
  if (voiceTurnState.value === 'waiting_reply' || voiceTurnState.value === 'speaking') return

  const rec = ensureRecognition()
  errorText.value = ''
  resetRecognitionBuffer()
  recognitionHandled = false
  shouldResumeListening = true
  voiceTurnState.value = 'listening'
  statusText.value = '正在聆听管理员问题...'

  try {
    await navigator.mediaDevices.getUserMedia({ audio: true })
    rec.start()
  } catch (e) {
    voiceRecording.value = false
    voiceTurnState.value = 'idle'
    errorText.value = e?.message || '开启语音失败'
    statusText.value = '语音启动失败'
  }
}

async function startVoice() {
  if (!running.value || voiceTurnState.value === 'waiting_reply' || voiceTurnState.value === 'speaking') return
  await startRecognitionCycle()
}

async function requestAdminChat(message) {
  return apiRequest('/api/v1/digital-human/admin/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      history: trimHistory(conversationHistory.value)
    })
  })
}

async function speakReply(text, requestId) {
  const normalized = normalizeText(text)
  if (!normalized) {
    handleSpeechFinished()
    return
  }

  if (requestId !== activeRequestId || !props.voiceMode || !running.value || !avatarSdkInstance) {
    voiceTurnState.value = 'idle'
    return
  }

  if (isRecentDuplicate(normalized, lastSpokenText, lastSpokenAt)) {
    handleSpeechFinished()
    return
  }

  lastSpokenText = normalized
  lastSpokenAt = Date.now()
  voiceTurnState.value = 'speaking'
  statusText.value = '数字人回复中'

  try {
    await avatarSdkInstance.interrupt?.()
  } catch {
    // ignore
  }

  try {
    await avatarSdkInstance.writeText?.(normalized, {
      nlp: false,
      avatar_dispatch: { interactive_mode: 1, content_analysis: 0 }
    })
  } catch (e) {
    errorText.value = e?.message || '数字人播报失败'
    handleSpeechFinished()
  }
}

async function submitRecognizedText(text) {
  const normalized = normalizeText(text)
  if (!normalized) {
    scheduleListeningResume(250)
    return
  }

  recognitionText.value = normalized
  if (isRecentDuplicate(normalized, lastSubmittedText, lastSubmittedAt)) {
    statusText.value = '检测到重复提问，已忽略'
    scheduleListeningResume(500)
    return
  }

  lastSubmittedText = normalized
  lastSubmittedAt = Date.now()
  activeRequestId += 1
  const requestId = activeRequestId

  appendHistory('user', normalized)
  voiceTurnState.value = 'waiting_reply'
  voiceRecording.value = false
  shouldResumeListening = true
  statusText.value = '正在思考回答...'
  errorText.value = ''

  try {
    const data = await requestAdminChat(normalized)
    if (requestId !== activeRequestId) return

    const answer = normalizeText(data?.answer || data?.speak_text)
    const speakText = normalizeText(data?.speak_text || answer)

    if (answer) {
      appendHistory('assistant', answer)
    }

    if (!props.voiceMode || !props.visible || !running.value) {
      voiceTurnState.value = 'idle'
      return
    }

    await speakReply(speakText, requestId)
  } catch (e) {
    if (requestId !== activeRequestId) return
    errorText.value = e?.message || '管理员聊天失败'
    await speakReply('抱歉，我暂时无法回答这个问题，请稍后再试。', requestId)
  }
}

watch(
  () => props.visible,
  async (visible) => {
    if (visible) await startDigitalHuman()
    else await stopDigitalHuman()
  },
  { immediate: true }
)

watch(
  () => props.voiceMode,
  async (enabled) => {
    if (!props.visible) return
    if (enabled) await startVoice()
    else await stopVoice()
  },
  { immediate: true }
)

onBeforeUnmount(async () => {
  await stopDigitalHuman()
})
</script>

<template>
  <div
    v-if="visible"
    class="admin-dh-widget"
    :data-state="voiceTurnState"
  >
    <div :id="STREAM_DOM_ID" class="admin-dh-stream" />
    <div
      v-if="voiceMode || errorText || voiceTurnState !== 'idle'"
      class="admin-dh-feedback"
      aria-live="polite"
    >
      <p class="admin-dh-status">{{ statusText }}</p>
      <p v-if="recognitionText" class="admin-dh-recognition">识别：{{ recognitionText }}</p>
      <p v-if="errorText" class="admin-dh-error">{{ errorText }}</p>
    </div>
  </div>
</template>

<style scoped>
.admin-dh-widget {
  width: min(21vw, 235px);
  min-width: 160px;
  aspect-ratio: 9 / 16;
  background: transparent;
  pointer-events: none;
  position: relative;
}

.admin-dh-stream {
  width: 100%;
  height: 100%;
  background: transparent;
}

.admin-dh-stream :deep(video),
.admin-dh-stream :deep(canvas) {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: transparent !important;
  box-shadow: none !important;
}

.admin-dh-feedback {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(2, 6, 23, 0.72);
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.35;
  backdrop-filter: blur(6px);
}

.admin-dh-status,
.admin-dh-recognition,
.admin-dh-error {
  margin: 0;
}

.admin-dh-recognition,
.admin-dh-error {
  margin-top: 4px;
}

.admin-dh-recognition {
  color: #bfdbfe;
}

.admin-dh-error {
  color: #fca5a5;
}
</style>
