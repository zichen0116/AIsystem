<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { apiRequest } from '@/api/http'

const props = defineProps({
  visible: { type: Boolean, default: false },
  voiceMode: { type: Boolean, default: false }
})

const STREAM_DOM_ID = 'admin-iflytek-avatar-stream'
const ADMIN_AVATAR_ID = '111188001'
const ADMIN_DASHBOARD_INTRO = [
  '欢迎来到 EduPrep 数据中台。',
  '左侧区域展示备课功能使用统计、资源库调用占比和备课效率周趋势，帮助管理者了解教学准备的活跃度与完成质量。',
  '中上区域是关键指标看板，实时呈现活跃教师数、备课任务总量、备课完成率和系统平均响应时长。',
  '中间主区域为活跃教师人数省级分布，用于观察不同地区的使用热度与覆盖情况。',
  '右侧区域包含系统使用学段占比、功能周使用趋势和热门学科 TOP5，可用于研判学段结构和功能偏好。',
  '通过这块大屏，管理员可以快速完成平台运行监控、教学资源运营分析和策略调整。'
].join('')

const statusText = ref('数字人未启动')
const errorText = ref('')
const running = ref(false)
const voiceRecording = ref(false)

let avatarSdkModule = null
let avatarSdkInstance = null
let speechRec = null
let iflytekConfig = null

function isDashboardIntroQuery(text) {
  const t = (text || '').trim()
  if (!t) return false
  return /介绍|讲解|说明/.test(t) && /大屏|数据中台|看板/.test(t)
}

function normalizeIflytekConfig(raw) {
  const sceneId = raw?.sceneId ?? raw?.scene_id ?? raw?.serviceId ?? raw?.service_id ?? ''
  return {
    ...raw,
    sceneId: String(sceneId || '').trim(),
    avatarServerUrl: raw?.avatarServerUrl ?? raw?.avatar_server_url ?? 'wss://avatar.cn-huadong-1.xf-yun.com/v1/interact',
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
        avatar_id: ADMIN_AVATAR_ID,
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
  } catch (e) {
    errorText.value = e?.message || '数字人启动失败'
    statusText.value = '启动失败'
    running.value = false
  }
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
    statusText.value = '数字人已关闭'
  }
}

function ensureRecognition() {
  if (speechRec) return speechRec
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Ctor) throw new Error('当前浏览器不支持语音识别，请使用 Edge/Chrome')
  const rec = new Ctor()
  rec.lang = 'zh-CN'
  rec.continuous = true
  rec.interimResults = false
  rec.maxAlternatives = 1
  rec.onresult = async (event) => {
    const txt = event?.results?.[event.results.length - 1]?.[0]?.transcript?.trim()
    if (!txt || !avatarSdkInstance) return
    const outputText = isDashboardIntroQuery(txt) ? ADMIN_DASHBOARD_INTRO : txt
    try {
      await avatarSdkInstance.writeText?.(outputText, {
        nlp: false,
        avatar_dispatch: { interactive_mode: 1, content_analysis: 0 }
      })
      statusText.value = isDashboardIntroQuery(txt) ? '已发送：数据大屏介绍' : `已发送：${txt}`
    } catch (e) {
      errorText.value = e?.message || '语音文本发送失败'
    }
  }
  rec.onerror = (e) => {
    errorText.value = `语音识别错误: ${e?.error || 'unknown'}`
  }
  rec.onend = () => {
    if (voiceRecording.value && props.voiceMode) {
      try {
        rec.start()
      } catch {
        // ignore
      }
    }
  }
  speechRec = rec
  return rec
}

async function startVoice() {
  if (voiceRecording.value || !running.value) return
  try {
    const rec = ensureRecognition()
    await navigator.mediaDevices.getUserMedia({ audio: true })
    rec.start()
    voiceRecording.value = true
    statusText.value = '语音模式已开启'
  } catch (e) {
    errorText.value = e?.message || '开启语音失败'
    voiceRecording.value = false
  }
}

async function stopVoice() {
  if (!voiceRecording.value) return
  try {
    speechRec?.stop?.()
  } catch {
    // ignore
  } finally {
    voiceRecording.value = false
    if (running.value) statusText.value = '语音模式已关闭'
  }
}

watch(
  () => props.visible,
  async (v) => {
    if (v) await startDigitalHuman()
    else await stopDigitalHuman()
  },
  { immediate: true }
)

watch(
  () => props.voiceMode,
  async (v) => {
    if (!props.visible) return
    if (v) await startVoice()
    else await stopVoice()
  },
  { immediate: true }
)

onBeforeUnmount(async () => {
  await stopDigitalHuman()
})
</script>

<template>
  <div v-if="visible" class="admin-dh-widget">
    <div :id="STREAM_DOM_ID" class="admin-dh-stream" />
  </div>
</template>

<style scoped>
.admin-dh-widget {
  width: min(21vw, 235px);
  min-width: 160px;
  aspect-ratio: 9 / 16;
  background: transparent;
  pointer-events: none;
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
</style>

