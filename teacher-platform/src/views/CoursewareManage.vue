<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCoursewareStore } from '../stores/courseware'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const router = useRouter()
const coursewareStore = useCoursewareStore()

// --- Filters ---
const filterType = ref('all')
const filterDate = ref('all')
const viewMode = ref('grid')

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

// --- Upload modal ---
const showAddModal = ref(false)
const fileInputRef = ref(null)
const selectedFiles = ref([])
const uploadTitle = ref('')
const uploadTags = ref('')
const uploadRemark = ref('')
const isUploading = ref(false)

// --- Edit modal ---
const showEditModal = ref(false)
const editItem = ref(null)
const editForm = ref({ title: '', tags: '', remark: '', file_type: '' })

// --- Action menu ---
const activeMenuId = ref(null)

// --- Delete confirm ---
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)

// --- Toast ---
const toastMessage = ref('')
const toastVisible = ref(false)

function showToast(msg) {
  toastMessage.value = msg
  toastVisible.value = true
  setTimeout(() => { toastVisible.value = false }, 3000)
}

// --- Data loading ---
const filteredList = computed(() => coursewareStore.filteredCoursewareList)
const loading = computed(() => coursewareStore.loading)

function buildFilters() {
  const filters = {}
  if (filterType.value !== 'all') filters.file_type = filterType.value
  if (filterDate.value !== 'all') filters.date_range = filterDate.value
  return filters
}

watch([filterType, filterDate], () => {
  coursewareStore.fetchFiltered(buildFilters())
})

onMounted(async () => {
  await Promise.all([
    coursewareStore.fetchAll(),
    coursewareStore.fetchFiltered(buildFilters()),
  ])
})

// --- Time formatting ---
function formatTime(isoStr) {
  if (!isoStr) return '\u2014'
  const d = dayjs(isoStr)
  const now = dayjs()
  const diffDays = now.diff(d, 'day')
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return d.format('YYYY年M月D日')
}

function formatSize(bytes) {
  if (!bytes) return '\u2014'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// --- Card click ---
function handleCardClick(item) {
  if (item.source_type === 'ppt') {
    router.push({ path: '/lesson-prep', query: { tab: 'ppt', projectId: item.source_id } })
  } else if (item.source_type === 'lesson_plan') {
    router.push({ path: '/lesson-prep', query: { tab: 'lesson-plan', lessonPlanId: item.source_id } })
  } else {
    showToast('该课件为手动上传，暂不支持在线编辑')
  }
}

// --- Action menu ---
function toggleMenu(id, event) {
  event.stopPropagation()
  activeMenuId.value = activeMenuId.value === id ? null : id
}

function closeMenu() {
  activeMenuId.value = null
}

// --- Edit ---
function openEdit(item, event) {
  event.stopPropagation()
  closeMenu()
  editItem.value = item
  editForm.value = {
    title: item.name || '',
    tags: item.tags || '',
    remark: item.remark || '',
    file_type: item.file_type || '',
  }
  showEditModal.value = true
}

async function saveEdit() {
  if (!editItem.value) return
  try {
    const data = { title: editForm.value.title }
    if (editItem.value.source_type === 'uploaded') {
      data.tags = editForm.value.tags
      data.remark = editForm.value.remark
      data.file_type = editForm.value.file_type
    }
    await coursewareStore.updateCoursewareItem(editItem.value.id, data)
    showEditModal.value = false
    showToast('修改成功')
  } catch (e) {
    showToast('修改失败: ' + e.message)
  }
}

// --- Delete ---
function confirmDelete(item, event) {
  event.stopPropagation()
  closeMenu()
  deleteTarget.value = item
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    await coursewareStore.deleteCourseware(deleteTarget.value.id)
    showDeleteConfirm.value = false
    showToast('删除成功')
  } catch (e) {
    showToast('删除失败: ' + e.message)
  }
}

// --- Download ---
function handleDownload(item, event) {
  event.stopPropagation()
  closeMenu()
  coursewareStore.downloadCourseware(item)
}

// --- Upload ---
function triggerFileSelect() {
  fileInputRef.value?.click()
}

function onFileSelected(event) {
  const files = Array.from(event.target.files || [])
  selectedFiles.value = files
}

