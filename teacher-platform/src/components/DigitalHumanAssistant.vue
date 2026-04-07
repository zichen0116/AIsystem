<script setup>
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { apiRequest } from '../api/http'
import digitalmanAvatar from '@/assets/digitanlman.png'

const STORAGE_KEY = 'eduprep-digital-human-fab-pos'
const FAB_SIZE = 52
const FAB_MARGIN = 8
const STREAM_DOM_ID = 'iflytek-avatar-stream'

const fabRef = ref(null)
const drawerOpen = ref(false)
const pos = ref({ left: 0, top: 0 })
const dragging = ref(false)

const loadingConfig = ref(false)
const sdkLoading = ref(false)
const starting = ref(false)
const stopping = ref(false)
const running = ref(false)
const iflytekConfig = ref(null)
const statusText = ref('数字人未启动')
const errorText = ref('')

// 语音交互
const voiceStarting = ref(false)
const voiceStopping = ref(false)
const voiceRecording = ref(false)
const voiceNlpEnabled = ref(true) // 默认始终启用理解（UI 不展示）
// 持续对话：由用户手动结束，不做单轮计时
const voiceFullDuplex = ref(true)
const voiceSingleSeconds = ref(20) // 保留字段避免模板残留报错（UI 已隐藏）

// 交互状态可视化
const isThinking = ref(false)
const isSpeaking = ref(false)
const lastAsrText = ref('')
const lastSubtitle = ref('')
const chatText = ref('')
const sendingText = ref(false)
const nlpStatusText = ref('') // NLP 连接/能力提示（用于排查“启用理解无效”）
const sdkConnected = ref(false)
const streamStarted = ref(false)
const asrDebugLines = ref([])
const asrDebugCurrent = ref('')
const audioFrameCount = ref(0)
const lastAudioSendAt = ref('')
const lastVoiceError = ref('')
const asrEventCount = ref(0)
const audioEventCount = ref(0)
const voiceDiagText = ref('')
const browserAsrText = ref('')
const browserAsrFinalText = ref('')
const browserAsrListening = ref(false)
const browserAsrAvailable = ref(false)
const voiceTurnState = ref('idle') // idle | user_speaking | waiting_avatar | avatar_speaking
const micActive = computed(() => voiceRecording.value || browserAsrListening.value)
const canToggleMic = computed(
  () => running.value && !voiceStarting.value && !voiceStopping.value
)
const voiceTurnLabel = computed(() => {
  if (voiceTurnState.value === 'user_speaking') return '当前：用户讲话中'
  if (voiceTurnState.value === 'waiting_avatar') return '当前：等待数字人回复'
  if (voiceTurnState.value === 'avatar_speaking') return '当前：数字人讲话中'
  return '当前：待机'
})

async function toggleMic() {
  if (!canToggleMic.value) return
  if (micActive.value) await stopVoice()
  else await startVoice()
}

let dragMoved = false
let startX = 0
let startY = 0
let startLeft = 0
let startTop = 0

const canInterrupt = computed(() => running.value && !stopping.value)

/** 动态 import 缓存（与官方 demo 同源模块） */
let avatarSdkModule = null
/** AvatarPlatform 实例（官方 SDK 对象） */
let avatarSdkInstance = null

// 语音链路：录音帧 -> writeAudio
let recorderAudioListener = null
let recorderAudioEventName = 'recoder_audio'
let audioFrameStarted = false
let nlpConnected = false
let restartingSession = false
let autoRecoveringSession = false

// 浏览器原生语音转文字（Web Speech API）
let speechRec = null

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition
}

function ensureBrowserSpeechRecognition() {
  const Ctor = getSpeechRecognitionCtor()
  browserAsrAvailable.value = !!Ctor
  if (!Ctor) return null
  if (speechRec) return speechRec

  const r = new Ctor()
  r.lang = 'zh-CN'
  r.continuous = true
  r.interimResults = true
  r.maxAlternatives = 1

  r.onstart = () => {
    browserAsrListening.value = true
  }
  r.onend = () => {
    browserAsrListening.value = false
  }
  r.onerror = (e) => {
    const msg = e?.error || e?.message || 'SpeechRecognition error'
    lastVoiceError.value = `浏览器ASR错误: ${msg}`
  }
  r.onresult = (event) => {
    let interim = ''
    let final = browserAsrFinalText.value || ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i]
      const txt = res?.[0]?.transcript || ''
      if (res.isFinal) final += txt
      else interim += txt
    }
    const merged = (final + interim).trim()
    browserAsrText.value = merged
    if (final.trim()) browserAsrFinalText.value = final.trim()

    // 复用调试展示
    asrDebugCurrent.value = merged
    if (browserAsrFinalText.value) lastAsrText.value = browserAsrFinalText.value
  }

  speechRec = r
  return r
}

function resetBrowserAsr() {
  browserAsrText.value = ''
  browserAsrFinalText.value = ''
}

