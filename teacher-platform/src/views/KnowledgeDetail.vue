<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useKnowledgeStore } from '../stores/knowledge'

const route = useRoute()
const router = useRouter()
const store = useKnowledgeStore()

const libraryId = computed(() => Number(route.params.id))
const kbTitle = computed(() => route.query.title || '知识库详情')

const allDocs = ref([])
const searchText = ref('')
const uploading = ref(false)

const docs = computed(() =>
  allDocs.value.filter(d =>
    !searchText.value ||
    d.name.toLowerCase().includes(searchText.value.toLowerCase())
  )
)

const fileInputRef = ref(null)

async function loadDocs() {
  try {
    const data = await store.fetchAssets(libraryId.value)
    allDocs.value = data.items.map(a => ({
      id: a.id,
      name: a.file_name,
      words: a.chunk_count || 0,
      uploads: a.image_count || 0,
      time: new Date(a.created_at).toLocaleString('zh-CN'),
      status: a.vector_status,
      filePath: a.file_path,
    }))
  } catch {
    allDocs.value = []
  }
}

onMounted(loadDocs)

// Poll for pending/processing assets
let pollTimer = null

function startPolling() {
  pollTimer = setInterval(async () => {
    const pending = allDocs.value.filter(d => d.status === 'pending' || d.status === 'processing')
    if (!pending.length) return
    for (const doc of pending) {
      try {
        const st = await store.getAssetStatus(doc.id)
        doc.status = st.vector_status
        doc.words = st.chunk_count || 0
        doc.uploads = st.image_count || 0
      } catch { /* ignore */ }
    }
  }, 5000)
}

onMounted(startPolling)
onBeforeUnmount(() => clearInterval(pollTimer))

function goBack() {
  router.push('/knowledge-base')
}

function triggerAddFile() {
  fileInputRef.value?.click()
}

async function handleFilesSelected(e) {
  const files = e.target.files
  if (!files || !files.length) return
  e.target.value = ''

  uploading.value = true
  try {
    for (const file of Array.from(files)) {
      // Step 1: Upload to OSS
      const uploadResult = await store.uploadFile(file)
      // Step 2: Create knowledge asset
      await store.createAsset({
        fileName: uploadResult.file_name,
        fileType: uploadResult.file_type,
        filePath: uploadResult.url,
        libraryId: libraryId.value,
      })
    }
    await loadDocs()
  } catch (err) {
    alert(err.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function deleteDoc(doc) {
  if (!confirm(`确定要删除文档「${doc.name}」吗？`)) return
  try {
    await store.deleteAsset(doc.id)
    allDocs.value = allDocs.value.filter(d => d.id !== doc.id)
  } catch (err) {
    alert(err.message || '删除失败')
  }
}

function downloadDoc(doc) {
  if (!doc.filePath) {
    alert('文件路径不可用')
    return
  }
  window.open(doc.filePath, '_blank')
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
          <button type="button" class="primary-btn" :disabled="uploading" @click="triggerAddFile">
            {{ uploading ? '上传中...' : '添加文件' }}
          </button>
          <input
            ref="fileInputRef"
            type="file"
            class="hidden-file-input"
            multiple
            accept=".pdf,.doc,.docx,.mp4,.jpg,.jpeg,.png"
            @change="handleFilesSelected"
          />
      </div>
    </div>

    <div class="kb-detail-table">
      <div class="kb-table-header">
        <div class="col col-index">#</div>
        <div class="col col-name">名称</div>
        <div class="col col-words">文本块数</div>
        <div class="col col-calls">图片数</div>
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
          <span class="status-dot" :class="doc.status"></span>
          <span>{{ { pending: '等待处理', processing: '处理中', completed: '可用', failed: '失败' }[doc.status] || doc.status }}</span>
        </div>
        <div class="col col-ops">
          <button type="button" class="link-btn" @click="downloadDoc(doc)">下载</button>
          <button type="button" class="link-btn danger" @click="deleteDoc(doc)">删除</button>
        </div>
      </div>
      <div v-if="docs.length === 0" class="kb-empty-row">
        <span>暂无文档，点击"添加文件"上传</span>
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

@media (max-width: 960px) {
  .kb-detail-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .kb-detail-actions { width: 100%; }
  .search-input { flex: 1; min-width: 0; }
  .kb-table-header,
  .kb-table-row {
    grid-template-columns: 40px 2fr 60px 60px 140px 80px 1fr;
    font-size: 14px;
  }
}

@media (max-width: 720px) {
  .kb-detail-page { padding: 16px 12px; }
  .kb-detail-title { font-size: 18px; }
  .kb-detail-table { overflow-x: auto; }
  .kb-table-header,
  .kb-table-row {
    grid-template-columns: 36px 1.5fr 50px 50px 120px 70px 140px;
    min-width: 540px;
    font-size: 13px;
  }
}

.status-dot.completed {
  background: #22c55e;
}
.status-dot.processing {
  background: #f59e0b;
}
.status-dot.pending {
  background: #94a3b8;
}
.status-dot.failed {
  background: #ef4444;
}
.kb-empty-row {
  text-align: center;
  padding: 40px 16px;
  color: #94a3b8;
  font-size: 14px;
}
</style>