async function doUpload() {
  if (selectedFiles.value.length === 0) return
  isUploading.value = true
  try {
    for (const file of selectedFiles.value) {
      await coursewareStore.uploadCourseware(file, {
        title: uploadTitle.value || undefined,
        tags: uploadTags.value || undefined,
        remark: uploadRemark.value || undefined,
      })
    }
    showAddModal.value = false
    selectedFiles.value = []
    uploadTitle.value = ''
    uploadTags.value = ''
    uploadRemark.value = ''
    showToast('上传成功')
  } catch (e) {
    showToast('上传失败: ' + e.message)
  } finally {
    isUploading.value = false
  }
}

// --- Favorite ---
function toggleFavorite(item, event) {
  event.stopPropagation()
  coursewareStore.toggleFavorite(item.id)
}

function isFavorited(item) {
  return coursewareStore.favorites.has(item.id)
}

// --- Helpers ---
function getTypeTag(type) {
  const map = { pdf: 'PDF', ppt: 'PPT', video: '视频', word: 'Word' }
  return map[type] || type
}

function getTypeTagClass(type) {
  const map = { pdf: 'tag-pdf', ppt: 'tag-ppt', video: 'tag-video', word: 'tag-word' }
  return map[type] || ''
}

const CARD_PALETTES = [
  'linear-gradient(135deg, #a8d8ea 0%, #7ec8c8 100%)',  // 薄荷蓝
  'linear-gradient(135deg, #f3c4fb 0%, #c9a0dc 100%)',  // 薰衣草紫
  'linear-gradient(135deg, #fbc4ab 0%, #e8998d 100%)',  // 珊瑚粉
  'linear-gradient(135deg, #b5ead7 0%, #8ac6a7 100%)',  // 抹茶绿
  'linear-gradient(135deg, #ffd6a5 0%, #f0b27a 100%)',  // 杏橘色
  'linear-gradient(135deg, #c7ceea 0%, #9fa8da 100%)',  // 雾蓝紫
  'linear-gradient(135deg, #fce4ec 0%, #f48fb1 100%)',  // 樱花粉
  'linear-gradient(135deg, #dcedc8 0%, #aed581 100%)',  // 嫩叶绿
  'linear-gradient(135deg, #b3e5fc 0%, #81d4fa 100%)',  // 天空蓝
  'linear-gradient(135deg, #ffe0b2 0%, #ffcc80 100%)',  // 暖阳橙
  'linear-gradient(135deg, #e1bee7 0%, #ba68c8 100%)',  // 丁香紫
  'linear-gradient(135deg, #c8e6c9 0%, #81c784 100%)',  // 翡翠绿
]
function _hashId(id) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = ((h << 5) - h + id.charCodeAt(i)) | 0
  return Math.abs(h)
}
function getThumbnailBg(itemId) {
  return CARD_PALETTES[_hashId(itemId) % CARD_PALETTES.length]
}

function getSourceLabel(sourceType) {
  return sourceType === 'uploaded' ? '手动上传' : 'AI生成'
}
</script>

