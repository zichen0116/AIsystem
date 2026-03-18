<script setup>
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

const props = defineProps({
  markdown: { type: String, default: '' }
})

const svgRef = ref(null)
let mm = null
const transformer = new Transformer()

function render() {
  if (!svgRef.value) return
  const md = (props.markdown || '').trim()
  if (!md) return

  const { root } = transformer.transform(md)
  if (!mm) {
    // 导出/适配时要求“立刻生效”，避免动画过渡导致截图时机不一致
    mm = Markmap.create(svgRef.value, { autoFit: true, duration: 0 }, root)
  } else {
    mm.setData(root)
    mm.fit()
  }
}

function fit() {
  mm?.fit?.()
}

function getTransform() {
  const g = svgRef.value?.querySelector?.('g')
  return g?.getAttribute?.('transform') ?? null
}

function setTransform(transform) {
  const g = svgRef.value?.querySelector?.('g')
  if (!g) return
  if (transform == null) g.removeAttribute('transform')
  else g.setAttribute('transform', String(transform))
}

function zoomIn() {
  // markmap 内部使用 d3-zoom，暴露的是 rescale/zoomTo 等；这里用相对缩放
  mm?.rescale?.(1.2)
}

function zoomOut() {
  mm?.rescale?.(1 / 1.2)
}

defineExpose({ fit, getTransform, setTransform, zoomIn, zoomOut })

onMounted(async () => {
  await nextTick()
  render()
})

watch(
  () => props.markdown,
  async () => {
    await nextTick()
    render()
  }
)

onBeforeUnmount(() => {
  try {
    mm?.destroy?.()
  } catch {
    // ignore
  }
  mm = null
})
</script>

<template>
  <svg ref="svgRef" class="markmap-svg" />
</template>

<style scoped>
.markmap-svg {
  width: 100%;
  height: 100%;
}
</style>

