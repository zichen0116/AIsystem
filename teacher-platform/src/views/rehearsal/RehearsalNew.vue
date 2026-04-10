<!-- teacher-platform/src/views/rehearsal/RehearsalNew.vue -->
<template>
  <div class="rehearsal-new-page">
    <!-- 背景光斑动画 -->
    <div class="bg-orb bg-orb-orange"></div>
    <div class="bg-orb bg-orb-pink"></div>

    <!-- 返回按钮 -->
    <button class="back-btn" @click="router.push('/rehearsal')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      <span>返回</span>
    </button>

    <div class="center-content">
      <!-- 主卡片 -->
      <div class="glass-card">

        <!-- ============ 表单态：无 sessionId 且未生成 ============ -->
        <template v-if="!route.query.sessionId && !store.generatingStatus">
          <h2 class="card-title">课堂预演</h2>
          <p class="card-desc">输入教学主题，AI 为您生成可播放的课堂预演</p>

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

          <button class="primary-btn" :disabled="!topic.trim() || isGenerating" @click="handleGenerate">
            {{ isGenerating ? '生成中...' : '开始生成' }}
          </button>
        </template>

        <!-- ============ 生成进度态 ============ -->
        <template v-if="store.generatingStatus">
          <!-- 进度步骤指示器 -->
          <div class="step-dots">
            <div v-for="(step, idx) in steps" :key="step"
              class="step-dot"
              :class="{ active: idx === currentStep, done: idx < currentStep }"
            ></div>
          </div>

          <!-- 中央动画区域 -->
          <div class="visualizer-area">
            <!-- 生成中：魔法课件动画 -->
            <template v-if="isGenerating">
              <!-- 轨道环 -->
              <div class="orbit orbit-1"></div>
              <div class="orbit orbit-2"></div>

              <!-- 浮动粒子 -->
              <div class="sparkle s1"></div>
              <div class="sparkle s2"></div>
              <div class="sparkle s3"></div>
              <div class="sparkle s4"></div>
              <div class="sparkle s5"></div>
              <div class="sparkle s6"></div>

              <!-- 3张迷你PPT卡片 -->
              <div class="mini-slide slide-back">
                <div class="slide-line" style="width:70%"></div>
                <div class="slide-line" style="width:50%"></div>
                <div class="slide-line" style="width:85%"></div>
                <div class="slide-line" style="width:40%"></div>
                <div class="slide-shimmer"></div>
              </div>
              <div class="mini-slide slide-mid">
                <div class="slide-line" style="width:60%"></div>
                <div class="slide-line" style="width:80%"></div>
                <div class="slide-line" style="width:45%"></div>
                <div class="slide-chart"></div>
                <div class="slide-shimmer"></div>
              </div>
              <div class="mini-slide slide-front">
                <div class="slide-title-bar"></div>
                <div class="slide-line" style="width:90%"></div>
                <div class="slide-line" style="width:65%"></div>
                <div class="slide-line" style="width:75%"></div>
                <div class="slide-shimmer"></div>
              </div>
            </template>

            <!-- 完成态 -->
            <div v-else-if="store.generatingStatus === 'complete'" class="result-icon result-success">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>

            <!-- 部分完成 -->
            <div v-else-if="store.generatingStatus === 'partial'" class="result-icon result-warning">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </div>

            <!-- 失败态 -->
            <div v-else-if="store.generatingStatus === 'failed' || store.generatingStatus === 'error'" class="result-icon result-error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
          </div>

          <!-- 状态文字 -->
          <h2 class="status-title">{{ statusTitle }}</h2>
          <p class="status-desc">{{ statusDesc }}</p>

          <!-- 进度条 -->
          <div v-if="isGenerating || store.generatingStatus === 'partial'" class="progress-bar-wrap">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <span class="progress-label">{{ progressPercent }}%</span>
          </div>

          <!-- 场景状态列表 -->
          <div v-if="store.sceneStatuses.length" class="scene-list">
            <div v-for="s in store.sceneStatuses" :key="s.sceneIndex" class="scene-row">
              <div class="scene-dot"
                :class="{
                  'dot-ready': s.status === 'ready',
                  'dot-generating': s.status === 'generating' || s.status === 'pending',
                  'dot-failed': s.status === 'failed'
                }"
              ></div>
              <span class="scene-name">{{ s.sceneIndex + 1 }}. {{ s.title || '场景' }}</span>
              <span class="scene-status-label" :class="`label-${s.status}`">
                {{ { ready: '就绪', failed: '失败', generating: '生成中', pending: '等待中' }[s.status] || s.status }}
              </span>
              <button v-if="s.status === 'failed'" class="retry-btn" @click="handleRetry(s.sceneIndex)">重试</button>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="action-area">
            <template v-if="isGenerating">
              <div class="ai-working">
                <svg class="sparkle-icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z"/>
                </svg>
                <span>AI 正在创作</span>
              </div>
            </template>
            <template v-else>
              <button v-if="store.scenes.length > 0 && store.currentSession"
                class="primary-btn" @click="goToPlay">
                开始播放（{{ store.scenes.length }} 页就绪）
              </button>
              <button class="ghost-btn" @click="router.push('/rehearsal')">返回</button>
            </template>
          </div>
        </template>
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

