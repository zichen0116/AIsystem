<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { usePptStore } from '@/stores/ppt'
import {
  getExportUrl, exportEditablePptx, generateImages,
  editPageImage, getImageVersions, setCurrentVersion,
  getTask, getExportTaskStatus
} from '@/api/ppt'

const pptStore = usePptStore()

const isExporting = ref(false)
const currentPageIndex = ref(0)
const zoomLevel = ref(100)
const selectedPageIds = ref(new Set())
const isMultiSelectMode = ref(false)
const showExportMenu = ref(false)
const isGenerating = ref(false)

// Pages data
const pages = ref([])

// -------- 单页在线编辑 --------
const showEditPanel = ref(false)
const editInstruction = ref('')
const editTaskId = ref(null)
const editStatus = ref('idle') // idle | processing | done | error
const editErrorMsg = ref('')
let editPollTimer = null

// -------- 版本历史 --------
const showVersionPanel = ref(false)
const pageVersions = ref([])
const versionsLoading = ref(false)
const versionSwitching = ref(false)

// -------- editable-pptx 任务 --------
const editableExportTaskId = ref(null)
const editableExportStatus = ref('idle') // idle | processing | done | error
const editableExportUrl = ref(null)
let editableExportPollTimer = null

// -------- export/images 任务 --------
const imagesExportTaskId = ref(null)
const imagesExportStatus = ref('idle')
const imagesExportUrl = ref(null)
let imagesExportPollTimer = null

onMounted(async () => {
  if (pptStore.projectId) {
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  }
})

watch(() => pptStore.outlinePages, () => {
  syncPages()
}, { deep: true })

function syncPages() {
  pages.value = pptStore.outlinePages.map(p => ({
    id: p.id,
    pageNumber: p.pageNumber,
    title: p.title,
    description: p.description,
    imageUrl: p.imageUrl,
    thumbnail: p.imageUrl || null,
    status: p.imageUrl ? 'completed' : (p.status === 'generating' ? 'generating' : 'pending')
  }))
}

const completedCount = computed(() => {
  return pages.value.filter(p => p.status === 'completed').length
})

const hasAllImages = computed(() => {
  return pages.value.every(p => p.status === 'completed')
})

const missingImageCount = computed(() => {
  return pages.value.filter(p => p.status !== 'completed').length
})

function goToDescription() {
  pptStore.setPhase('description')
}

function toggleMultiSelectMode() {
  isMultiSelectMode.value = !isMultiSelectMode.value
  if (!isMultiSelectMode.value) {
    selectedPageIds.value = new Set()
  }
}

function togglePageSelection(pageId) {
  if (selectedPageIds.value.has(pageId)) {
    selectedPageIds.value.delete(pageId)
  } else {
    selectedPageIds.value.add(pageId)
  }
  selectedPageIds.value = new Set(selectedPageIds.value)
}

function selectAllPages() {
  pages.value.forEach(p => {
    if (p.id && p.status === 'completed') {
      selectedPageIds.value.add(p.id)
    }
  })
  selectedPageIds.value = new Set(selectedPageIds.value)
}

function deselectAllPages() {
  selectedPageIds.value = new Set()
}

