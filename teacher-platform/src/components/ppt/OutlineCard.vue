<template>
  <div class="outline-card" :class="{ 'is-current': outline.is_current }">
    <div class="card-header">
      <span class="version-badge">v{{ outline.version }}</span>
      <span v-if="outline.is_current" class="current-tag">当前版本</span>
    </div>

    <div class="card-body">
      <!-- 查看模式 -->
      <div v-if="!editing" class="outline-content" v-html="renderedContent" />
      <!-- 编辑模式 -->
      <textarea
        v-else
        v-model="editContent"
        class="outline-editor"
        rows="12"
        placeholder="编辑大纲内容..."
      />
    </div>

    <!-- 配图预览 -->
    <div v-if="imageUrls.length" class="image-grid">
      <div v-for="(url, idx) in imageUrls" :key="idx" class="image-thumb">
        <img :src="url" alt="配图" @error="onImgError" />
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="card-footer">
      <button v-if="editable && !editing" class="btn btn-edit" @click="startEdit">
        编辑
      </button>
      <button v-if="editing" class="btn btn-save" @click="saveEdit">
        保存
      </button>
      <button v-if="editing" class="btn btn-cancel" @click="cancelEdit">
        取消
      </button>
      <button v-if="showApprove && !editing" class="btn btn-approve" @click="handleApprove">
        审批通过
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const props = defineProps({
  outline: { type: Object, required: true },
  editable: { type: Boolean, default: true },
  showApprove: { type: Boolean, default: true },
})

const emit = defineEmits(['approve', 'edit'])

const editing = ref(false)
const editContent = ref('')

const imageUrls = computed(() => {
  return Array.isArray(props.outline.image_urls) ? props.outline.image_urls : []
})

const renderedContent = computed(() => {
  const raw = props.outline.content || ''
  return md.render(raw)
})

function startEdit() {
  editContent.value = props.outline.content || ''
  editing.value = true
}

function saveEdit() {
  emit('edit', editContent.value)
  editing.value = false
}

function cancelEdit() {
  editing.value = false
  editContent.value = ''
}

function handleApprove() {
  emit('approve', {
    content: props.outline.content,
    image_urls: imageUrls.value,
  })
}

function onImgError(e) {
  e.target.style.display = 'none'
}
</script>

<style scoped>
.outline-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 20px;
  transition: box-shadow 0.2s;
}
.outline-card.is-current {
  border: 2px solid #3a61ea;
}
.outline-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.version-badge {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #3a61ea;
  background: #eef2ff;
  border-radius: 20px;
}
.current-tag {
  font-size: 12px;
  color: #16a34a;
  font-weight: 500;
}

.card-body {
  min-height: 80px;
}
.outline-content {
  font-size: 14px;
  line-height: 1.7;
  color: #333;
  word-break: break-word;
}
.outline-content :deep(h1),
.outline-content :deep(h2),
.outline-content :deep(h3) {
  margin: 12px 0 6px;
  color: #1a1a1a;
}
.outline-content :deep(ul),
.outline-content :deep(ol) {
  padding-left: 20px;
}
.outline-content :deep(p) {
  margin: 6px 0;
}

.outline-editor {
  width: 100%;
  box-sizing: border-box;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  resize: vertical;
  font-family: inherit;
  color: #333;
  outline: none;
  transition: border-color 0.2s;
}
.outline-editor:focus {
  border-color: #3a61ea;
}

/* 配图网格 */
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f0f0f0;
}
.image-thumb {
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
}
.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 底部按钮 */
.card-footer {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #f0f0f0;
}
.btn {
  padding: 6px 16px;
  font-size: 13px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s, opacity 0.2s;
}
.btn:hover {
  opacity: 0.85;
}
.btn-edit {
  background: #f0f4ff;
  color: #3a61ea;
}
.btn-save {
  background: #3a61ea;
  color: #fff;
}
.btn-cancel {
  background: #f3f4f6;
  color: #666;
}
.btn-approve {
  background: #16a34a;
  color: #fff;
  margin-left: auto;
}
</style>
