<script setup>
import { ref, computed, watch } from 'vue'
import { useCoursewareStore } from '../stores/courseware'

const coursewareStore = useCoursewareStore()
const coursewareList = computed(() => coursewareStore.coursewareList)

const filterType = ref('all')
const filterDate = ref('all')
const viewMode = ref('grid')
const showAddModal = ref(false)
const fileInputRef = ref(null)
const selectedFiles = ref([])

function triggerFileSelect() {
  fileInputRef.value?.click()
}

function onFileSelected(e) {
  const files = e.target.files
  if (files?.length) {
    selectedFiles.value = Array.from(files)
  }
  e.target.value = ''
}

function getTypeFromFilename(name) {
  const ext = (name.split('.').pop() || '').toLowerCase()
  if (['pdf'].includes(ext)) return 'pdf'
  if (['ppt', 'pptx'].includes(ext)) return 'ppt'
  if (['mp4', 'webm', 'mov'].includes(ext)) return 'video'
  if (['doc', 'docx'].includes(ext)) return 'word'
  return 'pdf'
}

function formatSize(bytes) {
  if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return bytes + ' B'
}

function doUpload() {
  if (!selectedFiles.value.length) return
  const now = new Date()
  const dateStr = now.getFullYear() + '年' + (now.getMonth() + 1) + '月' + now.getDate() + '日'
  const items = selectedFiles.value.map((file, i) => ({
    name: file.name.replace(/\.[^/.]+$/, '') || file.name,
    type: getTypeFromFilename(file.name),
    size: formatSize(file.size),
    subject: '未分类',
    grade: '—',
    modifyDate: dateStr,
    daysAgo: 0,
    favorited: false
  }))
  coursewareStore.addCourseware(items)
  selectedFiles.value = []
  showAddModal.value = false
}

const typeOptions = [
  { value: 'all', label: '所有类型' },
  { value: 'pdf', label: 'PDF' },
  { value: 'ppt', label: 'PPT' },
  { value: 'video', label: '视频' },
  { value: 'word', label: 'Word' }
]

const dateOptions = [
  { value: 'all', label: '全部日期' },
  { value: 'week', label: '近一周' },
  { value: 'month', label: '近一月' },
  { value: 'year', label: '近一年' }
]

const filteredList = computed(() => {
  let list = [...coursewareStore.coursewareList]
  if (filterType.value !== 'all') {
    list = list.filter(item => item.type === filterType.value)
  }
  if (filterDate.value !== 'all') {
    list = list.filter(item => {
      const d = item.daysAgo ?? 999
      if (filterDate.value === 'week') return d <= 7
      if (filterDate.value === 'month') return d <= 30
      if (filterDate.value === 'year') return d <= 365
      return true
    })
  }
  return list
})

const coursewarePage = ref(1)
const coursewarePageSize = 10 // 5列 x 2行
const coursewareTotalPages = computed(() => Math.max(1, Math.ceil(filteredList.value.length / coursewarePageSize)))
const paginatedCourseware = computed(() => {
  const start = (coursewarePage.value - 1) * coursewarePageSize
  return filteredList.value.slice(start, start + coursewarePageSize)
})
function goToCoursewarePage(p) {
  if (p >= 1 && p <= coursewareTotalPages.value) coursewarePage.value = p
}
watch([filterType, filterDate], () => { coursewarePage.value = 1 })

function toggleFavorite(item) {
  coursewareStore.toggleFavorite(item.id)
}

function getTypeTag(type) {
  const map = { pdf: 'PDF', ppt: 'PPT', video: '视频', word: 'Word' }
  return map[type] || type
}

function getTypeTagClass(type) {
  const map = { pdf: 'tag-pdf', ppt: 'tag-ppt', video: 'tag-video', word: 'tag-word' }
  return map[type] || ''
}

function getThumbnailBg(type) {
  const map = {
    pdf: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
    ppt: 'linear-gradient(135deg, #fed7aa 0%, #fdba74 100%)',
    video: 'linear-gradient(135deg, #bfdbfe 0%, #93c5fd 100%)',
    word: 'linear-gradient(135deg, #93c5fd 0%, #60a5fa 100%)'
  }
  return map[type] || '#f1f5f9'
}
</script>

