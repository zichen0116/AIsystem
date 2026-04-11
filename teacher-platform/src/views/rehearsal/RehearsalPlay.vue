<template>
  <div class="rehearsal-play">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>正在加载预演...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <p class="error-icon">!</p>
      <p class="error-text">{{ error }}</p>
      <div class="error-actions">
        <button class="error-btn primary" @click="retryLoad">重试</button>
        <button class="error-btn" @click="goBack">返回</button>
      </div>
    </div>

    <!-- 播放界面 -->
    <template v-else>
      <!-- Top bar -->
      <div class="top-bar">
        <button class="back-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          <span class="back-label">当前场景</span>
        </button>
        <span class="scene-title">{{ store.currentScene?.title || '' }}</span>
        <div class="top-spacer"></div>
      </div>

      <!-- Slide area -->
      <div class="slide-area">
        <div class="slide-container">
          <SlideRenderer v-if="store.currentScene" :slide="store.currentScene.slideContent" ref="slideRef">
            <SpotlightOverlay :target="store.spotlightTarget" :canvasRef="canvasEl" />
            <LaserPointer :target="store.laserTarget" :canvasRef="canvasEl" />
          </SlideRenderer>
          <div v-else class="empty-slide">
            <p>暂无内容</p>
          </div>
        </div>
      </div>

      <!-- Subtitle -->
      <SubtitlePanel :text="store.currentSubtitle" />

      <!-- Controls -->
      <PlaybackControls
        :isPlaying="store.isPlaying"
        :currentIndex="store.currentSceneIndex"
        :totalCount="store.totalScenesCount"
        @play="handlePlay"
        @pause="engine.pause()"
        @prev="engine.prevScene()"
        @next="engine.nextScene()"
        @jump="engine.jumpToScene($event)"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { usePlaybackEngine } from '../../composables/usePlaybackEngine.js'
import SlideRenderer from '../../components/rehearsal/SlideRenderer.vue'
import SpotlightOverlay from '../../components/rehearsal/SpotlightOverlay.vue'
import LaserPointer from '../../components/rehearsal/LaserPointer.vue'
import SubtitlePanel from '../../components/rehearsal/SubtitlePanel.vue'
import PlaybackControls from '../../components/rehearsal/PlaybackControls.vue'

const route = useRoute()
const router = useRouter()
const store = useRehearsalStore()
const engine = usePlaybackEngine()
const slideRef = ref(null)
const loading = ref(true)
const error = ref('')

const canvasEl = computed(() => slideRef.value?.canvasRef || null)

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) {
    error.value = '无效的预演 ID'
    loading.value = false
    return
  }
  try {
    if (!store.currentSession || store.currentSession.id !== id) {
      await store.loadSession(id)
    }
    if (store.scenes.length === 0) {
      error.value = '该预演暂无可播放的内容'
    }
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  engine.cleanup()
  store.savePlaybackProgress()
})

function handlePlay() {
  if (store.isPaused) {
    engine.resume()
  } else {
    engine.start()
  }
}

async function retryLoad() {
  loading.value = true
  error.value = ''
  try {
    const id = Number(route.params.id)
    await store.loadSession(id)
    if (store.scenes.length === 0) {
      error.value = '该预演暂无可播放的内容'
    }
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

function goBack() {
  engine.stop()
  router.push('/rehearsal')
}
</script>

<style scoped>
.rehearsal-play {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

/* 加载状态 */
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #8b949e;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #30363d;
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误状态 */
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.error-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.error-text {
  color: #8b949e;
  font-size: 15px;
  margin: 0;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.error-btn {
  padding: 8px 24px;
  border: 1px solid #30363d;
  background: transparent;
  color: #e6edf3;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s;
}

.error-btn:hover {
  background: #161b22;
  border-color: #8b949e;
}

.error-btn.primary {
  background: #58a6ff;
  border-color: #58a6ff;
  color: #0d1117;
}

.error-btn.primary:hover {
  background: #79b8ff;
  border-color: #79b8ff;
}

/* Top bar */
.top-bar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #21262d;
  min-height: 48px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: #8b949e;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  transition: all 0.15s;
}

.back-btn:hover {
  color: #e6edf3;
  background: rgba(255, 255, 255, 0.06);
}

.back-btn svg {
  width: 16px;
  height: 16px;
}

.scene-title {
  flex: 1;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #e6edf3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 16px;
}

.top-spacer {
  width: 100px;
}

/* Slide area */
.slide-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 32px;
  min-height: 0;
}

.slide-container {
  max-width: 960px;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  position: relative;
}

.empty-slide {
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #161b22;
  color: #8b949e;
  border-radius: 12px;
}
</style>
