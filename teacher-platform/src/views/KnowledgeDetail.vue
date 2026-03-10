<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const kbTitle = computed(() => route.query.title || '知识库详情')

const allDocs = ref([
  { id: 1, name: '备课功能.docx', words: 402, uploads: 0, time: '2026-03-09 23:04', status: '可用', file: null }
])

const searchText = ref('')

const docs = computed(() =>
  allDocs.value.filter(d =>
    !searchText.value ||
    d.name.toLowerCase().includes(searchText.value.toLowerCase())
  )
)

const fileInputRef = ref(null)

function goBack() {
  router.push('/knowledge-base')
}

function triggerAddFile() {
  fileInputRef.value?.click()
}

function formatNow() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function handleFilesSelected(e) {
  const files = e.target.files
  if (!files || !files.length) return
  const nextId = (arr) => Math.max(0, ...arr.map(d => d.id || 0)) + 1
  const now = formatNow()
  const added = Array.from(files).map((file, idx) => ({
    id: nextId(allDocs.value) + idx,
    name: file.name,
    words: 0,
    uploads: 0,
    time: now,
    status: '可用',
    file
  }))
  allDocs.value = [...allDocs.value, ...added]
  e.target.value = ''
}

function renameDoc(doc) {
  const next = window.prompt('重命名文档', doc.name)
  if (!next || !next.trim()) return
  doc.name = next.trim()
}

function deleteDoc(doc) {
  if (!window.confirm(`确定要删除文档「${doc.name}」吗？`)) return
  allDocs.value = allDocs.value.filter(d => d.id !== doc.id)
}

function downloadDoc(doc) {
  if (!doc.file) {
    window.alert('该示例文档仅为演示，暂不支持下载。请先通过“添加文件”上传真实文档后再下载。')
    return
  }
  const url = URL.createObjectURL(doc.file)
  const a = document.createElement('a')
  a.href = url
  a.download = doc.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="kb-detail-page">
    <div class="kb-detail-header">
      <div class="kb-detail-title-wrap">
        <button type="button" class="back-btn" @click="goBack">← 返回知识库</button>
        <h2 class="kb-detail-title">{{ kbTitle }}</h2>
      </div>
      <div class="kb-detail-actions">
          <input v-model="searchText" class="search-input" type="text" placeholder="搜索文档" />
          <button type="button" class="primary-btn" @click="triggerAddFile">添加文件</button>
          <input
            ref="fileInputRef"
            type="file"
            class="hidden-file-input"
            multiple
            @change="handleFilesSelected"
          />
      </div>
    </div>

    <div class="kb-detail-table">
      <div class="kb-table-header">
        <div class="col col-index">#</div>
        <div class="col col-name">名称</div>
        <div class="col col-words">字数</div>
        <div class="col col-calls">引用数</div>
        <div class="col col-time">上传时间</div>
        <div class="col col-status">状态</div>
        <div class="col col-ops">操作</div>
      </div>
      <div v-for="(doc, idx) in docs" :key="doc.id" class="kb-table-row">
        <div class="col col-index">{{ idx + 1 }}</div>
        <div class="col col-name">
          <span class="file-icon">📄</span>
          <span class="file-name">{{ doc.name }}</span>
        </div>
        <div class="col col-words">{{ doc.words }}</div>
        <div class="col col-calls">{{ doc.uploads }}</div>
        <div class="col col-time">{{ doc.time }}</div>
        <div class="col col-status">
          <span class="status-dot"></span>
          <span>可用</span>
        </div>
        <div class="col col-ops">
          <button type="button" class="link-btn" @click="renameDoc(doc)">重命名</button>
          <button type="button" class="link-btn" @click="downloadDoc(doc)">下载</button>
          <button type="button" class="link-btn danger" @click="deleteDoc(doc)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb-detail-page {
  min-height: 100%;
  padding: 24px;
  background: #f9fafb;
}

.kb-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}

.kb-detail-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.back-btn {
  border: none;
  background: transparent;
  color: #3b82f6;
  font-size: 16px;
  text-align: left;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
}

.back-btn::before {
  font-size: 16px;
}

.kb-detail-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #111827;
}

.kb-detail-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 220px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  font-size: 15px;
}

.primary-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: #3b82f6;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}

.hidden-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.kb-detail-table {
  margin-top: 8px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.kb-table-header,
.kb-table-row {
  display: grid;
  grid-template-columns: 50px 2.5fr 80px 80px 180px 130px 200px;
  align-items: center;
  font-size: 15px;
}

.kb-table-header {
  background: #f9fafb;
  color: #6b7280;
  font-weight: 500;
  padding: 10px 16px;
}

.kb-table-row {
  padding: 12px 16px;
  border-top: 1px solid #f3f4f6;
}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  font-size: 18px;
}

.file-name {
  color: #111827;
}

.col-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
}

.col-ops {
  display: flex;
  align-items: center;
  gap: 12px;
}

.link-btn {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
  color: #3b82f6;
  cursor: pointer;
}

.link-btn.danger {
  color: #ef4444;
}
</style>
