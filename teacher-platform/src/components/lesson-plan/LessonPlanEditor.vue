<template>
  <div :class="['editor-panel', { 'editor-fullscreen': isFullscreen }]">
    <!-- Toolbar -->
    <div class="editor-toolbar" v-if="hasContent || isStreaming">
      <div class="toolbar-left">
        <span class="char-count" v-if="charCount > 0">{{ charCount }} 字</span>
      </div>
      <div class="toolbar-right">
        <button class="toolbar-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏'">
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </button>
        <button class="toolbar-btn" @click="copyContent" :disabled="!hasContent">复制</button>
        <div class="download-group" v-if="hasContent">
          <button class="toolbar-btn" @click="showDownloadMenu = !showDownloadMenu">下载 ▾</button>
          <div class="download-menu" v-if="showDownloadMenu">
            <button @click="downloadMd">Markdown</button>
            <button @click="downloadDocx">Word 文档</button>
            <button @click="downloadPdf">PDF</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Streaming preview overlay (markdown-it rendered) -->
    <div class="streaming-preview" v-if="isStreaming" v-html="previewHtml"></div>

    <!-- Tiptap editor (hidden during streaming) -->
    <div class="editor-container" v-show="!isStreaming && editorReady">
      <!-- Format toolbar -->
      <div class="format-toolbar" v-if="editor && hasContent">
        <button class="fmt-btn" @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" :class="{ active: editor.isActive('heading', { level: 2 }) }">H2</button>
        <button class="fmt-btn" @click="editor.chain().focus().toggleHeading({ level: 3 }).run()" :class="{ active: editor.isActive('heading', { level: 3 }) }">H3</button>
        <span class="fmt-sep"></span>
        <button class="fmt-btn" @click="editor.chain().focus().toggleBold().run()" :class="{ active: editor.isActive('bold') }">B</button>
        <button class="fmt-btn" @click="editor.chain().focus().toggleItalic().run()" :class="{ active: editor.isActive('italic') }">I</button>
        <button class="fmt-btn" @click="editor.chain().focus().toggleUnderline().run()" :class="{ active: editor.isActive('underline') }">U</button>
        <button class="fmt-btn" @click="editor.chain().focus().toggleHighlight().run()" :class="{ active: editor.isActive('highlight') }">高亮</button>
        <span class="fmt-sep"></span>
        <button class="fmt-btn" @click="editor.chain().focus().toggleBulletList().run()">列表</button>
        <button class="fmt-btn" @click="editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()">表格</button>
        <button class="fmt-btn" @click="editor.chain().focus().toggleTaskList().run()">清单</button>
      </div>

      <editor-content :editor="editor" class="tiptap-content" />
    </div>

    <!-- Empty state -->
    <div class="editor-empty" v-if="!hasContent && !isStreaming && editorReady">
      <p class="empty-title">教案将在此处显示</p>
      <p class="empty-desc">在左侧对话框中描述您的教学需求，AI 将为您生成教案</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, onDeactivated, shallowRef } from 'vue'
import { EditorContent, Editor } from '@tiptap/vue-3'
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

const md = new MarkdownIt().use(taskListPlugin)

const props = defineProps({
  isStreaming: { type: Boolean, default: false },
  streamingMarkdown: { type: String, default: '' },
})

const emit = defineEmits(['update:markdown', 'update:headings', 'blur'])

const isFullscreen = ref(false)
const showDownloadMenu = ref(false)
const editor = shallowRef(null)
const editorReady = ref(false)

const editorExtensions = [
  StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
  Placeholder.configure({ placeholder: '教案内容将在这里显示...' }),
  Table.configure({ resizable: true }),
  TableRow,
  TableCell,
  TableHeader,
  TaskList,
  TaskItem.configure({ nested: true }),
  Highlight,
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  Underline,
  CharacterCount,
  Markdown,
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
  editorReady.value = true
}

onMounted(() => createEditor())

const hasContent = computed(() => editor.value ? !editor.value.isEmpty : false)
const charCount = computed(() => editor.value?.storage.characterCount.characters() || 0)
const previewHtml = computed(() => md.render(props.streamingMarkdown || ''))

// When streaming ends, inject final markdown into Tiptap
watch(() => props.isStreaming, (now, was) => {
  if (was && !now && props.streamingMarkdown) {
    editor.value?.commands.setContent(props.streamingMarkdown)
    editor.value?.setEditable(true)
    extractHeadings()
  }
})

// Lock editor when streaming starts
watch(() => props.isStreaming, (streaming) => {
  if (streaming) editor.value?.setEditable(false)
})

function extractHeadings() {
  if (!editor.value) return
  const headings = []
  editor.value.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      headings.push({ level: node.attrs.level, text: node.textContent, pos })
    }
  })
  emit('update:headings', headings)
}

function toggleFullscreen() { isFullscreen.value = !isFullscreen.value }

async function copyContent() {
  const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
  await navigator.clipboard.writeText(mkdown)
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function downloadMd() {
  showDownloadMenu.value = false
  const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
  downloadBlob(new Blob([mkdown], { type: 'text/markdown;charset=utf-8' }), '教案.md')
}

async function downloadDocx() {
  showDownloadMenu.value = false
  const { resolveApiUrl, getToken } = await import('../../api/http.js')
  const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
  const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/export/docx'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify({ content: mkdown, title: '教案' }),
  })
  if (!res.ok) return
  downloadBlob(await res.blob(), '教案.docx')
}

