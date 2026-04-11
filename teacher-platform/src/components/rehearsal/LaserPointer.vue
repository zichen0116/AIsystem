<template>
  <div
    v-if="target && point"
    class="laser-pointer"
    :style="{ left: `${point.x}px`, top: `${point.y}px`, color: target.color || '#ff3b30' }"
  >
    <div class="laser-ring" :style="{ borderColor: target.color || '#ff3b30' }" />
    <div class="laser-core" :style="{ backgroundColor: target.color || '#ff3b30' }" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  target: { type: Object, default: null },
  canvasRef: { type: Object, default: null },
})

const point = ref(null)
let resizeObserver = null
let frameId = 0

async function updatePoint() {
  await nextTick()

  if (!props.target?.elementId || !props.canvasRef) {
    point.value = null
    return
  }

  const el = props.canvasRef.querySelector(`[data-element-id="${props.target.elementId}"]`)
  if (!el) {
    point.value = null
    return
  }

  const canvas = props.canvasRef.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  point.value = {
    x: elRect.left - canvas.left + elRect.width / 2,
    y: elRect.top - canvas.top + elRect.height / 2,
  }
}

function scheduleUpdate() {
  cancelAnimationFrame(frameId)
  frameId = requestAnimationFrame(() => {
    updatePoint()
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
.laser-pointer {
  position: absolute;
  z-index: 11;
  pointer-events: none;
  transform: translate(-50%, -50%);
}

.laser-ring {
  position: absolute;
  inset: 0;
  width: 28px;
  height: 28px;
  margin: -14px 0 0 -14px;
  border: 1.5px solid #ff3b30;
  border-radius: 999px;
  animation: laser-ring 1.5s ease-out infinite;
}

.laser-core {
  width: 10px;
  height: 10px;
  margin: -5px 0 0 -5px;
  border-radius: 999px;
  box-shadow: 0 0 10px 3px currentColor;
  animation: laser-core 0.9s ease-in-out infinite;
}

@keyframes laser-ring {
  0% {
    opacity: 0.65;
    transform: scale(0.65);
  }
  100% {
    opacity: 0;
    transform: scale(2.4);
  }
}

@keyframes laser-core {
  0%,
  100% {
    opacity: 0.9;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}
</style>