<template>
  <div class="courseware-page">
    <div class="courseware-content">
      <div class="toolbar">
        <div class="toolbar-left">
          <div class="filter-group">
            <select v-model="filterDate" class="filter-select">
              <option v-for="opt in dateOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="filter-group">
            <select v-model="filterType" class="filter-select">
              <option v-for="opt in typeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
        </div>
        <div class="toolbar-right">
          <div class="view-toggles">
            <button class="view-btn" :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'" title="网格视图">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            </button>
            <button class="view-btn" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'" title="列表视图">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="6" width="16" height="2" rx="1"/><rect x="4" y="11" width="16" height="2" rx="1"/><rect x="4" y="16" width="16" height="2" rx="1"/></svg>
            </button>
          </div>
          <button class="add-btn" @click="showAddModal = true">+ 添加课件</button>
        </div>
      </div>

      <div class="courseware-grid" :class="viewMode">
        <div v-for="item in paginatedCourseware" :key="item.id" class="courseware-card">
          <div class="card-thumbnail" :style="{ background: getThumbnailBg(item.type) }">
            <span :class="['type-tag', getTypeTagClass(item.type)]">{{ getTypeTag(item.type) }}</span>
          </div>
          <div class="card-body">
            <div class="card-header-row">
              <h3 class="card-title">{{ item.name }}</h3>
              <button class="card-menu">⋮</button>
            </div>
            <p class="card-subject">{{ item.subject }} · {{ item.grade }}</p>
            <div class="card-footer-row">
              <p class="card-meta">🕐 {{ item.modifyDate }} · {{ item.size }}</p>
              <button
                class="favorite-btn"
                :class="{ favorited: item.favorited }"
                @click.stop="toggleFavorite(item)"
                title="收藏"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1" stroke-linejoin="round" stroke-linecap="round">
                  <path d="M12 2l2.4 7.4H22l-6 4.6 2.3 7.4L12 17.8l-6.3 4.6 2.3-7.4-6-4.6h7.6L12 2z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="coursewareTotalPages > 1" class="courseware-pagination">
        <button type="button" class="page-btn" :disabled="coursewarePage <= 1" @click="goToCoursewarePage(coursewarePage - 1)">‹</button>
        <button
          v-for="p in coursewareTotalPages"
          :key="p"
          type="button"
          class="page-btn"
          :class="{ active: coursewarePage === p }"
          @click="goToCoursewarePage(p)"
        >
          {{ p }}
        </button>
        <button type="button" class="page-btn" :disabled="coursewarePage >= coursewareTotalPages" @click="goToCoursewarePage(coursewarePage + 1)">›</button>
      </div>

      <Teleport to="body">
        <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
          <div class="modal-box">
            <h3>添加课件</h3>
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.ppt,.pptx,.doc,.docx,.mp4"
              multiple
              class="file-input-hidden"
              @change="onFileSelected"
            />
            <div class="upload-zone" @click="triggerFileSelect">
              <p>点击上传文件</p>
              <p class="hint">支持 PDF、PPT、MP4 或 DOC 格式</p>
            </div>
            <div class="modal-actions">
              <button class="cancel-btn" @click="showAddModal = false">取消</button>
              <button class="confirm-btn" :disabled="!selectedFiles.length" @click="doUpload">上传</button>
            </div>
            <p v-if="selectedFiles.length" class="selected-files-hint">已选 {{ selectedFiles.length }} 个文件</p>
          </div>
        </div>
      </Teleport>
    </div>
  </div>
</template>

<style scoped>
.courseware-page {
  min-height: 100%;
  background: linear-gradient(180deg, #f3f8ff 0%, #f7fbff 100%);
  display: flex;
  flex-direction: column;
}

.courseware-content {
  flex: 1;
  padding: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-select {
  padding: 8px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  font-size: 14px;
}

.filter-icon {
  font-size: 0.9rem;
  opacity: 0.7;
}

.view-toggles {
  display: flex;
  gap: 4px;
}

.view-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 36px;
  padding: 0;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
}

.view-btn:hover {
  border-color: #cbd5e1;
  color: #64748b;
}

.view-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.add-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.add-btn:hover {
  background: #2563eb;
}

.courseware-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 22px;
}

.courseware-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
}

.courseware-pagination .page-btn {
  min-width: 36px;
  height: 36px;
  padding: 0 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.courseware-pagination .page-btn:hover:not(:disabled) {
  border-color: #cbd5e1;
  color: #1e293b;
}

.courseware-pagination .page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.courseware-pagination .page-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.courseware-grid.list {
  grid-template-columns: 1fr;
}

.courseware-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
  cursor: pointer;
  border: 1px solid #f1f5f9;
}

.courseware-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.courseware-grid.list .courseware-card {
  display: flex;
  flex-direction: row;
}

.card-thumbnail {
  height: 140px;
  position: relative;
  flex-shrink: 0;
}

.courseware-grid.list .card-thumbnail {
  width: 120px;
  height: 90px;
}

.type-tag {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}

.tag-pdf { background: #fecaca; color: #b91c1c; }
.tag-ppt { background: #fed7aa; color: #c2410c; }
.tag-video { background: #bfdbfe; color: #1d4ed8; }
.tag-word { background: #93c5fd; color: #1d4ed8; }

.card-body {
  padding: 16px;
}

.card-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.card-menu {
  padding: 4px;
  border: none;
  background: transparent;
  font-size: 1rem;
  color: #94a3b8;
  cursor: pointer;
  flex-shrink: 0;
}

.card-subject {
  font-size: 0.8rem;
  color: #64748b;
  margin: 6px 0 4px;
}

.card-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.card-meta {
  font-size: 0.75rem;
  color: #94a3b8;
  margin: 0;
}

.favorite-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  font-size: 1.1rem;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.2s;
}

.favorite-btn:hover {
  color: #94a3b8;
  background: #f1f5f9;
}

.favorite-btn.favorited {
  color: #eab308;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  width: 400px;
}

.modal-box h3 {
  margin-bottom: 24px;
  color: #1e293b;
}

.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  margin-bottom: 24px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-zone:hover {
  transform: scale(1.02);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: #94a3b8;
}

.upload-zone p {
  color: #64748b;
}

.file-input-hidden {
  display: none;
}

.upload-zone .hint {
  font-size: 0.875rem;
  margin-top: 8px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn, .confirm-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.cancel-btn {
  background: #f1f5f9;
  border: none;
  color: #475569;
}

.confirm-btn {
  background: #3b82f6;
  border: none;
  color: #fff;
}

.confirm-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.selected-files-hint {
  margin: 8px 0 0;
  font-size: 0.875rem;
  color: #64748b;
}

@media (max-width: 1100px) {
  .courseware-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 900px) {
  .courseware-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .courseware-grid {
    grid-template-columns: 1fr;
  }
}
</style>
