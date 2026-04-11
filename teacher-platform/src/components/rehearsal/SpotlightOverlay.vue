<template>
  <svg v-if="target" class="spotlight-overlay" :viewBox="`0 0 ${width} ${height}`">
    <defs>
      <mask id="spotlight-mask">
        <rect x="0" y="0" :width="width" :height="height" fill="white" />
        <rect v-if="rect" :x="rect.x - 8" :y="rect.y - 8" :width="rect.w + 16" :height="rect.h + 16" rx="4" fill="black" />
      </mask>
    </defs>
    <rect x="0" y="0" :width="width" :height="height"
          :fill="`rgba(0,0,0,${target.dimOpacity || 0.4})`" mask="url(#spotlight-mask)" />
  </svg>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  target: { type: Object, default: null },
  canvasRef: { type: Object, default: null },
})

const rect = ref(null)
const width = ref(1000)
const height = ref(562)

function updateRect() {
  if (!props.target?.elementId || !props.canvasRef) { rect.value = null; return }
  const el = props.canvasRef.querySelector(`[data-element-id="${props.target.elementId}"]`)
  if (!el) { rect.value = null; return }
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

watch(() => props.target, updateRect, { immediate: true, deep: true })
onMounted(updateRect)
</script>

<style scoped>
.spotlight-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 10; transition: all 0.3s ease; }
</style>