const steps = ['大纲', '场景', '完成']

const currentStep = computed(() => {
  if (!store.generatingStatus) return 0
  if (store.generatingStatus === 'generating') {
    return store.sceneStatuses.length > 0 ? 1 : 0
  }
  return 2
})

const statusTitle = computed(() => {
  switch (store.generatingStatus) {
    case 'generating':
      return store.sceneStatuses.length > 0 ? '正在生成场景...' : '正在生成大纲...'
    case 'complete': return '生成完成'
    case 'partial': return '部分完成'
    case 'failed': return '生成失败'
    case 'error': return '出错了'
    default: return ''
  }
})

const statusDesc = computed(() => {
  if (store.generatingStatus === 'generating') {
    return store.generatingProgress || 'AI 正在为您打造精彩课件，请稍候...'
  }
  if (store.generatingStatus === 'complete') {
    return '所有场景已就绪，可以开始播放预演'
  }
  if (store.generatingStatus === 'partial') {
    return '部分页面生成失败，可点击重试'
  }
  return store.generatingProgress || ''
})

const progressPercent = computed(() => {
  if (!store.totalScenes) return 10
  const done = store.sceneStatuses.filter(s => s.status === 'ready' || s.status === 'failed').length
  return Math.round((done / store.totalScenes) * 90) + 10
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
/* ====== 全屏背景 ====== */
.rehearsal-new-page {
  min-height: 100vh;
  background: linear-gradient(145deg, #fff4dc 0%, #fff9f2 28%, #fdf1ff 62%, #eff7ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 24px;
}

/* 背景模糊光斑 */
.bg-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

.bg-orb-orange {
  width: 500px;
  height: 500px;
  top: -10%;
  left: 10%;
  background: rgba(249, 115, 22, 0.25);
  animation: orb-pulse 6s ease-in-out infinite;
}

.bg-orb-pink {
  width: 450px;
  height: 450px;
  top: -5%;
  right: 5%;
  background: rgba(236, 72, 153, 0.2);
  animation: orb-pulse 8s ease-in-out infinite reverse;
}

@keyframes orb-pulse {
  0%, 100% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.15); opacity: 1; }
}

/* 返回按钮 */
.back-btn {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 8px 16px;
  border-radius: 12px;
  color: #475569;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.85);
  color: #1e293b;
}

.back-btn svg {
  width: 16px;
  height: 16px;
}

.center-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 520px;
}

/* ====== 毛玻璃卡片 ====== */
.glass-card {
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 24px;
  padding: 40px 36px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.03);
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ====== 表单态 ====== */
.card-title {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
}

.card-desc {
  color: #64748b;
  font-size: 14px;
  margin: 0 0 28px;
  text-align: center;
}

.form-group {
  margin-bottom: 16px;
  width: 100%;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #475569;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-row {
  display: flex;
  gap: 16px;
  width: 100%;
}

.half {
  flex: 1;
}