async function waitForBrowserAsrFinalText(maxWaitMs = 800) {
  const start = Date.now()
  while (Date.now() - start < maxWaitMs) {
    const text = (browserAsrFinalText.value || browserAsrText.value || '').trim()
    if (text) return text
    await new Promise((r) => setTimeout(r, 80))
  }
  return (browserAsrFinalText.value || browserAsrText.value || '').trim()
}

function isSessionInvalidMessage(msg) {
  const m = (msg || '').toString().toLowerCase()
  return (
    m.includes('session is invalid') ||
    m.includes('over time') ||
    m.includes('timeout') ||
    m.includes('10108')
  )
}

async function restartAvatarSession() {
  if (restartingSession || autoRecoveringSession) return false
  if (!iflytekConfig.value) {
    await fetchIflytekConfig()
  }
  if (!iflytekConfig.value?.sceneId) return false
  restartingSession = true
  autoRecoveringSession = true
  try {
    // 彻底重启：停止对话 -> 销毁 -> 重新 start
    try {
      if (voiceRecording.value) await stopVoice()
    } catch {
      /* ignore */
    }
    await destroyAvatarSdk()
    await startDigitalHuman()
    return !!running.value
  } finally {
    restartingSession = false
    autoRecoveringSession = false
  }
}

function normalizeAudioChunk(payload) {
  if (!payload) return null
  if (payload instanceof ArrayBuffer) return payload
  if (payload?.data instanceof ArrayBuffer) return payload.data
  if (payload?.buffer instanceof ArrayBuffer) return payload.buffer
  if (payload instanceof Uint8Array) {
    return payload.buffer.slice(payload.byteOffset, payload.byteOffset + payload.byteLength)
  }
  if (payload?.data instanceof Uint8Array) {
    const u8 = payload.data
    return u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength)
  }
  return null
}

function extractAsrText(payload) {
  if (!payload) return ''
  if (typeof payload === 'string') return payload.trim()
  // 常见字段
  const direct =
    payload?.text ??
    payload?.result ??
    payload?.asr ??
    payload?.content ??
    payload?.data?.text ??
    payload?.data?.result ??
    payload?.data?.asr
  if (typeof direct === 'string' && direct.trim()) return direct.trim()

  // 兼容部分 ASR 返回：ws/cw 结构
  try {
    const ws = payload?.ws ?? payload?.data?.ws
    if (Array.isArray(ws)) {
      const text = ws
        .flatMap((w) => (Array.isArray(w?.cw) ? w.cw : []))
        .map((c) => c?.w || '')
        .join('')
        .trim()
      if (text) return text
    }
  } catch {
    /* ignore */
  }
  return ''
}

function getAvatarAudioSampleRate() {
  // 当前实现固定 audio_format: 1（16k）。若后续开放 UI 选择，可按 audio_format 映射 16k/24k。
  return 16000
}

async function ensureMicPermission(UserMedia) {
  try {
    await UserMedia?.requestPermissions?.('audioinput')
  } catch {
    // 部分浏览器不支持 requestPermissions，降级到 getUserMedia
  }
  if (UserMedia?.getUserMedia) {
    await UserMedia.getUserMedia({ audio: true })
  } else {
    await navigator.mediaDevices.getUserMedia({ audio: true })
  }
}

function defaultPos() {
  const m = 24
  return {
    left: window.innerWidth - FAB_SIZE - m,
    top: window.innerHeight - FAB_SIZE - m
  }
}

function clamp(left, top) {
  const maxL = Math.max(FAB_MARGIN, window.innerWidth - FAB_SIZE - FAB_MARGIN)
  const maxT = Math.max(FAB_MARGIN, window.innerHeight - FAB_SIZE - FAB_MARGIN)
  return {
    left: Math.min(Math.max(FAB_MARGIN, left), maxL),
    top: Math.min(Math.max(FAB_MARGIN, top), maxT)
  }
}

function loadPos() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw)
      if (typeof p.left === 'number' && typeof p.top === 'number') return clamp(p.left, p.top)
    }
  } catch {
    /* ignore */
  }
  const d = defaultPos()
  return clamp(d.left, d.top)
}

function savePos() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pos.value))
  } catch {
    /* ignore */
  }
}

function onResize() {
  pos.value = clamp(pos.value.left, pos.value.top)
}

