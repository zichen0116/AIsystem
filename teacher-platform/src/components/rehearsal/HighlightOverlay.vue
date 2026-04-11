<template>
  <div v-if="target && rects.length" class="highlight-overlay-root">
    <div
      v-for="(rect, index) in rects"
      :key="`${rect.elementId}-${index}`"
      class="highlight-overlay"
      :style="{
        left: `${rect.x}px`,
        top: `${rect.y}px`,
        width: `${rect.w}px`,
        height: `${rect.h}px`,
        borderColor: target.color || '#ff6b6b',
        borderWidth: `${target.borderWidth || 3}px`,
        backgroundColor: toRgba(target.color || '#ff6b6b', target.opacity ?? 0.22),
        boxShadow: `0 0 18px ${toRgba(target.color || '#ff6b6b', 0.35)}`,
      }"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  target: { type: Object, default: null },
  canvasRef: { type: Object, default: null },
})

const rects = ref([])
let resizeObserver = null
let frameId = 0

function toRgba(color, opacity) {
  if (!color.startsWith('#')) return color

  const hex = color.slice(1)
  const normalized = hex.length === 3
    ? hex.split('').map((char) => char + char).join('')
    : hex

  const red = Number.parseInt(normalized.slice(0, 2), 16)
  const green = Number.parseInt(normalized.slice(2, 4), 16)
  const blue = Number.parseInt(normalized.slice(4, 6), 16)
  return `rgba(${red}, ${green}, ${blue}, ${opacity})`
}

async function updateRects() {
  await nextTick()

  if (!props.target || !props.canvasRef) {
    rects.value = []
    return
  }

  const elementIds = Array.isArray(props.target.elementIds)
    ? props.target.elementIds.filter(Boolean)
    : [props.target.elementId].filter(Boolean)

  if (elementIds.length === 0) {
    rects.value = []
    return
  }

  const canvas = props.canvasRef.getBoundingClientRect()
  rects.value = elementIds
    .map((elementId) => {
      const el = props.canvasRef.querySelector(`[data-element-id="${elementId}"]`)
      if (!el) return null

      const elRect = el.getBoundingClientRect()
      return {
        elementId,
        x: elRect.left - canvas.left,
        y: elRect.top - canvas.top,
        w: elRect.width,
        h: elRect.height,
      }
    })
    .filter(Boolean)
}

function scheduleUpdate() {
  cancelAnimationFrame(frameId)
  frameId = requestAnimationFrame(() => {
    updateRects()
  })
}

function bindObserver(canvasEl) {
  resizeObserver?.disconnect()
  resizeObserver = null
  if (!canvasEl || typeof ResizeObserver === 'undefined') return

  resizeObserver = new ResizeObserver(() => {
    scheduleUpdate()
  })
  resizeObserver.observe(canvasEl)
}

watch(() => props.target, scheduleUpdate, { immediate: true, deep: true })
watch(() => props.canvasRef, (canvasEl) => {
  bindObserver(canvasEl)
  scheduleUpdate()
}, { immediate: true })

onMounted(() => {
  window.addEventListener('resize', scheduleUpdate)
  scheduleUpdate()
})

onUnmounted(() => {
  window.removeEventListener('resize', scheduleUpdate)
  resizeObserver?.disconnect()
  cancelAnimationFrame(frameId)
})
</script>

<style scoped>
.highlight-overlay-root {
  position: absolute;
  inset: 0;
  z-index: 9;
  pointer-events: none;
}

.highlight-overlay {
  position: absolute;
  border-style: solid;
  border-radius: 10px;
  animation: highlight-breathe 1.8s ease-in-out infinite;
}

@keyframes highlight-breathe {
  0%,
  100% {
    opacity: 0.78;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.02);
  }
}
</style>
