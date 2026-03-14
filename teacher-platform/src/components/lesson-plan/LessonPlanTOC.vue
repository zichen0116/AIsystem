<template>
  <div :class="['toc-panel', { 'toc-collapsed': collapsed }]">
    <div class="toc-header">
      <span v-if="!collapsed" class="toc-title">目录</span>
      <button class="toc-toggle" @click="collapsed = !collapsed" :title="collapsed ? '展开目录' : '收起目录'">
        {{ collapsed ? '▶' : '◀' }}
      </button>
    </div>
    <ul class="toc-list" v-if="!collapsed && headings.length > 0">
      <li
        v-for="(h, idx) in headings"
        :key="idx"
        :class="['toc-item', `toc-level-${h.level}`, { active: activeIndex === idx }]"
        @click="$emit('scroll-to', h.pos)"
      >
        {{ h.text }}
      </li>
    </ul>
    <p class="toc-empty" v-if="!collapsed && headings.length === 0">暂无目录</p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, onDeactivated } from 'vue'

const props = defineProps({
  headings: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
})
defineEmits(['scroll-to'])

const collapsed = ref(false)
const activeIndex = ref(-1)
let observer = null

function setupObserver() {
  if (observer) observer.disconnect()
  if (props.isStreaming || props.headings.length === 0) return

  // Find all heading elements in the editor
  const editorEl = document.querySelector('.tiptap-content .ProseMirror')
  if (!editorEl) return

  const headingEls = editorEl.querySelectorAll('h1, h2, h3')
  if (headingEls.length === 0) return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const idx = Array.from(headingEls).indexOf(entry.target)
          if (idx !== -1) activeIndex.value = idx
        }
      }
    },
    { root: editorEl.closest('.editor-container'), rootMargin: '-10% 0px -80% 0px', threshold: 0 }
  )

  headingEls.forEach((el) => observer.observe(el))
}

// Re-setup observer when headings change (but not during streaming)
watch(() => [props.headings, props.isStreaming], () => {
  if (!props.isStreaming) {
    // Small delay to let DOM update
    setTimeout(setupObserver, 100)
  }
}, { deep: true })

onMounted(() => setupObserver())
onDeactivated(() => { if (observer) observer.disconnect() })
onBeforeUnmount(() => { if (observer) observer.disconnect() })
</script>

<style scoped>
.toc-panel { width: 180px; border-right: 1px solid #e2e8f0; background: #f8fafc; display: flex; flex-direction: column; flex-shrink: 0; transition: width 0.2s ease; overflow: hidden; }
.toc-collapsed { width: 36px; }
.toc-header { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-bottom: 1px solid #e2e8f0; }
.toc-title { font-size: 0.85rem; font-weight: 600; color: #475569; }
.toc-toggle { width: 24px; height: 24px; border: none; background: none; color: #94a3b8; cursor: pointer; font-size: 0.75rem; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
.toc-toggle:hover { background: #e2e8f0; color: #475569; }
.toc-list { list-style: none; padding: 8px 0; margin: 0; overflow-y: auto; flex: 1; }
.toc-item { padding: 6px 16px; font-size: 0.82rem; color: #64748b; cursor: pointer; border-left: 2px solid transparent; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.toc-item:hover { color: #2563eb; background: #eff6ff; }
.toc-item.active { color: #2563eb; border-left-color: #2563eb; font-weight: 500; }
.toc-level-2 { padding-left: 16px; }
.toc-level-3 { padding-left: 28px; font-size: 0.78rem; }
.toc-empty { padding: 16px; font-size: 0.82rem; color: #94a3b8; text-align: center; }
</style>