function onPointerDown(e) {
  if (e.button !== 0) return
  dragging.value = true
  dragMoved = false
  startX = e.clientX
  startY = e.clientY
  startLeft = pos.value.left
  startTop = pos.value.top
  const el = fabRef.value
  if (el?.setPointerCapture) el.setPointerCapture(e.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function onPointerMove(e) {
  if (!dragging.value) return
  const dx = e.clientX - startX
  const dy = e.clientY - startY
  if (Math.abs(dx) > 4 || Math.abs(dy) > 4) dragMoved = true
  pos.value = clamp(startLeft + dx, startTop + dy)
}

function onPointerUp(e) {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  dragging.value = false
  const el = fabRef.value
  if (el?.releasePointerCapture) {
    try {
      el.releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }
  savePos()
  if (!dragMoved) drawerOpen.value = !drawerOpen.value
}

function closeDrawer() {
  drawerOpen.value = false
}

function onEscape(e) {
  if (e.key === 'Escape') closeDrawer()
}

async function loadAvatarSdkModule() {
  if (avatarSdkModule) {
    return avatarSdkModule
  }
  sdkLoading.value = true
  statusText.value = '正在加载讯飞 Avatar SDK...'
  try {
    const mod = await import('@/libs/avatar-sdk-web_3.1.2.1002/index.js')
    if (!mod?.default) {
      throw new Error('SDK 模块未导出 default（AvatarPlatform）')
    }
    avatarSdkModule = mod
    statusText.value = 'SDK 已加载，可点击启动'
    return mod
  } catch (e) {
    throw new Error(e?.message || '加载 Avatar SDK 失败，请确认 src/libs/avatar-sdk-web_3.1.2.1002 存在')
  } finally {
    sdkLoading.value = false
  }
}

async function destroyAvatarSdk() {
  if (!avatarSdkInstance) return
  // 无论实例状态如何，先清掉“对话/录音”UI 状态，避免残留
  voiceRecording.value = false
  voiceStarting.value = false
  voiceStopping.value = false
  audioFrameStarted = false
  try {
    await avatarSdkInstance.stop?.()
  } catch {
    /* ignore */
  }
  try {
    await avatarSdkInstance.destroy?.()
  } catch {
    /* ignore */
  }
  avatarSdkInstance = null
}

function resumePlayback() {
  try {
    avatarSdkInstance?.player?.resume?.()
    statusText.value = '已尝试恢复播放'
  } catch (e) {
    errorText.value = e?.message || '恢复播放失败'
  }
}

/** 兼容 FastAPI 驼峰/蛇形字段，并兜底 sceneId（接口服务 ID 常作 sceneId） */
function normalizeIflytekConfig(raw) {
  if (!raw || typeof raw !== 'object') return raw
  const sceneId =
    raw.sceneId ??
    raw.scene_id ??
    raw.serviceId ??
    raw.service_id ??
    ''
  const out = {
    ...raw,
    sceneId: sceneId ? String(sceneId).trim() : '',
    avatarServerUrl:
      raw.avatarServerUrl ??
      raw.avatar_server_url ??
      'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact',
    appId: raw.appId ?? raw.app_id,
    apiKey: raw.apiKey ?? raw.api_key,
    apiSecret: raw.apiSecret ?? raw.api_secret,
    defaultAvatarId: raw.defaultAvatarId ?? raw.default_avatar_id,
    defaultWidth: raw.defaultWidth ?? raw.default_width ?? 1280,
    defaultHeight: raw.defaultHeight ?? raw.default_height ?? 720,
    defaultTtsVcn:
      raw.defaultTtsVcn ?? raw.default_tts_vcn ?? 'x4_xiaoxuan',
    streamProtocol: raw.streamProtocol ?? raw.stream_protocol ?? 'xrtc'
  }
  return out
}

const STREAM_PROTOCOLS = ['xrtc', 'webrtc', 'rtmp']

/** 文档 2.2.3：在 setApiInfo / start 之前注册交互事件，避免漏掉早期回调 */
function attachIflytekSdkListeners(inst, SDKEvents) {
  if (!SDKEvents || !inst?.on) return
  inst.on(SDKEvents.connected, () => {
    statusText.value = '已连接交互服务…'
    sdkConnected.value = true
  })
  inst.on(SDKEvents.stream_start, () => {
    statusText.value = '引擎已开始推流（文档说明：此时未必已在画面看到视频）'
    streamStarted.value = true
  })
  // 语音理解/播报状态（用于“在思考/在说话”的 UI）
  inst.on(SDKEvents.asr, (asrData) => {
    asrEventCount.value += 1
    const text = extractAsrText(asrData)
    if (text) {
      lastAsrText.value = text
      asrDebugCurrent.value = text
      const time = new Date().toLocaleTimeString()
      asrDebugLines.value = [{ time, text }, ...asrDebugLines.value].slice(0, 8)
    } else {
      // 没提取到文本时，保留一条调试信息，方便判断“有事件但字段不匹配”
      const brief = JSON.stringify(asrData ?? {}).slice(0, 120)
      asrDebugCurrent.value = brief ? `收到ASR事件但未提取到文本：${brief}` : '收到ASR事件但未提取到文本'
    }
    isThinking.value = true
  })
  inst.on(SDKEvents.nlp, () => {
    isThinking.value = true
  })
  inst.on(SDKEvents.tts_duration, () => {
    // 一旦进入 TTS/播报阶段，认为“开始说话”
    isThinking.value = false
    isSpeaking.value = true
    if (!voiceRecording.value) voiceTurnState.value = 'avatar_speaking'
  })
  inst.on(SDKEvents.subtitle_info, (subtitleData) => {
    const text = (subtitleData?.text ?? subtitleData?.subtitle ?? '').toString()
    if (text) lastSubtitle.value = text
    isThinking.value = false
    isSpeaking.value = true
  })
  inst.on(SDKEvents.frame_start, () => {
    isThinking.value = false
    isSpeaking.value = true
    if (!voiceRecording.value) voiceTurnState.value = 'avatar_speaking'
  })
  inst.on(SDKEvents.frame_stop, () => {
    isSpeaking.value = false
    if (voiceTurnState.value === 'avatar_speaking') {
      voiceTurnState.value = 'idle'
    }
  })
  inst.on(SDKEvents.disconnected, (e) => {
    if (e) {
      errorText.value = `连接断开：${e?.message ?? e?.code ?? String(e)}`
    }
    running.value = false
    isThinking.value = false
    isSpeaking.value = false
    nlpConnected = false
    nlpStatusText.value = ''
    sdkConnected.value = false
    streamStarted.value = false
    // 断线时强制结束对话，避免“录音中但已无连接”
    try {
      if (voiceRecording.value) stopVoice()
    } catch {
      /* ignore */
    }
  })
  inst.on(SDKEvents.error, (err) => {
    const code = err?.code
    const msg = err?.message ?? code ?? String(err)
    errorText.value = `SDK：${msg}`
    if (isSessionInvalidMessage(msg)) {
      running.value = false
      nlpConnected = false
      nlpStatusText.value = ''
      sdkConnected.value = false
      streamStarted.value = false
      // 会话失效时自动恢复，减少人工反复点击
      if (!autoRecoveringSession && drawerOpen.value) {
        statusText.value = '会话失效，自动重连中...'
        void restartAvatarSession()
      }
    }
  })
}

function attachRecorderListeners(recorder, RecorderEvents) {
  if (!recorder?.on || !RecorderEvents) return
  try {
    recorder.removeAllListeners?.()
  } catch {
    /* ignore */
  }
  recorder.on(RecorderEvents.error, (err) => {
    const msg = err?.message ?? err?.code ?? String(err)
    if (msg) errorText.value = `录音：${msg}`
  })
  recorder.on(RecorderEvents.ended, () => {
    voiceRecording.value = false
    statusText.value = '录音已结束'
  })
  // 仅用于调试：统计录音器是否持续产出音频块（不参与业务上送）
  const audioEvtNames = [RecorderEvents.recoder_audio, RecorderEvents.recorder_audio, 'recoder_audio', 'recorder_audio']
    .filter(Boolean)
  for (const evt of [...new Set(audioEvtNames)]) {
    try {
      recorder.on(evt, () => {
        audioFrameCount.value += 1
        audioEventCount.value += 1
        lastAudioSendAt.value = new Date().toLocaleTimeString()
      })
      recorderAudioEventName = evt
    } catch {
      /* ignore */
    }
  }
}

async function startRecordingNow(recorder, expectedSampleRate) {
  if (!recorder) {
    throw new Error('录音器不可用')
  }

  statusText.value = '录音中...'
  voiceRecording.value = true
  voiceTurnState.value = 'user_speaking'
  const durationMs = 0 // 持续对话：由用户点击“结束对话”结束
  recorder
    .startRecord(
      durationMs,
      () => {
        voiceRecording.value = false
      },
      { nlp: voiceNlpEnabled.value }
    )
    .catch((e) => {
      const msg = e?.message ?? e?.code ?? String(e)
      lastVoiceError.value = `startRecord失败: ${msg}`
      errorText.value = `录音启动失败：${msg}`
      voiceRecording.value = false
      voiceTurnState.value = 'idle'
    })
}

async function fetchIflytekConfig() {
  if (iflytekConfig.value || loadingConfig.value) return
  loadingConfig.value = true
  try {
    const data = await apiRequest('/api/v1/digital-human/iflytek/web-sdk-config')
    iflytekConfig.value = normalizeIflytekConfig(data)
    if (!iflytekConfig.value.sceneId) {
      errorText.value =
        '缺少 sceneId：请在 backend/.env 设置 IFLYTEK_AVATAR_SCENE_ID，或填写 IFLYTEK_VMS_SERVICE_ID 作为场景 ID，并重启后端'
      statusText.value = '配置不完整'
    } else {
      errorText.value = ''
      statusText.value = '配置加载完成，可点击启动'
    }
  } catch (e) {
    const msg = e?.message || '加载数字人配置失败'
    errorText.value = msg
    statusText.value = '配置加载失败'
  } finally {
    loadingConfig.value = false
  }
}

async function startDigitalHuman() {
  errorText.value = ''
  isThinking.value = false
  isSpeaking.value = false
  nlpConnected = false
  nlpStatusText.value = ''
  sdkConnected.value = false
  streamStarted.value = false
  if (!iflytekConfig.value) {
    await fetchIflytekConfig()
    if (!iflytekConfig.value) return
  }
  const cfg = iflytekConfig.value
  if (!cfg.sceneId) {
    errorText.value = '缺少 sceneId，请检查后端环境变量'
    return
  }

  let mod
  try {
    mod = await loadAvatarSdkModule()
  } catch (e) {
    errorText.value = e?.message || 'SDK 加载失败'
    return
  }

  const AvatarPlatform = mod.default
  const PlayerEvents = mod.PlayerEvents
  const SDKEvents = mod.SDKEvents
  const wrapper = document.getElementById(STREAM_DOM_ID)
  if (!wrapper) {
    errorText.value = '找不到渲染容器'
    return
  }

  starting.value = true
  statusText.value = '正在启动数字人...'
  try {
    await destroyAvatarSdk()

    avatarSdkInstance = new AvatarPlatform({ useInlinePlayer: true })
    attachIflytekSdkListeners(avatarSdkInstance, SDKEvents)

    const streamProtocol = STREAM_PROTOCOLS.includes(cfg.streamProtocol)
      ? cfg.streamProtocol
      : 'xrtc'

    // 竖版展示优先：若后端给了横屏分辨率（如 1280x720），这里自动切换为竖屏 720x1280
    const rawW = Number(cfg.defaultWidth ?? 1280) || 1280
    const rawH = Number(cfg.defaultHeight ?? 720) || 720
    const portraitW = rawW >= rawH ? rawH : rawW
    const portraitH = rawW >= rawH ? rawW : rawH

    avatarSdkInstance.setApiInfo({
      serverUrl: cfg.avatarServerUrl || 'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact',
      appId: cfg.appId,
      apiKey: cfg.apiKey,
      apiSecret: cfg.apiSecret,
      sceneId: cfg.sceneId
    })

    avatarSdkInstance.setGlobalParams({
      avatar_dispatch: { interactive_mode: 0, content_analysis: 0 },
      stream: {
        protocol: streamProtocol,
        // 只显示数字人（透明背景）：需要场景支持透明通道
        alpha: 1,
        bitrate: 1000000,
        fps: 25
      },
      avatar: {
        avatar_id: String(cfg.defaultAvatarId ?? ''),
        width: portraitW,
        height: portraitH,
        scale: 1,
        move_h: 0,
        move_v: 0,
        audio_format: 1
      },
      tts: {
        vcn: cfg.defaultTtsVcn || 'x4_xiaoxuan',
        speed: 50,
        pitch: 50,
        volume: 100
      }
    })

    await avatarSdkInstance.start({ wrapper })

    // 文档 2.2.3：player = avatarPlatform.player || avatarPlatform.createPlayer()
    const player =
      avatarSdkInstance.player ||
      (typeof avatarSdkInstance.createPlayer === 'function'
        ? avatarSdkInstance.createPlayer()
        : undefined)
    if (PlayerEvents && player?.on) {
      player.on(PlayerEvents.playNotAllowed, () => {
        statusText.value = '浏览器限制自动播放，请点击「恢复播放」'
      })
      player.on(PlayerEvents.error, (err) => {
        const msg = err?.message ?? err?.code ?? String(err)
        if (msg) errorText.value = `播放器：${msg}`
      })
    }

    await nextTick()
    await new Promise((r) => requestAnimationFrame(r))
    try {
      player?.resize?.()
    } catch {
      /* ignore */
    }
    try {
      await player?.resume?.()
    } catch {
      /* 部分环境无限制时 resume 可能抛错，忽略 */
    }

    running.value = true
    statusText.value = '数字人已启动'
  } catch (e) {
    errorText.value = e?.message || '启动失败，请检查密钥、sceneId、形象 ID'
    statusText.value = '启动失败'
    running.value = false
    await destroyAvatarSdk()
  } finally {
    starting.value = false
  }
}

async function startVoice() {
  errorText.value = ''
  if (!running.value || !avatarSdkInstance) {
    errorText.value = '请先启动数字人'
    return
  }
  if (!sdkConnected.value || !streamStarted.value) {
    errorText.value = '连接未就绪，请等待数字人启动完成后再开始对话'
    return
  }
  if (voiceRecording.value || voiceStarting.value) return

  let mod
  try {
    mod = await loadAvatarSdkModule()
  } catch (e) {
    errorText.value = e?.message || 'SDK 加载失败'
    return
  }

  voiceStarting.value = true
  voiceTurnState.value = 'user_speaking'
  statusText.value = '正在请求麦克风权限...'
  try {
    // 每轮开始前清空本轮语音识别调试文本
    asrDebugCurrent.value = ''
    audioFrameCount.value = 0
    lastAudioSendAt.value = ''
    lastVoiceError.value = ''
    asrEventCount.value = 0
    audioEventCount.value = 0
    voiceDiagText.value = ''
    resetBrowserAsr()
    await ensureMicPermission(mod.UserMedia)
    // 文档：interrupt 可打断当前播报与理解结果，开始新一轮更干净
    try {
      await avatarSdkInstance.interrupt?.()
    } catch {
      /* ignore */
    }

    // 语音模式改为：浏览器 SpeechRecognition 先转文字
    const rec = ensureBrowserSpeechRecognition()
    if (!rec) {
      throw new Error('当前浏览器不支持 SpeechRecognition（请用 Edge/Chrome）')
    }

    voiceRecording.value = true
    recorderAudioEventName = 'browser(SpeechRecognition)'
    voiceDiagText.value = '浏览器语音识别中…结束讲话后会自动把文字发给数字人'
    try {
      rec.start()
    } catch {
      /* ignore */
    }
  } catch (e) {
    voiceRecording.value = false
    errorText.value = e?.message || '启动语音失败'
    statusText.value = '语音启动失败'
  } finally {
    voiceStarting.value = false
  }
}

async function stopVoice() {
  if (!voiceRecording.value || voiceStopping.value) return
  voiceStopping.value = true
  voiceTurnState.value = 'waiting_avatar'
  statusText.value = '正在结束录音...'
  try {
    try {
      speechRec?.stop?.()
    } catch {
      /* ignore */
    }

    // SpeechRecognition 的最终结果可能在 stop() 后稍晚返回，短暂等待再取文本
    const text = await waitForBrowserAsrFinalText(900)
    if (!text) {
      voiceDiagText.value = '未识别到有效文本，请重试（说话更靠近麦克风，环境更安静）'
      return
    }

    // 自动把识别到的文字发给数字人（走已验证可用的文字链路）
    statusText.value = '识别完成，正在发送给数字人...'
    chatText.value = text
    await sendText()
  } catch {
    /* ignore */
  } finally {
    voiceStopping.value = false
    voiceRecording.value = false
    statusText.value = '录音已结束'
    audioFrameStarted = false
    if (voiceTurnState.value === 'user_speaking') {
      voiceTurnState.value = 'idle'
    }
  }
}

async function stopDigitalHuman() {
  stopping.value = true
  statusText.value = '正在停止数字人...'
  try {
    if (voiceRecording.value) await stopVoice()
    await destroyAvatarSdk()
  } finally {
    running.value = false
    stopping.value = false
    statusText.value = '数字人已停止'
    isThinking.value = false
    isSpeaking.value = false
    nlpConnected = false
    voiceTurnState.value = 'idle'
  }
}

async function interruptCurrentSpeech() {
  if (!running.value || !avatarSdkInstance) return
  stopping.value = true
  try {
    await avatarSdkInstance.interrupt?.()
    isSpeaking.value = false
    statusText.value = '已打断当前播报'
  } catch (e) {
    const msg = e?.message ?? e?.code ?? String(e)
    errorText.value = `打断失败：${msg}`
  } finally {
    stopping.value = false
  }
}

async function sendText() {
  errorText.value = ''
  const text = (chatText.value || '').trim()
  if (!text) return
  if (!running.value || !avatarSdkInstance) {
    errorText.value = '请先启动数字人'
    return
  }
  if (!sdkConnected.value) {
    errorText.value = '尚未建立连接，请稍等或重启数字人'
    return
  }
  if (!streamStarted.value) {
    errorText.value = '流尚未启动完成，请稍后再发送'
    return
  }
  sendingText.value = true
  statusText.value = '正在发送...'
  try {
    // 文档：start 成功后可直接 writeText；nlp=true 由接口服务侧能力决定
    await avatarSdkInstance.writeText?.(text, {
      nlp: voiceNlpEnabled.value,
      avatar_dispatch: { interactive_mode: 1, content_analysis: 0 }
    })
    chatText.value = ''
    statusText.value = '已发送'
    // “思考中”只有在启用理解并且场景会回 NLP/ASR 时才会更明显；这里做一个短暂占位
    isThinking.value = !!voiceNlpEnabled.value
    if (isThinking.value) {
      setTimeout(() => {
        if (!isSpeaking.value) isThinking.value = false
      }, 800)
    }
  } catch (e) {
    const msg = e?.message ?? e?.code ?? String(e)
    if (isSessionInvalidMessage(msg)) {
      errorText.value = `会话失效，正在重连…`
      statusText.value = '重连中'
      const ok = await restartAvatarSession()
      if (ok) {
        try {
          // 重连后重试一次
          await avatarSdkInstance?.writeText?.(text, {
            nlp: voiceNlpEnabled.value,
            avatar_dispatch: { interactive_mode: 0, content_analysis: 0 }
          })
          chatText.value = ''
          statusText.value = '已发送'
          isThinking.value = !!voiceNlpEnabled.value
        } catch (e2) {
          const msg2 = e2?.message ?? e2?.code ?? String(e2)
          errorText.value = `发送失败：${msg2}`
          statusText.value = '发送失败'
        }
      } else {
        errorText.value = `发送失败：${msg}`
        statusText.value = '发送失败'
      }
    } else {
      errorText.value = `发送失败：${msg}`
      statusText.value = '发送失败'
    }
  } finally {
    sendingText.value = false
  }
}

function onChatKeydown(e) {
  // Enter 发送，Shift+Enter 换行
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void sendText()
  }
}

watch(drawerOpen, async (open) => {
  if (typeof document !== 'undefined') document.body.style.overflow = open ? 'hidden' : ''
  if (open) {
    window.addEventListener('keydown', onEscape)
    errorText.value = ''
    await fetchIflytekConfig()

    // 打开抽屉默认“自动启动数字人”，但不自动开始对话（对话由用户点击“开始对话”触发）
    try {
      if (!running.value && !starting.value) {
        await startDigitalHuman()
      }
    } catch {
      // ignore
    }
  } else {
    window.removeEventListener('keydown', onEscape)
    // 关闭抽屉 = 默认结束对话（录音停止 + 发送 end 帧），对话不再继续
    try {
      if (voiceRecording.value) await stopVoice()
    } catch {
      /* ignore */
    }

    if (running.value) await stopDigitalHuman()
    else await destroyAvatarSdk()
  }
})

onMounted(() => {
  pos.value = loadPos()
  window.addEventListener('resize', onResize)
})

onUnmounted(async () => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onEscape)
  document.body.style.overflow = ''
  await destroyAvatarSdk()
})
</script>

