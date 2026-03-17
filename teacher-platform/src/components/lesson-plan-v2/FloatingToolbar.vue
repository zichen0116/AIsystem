<template>
  <div
    v-if="visible"
    ref="toolbarRef"
    class="floating-toolbar"
    :style="toolbarStyle"
    @mousedown.prevent
  >
    <button @click="editor.chain().focus().toggleBold().run()" :class="{ active: editor.isActive('bold') }">
      <strong>B</strong>
    </button>
    <button @click="editor.chain().focus().toggleItalic().run()" :class="{ active: editor.isActive('italic') }">
      <em>I</em>
    </button>
    <button @click="editor.chain().focus().toggleUnderline().run()" :class="{ active: editor.isActive('underline') }">
      <u>U</u>
    </button>
    <div class="divider" />
    <button @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" :class="{ active: editor.isActive('heading', { level: 2 }) }">
      H2
    </button>
    <button @click="editor.chain().focus().toggleHeading({ level: 3 }).run()" :class="{ active: editor.isActive('heading', { level: 3 }) }">
      H3
    </button>
    <div class="divider" />
    <button @click="editor.chain().focus().toggleBulletList().run()" :class="{ active: editor.isActive('bulletList') }">
      •
    </button>
    <button @click="editor.chain().focus().toggleOrderedList().run()" :class="{ active: editor.isActive('orderedList') }">
      ≡
    </button>
    <div class="divider" />
    <button @click="editor.chain().focus().toggleHighlight().run()" :class="{ active: editor.isActive('highlight') }">
      🖍
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, onMounted } from 'vue'

const props = defineProps({
  editor: { type: Object, default: null },
})

const visible = ref(false)
const toolbarTop = ref(0)
const toolbarLeft = ref(0)
const toolbarRef = ref(null)
let blurTimer = null
let rafId = null
let scrollEl = null

const toolbarStyle = computed(() => ({
  top: `${toolbarTop.value}px`,
  left: `${toolbarLeft.value}px`,
}))

function getSelectionRect() {
  const sel = window.getSelection?.()
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null
  const range = sel.getRangeAt(0)
  const rect = range.getBoundingClientRect()
  if (!rect || (!rect.width && !rect.height)) return null
  return rect
}

function updateToolbar() {
  if (!props.editor) { visible.value = false; return }
  const { state } = props.editor
  const { from, to, empty } = state.selection
  if (empty) { visible.value = false; return }

  const view = props.editor.view
  const editorCanvas = view.dom.closest('.editor-canvas')
  const editorRect = editorCanvas?.getBoundingClientRect()
  if (!editorRect) return

  visible.value = true

  let rect = getSelectionRect()
  if (!rect) {
    const start = view.coordsAtPos(from)
    const end = view.coordsAtPos(to)
    const top = Math.min(start.top, end.top)
    const bottom = Math.max(start.bottom, end.bottom)
    const left = Math.min(start.left, end.left)
    const right = Math.max(start.right, end.right)
    rect = { top, bottom, left, right, width: right - left, height: bottom - top }
  }

  const toolbarWidth = toolbarRef.value?.offsetWidth || 280
  const toolbarHeight = toolbarRef.value?.offsetHeight || 36
  const gap = 8

  let top = rect.top - editorRect.top + editorCanvas.scrollTop - toolbarHeight - gap
  let left = rect.left + rect.width / 2 - editorRect.left + editorCanvas.scrollLeft - toolbarWidth / 2

  // Keep toolbar inside viewport of editor canvas.
  const minLeft = editorCanvas.scrollLeft + gap
  const maxLeft = editorCanvas.scrollLeft + editorCanvas.clientWidth - toolbarWidth - gap
  left = Math.max(minLeft, Math.min(left, maxLeft))

  const minTop = editorCanvas.scrollTop + gap
  top = Math.max(minTop, top)

  toolbarTop.value = top
  toolbarLeft.value = left
}

function scheduleUpdateToolbar() {
  if (rafId !== null) cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(() => {
    rafId = null
    updateToolbar()
  })
}

function bindScrollListener(editor) {
  scrollEl?.removeEventListener('scroll', scheduleUpdateToolbar)
  scrollEl = editor?.view?.dom?.closest?.('.editor-canvas') || null
  scrollEl?.addEventListener('scroll', scheduleUpdateToolbar, { passive: true })
}

function handleBlur() {
  // Delay blur to allow toolbar button clicks to re-focus
  clearTimeout(blurTimer)
  blurTimer = setTimeout(() => { visible.value = false }, 200)
}

function handleFocus() {
  clearTimeout(blurTimer)
}

watch(() => props.editor, (editor, oldEditor) => {
  if (oldEditor) {
    oldEditor.off('selectionUpdate', scheduleUpdateToolbar)
    oldEditor.off('blur', handleBlur)
    oldEditor.off('focus', handleFocus)
  }
  if (editor) {
    editor.on('selectionUpdate', scheduleUpdateToolbar)
    editor.on('blur', handleBlur)
    editor.on('focus', handleFocus)
    bindScrollListener(editor)
  } else {
    bindScrollListener(null)
  }
}, { immediate: true })

onMounted(() => {
  window.addEventListener('resize', scheduleUpdateToolbar)
})

onBeforeUnmount(() => {
  clearTimeout(blurTimer)
  if (rafId !== null) cancelAnimationFrame(rafId)
  window.removeEventListener('resize', scheduleUpdateToolbar)
  scrollEl?.removeEventListener('scroll', scheduleUpdateToolbar)
  scrollEl = null
  if (props.editor) {
    props.editor.off('selectionUpdate', scheduleUpdateToolbar)
    props.editor.off('blur', handleBlur)
    props.editor.off('focus', handleFocus)
  }
})
</script>

<style scoped>
.floating-toolbar {
  position: absolute;
  background: rgba(55, 53, 47, 0.95);
  backdrop-filter: blur(8px);
  border-radius: 6px;
  padding: 4px 6px;
  display: flex;
  gap: 2px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  z-index: 50;
}
.floating-toolbar button {
  width: 30px;
  height: 28px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.floating-toolbar button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
.floating-toolbar button.active {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}
.divider {
  width: 1px;
  background: rgba(255, 255, 255, 0.2);
  margin: 4px 4px;
}
</style>
