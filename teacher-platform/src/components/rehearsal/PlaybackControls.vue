<template>
  <div class="playback-controls">
    <el-button :icon="ArrowLeft" circle size="small" :disabled="currentIndex <= 0" @click="$emit('prev')" />
    <el-button v-if="!isPlaying" :icon="VideoPlay" circle type="primary" @click="$emit('play')" />
    <el-button v-else :icon="VideoPause" circle type="primary" @click="$emit('pause')" />
    <el-button :icon="ArrowRight" circle size="small" :disabled="currentIndex >= totalCount - 1" @click="$emit('next')" />
    <span class="page-indicator">{{ currentIndex + 1 }} / {{ totalCount }}</span>
  </div>
</template>

<script setup>
import { ArrowLeft, ArrowRight, VideoPlay, VideoPause } from '@element-plus/icons-vue'

defineProps({
  isPlaying: { type: Boolean, default: false },
  currentIndex: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
})
defineEmits(['prev', 'next', 'play', 'pause'])
</script>

<style scoped>
.playback-controls { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px; border-top: 1px solid #30363d; background: #0d1117; }
.page-indicator { color: #8b949e; font-size: 13px; margin-left: 16px; }
</style>
