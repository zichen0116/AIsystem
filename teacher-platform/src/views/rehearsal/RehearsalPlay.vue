<template>
  <div class="rehearsal-play">
    <!-- Top bar -->
    <div class="top-bar">
      <el-button text @click="goBack">← 返回</el-button>
      <span class="title">{{ store.currentSession?.title || '课堂预演' }}</span>
      <span class="page-info">第 {{ store.currentSceneIndex + 1 }}/{{ store.totalScenesCount }} 页</span>
    </div>

    <!-- Slide area -->
    <div class="slide-area">
      <SlideRenderer v-if="store.currentScene" :slide="store.currentScene.slideContent" ref="slideRef">
        <SpotlightOverlay :target="store.spotlightTarget" :canvasRef="canvasEl" />
        <LaserPointer :target="store.laserTarget" :canvasRef="canvasEl" />
      </SlideRenderer>
      <div v-else class="empty-slide">
        <p>暂无内容</p>
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
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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

const canvasEl = computed(() => slideRef.value?.canvasRef || null)

onMounted(async () => {
  const id = Number(route.params.id)
  if (id && (!store.currentSession || store.currentSession.id !== id)) {
    await store.loadSession(id)
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

function goBack() {
  engine.stop()
  router.push('/rehearsal/history')
}
</script>

<style scoped>
.rehearsal-play { display: flex; flex-direction: column; height: 100vh; background: #0d1117; }
.top-bar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; border-bottom: 1px solid #30363d; }
.title { color: #e6edf3; font-size: 15px; }
.page-info { color: #8b949e; font-size: 13px; }
.slide-area { flex: 1; display: flex; align-items: center; justify-content: center; padding: 16px; position: relative; }
.slide-area .slide-renderer { max-width: 900px; width: 100%; position: relative; }
.empty-slide { color: #8b949e; text-align: center; }
</style>