<template>
  <Teleport to="body">
    <button
      v-if="!drawerOpen"
      ref="fabRef"
      type="button"
      class="dh-fab"
      :class="{ 'is-dragging': dragging }"
      :style="{ left: `${pos.left}px`, top: `${pos.top}px` }"
      aria-label="数字人助手"
      :aria-expanded="drawerOpen"
      aria-controls="digital-human-drawer"
      @pointerdown="onPointerDown"
    >
      <span class="dh-fab-icon" aria-hidden="true">
        <img :src="digitalmanAvatar" alt="数字人头像" />
      </span>
      <span class="dh-fab-label">数字人</span>
    </button>

    <div v-if="drawerOpen" class="dh-backdrop" aria-hidden="true" @click="closeDrawer" />
    <Transition name="dh-slide">
      <aside
        v-if="drawerOpen"
        id="digital-human-drawer"
        class="dh-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="digital-human-title"
        @click.stop
      >
        <header class="dh-drawer-head">
          <h2 id="digital-human-title" class="dh-drawer-title">数字人</h2>
          <div class="dh-head-actions">
            <button type="button" class="dh-action" :disabled="!canInterrupt" @click="interruptCurrentSpeech">
              {{ stopping ? '中止中...' : '中止' }}
            </button>
          </div>
          <button type="button" class="dh-close" aria-label="关闭" @click="closeDrawer">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </header>
        <div class="dh-drawer-body">
          <div class="dh-statebar dh-statebar-top" aria-live="polite">
            <span class="dh-pill" :class="{ on: running }">运行中</span>
            <span class="dh-pill" :class="{ on: voiceRecording }">录音中</span>
            <span class="dh-pill" :class="{ on: isThinking }">思考中</span>
            <span class="dh-pill" :class="{ on: isSpeaking }">说话中</span>
          </div>

          <p class="dh-turn-label">{{ voiceTurnLabel }}</p>
          <p v-if="lastAsrText" class="dh-mini">识别：{{ lastAsrText }}</p>
          <p v-if="lastSubtitle" class="dh-mini">字幕：{{ lastSubtitle }}</p>
          <p class="dh-status">{{ statusText }}</p>
          <p v-if="errorText" class="dh-error">{{ errorText }}</p>

          <div class="dh-stream-shell">
            <div :id="STREAM_DOM_ID" class="dh-stream-canvas"></div>
          </div>

          <div class="dh-inputbar">
            <button
              type="button"
              class="dh-mic"
              :class="{ on: micActive }"
              :disabled="!canToggleMic"
              @click="toggleMic"
              aria-label="语音输入"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 14a3 3 0 0 0 3-3V7a3 3 0 0 0-6 0v4a3 3 0 0 0 3 3z" />
                <path d="M19 11a7 7 0 0 1-14 0" />
                <path d="M12 19v3" />
              </svg>
            </button>

            <input
              v-model="chatText"
              class="dh-input"
              type="text"
              placeholder="也可以输入文字…"
              :disabled="!running || sendingText"
              @keydown="onChatKeydown"
            />
            <button
              type="button"
              class="dh-send"
              :disabled="!running || sendingText || !chatText.trim()"
              @click="sendText"
            >
              {{ sendingText ? '发送中...' : '发送' }}
            </button>
          </div>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dh-fab {
  position: fixed;
  z-index: 10050;
  width: 132px;
  height: 52px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  cursor: grab;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: #dbeafe;
  color: #1e3a8a;
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25), 0 2px 6px rgba(15, 23, 42, 0.08);
  user-select: none;
  touch-action: none;
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}

