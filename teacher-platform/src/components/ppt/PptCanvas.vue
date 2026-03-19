<template>
  <div class="ppt-canvas" ref="canvasContainer" @wheel.prevent="handleWheel">
    <div v-if="!pptxDoc" class="canvas-empty">
      <div v-if="generating" class="canvas-progress">
        <div class="progress-spinner" />
        <p>PPT 生成中... {{ currentPage }}/{{ totalPages }}</p>
      </div>
      <p v-else class="canvas-hint">选择模板并生成 PPT 后，预览将在此显示</p>
    </div>

    <div v-else class="canvas-stage">
      <div v-if="showZoomToast" class="canvas-zoom">缩放 {{ zoomPercent }}%</div>
      <svg ref="renderSvg" class="canvas-render" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Ppt2Svg } from '../../utils/docmee/ppt2svg.js'
import { ZOOM_TOAST_DURATION_MS, getNextZoomPercent } from '../../utils/pptPreview.js'

const props = defineProps({
  pptxDoc: { type: Object, default: null },
  slideIndex: { type: Number, default: 0 },
  generating: { type: Boolean, default: false },
  currentPage: { type: Number, default: 0 },
  totalPages: { type: Number, default: 0 },
})

const emit = defineEmits(['change'])

const canvasContainer = ref(null)
const renderSvg = ref(null)
const zoomPercent = ref(100)
const showZoomToast = ref(false)
const zoom = computed(() => zoomPercent.value / 100)

let painter = null
let resizeObserver = null
let zoomToastTimer = null

function getBaseSize() {
  const container = canvasContainer.value
  if (!container || !props.pptxDoc) return null

  const maxWidth = Math.max(container.clientWidth - 48, 320)
  const maxHeight = Math.max(container.clientHeight - 48, 180)
  const ratio = props.pptxDoc.width / props.pptxDoc.height
  const width = Math.min(maxWidth, maxHeight * ratio)
  const height = width / ratio

  return {
    width: Math.max(Math.floor(width), 320),
    height: Math.max(Math.floor(height), 180),
  }
}

async function renderSlide() {
  if (!props.pptxDoc || !renderSvg.value) return

  const pageCount = props.pptxDoc.pages?.length || 0
  if (!pageCount) return

  const safeIndex = Math.min(Math.max(props.slideIndex, 0), pageCount - 1)
  const baseSize = getBaseSize()
  if (!baseSize) return

  if (!painter) {
    painter = new Ppt2Svg(renderSvg.value)
    painter.setMode('edit')
    painter.onchange = () => {
      emit('change', props.pptxDoc)
    }
  }

  painter.resetSize(baseSize.width * zoom.value, baseSize.height * zoom.value)
  painter.drawPptx(props.pptxDoc, safeIndex)
}

function handleWheel(event) {
  if (!props.pptxDoc) return

  zoomPercent.value = getNextZoomPercent(zoomPercent.value, event.deltaY < 0 ? -1 : 1)
  showZoomToast.value = true

  if (zoomToastTimer) {
    clearTimeout(zoomToastTimer)
  }

  zoomToastTimer = setTimeout(() => {
    showZoomToast.value = false
  }, ZOOM_TOAST_DURATION_MS)
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    void renderSlide()
  })

  if (canvasContainer.value) {
    resizeObserver.observe(canvasContainer.value)
  }

  nextTick(() => {
    void renderSlide()
  })
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (zoomToastTimer) {
    clearTimeout(zoomToastTimer)
  }
})

watch(
  () => [props.pptxDoc, props.slideIndex, zoomPercent.value],
  () => {
    nextTick(() => {
      void renderSlide()
    })
  },
  { deep: false },
)
</script>

<style scoped>
.ppt-canvas {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  background: #f0f2f5;
  overflow: auto;
  padding: 0;
  min-height: 0;
  position: relative;
}

.canvas-empty {
  text-align: center;
  color: #999;
  margin: auto;
}

.canvas-hint {
  font-size: 14px;
}

.canvas-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.progress-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e5e7eb;
  border-top-color: #3a61ea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.canvas-stage {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: fit-content;
  min-height: fit-content;
  padding: 24px 24px 8px;
  margin: auto;
}

.canvas-zoom {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 12px;
  color: #667085;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dbe1ea;
  border-radius: 999px;
  padding: 6px 10px;
}

.canvas-render {
  display: block;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}
</style>
