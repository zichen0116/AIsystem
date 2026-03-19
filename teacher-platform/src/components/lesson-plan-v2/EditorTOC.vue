<template>
  <div
    v-if="headings.length"
    class="editor-toc"
    :class="{ 'toc-visible': isVisible }"
    @mouseenter="isVisible = true"
    @mouseleave="isVisible = false"
  >
    <div class="toc-trigger"></div>
    <div class="toc-content">
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
const isVisible = ref(false)
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
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 40;
  transition: all 0.3s ease;
}

.toc-trigger {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 20px;
  cursor: pointer;
}

.toc-content {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%) translateX(100%);
  width: 200px;
  max-height: 60vh;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px 0 0 8px;
  border-right: none;
  padding: 16px 12px 16px 16px;
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s ease;
}

.editor-toc.toc-visible .toc-content {
  transform: translateY(-50%) translateX(0);
}

.toc-title {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.4);
  font-weight: 600;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.toc-item {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.6);
  padding: 4px 8px;
  margin-bottom: 2px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-radius: 4px;
  transition: all 0.2s;
  line-height: 1.4;
}

.toc-item:hover {
  background: rgba(0, 0, 0, 0.04);
  color: rgba(0, 0, 0, 0.8);
}

.toc-item.active {
  color: rgb(35, 131, 226);
  background: rgba(35, 131, 226, 0.08);
  font-weight: 500;
}

.toc-item.level-2 {
  padding-left: 8px;
}

.toc-item.level-3 {
  padding-left: 20px;
  font-size: 12px;
}

.toc-content::-webkit-scrollbar {
  width: 4px;
}

.toc-content::-webkit-scrollbar-track {
  background: transparent;
}

.toc-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 2px;
}

.toc-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}
</style>
