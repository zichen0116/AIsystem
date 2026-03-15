<template>
  <BubbleMenu v-if="editor" :editor="editor" :tippy-options="{ duration: 150 }">
    <div class="floating-toolbar">
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
  </BubbleMenu>
</template>

<script setup>
import { BubbleMenu } from '@tiptap/vue-3'

defineProps({
  editor: { type: Object, default: null },
})
</script>

<style scoped>
.floating-toolbar {
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
