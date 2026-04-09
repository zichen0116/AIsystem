<!-- teacher-platform/src/views/rehearsal/RehearsalNew.vue -->
<template>
  <div class="rehearsal-new">
    <div class="new-card">
      <h2>课堂预演</h2>
      <p class="desc">输入教学主题，AI 为您生成可播放的课堂预演</p>

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

      <!-- 生成预览 -->
      <div v-if="store.generatingStatus" class="progress-section">
        <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="8" />
        <p class="progress-text">{{ store.generatingProgress }}</p>

        <!-- 页级状态列表 -->
        <div v-if="store.sceneStatuses.length" class="scene-status-list">
          <div v-for="s in store.sceneStatuses" :key="s.sceneIndex" class="scene-status-item">
            <span class="scene-title">{{ s.sceneIndex + 1 }}. {{ s.title }}</span>
            <el-tag :type="s.status === 'ready' ? 'success' : 'danger'" size="small">
              {{ s.status === 'ready' ? '就绪' : '失败' }}
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'

const router = useRouter()
const store = useRehearsalStore()

const topic = ref('')
const language = ref('zh-CN')
const enableTTS = ref(true)

const isGenerating = computed(() => store.generatingStatus === 'generating')

const progressPercent = computed(() => {
  if (!store.totalScenes) return 10
  const done = store.sceneStatuses.length
  return Math.round((done / store.totalScenes) * 90) + 10
})

const progressStatus = computed(() => {
  if (store.generatingStatus === 'error') return 'exception'
  if (store.generatingStatus === 'complete') return 'success'
  return undefined
})

async function handleGenerate() {
  store.$reset()
  await store.startGenerate({
    topic: topic.value.trim(),
    language: language.value,
    enable_tts: enableTTS.value,
    voice: 'Cherry',
    speed: 1.0,
  })
}

async function handleRetry(sceneOrder) {
  if (!store.currentSession?.id) return
  await store.retryFailedScene(store.currentSession.id, sceneOrder)
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