.dh-fab:hover {
  box-shadow: 0 10px 26px rgba(59, 130, 246, 0.3), 0 3px 10px rgba(15, 23, 42, 0.12);
}

.dh-fab.is-dragging {
  cursor: grabbing;
  transform: scale(1.02);
}

.dh-fab-icon img {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  border: 1.5px solid rgba(255, 255, 255, 0.85);
}

.dh-fab-label {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1;
  opacity: 1;
}

.dh-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10040;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(2px);
}

.dh-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 10041;
  width: min(420px, 100vw);
  max-width: 100vw;
  background: #ffffff;
  box-shadow: -12px 0 40px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
}

.dh-drawer-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.dh-head-actions {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

.dh-head-actions .dh-action {
  height: 32px;
  border-radius: 999px;
  padding: 0 14px;
  font-weight: 600;
}

.dh-head-actions .dh-action:not(.primary) {
  background: #ffffff;
}

.dh-head-actions .dh-action:hover:not(:disabled) {
  filter: brightness(0.98);
}

.dh-head-actions .dh-action.primary:hover:not(:disabled) {
  filter: brightness(0.95);
}

.dh-drawer-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}

.dh-close {
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s,
    color 0.15s;
}

.dh-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.dh-drawer-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 20px 18px;
  display: flex;
  flex-direction: column;
}

