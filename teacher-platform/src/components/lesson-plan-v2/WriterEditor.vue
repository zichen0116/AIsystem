<template>
  <div class="writer-editor">
    <!-- Top toolbar -->
    <div class="editor-topbar">
      <button class="back-btn" @click="$emit('back')">← 返回对话</button>
      <div class="export-group">
        <button @click="copyAll">📋 复制全文</button>
        <button @click="downloadWord">⬇ Word</button>
        <button @click="downloadPDF">⬇ PDF</button>
        <button @click="downloadMarkdown">⬇ Markdown</button>
      </div>
    </div>

    <!-- Editor canvas -->
    <div class="editor-canvas" ref="canvasRef">
      <!-- Streaming preview (when AI is generating) -->
      <div v-if="isStreaming" class="streaming-preview" v-html="streamingHtml" />

      <!-- Tiptap editor (when not streaming) -->
      <EditorContent v-show="!isStreaming" :editor="editor" />

      <!-- Floating format toolbar -->
      <FloatingToolbar v-if="editor && !isStreaming" :editor="editor" />

      <!-- Floating TOC -->
      <EditorTOC
        :headings="headings"
        :editor-element="editorEl"
        @scroll-to="scrollToPos"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Highlight from '@tiptap/extension-highlight'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import CharacterCount from '@tiptap/extension-character-count'
import { Markdown } from 'tiptap-markdown'
import MarkdownIt from 'markdown-it'
import taskListPlugin from 'markdown-it-task-lists'
import FloatingToolbar from './FloatingToolbar.vue'
import EditorTOC from './EditorTOC.vue'
import { resolveApiUrl, getToken } from '../../api/http.js'

const props = defineProps({
  isStreaming: { type: Boolean, default: false },
  streamingMarkdown: { type: String, default: '' },
})

const emit = defineEmits(['back', 'update:markdown', 'blur'])

const canvasRef = ref(null)
const editor = ref(null)
const headings = ref([])

const md = new MarkdownIt().use(taskListPlugin)
const streamingHtml = computed(() => md.render(props.streamingMarkdown || ''))

const editorEl = computed(() =>
  canvasRef.value?.querySelector('.ProseMirror') || null
)

const editorExtensions = [
  StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
  Placeholder.configure({ placeholder: '教案内容将在这里显示...' }),
  Table.configure({ resizable: true }),
  TableRow, TableCell, TableHeader,
  TaskList, TaskItem.configure({ nested: true }),
  Highlight,
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  Underline, CharacterCount, Markdown,
]

function createEditor(content = '') {
  if (editor.value) editor.value.destroy()
  editor.value = new Editor({
    extensions: editorExtensions,
    content,
    editable: true,
    onUpdate: () => {
      const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
      emit('update:markdown', mkdown)
      extractHeadings()
    },
    onBlur: () => emit('blur'),
  })
}

function extractHeadings() {
  if (!editor.value) return
  const h = []
  editor.value.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      h.push({ level: node.attrs.level, text: node.textContent, pos })
    }
  })
  headings.value = h
}

function scrollToPos(pos) {
  if (!editor.value) return
  const domAtPos = editor.value.view.domAtPos(pos)
  domAtPos.node?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
}

function getMarkdown() {
  return editor.value?.storage.markdown.getMarkdown() || ''
}

function loadContent(markdown) {
  if (!editor.value) createEditor(markdown)
  else editor.value.commands.setContent(markdown)
  nextTick(extractHeadings)
}

// When streaming ends, load content into editor
watch(() => props.isStreaming, (streaming, wasStreaming) => {
  if (wasStreaming && !streaming && props.streamingMarkdown) {
    loadContent(props.streamingMarkdown)
  }
})

function copyAll() {
  const text = getMarkdown()
  navigator.clipboard.writeText(text)
}

async function downloadWord() {
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/export/docx'), {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content: getMarkdown(), title: '教案' }),
    })
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = '教案.docx'; a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('DOCX export error:', err)
  }
}

function downloadPDF() {
  import('html2pdf.js').then(({ default: html2pdf }) => {
    const el = canvasRef.value?.querySelector('.ProseMirror')
    if (!el) return
    html2pdf().set({ margin: 10, filename: '教案.pdf' }).from(el).save()
  })
}

function downloadMarkdown() {
  const text = getMarkdown()
  const blob = new Blob([text], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = '教案.md'; a.click()
  URL.revokeObjectURL(url)
}

function destroy() {
  editor.value?.destroy()
  editor.value = null
}

defineExpose({ getMarkdown, loadContent, destroy, createEditor })

onBeforeUnmount(destroy)
</script>

<style scoped>
.writer-editor {
  width: 60%;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.editor-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  border-bottom: 1px solid #eaedf0;
  background: #fafbfc;
  flex-shrink: 0;
}
.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
}
.back-btn:hover {
  color: #2563eb;
  border-color: #2563eb;
}
.export-group {
  display: flex;
  gap: 8px;
}
.export-group button {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
}
.export-group button:hover {
  color: #2563eb;
  border-color: #2563eb;
}
.editor-canvas {
  flex: 1;
  padding: 32px 48px;
  overflow-y: auto;
  font-size: 15px;
  line-height: 1.8;
  color: #333;
  position: relative;
}
.editor-canvas :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #1a1a2e;
}
.editor-canvas :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin: 24px 0 12px;
  color: #1a1a2e;
  padding-bottom: 8px;
  border-bottom: 1px solid #eaedf0;
}
.editor-canvas :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 8px;
  color: #333;
}
.editor-canvas :deep(p) {
  margin-bottom: 12px;
}
.editor-canvas :deep(ul) {
  padding-left: 20px;
  margin-bottom: 12px;
}
.editor-canvas :deep(li) {
  margin-bottom: 4px;
}
.editor-canvas :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}
.editor-canvas :deep(th),
.editor-canvas :deep(td) {
  border: 1px solid #e0e3e8;
  padding: 8px 12px;
  text-align: left;
  font-size: 13px;
}
.editor-canvas :deep(th) {
  background: #f7f8fa;
  font-weight: 500;
}
.streaming-preview {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
}
.streaming-preview :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #1a1a2e;
}
.streaming-preview :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin: 24px 0 12px;
  color: #1a1a2e;
  padding-bottom: 8px;
  border-bottom: 1px solid #eaedf0;
}
.streaming-preview :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 8px;
  color: #333;
}
.streaming-preview :deep(p) {
  margin-bottom: 12px;
}
.streaming-preview :deep(ul) {
  padding-left: 20px;
  margin-bottom: 12px;
}
.streaming-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}
.streaming-preview :deep(th),
.streaming-preview :deep(td) {
  border: 1px solid #e0e3e8;
  padding: 8px 12px;
  text-align: left;
  font-size: 13px;
}
.streaming-preview :deep(th) {
  background: #f7f8fa;
  font-weight: 500;
}
</style>
