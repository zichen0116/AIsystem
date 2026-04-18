<template>
  <div class="slide-renderer" ref="containerRef"
       :style="{ aspectRatio: '16/9', background: bgColor, position: 'relative', overflow: 'hidden' }">
    <div class="slide-canvas" ref="canvasRef"
         :style="{ width: viewportSize + 'px', height: viewportHeight + 'px', transform: `scale(${scale})`, transformOrigin: 'top left', position: 'relative' }">
      <template v-for="el in elements" :key="el.id">
        <!-- Text element -->
        <div v-if="el.type === 'text'" :data-element-id="el.id"
             :style="{ position: 'absolute', left: el.left + 'px', top: el.top + 'px', width: el.width + 'px', height: el.height + 'px', fontSize: (el.fontSize || 18) + 'px', color: el.color || '#333' }"
             v-html="el.content" />
        <!-- Image element -->
        <img v-else-if="el.type === 'image'" :data-element-id="el.id"
             :src="el.src" :style="{ position: 'absolute', left: el.left + 'px', top: el.top + 'px', width: el.width + 'px', height: el.height + 'px', objectFit: 'contain' }" />
        <!-- Shape element -->
        <div v-else-if="el.type === 'shape'" :data-element-id="el.id"
             :style="{ position: 'absolute', left: el.left + 'px', top: el.top + 'px', width: el.width + 'px', height: el.height + 'px', background: el.fill || '#e0e0e0', borderRadius: el.shape === 'ellipse' ? '50%' : el.shape === 'roundRect' ? '8px' : '0' }" />
      </template>
    </div>
    <slot />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  slide: { type: Object, default: null },
})

const containerRef = ref(null)
const canvasRef = ref(null)
const scale = ref(1)

const viewportSize = computed(() => props.slide?.viewportSize || 1000)
const viewportHeight = computed(() => viewportSize.value * (props.slide?.viewportRatio || 0.5625))
const elements = computed(() => props.slide?.elements || [])
const bgColor = computed(() => {
  const bg = props.slide?.background
  if (!bg) return '#ffffff'
  if (bg.type === 'solid') return bg.color || '#ffffff'
  return '#ffffff'
})

function updateScale() {
  if (!containerRef.value) return
  const containerWidth = containerRef.value.clientWidth
  scale.value = containerWidth / viewportSize.value
}

let resizeObserver = null
onMounted(() => {
  updateScale()
  resizeObserver = new ResizeObserver(updateScale)
  if (containerRef.value) resizeObserver.observe(containerRef.value)
})
onUnmounted(() => { resizeObserver?.disconnect() })

defineExpose({ canvasRef })
</script>

<style scoped>
.slide-renderer { width: 100%; border-radius: 4px; user-select: none; }
</style>
