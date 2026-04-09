<template>
  <div v-if="target && rect" class="laser-pointer"
       :style="{ left: rect.x + 'px', top: rect.y + 'px', width: rect.w + 'px', height: rect.h + 'px', borderColor: target.color || '#ff0000' }">
    <div class="laser-dot" :style="{ background: target.color || '#ff0000' }" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  target: { type: Object, default: null },
  canvasRef: { type: Object, default: null },
})

const rect = ref(null)

function updateRect() {
  if (!props.target?.elementId || !props.canvasRef) { rect.value = null; return }
  const el = props.canvasRef.querySelector(`[data-element-id="${props.target.elementId}"]`)
  if (!el) { rect.value = null; return }
  const canvas = props.canvasRef.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  rect.value = {
    x: elRect.left - canvas.left,
    y: elRect.top - canvas.top,
    w: elRect.width,
    h: elRect.height,
  }
}

watch(() => props.target, updateRect, { immediate: true, deep: true })
onMounted(updateRect)
</script>

<style scoped>
.laser-pointer { position: absolute; border: 2px solid; border-radius: 4px; pointer-events: none; z-index: 11; animation: laser-pulse 1s ease-in-out infinite; }
.laser-dot { position: absolute; top: -6px; right: -6px; width: 12px; height: 12px; border-radius: 50%; animation: laser-glow 0.8s ease-in-out infinite; }
@keyframes laser-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
@keyframes laser-glow { 0%, 100% { box-shadow: 0 0 4px 2px currentColor; } 50% { box-shadow: 0 0 8px 4px currentColor; } }
</style>