.dh-action {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  border-radius: 10px;
  height: 34px;
  padding: 0 12px;
  cursor: pointer;
}

.dh-action.primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.dh-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dh-voice-opts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
  margin: 0 0 8px;
  color: #475569;
  font-size: 12px;
}

.dh-opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.dh-opt-seconds input[type='number'] {
  width: 72px;
  height: 28px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 8px;
}

.dh-statebar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 8px;
}

.dh-statebar-top {
  margin-top: 2px;
}

.dh-turn-label {
  margin: 0 0 8px;
  font-size: 13px;
  color: #334155;
  font-weight: 600;
}

.dh-turn {
  margin: 0 0 8px;
}

.dh-turn-btn {
  width: 100%;
  height: 34px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
}

.dh-turn-btn.on {
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(37, 99, 235, 0.12);
  color: #0f172a;
}

.dh-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid #e2e8f0;
  color: #64748b;
  background: #f8fafc;
}

.dh-pill.on {
  color: #0f172a;
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(37, 99, 235, 0.12);
}

.dh-mini {
  margin: 0 0 6px;
  font-size: 12px;
  color: #475569;
  line-height: 1.4;
  word-break: break-word;
}

.dh-chat {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: stretch;
  margin: 0 0 10px;
}


.dh-chat-input {
  width: 100%;
  resize: vertical;
  min-height: 54px;
  max-height: 140px;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.4;
  outline: none;
}

