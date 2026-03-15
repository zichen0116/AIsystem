<template>
  <div v-if="headings.length" class="editor-toc">
    <div class="toc-title">目录</div>
    <div
      v-for="(h, i) in headings"
      :key="i"
      class="toc-item"
      :class="[`level-${h.level}`, { active: activeIndex === i }]"
      @click="$emit('scroll-to', h.pos)"
    >
      {{ h.text }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  headings: { type: Array, default: () => [] },
  editorElement: { type: Object, default: null },
})

defineEmits(['scroll-to'])

const activeIndex = ref(0)
let observer = null

function setupObserver() {
  if (observer) observer.disconnect()
  if (!props.editorElement) return
  const headingEls = props.editorElement.querySelectorAll('h1, h2, h3')
  if (!headingEls.length) return
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const idx = Array.from(headingEls).indexOf(entry.target)
          if (idx >= 0) activeIndex.value = idx
        }
      })
    },
    { root: props.editorElement.closest('.editor-canvas'), rootMargin: '-10% 0px -80% 0px' }
  )
  headingEls.forEach(el => observer.observe(el))
}

watch(() => [props.headings, props.editorElement], () => {
  setTimeout(setupObserver, 100)
}, { deep: true })

onMounted(() => { if (props.editorElement) setupObserver() })
onBeforeUnmount(() => { observer?.disconnect() })
</script>

<style scoped>
.editor-toc {
  position: absolute;
  right: 20px;
  top: 32px;
  width: 160px;
  background: #fff;
  border: 1px solid #eaedf0;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  z-index: 40;
}
.toc-title {
  font-size: 11px;
  color: #aaa;
  font-weight: 500;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.toc-item {
  font-size: 12px;
  color: #666;
  padding: 3px 0;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.2s;
}
.toc-item:hover {
  color: #2563eb;
}
.toc-item.active {
  color: #2563eb;
  font-weight: 500;
}
.toc-item.level-3 {
  padding-left: 12px;
}
</style>