.primary-btn {
  width: 100%;
  padding: 12px 24px;
  border: none;
  background: linear-gradient(135deg, #ec4899, #f97316);
  color: white;
  font-size: 15px;
  font-weight: 600;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(236, 72, 153, 0.3);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ghost-btn {
  width: 100%;
  padding: 10px 24px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.5);
  color: #64748b;
  font-size: 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
  margin-top: 8px;
}

.ghost-btn:hover {
  background: rgba(255, 255, 255, 0.8);
  color: #1e293b;
}

/* ====== 进度步骤指示器 ====== */
.step-dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 32px;
}

.step-dot {
  height: 6px;
  width: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  transition: all 0.5s ease;
}

.step-dot.active {
  width: 32px;
  background: linear-gradient(90deg, #ec4899, #f97316);
  box-shadow: 0 0 12px rgba(236, 72, 153, 0.4);
}

.step-dot.done {
  background: rgba(236, 72, 153, 0.35);
}

/* ====== 中央动画区域 ====== */
.visualizer-area {
  width: 192px;
  height: 192px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

/* 轨道环 */
.orbit {
  position: absolute;
  border: 1.5px dashed rgba(236, 72, 153, 0.15);
  border-radius: 50%;
  pointer-events: none;
}

.orbit-1 {
  width: 180px;
  height: 180px;
  animation: slow-rotate 40s linear infinite;
}

.orbit-2 {
  width: 220px;
  height: 220px;
  animation: slow-rotate 55s linear infinite reverse;
  border-color: rgba(249, 115, 22, 0.12);
}

@keyframes slow-rotate {
  to { transform: rotate(360deg); }
}

/* 浮动粒子 */
.sparkle {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.s1 { width: 6px; height: 6px; background: #ec4899; top: 8px; left: 30px; animation: sparkle-float 3s ease-in-out infinite; opacity: 0.6; }
.s2 { width: 4px; height: 4px; background: #f97316; top: 20px; right: 15px; animation: sparkle-float 2.5s ease-in-out infinite 0.5s; opacity: 0.7; }
.s3 { width: 5px; height: 5px; background: #a855f7; bottom: 25px; left: 15px; animation: sparkle-float 3.5s ease-in-out infinite 1s; opacity: 0.5; }
.s4 { width: 3px; height: 3px; background: #ec4899; bottom: 10px; right: 30px; animation: sparkle-float 2.8s ease-in-out infinite 0.3s; opacity: 0.6; }
.s5 { width: 5px; height: 5px; background: #f59e0b; top: 50%; left: 0; animation: sparkle-float 3.2s ease-in-out infinite 0.8s; opacity: 0.5; }
.s6 { width: 4px; height: 4px; background: #a855f7; top: 40%; right: 0; animation: sparkle-float 2.6s ease-in-out infinite 1.2s; opacity: 0.6; }

@keyframes sparkle-float {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.4; }
  25% { transform: translate(6px, -8px) scale(1.3); opacity: 0.8; }
  50% { transform: translate(-4px, -14px) scale(0.8); opacity: 0.6; }
  75% { transform: translate(8px, -6px) scale(1.1); opacity: 0.9; }
}

/* 迷你PPT卡片 */
.mini-slide {
  position: absolute;
  background: white;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.slide-back {
  width: 72px;
  height: 52px;
  top: 28px;
  left: 22px;
  transform: rotate(-12deg);
  animation: float 3.5s ease-in-out infinite;
  z-index: 1;
}

.slide-mid {
  width: 80px;
  height: 58px;
  top: 36px;
  right: 18px;
  transform: rotate(8deg);
  animation: float 3s ease-in-out infinite 0.5s;
  z-index: 2;
}

.slide-front {
  width: 88px;
  height: 64px;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%) rotate(-3deg);
  animation: float 3.2s ease-in-out infinite 1s;
  z-index: 3;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
}

@keyframes float {
  0%, 100% { transform: translateX(var(--tx, 0)) rotate(var(--rot, 0deg)) translateY(0); }
  50% { transform: translateX(var(--tx, 0)) rotate(var(--rot, 0deg)) translateY(-8px); }
}

.slide-back { --rot: -12deg; --tx: 0px; }
.slide-mid { --rot: 8deg; --tx: 0px; }
.slide-front { --rot: -3deg; --tx: -50%; }

.slide-line {
  height: 3px;
  background: #f1f5f9;
  border-radius: 2px;
}

.slide-title-bar {
  height: 5px;
  width: 55%;
  background: linear-gradient(90deg, rgba(236, 72, 153, 0.25), rgba(249, 115, 22, 0.2));
  border-radius: 3px;
}

.slide-chart {
  width: 20px;
  height: 16px;
  border-radius: 3px;
  background: rgba(236, 72, 153, 0.08);
  align-self: flex-end;
}

/* 扫光效果 */
.slide-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 40%, rgba(255, 255, 255, 0.6) 50%, transparent 60%);
  animation: shimmer 2.5s linear infinite;
  pointer-events: none;
}

@keyframes shimmer {
  0% { transform: translateX(-150%); }
  100% { transform: translateX(200%); }
}

/* ====== 结果图标 ====== */
.result-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: scale-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.result-icon svg {
  width: 36px;
  height: 36px;
}

.result-success {
  background: rgba(34, 197, 94, 0.12);
  border: 2px solid rgba(34, 197, 94, 0.25);
  color: #16a34a;
}

.result-warning {
  background: rgba(245, 158, 11, 0.12);
  border: 2px solid rgba(245, 158, 11, 0.25);
  color: #d97706;
}

.result-error {
  background: rgba(239, 68, 68, 0.12);
  border: 2px solid rgba(239, 68, 68, 0.25);
  color: #dc2626;
}

@keyframes scale-in {
  0% { transform: scale(0.3); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

/* ====== 状态文字 ====== */
.status-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
}

.status-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: #64748b;
  text-align: center;
  line-height: 1.5;
}

/* ====== 自定义进度条 ====== */
.progress-bar-wrap {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ec4899, #f97316);
  border-radius: 3px;
  transition: width 0.6s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 60%, rgba(255, 255, 255, 0.4) 70%, transparent 80%);
  animation: shimmer 2s linear infinite;
}

.progress-label {
  font-size: 13px;
  font-weight: 600;
  color: #ec4899;
  min-width: 36px;
  text-align: right;
}

/* ====== 场景列表 ====== */
.scene-list {
  width: 100%;
  margin-top: 20px;
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0,0,0,0.1) transparent;
}

.scene-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.scene-row:last-child {
  border-bottom: none;
}

.scene-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-ready {
  background: #22c55e;
}

.dot-generating {
  background: #3b82f6;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.dot-failed {
  background: #ef4444;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.scene-name {
  flex: 1;
  font-size: 13px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scene-status-label {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
}

.label-ready {
  background: #dcfce7;
  color: #16a34a;
}

.label-generating, .label-pending {
  background: #dbeafe;
  color: #2563eb;
}

.label-failed {
  background: #fef2f2;
  color: #dc2626;
}

.retry-btn {
  border: none;
  background: transparent;
  color: #ec4899;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 6px;
  transition: all 0.15s;
}

.retry-btn:hover {
  background: rgba(236, 72, 153, 0.08);
}

/* ====== 底部操作区 ====== */
.action-area {
  width: 100%;
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.ai-working {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.sparkle-icon {
  width: 14px;
  height: 14px;
  color: #ec4899;
  animation: sparkle-pulse 2s ease-in-out infinite;
}

@keyframes sparkle-pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8) rotate(0deg); }
  50% { opacity: 1; transform: scale(1.2) rotate(15deg); }
}

/* ====== 响应式 ====== */
@media (max-width: 560px) {
  .glass-card {
    padding: 28px 20px;
    border-radius: 20px;
    min-height: 360px;
  }

  .visualizer-area {
    width: 160px;
    height: 160px;
  }

  .mini-slide { transform: scale(0.85); }
  .orbit-1 { width: 150px; height: 150px; }
  .orbit-2 { width: 180px; height: 180px; }
}

/* 尊重减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .bg-orb,
  .sparkle,
  .orbit,
  .mini-slide,
  .slide-shimmer,
  .sparkle-icon,
  .dot-generating,
  .progress-fill::after {
    animation: none !important;
  }
}
</style>
