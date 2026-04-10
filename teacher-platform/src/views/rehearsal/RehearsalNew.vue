<!-- teacher-platform/src/views/rehearsal/RehearsalNew.vue -->
<template>
  <div class="rehearsal-new">
    <div class="new-card">
      <h2>课堂预演</h2>
      <p class="desc">输入教学主题，AI 为您生成可播放的课堂预演</p>

      <!-- 表单输入：仅在无 sessionId 且未生成时显示 -->
      <template v-if="!route.query.sessionId && !store.generatingStatus">
        <div class="form-group">
          <label>教学主题</label>
          <el-input v-model="topic" type="textarea" :rows="3"
            placeholder="例：高中物理 - 牛顿第二定律" :disabled="isGenerating" />
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>语言</label>
            <el-select v-model="language" :disabled="isGenerating">
              <el-option label="中文" value="zh-CN" />
              <el-option label="English" value="en-US" />
            </el-select>
          </div>
          <div class="form-group half">
            <label>语音合成</label>
            <el-switch v-model="enableTTS" :disabled="isGenerating" />
          </div>
        </div>

        <el-button type="primary" :loading="isGenerating"
          :disabled="!topic.trim() || isGenerating" @click="handleGenerate" style="width:100%">
          {{ isGenerating ? '生成中...' : '开始生成' }}
        </el-button>
      </template>

      <!-- 生成进度 -->
      <div v-if="store.generatingStatus" class="progress-section">
        <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="8" />
        <p class="progress-text">{{ store.generatingProgress }}</p>

        <!-- 页级状态列表 -->
        <div v-if="store.sceneStatuses.length" class="scene-status-list">
          <div v-for="s in store.sceneStatuses" :key="s.sceneIndex" class="scene-status-item">
            <span class="scene-title">{{ s.sceneIndex + 1 }}. {{ s.title }}</span>
            <el-tag :type="s.status === 'ready' ? 'success' : s.status === 'failed' ? 'danger' : 'info'" size="small">
              {{ s.status === 'ready' ? '就绪' : s.status === 'failed' ? '失败' : '生成中' }}
            </el-tag>
            <el-button v-if="s.status === 'failed'" size="small" text type="primary"
              @click="handleRetry(s.sceneIndex)">
              重试
            </el-button>
          </div>
        </div>

        <el-button v-if="store.scenes.length > 0 && store.currentSession"
          type="success" @click="goToPlay" style="width:100%;margin-top:12px">
          开始播放（{{ store.scenes.length }} 页就绪）
        </el-button>

        <el-button @click="router.push('/rehearsal')" style="width:100%;margin-top:8px">
          返回
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { fetchSession } from '../../api/rehearsal.js'

const router = useRouter()
const route = useRoute()
const store = useRehearsalStore()

const topic = ref('')
const language = ref('zh-CN')
const enableTTS = ref(true)
let pollTimer = null

const isGenerating = computed(() => store.generatingStatus === 'generating')

const progressPercent = computed(() => {
  if (!store.totalScenes) return 10
  const done = store.sceneStatuses.filter(s => s.status === 'ready' || s.status === 'failed').length
  return Math.round((done / store.totalScenes) * 90) + 10
})

const progressStatus = computed(() => {
  if (store.generatingStatus === 'error') return 'exception'
  if (store.generatingStatus === 'complete') return 'success'
  if (store.generatingStatus === 'partial' || store.generatingStatus === 'failed') return 'warning'
  return undefined
})

onMounted(async () => {
  const queryTopic = route.query.topic
  const querySessionId = route.query.sessionId

  if (querySessionId) {
    await loadExistingSession(Number(querySessionId))
  } else if (queryTopic) {
    topic.value = queryTopic
    handleGenerate()
  }
})

onUnmounted(() => {
  stopPolling()
})