<template>
  <div class="courseware-page" @click="closeMenu">
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

      <!-- Loading state -->
      <div v-if="loading" class="empty-state">
        <p>加载中...</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="filteredList.length === 0" class="empty-state">
        <p>暂无课件，点击添加课件上传或前往备课生成</p>
      </div>

      <!-- Courseware grid -->
      <div v-else class="courseware-grid" :class="viewMode">
        <div
          v-for="item in filteredList"
          :key="item.id"
          class="courseware-card"
          @click="handleCardClick(item)"
        >
          <div class="card-thumbnail" :style="{ background: getThumbnailBg(item.id) }">
            <img v-if="item.cover_image" :src="item.cover_image" class="cover-img" />
            <span :class="['type-tag', getTypeTagClass(item.file_type)]">{{ getTypeTag(item.file_type) }}</span>
            <button class="card-menu thumbnail-menu" @click="toggleMenu(item.id, $event)">&#8942;</button>
            <!-- Action dropdown -->
            <div v-if="activeMenuId === item.id" class="action-menu" @click.stop>
              <button class="action-item" @click="openEdit(item, $event)">编辑信息</button>
              <button class="action-item" @click="handleDownload(item, $event)">下载</button>
              <button class="action-item action-danger" @click="confirmDelete(item, $event)">删除</button>
            </div>
          </div>
          <div class="card-body">
            <div class="card-header-row">
              <h3 class="card-title">{{ item.name }}</h3>
            </div>
            <p class="card-subject">{{ getSourceLabel(item.source_type) }}</p>
            <div class="card-footer-row">
              <p class="card-meta">{{ formatTime(item.updated_at) }} · {{ formatSize(item.file_size) }}</p>
              <button
                class="favorite-btn"
                :class="{ favorited: isFavorited(item) }"
                @click="toggleFavorite(item, $event)"
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

      <!-- Upload modal -->
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
            <div class="modal-field">
              <label>标题（可选）</label>
              <input v-model="uploadTitle" type="text" class="modal-input" placeholder="自定义课件标题" />
            </div>
            <div class="modal-field">
              <label>标签（可选）</label>
              <input v-model="uploadTags" type="text" class="modal-input" placeholder="例如：数学,高一" />
            </div>
            <div class="modal-field">
              <label>备注（可选）</label>
              <input v-model="uploadRemark" type="text" class="modal-input" placeholder="备注信息" />
            </div>
            <div class="modal-actions">
              <button class="cancel-btn" @click="showAddModal = false">取消</button>
              <button class="confirm-btn" :disabled="!selectedFiles.length || isUploading" @click="doUpload">
                {{ isUploading ? '上传中...' : '上传' }}
              </button>
            </div>
            <p v-if="selectedFiles.length" class="selected-files-hint">已选 {{ selectedFiles.length }} 个文件</p>
          </div>
        </div>
      </Teleport>

      <!-- Edit modal -->
      <Teleport to="body">
        <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
          <div class="modal-box">
            <h3>编辑课件信息</h3>
            <div class="modal-field">
              <label>标题</label>
              <input v-model="editForm.title" type="text" class="modal-input" />
            </div>
            <template v-if="editItem && editItem.source_type === 'uploaded'">
              <div class="modal-field">
                <label>标签</label>
                <input v-model="editForm.tags" type="text" class="modal-input" />
              </div>
              <div class="modal-field">
                <label>备注</label>
                <input v-model="editForm.remark" type="text" class="modal-input" />
              </div>
              <div class="modal-field">
                <label>文件类型</label>
                <select v-model="editForm.file_type" class="modal-input">
                  <option value="pdf">PDF</option>
                  <option value="ppt">PPT</option>
                  <option value="word">Word</option>
                  <option value="video">视频</option>
                  <option value="image">图片</option>
                </select>
              </div>
            </template>
            <div class="modal-actions">
              <button class="cancel-btn" @click="showEditModal = false">取消</button>
              <button class="confirm-btn" @click="saveEdit">保存</button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Delete confirmation -->
      <Teleport to="body">
        <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
          <div class="modal-box">
            <h3>确认删除</h3>
            <p class="delete-msg">确定要删除「{{ deleteTarget?.name }}」吗？此操作不可撤销。</p>
            <div class="modal-actions">
              <button class="cancel-btn" @click="showDeleteConfirm = false">取消</button>
              <button class="confirm-btn confirm-danger" @click="doDelete">删除</button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Toast -->
      <Teleport to="body">
        <div v-if="toastVisible" class="toast">{{ toastMessage }}</div>
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

/* --- Cover image --- */
.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: absolute;
  top: 0;
  left: 0;
}

/* --- Thumbnail action menu button --- */
.thumbnail-menu {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 6px;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 4px;
  font-size: 1.1rem;
  color: #475569;
  cursor: pointer;
  line-height: 1;
  z-index: 2;
}

.thumbnail-menu:hover {
  background: #fff;
}

/* --- Action dropdown --- */
.action-menu {
  position: absolute;
  top: 36px;
  left: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  z-index: 10;
  min-width: 120px;
  overflow: hidden;
}

.action-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  border: none;
  background: none;
  text-align: left;
  font-size: 14px;
  color: #334155;
  cursor: pointer;
}

.action-item:hover {
  background: #f1f5f9;
}

.action-danger {
  color: #dc2626;
}

.action-danger:hover {
  background: #fef2f2;
}

/* --- Empty state --- */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: #94a3b8;
  font-size: 15px;
}

/* --- Modal fields --- */
.modal-field {
  margin-bottom: 16px;
}

.modal-field label {
  display: block;
  font-size: 13px;
  color: #475569;
  margin-bottom: 6px;
  font-weight: 500;
}

.modal-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}

.modal-input:focus {
  outline: none;
  border-color: #3b82f6;
}

/* --- Delete confirmation --- */
.delete-msg {
  color: #475569;
  font-size: 14px;
  margin-bottom: 24px;
  line-height: 1.6;
}

.confirm-danger {
  background: #dc2626;
}

.confirm-danger:hover {
  background: #b91c1c;
}

/* --- Toast --- */
.toast {
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  background: #1e293b;
  color: #fff;
  padding: 12px 28px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
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
