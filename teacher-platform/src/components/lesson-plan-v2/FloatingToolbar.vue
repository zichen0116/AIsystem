<template>
  <div
    v-if="visible"
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
import { ref, computed, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  editor: { type: Object, default: null },
})

const visible = ref(false)
const toolbarTop = ref(0)
const toolbarLeft = ref(0)
let blurTimer = null

const toolbarStyle = computed(() => ({
  top: `${toolbarTop.value}px`,
  left: `${toolbarLeft.value}px`,
}))

function updateToolbar() {
  if (!props.editor) { visible.value = false; return }
  const { state } = props.editor
  const { from, to, empty } = state.selection
  if (empty) { visible.value = false; return }

  visible.value = true
  const view = props.editor.view
  const start = view.coordsAtPos(from)
  const end = view.coordsAtPos(to)
  const editorRect = view.dom.closest('.editor-canvas')?.getBoundingClientRect()
  if (!editorRect) return

  // Center toolbar above selection
  const toolbarWidth = 280
  toolbarTop.value = start.top - editorRect.top - 44
  toolbarLeft.value = (start.left + end.left) / 2 - editorRect.left - toolbarWidth / 2
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
    oldEditor.off('selectionUpdate', updateToolbar)
    oldEditor.off('blur', handleBlur)
    oldEditor.off('focus', handleFocus)
  }
  if (editor) {
    editor.on('selectionUpdate', updateToolbar)
    editor.on('blur', handleBlur)
    editor.on('focus', handleFocus)
  }
}, { immediate: true })

onBeforeUnmount(() => {
  clearTimeout(blurTimer)
  if (props.editor) {
    props.editor.off('selectionUpdate', updateToolbar)
    props.editor.off('blur', handleBlur)
    props.editor.off('focus', handleFocus)
  }
})
</script>

<style scoped>
.floating-toolbar {
  position: absolute;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 4px 8px;
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
  color: #ccc;
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
  background: #444;
  margin: 4px 4px;
}
</style>