async function handleGenerateAll() {
  if (!pptStore.projectId) return

  isGenerating.value = true
  try {
    const pageIds = isMultiSelectMode.value && selectedPageIds.value.size > 0
      ? Array.from(selectedPageIds.value)
      : null
    await generateImages(pptStore.projectId, pageIds)
    // Refresh pages after generation
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (error) {
    console.error('生成图片失败:', error)
  } finally {
    isGenerating.value = false
  }
}

async function handleGeneratePage(index) {
  if (!pptStore.projectId) return

  const page = pages.value[index]
  if (!page || !page.id) return

  isGenerating.value = true
  try {
    await generateImages(pptStore.projectId, [page.id])
    // Refresh pages after generation
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (error) {
    console.error('生成页面图片失败:', error)
  } finally {
    isGenerating.value = false
  }
}

function handleEditCurrentPage() {
  // 打开在线编辑面板
  editInstruction.value = ''
  editStatus.value = 'idle'
  editErrorMsg.value = ''
  showEditPanel.value = true
  showVersionPanel.value = false
}

async function handleRegenerateCurrentPage() {
  if (!pptStore.projectId || !currentPage.value) return

  isGenerating.value = true
  try {
    await generateImages(pptStore.projectId, [currentPage.value.id])
    // Refresh pages after generation
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (error) {
    console.error('重新生成页面图片失败:', error)
  } finally {
    isGenerating.value = false
  }
}

async function handleExport(type) {
  if (!pptStore.projectId) return
  isExporting.value = false
  showExportMenu.value = false
  const url = getExportUrl(pptStore.projectId, type)
  window.open(url, '_blank')
}

function handleExportAll() {
  handleExport('pptx')
}

function handleExportPdf() {
  handleExport('pdf')
}

async function handleExportEditable() {
  if (!pptStore.projectId) return
  showExportMenu.value = false
  editableExportStatus.value = 'processing'
  editableExportUrl.value = null
  try {
    const res = await exportEditablePptx(pptStore.projectId)
    editableExportTaskId.value = res.task_id
    _pollEditableExport()
  } catch (e) {
    editableExportStatus.value = 'error'
    console.error('启动可编辑导出失败:', e)
  }
}

function _pollEditableExport() {
  clearInterval(editableExportPollTimer)
  editableExportPollTimer = setInterval(async () => {
    try {
      const task = await getExportTaskStatus(editableExportTaskId.value)
      if (task.status === 'COMPLETED') {
        clearInterval(editableExportPollTimer)
        editableExportStatus.value = 'done'
        editableExportUrl.value = task.result?.url || null
        if (editableExportUrl.value) {
          window.open(editableExportUrl.value, '_blank')
        }
      } else if (task.status === 'FAILED') {
        clearInterval(editableExportPollTimer)
        editableExportStatus.value = 'error'
      }
    } catch (e) {
      clearInterval(editableExportPollTimer)
      editableExportStatus.value = 'error'
    }
  }, 2000)
}

async function handleExportImages() {
  if (!pptStore.projectId) return
  showExportMenu.value = false
  // export/images 走异步任务
  imagesExportStatus.value = 'processing'
  imagesExportUrl.value = null
  try {
    const { apiRequest } = await import('@/api/http')
    const res = await apiRequest(`/api/v1/ppt/projects/${pptStore.projectId}/export/images`, { method: 'POST' })
    imagesExportTaskId.value = res.task_id
    _pollImagesExport()
  } catch (e) {
    imagesExportStatus.value = 'error'
    console.error('启动图片导出失败:', e)
  }
}

function _pollImagesExport() {
  clearInterval(imagesExportPollTimer)
  imagesExportPollTimer = setInterval(async () => {
    try {
      const task = await getExportTaskStatus(imagesExportTaskId.value)
      if (task.status === 'COMPLETED') {
        clearInterval(imagesExportPollTimer)
        imagesExportStatus.value = 'done'
        imagesExportUrl.value = task.result?.url || null
        if (imagesExportUrl.value) {
          window.open(imagesExportUrl.value, '_blank')
        }
      } else if (task.status === 'FAILED') {
        clearInterval(imagesExportPollTimer)
        imagesExportStatus.value = 'error'
      }
    } catch (e) {
      clearInterval(imagesExportPollTimer)
      imagesExportStatus.value = 'error'
    }
  }, 2000)
}

// -------- 单页在线编辑 --------

async function submitEditInstruction() {
  if (!editInstruction.value.trim() || !currentPage.value?.id) return
  editStatus.value = 'processing'
  editErrorMsg.value = ''
  editTaskId.value = null
  try {
    const res = await editPageImage(pptStore.projectId, currentPage.value.id, editInstruction.value)
    editTaskId.value = res.task_id
    _pollEditTask()
  } catch (e) {
    editStatus.value = 'error'
    editErrorMsg.value = '发起编辑失败，请重试'
  }
}

function _pollEditTask() {
  clearInterval(editPollTimer)
  editPollTimer = setInterval(async () => {
    try {
      const task = await getTask(pptStore.projectId, editTaskId.value)
      if (task.status === 'COMPLETED') {
        clearInterval(editPollTimer)
        editStatus.value = 'done'
        // 刷新页面图和版本列表
        await pptStore.fetchPages(pptStore.projectId)
        syncPages()
        if (showVersionPanel.value) {
          await loadVersions()
        }
      } else if (task.status === 'FAILED') {
        clearInterval(editPollTimer)
        editStatus.value = 'error'
        editErrorMsg.value = task.result?.error || '编辑失败，请重试'
      }
    } catch (e) {
      clearInterval(editPollTimer)
      editStatus.value = 'error'
      editErrorMsg.value = '查询任务状态失败'
    }
  }, 2000)
}

function retryEdit() {
  editStatus.value = 'idle'
  editErrorMsg.value = ''
}

// -------- 版本历史 --------

async function toggleVersionPanel() {
  showVersionPanel.value = !showVersionPanel.value
  showEditPanel.value = false
  if (showVersionPanel.value && currentPage.value?.id) {
    await loadVersions()
  }
}

async function loadVersions() {
  if (!currentPage.value?.id) return
  versionsLoading.value = true
  try {
    pageVersions.value = await getImageVersions(pptStore.projectId, currentPage.value.id)
  } catch (e) {
    console.error('加载版本失败:', e)
    pageVersions.value = []
  } finally {
    versionsLoading.value = false
  }
}

async function switchVersion(version) {
  if (versionSwitching.value || version.is_active) return
  versionSwitching.value = true
  try {
    await setCurrentVersion(pptStore.projectId, currentPage.value.id, version.id)
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
    await loadVersions()
  } catch (e) {
    console.error('切换版本失败:', e)
  } finally {
    versionSwitching.value = false
  }
}

// 当切换预览页时刷新版本列表
watch(currentPageIndex, async () => {
  if (showVersionPanel.value) {
    await loadVersions()
  }
})

onUnmounted(() => {
  clearInterval(editPollTimer)
  clearInterval(editableExportPollTimer)
  clearInterval(imagesExportPollTimer)
})

function prevPage() {
  if (currentPageIndex.value > 0) {
    currentPageIndex.value--
  }
}

function nextPage() {
  if (currentPageIndex.value < pages.value.length - 1) {
    currentPageIndex.value++
  }
}

function selectPage(index) {
  if (isMultiSelectMode.value) {
    const page = pages.value[index]
    if (page.id && page.status === 'completed') {
      togglePageSelection(page.id)
    }
  } else {
    currentPageIndex.value = index
  }
}

function getStatusClass(status) {
  switch (status) {
    case 'completed': return 'status-completed'
    case 'generating': return 'status-generating'
    default: return 'status-pending'
  }
}

function getStatusText(status) {
  switch (status) {
    case 'completed': return '已完成'
    case 'generating': return '生成中'
    default: return '未生成'
  }
}

const currentPage = computed(() => pages.value[currentPageIndex.value])
</script>

<template>
  <div class="slide-preview">
    <!-- 顶栏 -->
    <header class="header">
      <div class="header-left">
        <button class="icon-btn" @click="goToDescription" title="返回">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="logo">
          <span class="logo-text">AI备课</span>
        </div>
        <span class="header-divider">|</span>
        <span class="header-title">预览</span>
      </div>

      <div class="header-right">
        <button class="icon-btn" title="项目设置">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
        <button class="icon-btn" title="更换模板">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </button>
        <button class="icon-btn" title="刷新">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
        </button>

        <!-- 导出按钮 -->
        <div class="export-dropdown">
          <button
            class="export-btn"
            :class="{ disabled: !isMultiSelectMode && !hasAllImages }"
            :disabled="!isMultiSelectMode && !hasAllImages"
            @click="showExportMenu = !showExportMenu"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {{ isMultiSelectMode && selectedPageIds.size > 0 ? `导出 (${selectedPageIds.size})` : '导出' }}
          </button>

          <div v-if="showExportMenu" class="export-menu">
            <button class="export-menu-item" @click="handleExportAll">
              导出 PPTX
            </button>
            <button class="export-menu-item" @click="handleExportEditable">
              导出可编辑 PPTX（Beta）
              <span v-if="editableExportStatus === 'processing'" class="export-tag">处理中...</span>
              <span v-else-if="editableExportStatus === 'done'" class="export-tag done">✓ 完成</span>
              <span v-else-if="editableExportStatus === 'error'" class="export-tag err">失败</span>
            </button>
            <button class="export-menu-item" @click="handleExportPdf">
              导出 PDF
            </button>
            <button class="export-menu-item" @click="handleExportImages">
              导出图片（ZIP）
              <span v-if="imagesExportStatus === 'processing'" class="export-tag">处理中...</span>
              <span v-else-if="imagesExportStatus === 'done'" class="export-tag done">✓ 完成</span>
              <span v-else-if="imagesExportStatus === 'error'" class="export-tag err">失败</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：缩略图列表 -->
      <aside class="left-panel">
        <div class="panel-header">
          <!-- 批量生成按钮 -->
          <button
            class="generate-btn"
            :disabled="isMultiSelectMode && selectedPageIds.size === 0"
            @click="handleGenerateAll"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
            </svg>
            {{ isMultiSelectMode && selectedPageIds.size > 0 ? `生成选中页面 (${selectedPageIds.size})` : `批量生成图片 (${pages.length})` }}
          </button>
        </div>

        <!-- 多选模式切换 -->
        <div class="multiselect-bar">
          <button
            class="multiselect-toggle"
            :class="{ active: isMultiSelectMode }"
            @click="toggleMultiSelectMode"
          >
            <svg v-if="!isMultiSelectMode" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="9 11 12 14 22 4"/>
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            </svg>
            {{ isMultiSelectMode ? '取消多选' : '多选' }}
          </button>
          <template v-if="isMultiSelectMode">
            <button
              class="select-all-btn"
              @click="selectedPageIds.size === pages.filter(p => p.status === 'completed').length ? deselectAllPages() : selectAllPages()"
            >
              {{ selectedPageIds.size === pages.filter(p => p.status === 'completed').length ? '取消全选' : '全选' }}
            </button>
            <span v-if="selectedPageIds.size > 0" class="selected-count">
              ({{ selectedPageIds.size }}页)
            </span>
          </template>
        </div>

        <!-- 缩略图列表 -->
        <div class="thumbnails-container">
          <div
            v-for="(page, index) in pages"
            :key="page.id"
            class="thumbnail-card"
            :class="{
              selected: currentPageIndex === index,
              'multi-selected': selectedPageIds.has(page.id)
            }"
            @click="selectPage(index)"
          >
            <!-- 复选框（多选模式时显示） -->
            <div
              v-if="isMultiSelectMode && page.status === 'completed'"
              class="checkbox"
              :class="{ checked: selectedPageIds.has(page.id) }"
              @click.stop="togglePageSelection(page.id)"
            >
              <svg v-if="selectedPageIds.has(page.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>

            <div class="thumbnail-image">
              <template v-if="page.thumbnail">
                <img :src="page.thumbnail" :alt="page.title">
              </template>
              <template v-else>
                <div class="thumbnail-placeholder">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                  </svg>
                </div>
              </template>

              <!-- 悬停时的操作按钮 -->
              <div class="thumbnail-overlay">
                <span class="thumbnail-number">{{ index + 1 }}</span>
              </div>
            </div>

            <div class="thumbnail-info">
              <span class="thumbnail-title">{{ page.title || '未命名' }}</span>
              <span class="thumbnail-status" :class="getStatusClass(page.status)">
                {{ getStatusText(page.status) }}
              </span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧：大图预览 -->
      <main class="preview-area">
        <template v-if="pages.length === 0">
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <h3 class="empty-title">还没有页面</h3>
            <p class="empty-desc">请先返回编辑页面添加内容</p>
            <button class="back-edit-btn" @click="goToDescription">
              返回编辑
            </button>
          </div>
        </template>

        <template v-else>
          <!-- 预览区 -->
          <div class="preview-container">
            <div
              class="preview-slide"
              :style="{ aspectRatio: '16/9' }"
            >
              <template v-if="currentPage?.thumbnail">
                <img
                  :src="currentPage.imageUrl"
                  :alt="currentPage.title"
                  class="slide-image"
                >
              </template>
              <template v-else>
                <div class="slide-placeholder">
                  <div class="placeholder-icon">🍌</div>
                  <p class="placeholder-text">
                    {{ currentPage?.status === 'generating' ? '生成中...' : '尚未生成图片' }}
                  </p>
                  <button
                    v-if="currentPage?.status !== 'generating'"
                    class="generate-page-btn"
                    @click="handleGeneratePage(currentPageIndex)"
                  >
                    生成此页
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- 控制栏 -->
          <div class="control-bar">
            <div class="control-left">
              <!-- 导航 -->
              <button class="nav-btn" :disabled="currentPageIndex === 0" @click="prevPage">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <polyline points="15 18 9 12 15 6"/>
                </svg>
                上一页
              </button>
              <span class="page-indicator">{{ currentPageIndex + 1 }} / {{ pages.length }}</span>
              <button class="nav-btn" :disabled="currentPageIndex >= pages.length - 1" @click="nextPage">
                下一页
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            </div>

            <div class="control-right">
              <button
                class="action-btn secondary"
                :class="{ active: showVersionPanel }"
                :disabled="!currentPage?.id"
                @click="toggleVersionPanel"
              >
                版本历史
              </button>
              <button
                class="action-btn secondary"
                :class="{ active: showEditPanel }"
                :disabled="!currentPage?.id"
                @click="handleEditCurrentPage"
              >
                在线编辑
              </button>
              <button
                class="action-btn secondary"
                :disabled="currentPage?.status === 'generating'"
                @click="handleRegenerateCurrentPage"
              >
                {{ currentPage?.status === 'generating' ? '生成中...' : '重新生成' }}
              </button>
            </div>
          </div>
        </template>
      </main>

      <!-- 在线编辑面板 -->
      <aside v-if="showEditPanel" class="right-panel">
        <div class="panel-title">
          <span>在线编辑</span>
          <button class="close-btn" @click="showEditPanel = false">✕</button>
        </div>

        <div v-if="editStatus === 'done'" class="edit-success">
          <div class="success-icon">✓</div>
          <p>编辑完成，图片已更新</p>
          <button class="action-btn secondary small" @click="editStatus = 'idle'">继续编辑</button>
        </div>

        <div v-else-if="editStatus === 'error'" class="edit-error">
          <p>{{ editErrorMsg || '编辑失败' }}</p>
          <button class="action-btn secondary small" @click="retryEdit">重试</button>
        </div>

        <template v-else>
          <p class="panel-hint">用自然语言描述你想对当前页面图片做的修改</p>
          <textarea
            v-model="editInstruction"
            class="edit-textarea"
            placeholder="例如：把背景改为深蓝色，突出标题区"
            :disabled="editStatus === 'processing'"
            rows="5"
          />
          <button
            class="action-btn primary full"
            :disabled="!editInstruction.trim() || editStatus === 'processing'"
            @click="submitEditInstruction"
          >
            {{ editStatus === 'processing' ? '编辑中，请稍候...' : '发起编辑' }}
          </button>
          <p v-if="editStatus === 'processing'" class="panel-hint muted">
            AI 正在处理，完成后自动刷新图片
          </p>
        </template>
      </aside>

      <!-- 版本历史面板 -->
      <aside v-if="showVersionPanel" class="right-panel">
        <div class="panel-title">
          <span>版本历史</span>
          <button class="close-btn" @click="showVersionPanel = false">✕</button>
        </div>

        <div v-if="versionsLoading" class="panel-loading">加载中...</div>

        <div v-else-if="pageVersions.length === 0" class="panel-hint">
          该页面暂无版本历史
        </div>

        <div v-else class="version-list">
          <div
            v-for="ver in pageVersions"
            :key="ver.id"
            class="version-item"
            :class="{ 'is-current': ver.is_active }"
          >
            <img v-if="ver.image_url" :src="ver.image_url" class="version-thumb" />
            <div class="version-meta">
              <span class="version-no">v{{ ver.version }}</span>
              <span class="version-op">{{ ver.operation === 'edit' ? '编辑' : '生成' }}</span>
              <span v-if="ver.is_active" class="version-current-badge">当前</span>
            </div>
            <button
              v-if="!ver.is_active"
              class="action-btn secondary small"
              :disabled="versionSwitching"
              @click="switchVersion(ver)"
            >
              {{ versionSwitching ? '切换中' : '恢复此版本' }}
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.slide-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
}

/* Header */
.header {
  height: 56px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.header-divider {
  color: #e5e7eb;
}

.header-title {
  font-size: 15px;
  font-weight: 500;
  color: #64748b;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Export Dropdown */
.export-dropdown {
  position: relative;
}

.export-btn {
  padding: 8px 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  font-family: inherit;
}

.export-btn:hover:not(:disabled) {
  background: #2563eb;
}

.export-btn:disabled,
.export-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.export-menu {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  width: 200px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  overflow: hidden;
  z-index: 100;
}

.export-menu-item {
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: white;
  text-align: left;
  font-size: 13px;
  color: #1e293b;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.export-menu-item:hover {
  background: #f8fafc;
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Left Panel */
.left-panel {
  width: 280px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-header {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.generate-btn {
  width: 100%;
  padding: 10px 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s;
  font-family: inherit;
}

.generate-btn:hover:not(:disabled) {
  background: #2563eb;
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.multiselect-bar {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.multiselect-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: #64748b;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  font-family: inherit;
}

.multiselect-toggle:hover {
  background: #f1f5f9;
}

.multiselect-toggle.active {
  background: #FEF3C7;
  color: #92400e;
}

.select-all-btn {
  color: #3b82f6;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
}

.select-all-btn:hover {
  text-decoration: underline;
}

.selected-count {
  color: #3b82f6;
  font-weight: 500;
}

.thumbnails-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.thumbnail-card {
  position: relative;
  cursor: pointer;
  transition: all 0.2s;
}

.thumbnail-card:hover .thumbnail-overlay {
  opacity: 1;
}

.thumbnail-card.selected .thumbnail-image {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.thumbnail-card.multi-selected .thumbnail-image {
  outline: 2px solid #F59E0B;
  outline-offset: 2px;
}

.checkbox {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255,255,255,0.9);
  border: 2px solid #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  transition: all 0.2s;
}

.checkbox.checked {
  background: #F59E0B;
  border-color: #F59E0B;
  color: white;
}

.thumbnail-image {
  position: relative;
  aspect-ratio: 16/9;
  background: #f1f5f9;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.thumbnail-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.thumbnail-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 6px;
  opacity: 0;
  transition: opacity 0.2s;
}

.thumbnail-number {
  width: 22px;
  height: 22px;
  background: rgba(255,255,255,0.9);
  color: #1e293b;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumbnail-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.thumbnail-title {
  font-size: 12px;
  color: #1e293b;
  font-weight: 500;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thumbnail-status {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 999px;
  flex-shrink: 0;
}

.thumbnail-status.status-completed {
  background: #d1fae5;
  color: #059669;
}

.thumbnail-status.status-generating {
  background: #fef3c7;
  color: #92400e;
}

.thumbnail-status.status-pending {
  background: #f1f5f9;
  color: #94a3b8;
}

/* Preview Area */
.preview-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #FFFBEB 0%, #f8fafc 50%, #f1f5f9 100%);
  overflow: hidden;
}

.preview-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
}

.preview-slide {
  width: 100%;
  max-width: 800px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  overflow: hidden;
  position: relative;
}

.slide-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.slide-placeholder {
  width: 100%;
  height: 100%;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  gap: 12px;
}

.placeholder-icon {
  font-size: 64px;
}

.placeholder-text {
  color: #64748b;
  font-size: 14px;
}

.generate-page-btn {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.generate-page-btn:hover {
  background: #2563eb;
}

/* Control Bar */
.control-bar {
  padding: 12px 16px;
  background: white;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.control-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background: transparent;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.nav-btn:hover:not(:disabled) {
  background: #f8fafc;
  color: #1e293b;
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-indicator {
  font-size: 13px;
  color: #64748b;
  min-width: 60px;
  text-align: center;
}

.action-btn {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  font-family: inherit;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.secondary {
  background: white;
  color: #1e293b;
  border: 1px solid #e5e7eb;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #f8fafc;
}

/* Empty State */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.empty-icon {
  font-size: 64px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.empty-desc {
  font-size: 14px;
  color: #64748b;
}

.back-edit-btn {
  margin-top: 8px;
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.back-edit-btn:hover {
  background: #2563eb;
}

/* Export tags */
.export-tag {
  margin-left: 6px;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
}
.export-tag.done { background: #d1fae5; color: #059669; }
.export-tag.err { background: #fee2e2; color: #dc2626; }

/* Right panels */
.right-panel {
  width: 280px;
  background: white;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
  padding: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #94a3b8;
  padding: 2px 4px;
}
.close-btn:hover { color: #1e293b; }

.panel-hint {
  padding: 8px 16px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}
.panel-hint.muted { color: #94a3b8; }

.panel-loading {
  padding: 24px 16px;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
}

.edit-textarea {
  margin: 0 16px 12px;
  width: calc(100% - 32px);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  color: #1e293b;
  line-height: 1.5;
}
.edit-textarea:focus { outline: none; border-color: #3b82f6; }
.edit-textarea:disabled { background: #f8fafc; }

.edit-success, .edit-error {
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}
.success-icon { font-size: 32px; color: #059669; }
.edit-error { color: #dc2626; }

/* Version list */
.version-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.version-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}
.version-item.is-current { border-color: #3b82f6; }

.version-thumb {
  width: 100%;
  aspect-ratio: 16/9;
  object-fit: cover;
  display: block;
  background: #f1f5f9;
}

.version-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 12px;
}
.version-no { font-weight: 600; color: #1e293b; }
.version-op { color: #64748b; }
.version-current-badge {
  margin-left: auto;
  padding: 1px 6px;
  background: #dbeafe;
  color: #2563eb;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
}

/* Btn extensions */
.action-btn.primary {
  background: #3b82f6;
  color: white;
  border: none;
}
.action-btn.primary:hover:not(:disabled) { background: #2563eb; }
.action-btn.primary:disabled { opacity: 0.5; cursor: not-allowed; }

.action-btn.full { width: calc(100% - 32px); margin: 0 16px 12px; justify-content: center; }
.action-btn.small { padding: 5px 10px; font-size: 12px; width: calc(100% - 20px); margin: 0 10px 10px; justify-content: center; }
.action-btn.active { background: #EFF6FF; color: #2563eb; border-color: #bfdbfe; }
</style>