async function loadExistingSession(sessionId) {
  try {
    const data = await fetchSession(sessionId)
    store.currentSession = { id: data.id, title: data.title, status: data.status }
    store.totalScenes = data.total_scenes || 0
    store.sceneStatuses = (data.scenes || []).map(s => ({
      sceneIndex: s.scene_order,
      status: s.scene_status,
      title: s.title,
      sceneId: s.id,
    }))

    store.scenes = (data.scenes || [])
      .filter(s => s.scene_status === 'ready')
      .map(s => ({
        sceneOrder: s.scene_order,
        title: s.title,
        slideContent: s.slide_content,
        actions: s.actions,
        keyPoints: s.key_points,
        sceneStatus: s.scene_status,
        audioStatus: s.audio_status,
      }))

    if (data.status === 'generating') {
      store.generatingStatus = 'generating'
      const doneCount = store.sceneStatuses.filter(s => s.status === 'ready' || s.status === 'failed').length
      store.generatingProgress = `已完成 ${doneCount}/${store.totalScenes} 页...`
      startPolling(sessionId)
    } else if (data.status === 'ready') {
      store.generatingStatus = 'complete'
      store.generatingProgress = '生成完成'
    } else if (data.status === 'partial') {
      store.generatingStatus = 'partial'
      store.generatingProgress = '部分页面生成失败，可重试失败页面'
    } else {
      store.generatingStatus = 'failed'
      store.generatingProgress = '生成失败'
    }
  } catch (e) {
    store.generatingStatus = 'error'
    store.generatingProgress = `加载失败: ${e.message}`
  }
}

function startPolling(sessionId) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const data = await fetchSession(sessionId)
      store.totalScenes = data.total_scenes || 0
      store.sceneStatuses = (data.scenes || []).map(s => ({
        sceneIndex: s.scene_order,
        status: s.scene_status,
        title: s.title,
        sceneId: s.id,
      }))

      store.scenes = (data.scenes || [])
        .filter(s => s.scene_status === 'ready')
        .map(s => ({
          sceneOrder: s.scene_order,
          title: s.title,
          slideContent: s.slide_content,
          actions: s.actions,
          keyPoints: s.key_points,
          sceneStatus: s.scene_status,
          audioStatus: s.audio_status,
        }))

      const doneCount = store.sceneStatuses.filter(s => s.status !== 'pending' && s.status !== 'generating').length
      const failedCount = store.sceneStatuses.filter(s => s.status === 'failed').length
      store.generatingProgress = `已完成 ${doneCount}/${store.totalScenes} 页`
        + (failedCount > 0 ? `（${failedCount} 页失败）` : '') + '...'

      if (data.status !== 'generating') {
        if (data.status === 'ready') {
          store.generatingStatus = 'complete'
          store.generatingProgress = '生成完成'
        } else if (data.status === 'partial') {
          store.generatingStatus = 'partial'
          store.generatingProgress = '部分页面生成失败，可重试失败页面'
        } else {
          store.generatingStatus = 'failed'
          store.generatingProgress = '生成失败'
        }
        store.currentSession.status = data.status
        stopPolling()
      }
    } catch (e) {
      console.error('Polling failed:', e)
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleGenerate() {
  store.$reset()
  await store.startGenerate({
    topic: topic.value.trim(),
    language: language.value,
    enable_tts: enableTTS.value,
    speed: 1.0,
  })
}

async function handleRetry(sceneOrder) {
  if (!store.currentSession?.id) return
  await store.retryFailedScene(store.currentSession.id, sceneOrder)
  await loadExistingSession(store.currentSession.id)
}

function goToPlay() {
  if (store.currentSession?.id) {
    router.push(`/rehearsal/play/${store.currentSession.id}`)
  }
}
</script>

<style scoped>
.rehearsal-new { max-width: 560px; margin: 60px auto; padding: 0 20px; }
.new-card { background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
h2 { margin: 0 0 4px; font-size: 22px; }
.desc { color: #8b949e; font-size: 14px; margin: 0 0 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: #57606a; margin-bottom: 6px; }
.form-row { display: flex; gap: 16px; }
.half { flex: 1; }
.progress-section { margin-top: 20px; padding-top: 16px; border-top: 1px solid #eee; }
.progress-text { font-size: 13px; color: #58a6ff; margin: 8px 0 0; }
.scene-status-list { margin-top: 12px; }
.scene-status-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.scene-title { flex: 1; font-size: 13px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