async function downloadPdf() {
  showDownloadMenu.value = false
  const html2pdf = (await import('html2pdf.js')).default
  const el = document.querySelector('.tiptap-content .ProseMirror')
  if (!el) return
  html2pdf().set({ margin: 10, filename: '教案.pdf', html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a4' } }).from(el).save()
}

// --- Exposed methods for parent ---
function getMarkdown() { return editor.value?.storage.markdown.getMarkdown() || '' }
function loadContent(markdown) { createEditor(markdown) }
function scrollToPos(pos) {
  const view = editor.value?.view
  if (!view) return
  const coords = view.coordsAtPos(pos)
  const container = view.dom.closest('.editor-container')
  if (container) container.scrollTo({ top: coords.top - container.getBoundingClientRect().top + container.scrollTop - 20, behavior: 'smooth' })
}

onDeactivated(() => { editor.value?.destroy(); editor.value = null; editorReady.value = false })
onBeforeUnmount(() => { editor.value?.destroy() })

defineExpose({ getMarkdown, loadContent, scrollToPos })
</script>

<style scoped>
.editor-panel { display: flex; flex-direction: column; height: 100%; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; }
.editor-fullscreen { position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000; border-radius: 0; }
.editor-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; flex-shrink: 0; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; }
.char-count { font-size: 0.8rem; color: #94a3b8; }
.toolbar-btn { padding: 4px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; font-size: 0.85rem; color: #475569; cursor: pointer; }
.toolbar-btn:hover { background: #f1f5f9; }
.toolbar-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.download-group { position: relative; }
.download-menu { position: absolute; top: 100%; right: 0; margin-top: 4px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 10; overflow: hidden; }
.download-menu button { display: block; width: 100%; padding: 8px 20px; border: none; background: none; font-size: 0.85rem; color: #334155; cursor: pointer; text-align: left; white-space: nowrap; }
.download-menu button:hover { background: #f1f5f9; }

.streaming-preview { flex: 1; overflow-y: auto; padding: 24px 32px; font-size: 0.95rem; line-height: 1.7; color: #1e293b; }
.streaming-preview :deep(h1) { font-size: 1.5rem; font-weight: 700; margin: 1.5em 0 0.5em; }
.streaming-preview :deep(h2) { font-size: 1.25rem; font-weight: 600; margin: 1.2em 0 0.4em; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }
.streaming-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 1em 0; }
.streaming-preview :deep(th), .streaming-preview :deep(td) { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
.streaming-preview :deep(th) { background: #f1f5f9; font-weight: 600; }

.editor-container { flex: 1; overflow-y: auto; }
.tiptap-content :deep(.ProseMirror) { padding: 24px 32px; min-height: 100%; outline: none; font-size: 0.95rem; line-height: 1.7; color: #1e293b; }
.tiptap-content :deep(.ProseMirror h1) { font-size: 1.5rem; font-weight: 700; margin: 1.5em 0 0.5em; color: #0f172a; }
.tiptap-content :deep(.ProseMirror h2) { font-size: 1.25rem; font-weight: 600; margin: 1.2em 0 0.4em; color: #1e293b; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }
.tiptap-content :deep(.ProseMirror h3) { font-size: 1.1rem; font-weight: 600; margin: 1em 0 0.3em; color: #334155; }
.tiptap-content :deep(.ProseMirror table) { border-collapse: collapse; width: 100%; margin: 1em 0; }
.tiptap-content :deep(.ProseMirror th), .tiptap-content :deep(.ProseMirror td) { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
.tiptap-content :deep(.ProseMirror th) { background: #f1f5f9; font-weight: 600; }
.tiptap-content :deep(.ProseMirror ul[data-type="taskList"]) { list-style: none; padding-left: 0; }
.tiptap-content :deep(.ProseMirror ul[data-type="taskList"] li) { display: flex; align-items: flex-start; gap: 8px; }
.tiptap-content :deep(.ProseMirror p.is-editor-empty:first-child::before) { content: attr(data-placeholder); color: #94a3b8; pointer-events: none; float: left; height: 0; }

.format-toolbar { display: flex; gap: 4px; padding: 6px 12px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; flex-wrap: wrap; align-items: center; }
.fmt-btn { padding: 4px 10px; border: none; background: none; font-size: 0.8rem; color: #64748b; cursor: pointer; border-radius: 4px; }
.fmt-btn:hover { background: #e2e8f0; color: #2563eb; }
.fmt-btn.active { background: #dbeafe; color: #2563eb; font-weight: 600; }
.fmt-sep { width: 1px; height: 18px; background: #e2e8f0; margin: 0 4px; }

.editor-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #94a3b8; padding: 40px; }
.empty-title { font-size: 1.1rem; font-weight: 500; color: #64748b; margin-bottom: 8px; }
.empty-desc { font-size: 0.9rem; color: #94a3b8; text-align: center; }
</style>