.dh-chat-input:focus {
  border-color: rgba(37, 99, 235, 0.7);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
}

.dh-chat-send {
  height: auto;
  padding: 0 14px;
  border-radius: 12px;
  min-width: 72px;
}

.dh-status {
  margin: 0;
  font-size: 13px;
  color: #334155;
}

.dh-error {
  margin: 6px 0 10px;
  color: #dc2626;
  font-size: 12px;
  line-height: 1.5;
}

.dh-stream-shell {
  margin-top: 10px;
  /* 竖屏容器：黑框本身就是 9:16，不要横板画幅 */
  width: 100%;
  aspect-ratio: 9 / 16;
  height: auto;
  max-height: 72vh;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: transparent;
  display: flex;
  align-items: stretch;
  justify-content: stretch;
  overflow: hidden;
  flex: 1;
  min-height: 360px;
}
.dh-inputbar {
  position: sticky;
  bottom: 0;
  margin-top: 12px;
  padding-top: 10px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  display: grid;
  grid-template-columns: 44px 1fr 84px;
  gap: 10px;
  align-items: center;
}

.dh-mic {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.dh-mic.on {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.dh-mic:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dh-input {
  height: 44px;
  border-radius: 14px;
  border: 1px solid #cbd5e1;
  padding: 0 14px;
  outline: none;
  font-size: 14px;
}

.dh-input:focus {
  border-color: rgba(37, 99, 235, 0.7);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
}

.dh-send {
  height: 44px;
  border-radius: 14px;
  border: none;
  background: #2563eb;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.dh-send:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.dh-stream-canvas {
  flex: 1;
  width: 100%;
  min-height: 0;
  min-width: 0;
  position: relative;
}

.dh-stream-canvas :deep(video),
.dh-stream-canvas :deep(canvas) {
  width: 100%;
  height: 100%;
  object-fit: contain; /* 竖版完整显示在黑框内 */
}

.dh-tips {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.dh-slide-enter-active,
.dh-slide-leave-active {
  transition: transform 0.26s cubic-bezier(0.4, 0, 0.2, 1);
}

.dh-slide-enter-from,
.dh-slide-leave-to {
  transform: translateX(100%);
}
</style>
