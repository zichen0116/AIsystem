<template>
  <div class="playback-controls">
    <div class="controls-center">
      <button class="ctrl-btn" :disabled="currentIndex <= 0" @click="$emit('prev')" title="上一页">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>

      <button class="ctrl-btn play-btn" @click="$emit(isPlaying ? 'pause' : 'play')" :title="isPlaying ? '暂停' : '播放'">
        <svg v-if="!isPlaying" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
      </button>

      <button class="ctrl-btn" :disabled="currentIndex >= totalCount - 1" @click="$emit('next')" title="下一页">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    </div>

    <div class="progress-bar">
      <div class="progress-dots">
        <button
          v-for="i in totalCount"
          :key="i"
          class="dot"
          :class="{ active: i - 1 === currentIndex, done: i - 1 < currentIndex }"
          @click="$emit('jump', i - 1)"
          :title="`第 ${i} 页`"
        ></button>
      </div>
      <span class="page-text">{{ currentIndex + 1 }} / {{ totalCount }}</span>
    </div>

    <div class="controls-right">
      <button class="ctrl-btn" @click="toggleFullscreen" title="全屏">
        <svg v-if="!isFullscreen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  isPlaying: { type: Boolean, default: false },
  currentIndex: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
})
defineEmits(['prev', 'next', 'play', 'pause', 'jump'])

const isFullscreen = ref(false)

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
  } else {
    document.exitFullscreen().catch(() => {})
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
})
onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})
</script>

<style scoped>
.playback-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: #161b22;
  border-top: 1px solid #30363d;
  gap: 16px;
}

.controls-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ctrl-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: #e6edf3;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.ctrl-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.ctrl-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.ctrl-btn svg {
  width: 18px;
  height: 18px;
}

.play-btn {
  width: 44px;
  height: 44px;
  background: #e6edf3;
  color: #0d1117;
  border-radius: 50%;
}

.play-btn:hover {
  background: #ffffff !important;
}

.play-btn svg {
  width: 20px;
  height: 20px;
}

.progress-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.progress-dots {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.progress-dots::-webkit-scrollbar {
  display: none;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none;
  background: #30363d;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
  padding: 0;
}

.dot:hover {
  background: #8b949e;
  transform: scale(1.3);
}

.dot.done {
  background: #58a6ff;
}

.dot.active {
  background: #e6edf3;
  transform: scale(1.5);
  box-shadow: 0 0 6px rgba(230, 237, 243, 0.4);
}

.page-text {
  color: #8b949e;
  font-size: 13px;
  white-space: nowrap;
}

.controls-right {
  display: flex;
  align-items: center;
}
</style>
