<template>
  <div class="thumbnail-list">
    <div
      v-for="(_, i) in slides"
      :key="i"
      class="thumb-item"
      :class="{ active: i === activeIndex }"
      @click="$emit('select', i)"
    >
      <span class="thumb-num">{{ i + 1 }}</span>
      <canvas :ref="(el) => setCanvasRef(el, i)" class="thumb-preview" />
    </div>
    <div v-if="!slides.length" class="thumb-empty">暂无页面</div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, watch } from 'vue'
import { Ppt2Canvas } from '../../utils/docmee/ppt2canvas.js'
import { getThumbnailRenderIndices } from '../../utils/pptPreview.js'

const props = defineProps({
  slides: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: 0 },
  pptxDoc: { type: Object, default: null },
  dirtySlideIndex: { type: Number, default: null },
  renderNonce: { type: Number, default: 0 },
})

defineEmits(['select'])

const canvasRefs = []
const painters = new Map()

function setCanvasRef(el, index) {
  if (el) {
    canvasRefs[index] = el
  }
}

async function renderThumb(index) {
  if (!props.pptxDoc || !canvasRefs[index]) return

  const canvas = canvasRefs[index]
  let painter = painters.get(index)
  if (!painter) {
    painter = new Ppt2Canvas(canvas)
    painters.set(index, painter)
  }

  painter.resetSize(144, 81)
  await painter.drawPptx(props.pptxDoc, index)
}

async function renderTargetThumbs() {
  if (!props.pptxDoc?.pages?.length) return

  await nextTick()

  const targetIndices = getThumbnailRenderIndices({
    slideCount: props.slides.length,
    dirtySlideIndex: props.dirtySlideIndex,
  })

  for (const index of targetIndices) {
    await renderThumb(index)
  }
}

watch(
  () => [props.pptxDoc, props.slides.length, props.renderNonce],
  () => {
    void renderTargetThumbs()
  },
  { deep: false, immediate: true },
)

onBeforeUnmount(() => {
  painters.clear()
})
</script>

<style scoped>
.thumbnail-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  overflow-y: auto;
}

.thumb-item {
  position: relative;
  border: 2px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 16 / 9;
  background: #f8fafc;
  min-height: 60px;
}

.thumb-item:hover {
  border-color: #cbd5e1;
}

.thumb-item.active {
  border-color: #3a61ea;
  box-shadow: 0 0 0 1px #3a61ea;
}

.thumb-num {
  position: absolute;
  top: 3px;
  left: 5px;
  font-size: 10px;
  color: #94a3b8;
  z-index: 1;
}

.thumb-preview {
  width: 100%;
  height: 100%;
  display: block;
}

.thumb-empty {
  padding: 20px;
  text-align: center;
  color: #ccc;
  font-size: 12px;
}
</style>
