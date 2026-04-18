<template>
  <svg v-if="target && rect" class="spotlight-overlay" :viewBox="`0 0 ${width} ${height}`">
    <defs>
      <mask :id="maskId">
        <rect x="0" y="0" :width="width" :height="height" fill="white" />
        <rect
          :x="rect.x - 8"
          :y="rect.y - 8"
          :width="rect.w + 16"
          :height="rect.h + 16"
          rx="10"
          fill="black"
        />
      </mask>
    </defs>
    <rect
      x="0"
      y="0"
      :width="width"
      :height="height"
      :fill="`rgba(0,0,0,${target.dimOpacity || 0.4})`"
      :mask="`url(#${maskId})`"
    />
    <rect
      :x="rect.x - 2"
      :y="rect.y - 2"
      :width="rect.w + 4"
      :height="rect.h + 4"
      rx="8"
      fill="none"
      stroke="rgba(255,255,255,0.75)"
      stroke-width="2"
    />
  </svg>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  target: { type: Object, default: null },
  canvasRef: { type: Object, default: null },
})

const maskId = `spotlight-mask-${Math.random().toString(36).slice(2)}`
const rect = ref(null)
const width = ref(1000)
const height = ref(562)
let resizeObserver = null
let frameId = 0

async function updateRect() {
  await nextTick()

  if (!props.target?.elementId || !props.canvasRef) {
    rect.value = null
    return
  }

  const el = props.canvasRef.querySelector(`[data-element-id="${props.target.elementId}"]`)
  if (!el) {
    rect.value = null
    return
  }

  const canvas = props.canvasRef.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()

  width.value = canvas.width
  height.value = canvas.height
  rect.value = {
    x: elRect.left - canvas.left,
    y: elRect.top - canvas.top,
    w: elRect.width,
    h: elRect.height,
  }
}

function scheduleUpdate() {
  cancelAnimationFrame(frameId)
  frameId = requestAnimationFrame(() => {
    updateRect()
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
.spotlight-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
  transition: opacity 0.25s ease;
}
</style>
