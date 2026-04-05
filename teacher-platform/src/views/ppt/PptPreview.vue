<script setup>
import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { usePptStore } from '@/stores/ppt'
import {
  exportEditablePptx, generateImages,
  editPageImage, getImageVersions, setCurrentVersion,
  getTask, getExportTaskStatus,
  getMaterials, generateMaterial,
  getPresetTemplates, getUserTemplates, uploadProjectTemplate,
  regeneratePageRenovation, updateProjectSettings
} from '@/api/ppt'
import { authFetch } from '@/api/http'

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

// -------- 素材库 --------
const showMaterialPanel = ref(false)
const materials = ref([])
const materialPrompt = ref('')
const materialAspectRatio = ref('1:1')
const materialGenerating = ref(false)
const materialTaskId = ref(null)
let materialPollTimer = null

// -------- 模板切换 --------
const showTemplateModal = ref(false)
const presetTemplates = ref([])
const userTemplatesList = ref([])
const templatesLoading = ref(false)
const currentTemplateUrl = computed(() => pptStore.projectSettings?.template_image_url || null)
let settingsBtnEl = null
let refreshBtnEl = null

// -------- 在线编辑 context_images --------
const contextUseTemplate = ref(false)
const contextMaterialIds = ref([])
const contextUploadedFiles = ref([])
const contextUploadedFileUrls = ref([])
const previewImageRef = ref(null)
const isRegionSelectionMode = ref(false)
const isSelectingRegion = ref(false)
const selectionStart = ref(null)
const selectionRect = ref(null)
const selectionBBox = ref(null)

// -------- renovation 单页再生 --------
const renovationRegenerating = ref(false)
const isRenovationMode = computed(() => pptStore.creationType === 'renovation')
const currentAspectRatioStyle = computed(() => {
  const value = String(pptStore.projectSettings?.aspect_ratio || '16:9')
  const [w, h] = value.split(':').map(Number)
  return w > 0 && h > 0 ? `${w}/${h}` : '16/9'
})
const selectedRegionSummary = computed(() => {
  if (!selectionBBox.value) return ''
  return `${selectionBBox.value.width} x ${selectionBBox.value.height}px`
})

onMounted(async () => {
  if (pptStore.projectId) {
    await reloadPreviewData({ includeMaterials: true })
  }
  await nextTick()
  bindHeaderQuickActions()
})

watch(() => pptStore.outlinePages, () => {
  syncPages()
}, { deep: true })

watch(contextUploadedFiles, (files, previousFiles = []) => {
  previousFiles.forEach((_, index) => {
    const url = contextUploadedFileUrls.value[index]
    if (url) {
      URL.revokeObjectURL(url)
    }
  })
  contextUploadedFileUrls.value = files.map(file => URL.createObjectURL(file))
})

function syncPages() {
  pages.value = pptStore.outlinePages.map(p => ({
    id: p.id,
    pageNumber: p.pageNumber,
    title: p.title,
    description: p.description,
    imageUrl: p.imageUrl,
    thumbnail: p.imageUrl || null,
    status: p.isImageGenerating ? 'generating' : (p.imageUrl ? 'completed' : 'pending')
  }))
}

function markPagesGenerating(targetPageIds = null) {
  const targetSet = targetPageIds?.length ? new Set(targetPageIds) : null
  pages.value = pages.value.map(page => {
    if (targetSet && !targetSet.has(page.id)) {
      return page
    }
    return {
      ...page,
      status: 'generating'
    }
  })
}

function resetRegionSelection() {
  isRegionSelectionMode.value = false
  isSelectingRegion.value = false
  selectionStart.value = null
  selectionRect.value = null
  selectionBBox.value = null
}

function getPreviewImageMetrics() {
  const imageEl = previewImageRef.value
  if (!imageEl) return null

  const rect = imageEl.getBoundingClientRect()
  const naturalWidth = imageEl.naturalWidth || rect.width
  const naturalHeight = imageEl.naturalHeight || rect.height
  if (!rect.width || !rect.height || !naturalWidth || !naturalHeight) {
    return null
  }

  const naturalRatio = naturalWidth / naturalHeight
  const displayRatio = rect.width / rect.height

  let contentWidth = rect.width
  let contentHeight = rect.height
  let offsetX = 0
  let offsetY = 0

  if (naturalRatio > displayRatio) {
    contentHeight = rect.width / naturalRatio
    offsetY = (rect.height - contentHeight) / 2
  } else if (naturalRatio < displayRatio) {
    contentWidth = rect.height * naturalRatio
    offsetX = (rect.width - contentWidth) / 2
  }

  return {
    rect,
    naturalWidth,
    naturalHeight,
    contentWidth,
    contentHeight,
    offsetX,
    offsetY
  }
}

function removeContextUploadedFile(index) {
  contextUploadedFiles.value = contextUploadedFiles.value.filter((_, i) => i !== index)
}

function clearSelectedRegion() {
  selectionRect.value = null
  selectionBBox.value = null
}

function handleContextFileUpload(event) {
  const files = Array.from(event?.target?.files || [])
  if (files.length > 0) {
    contextUploadedFiles.value = [...contextUploadedFiles.value, ...files]
  }
  if (event?.target) {
    event.target.value = ''
  }
}

function toggleRegionSelectionMode() {
  if (isRegionSelectionMode.value) {
    resetRegionSelection()
  } else {
    clearSelectedRegion()
    isRegionSelectionMode.value = true
  }
}

function handleRegionPointerDown(event) {
  if (!showEditPanel.value || !isRegionSelectionMode.value || !previewImageRef.value) return
  const metrics = getPreviewImageMetrics()
  if (!metrics) return

  const x = event.clientX - metrics.rect.left - metrics.offsetX
  const y = event.clientY - metrics.rect.top - metrics.offsetY
  if (x < 0 || y < 0 || x > metrics.contentWidth || y > metrics.contentHeight) return

  isSelectingRegion.value = true
  selectionStart.value = { x, y }
  selectionRect.value = {
    left: metrics.offsetX + x,
    top: metrics.offsetY + y,
    width: 0,
    height: 0
  }
}

function handleRegionPointerMove(event) {
  if (!showEditPanel.value || !isRegionSelectionMode.value || !isSelectingRegion.value || !selectionStart.value) return
  const metrics = getPreviewImageMetrics()
  if (!metrics) return

  const x = Math.max(0, Math.min(event.clientX - metrics.rect.left - metrics.offsetX, metrics.contentWidth))
  const y = Math.max(0, Math.min(event.clientY - metrics.rect.top - metrics.offsetY, metrics.contentHeight))

  selectionRect.value = {
    left: metrics.offsetX + Math.min(selectionStart.value.x, x),
    top: metrics.offsetY + Math.min(selectionStart.value.y, y),
    width: Math.abs(x - selectionStart.value.x),
    height: Math.abs(y - selectionStart.value.y)
  }
}

async function handleRegionPointerUp() {
  if (!showEditPanel.value || !isRegionSelectionMode.value || !isSelectingRegion.value || !selectionRect.value || !previewImageRef.value) {
    isSelectingRegion.value = false
    selectionStart.value = null
    return
  }

  const metrics = getPreviewImageMetrics()
  isSelectingRegion.value = false
  selectionStart.value = null
  if (!metrics) return

  const leftInImage = selectionRect.value.left - metrics.offsetX
  const topInImage = selectionRect.value.top - metrics.offsetY
  if (selectionRect.value.width < 12 || selectionRect.value.height < 12) {
    clearSelectedRegion()
    return
  }

  const scaleX = metrics.naturalWidth / metrics.contentWidth
  const scaleY = metrics.naturalHeight / metrics.contentHeight
  selectionBBox.value = {
    x: Math.max(0, Math.round(leftInImage * scaleX)),
    y: Math.max(0, Math.round(topInImage * scaleY)),
    width: Math.max(1, Math.round(selectionRect.value.width * scaleX)),
    height: Math.max(1, Math.round(selectionRect.value.height * scaleY))
  }

  /*

    alert('框选区域裁剪失败，可能是当前图片不允许浏览器读取像素数据')
  }
}
  */
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function reloadPreviewData({ includeMaterials = false } = {}) {
  if (!pptStore.projectId) return
  await pptStore.fetchPages(pptStore.projectId)
  syncPages()
  if (includeMaterials) {
    await loadMaterials()
  }
}

async function waitForImageTask(taskId) {
  if (!pptStore.projectId || !taskId) return
  const deadline = Date.now() + 8 * 60 * 1000

  while (Date.now() < deadline) {
    const task = await getTask(pptStore.projectId, taskId)
    await reloadPreviewData()
    if (task.status === 'COMPLETED' || task.status === 'FAILED') {
      const failureCount = task?.result?.failure_count || 0
      const failedPages = task?.result?.failed_pages || []
      if (task.status === 'FAILED' || failureCount > 0) {
        const firstError = failedPages[0]?.error
        const baseMsg = task.status === 'FAILED'
          ? (task?.result?.error || '图片生成失败')
          : `部分页面生成失败（${failureCount} 页）`
        throw new Error(firstError ? `${baseMsg}: ${firstError}` : baseMsg)
      }
      return
    }

    await sleep(2500)
  }

  throw new Error('图片生成超时，请稍后点击刷新查看结果')
}

async function startImageGeneration(pageIds = null) {
  if (!pptStore.projectId) return
  const res = await generateImages(pptStore.projectId, pageIds)
  markPagesGenerating(pageIds)
  if (res?.task_id) {
    await waitForImageTask(res.task_id)
  }
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

function bindHeaderQuickActions() {
  const headerIconButtons = document.querySelectorAll('.header-right > .icon-btn')
  settingsBtnEl = headerIconButtons?.[0] || null
  refreshBtnEl = headerIconButtons?.[2] || null

  if (settingsBtnEl) {
    settingsBtnEl.addEventListener('click', openProjectSettingsModal)
  }
  if (refreshBtnEl) {
    refreshBtnEl.addEventListener('click', handleRefreshPreview)
  }
}

function unbindHeaderQuickActions() {
  if (settingsBtnEl) {
    settingsBtnEl.removeEventListener('click', openProjectSettingsModal)
    settingsBtnEl = null
  }
  if (refreshBtnEl) {
    refreshBtnEl.removeEventListener('click', handleRefreshPreview)
    refreshBtnEl = null
  }
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
  if (!pptStore.projectId || isGenerating.value) return

  isGenerating.value = true
  try {
    const pageIds = isMultiSelectMode.value && selectedPageIds.value.size > 0
      ? Array.from(selectedPageIds.value)
      : null
    await startImageGeneration(pageIds)
  } catch (error) {
    console.error('生成图片失败:', error)
    alert(error?.message || '生成图片失败，请稍后重试')
  } finally {
    isGenerating.value = false
  }
}

async function handleGeneratePage(index) {
  if (!pptStore.projectId || isGenerating.value) return

  const page = pages.value[index]
  if (!page || !page.id) return

  isGenerating.value = true
  try {
    await startImageGeneration([page.id])
  } catch (error) {
    console.error('生成页面图片失败:', error)
    alert(error?.message || '生成页面图片失败，请稍后重试')
  } finally {
    isGenerating.value = false
  }
}

function handleEditCurrentPage() {
  // 打开在线编辑面板
  editInstruction.value = ''
  editStatus.value = 'idle'
  editErrorMsg.value = ''
  contextUseTemplate.value = false
  contextMaterialIds.value = []
  contextUploadedFiles.value = []
  resetRegionSelection()
  showEditPanel.value = true
  showVersionPanel.value = false
}

async function handleRegenerateCurrentPage() {
  if (!pptStore.projectId || !currentPage.value || isGenerating.value) return

  isGenerating.value = true
  try {
    await startImageGeneration([currentPage.value.id])
  } catch (error) {
    console.error('重新生成页面图片失败:', error)
    alert(error?.message || '重新生成页面图片失败，请稍后重试')
  } finally {
    isGenerating.value = false
  }
}

async function handleRefreshPreview() {
  if (!pptStore.projectId) return
  try {
    await reloadPreviewData({ includeMaterials: true })
  } catch (error) {
    console.error('refresh preview failed:', error)
    alert('刷新失败，请稍后重试')
  }
}

async function openProjectSettingsModal() {
  if (!pptStore.projectId) return
  const currentAspectRatio = pptStore.projectSettings?.aspect_ratio || '16:9'
  const input = window.prompt(
    '设置图片比例（可选：16:9、4:3、1:1、9:16、3:4）',
    currentAspectRatio
  )
  if (!input) return
  const value = input.trim()
  const allowed = ['16:9', '4:3', '1:1', '9:16', '3:4']
  if (!allowed.includes(value)) {
    alert('比例无效，请输入 16:9、4:3、1:1、9:16 或 3:4')
    return
  }
  try {
    await updateProjectSettings(pptStore.projectId, { aspect_ratio: value })
    pptStore.projectSettings = { ...pptStore.projectSettings, aspect_ratio: value }
    alert('项目设置已保存')
  } catch (error) {
    console.error('save preview settings failed:', error)
    alert('保存设置失败，请稍后重试')
  }
}

async function handleExport(type) {
  if (!pptStore.projectId) return
  isExporting.value = true
  showExportMenu.value = false
  try {
    const res = await authFetch(`/api/v1/ppt/projects/${pptStore.projectId}/export/${type}`)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body?.detail || `导出失败 ${res.status}`)
    }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${pptStore.projectData?.title || 'presentation'}.${type}`
    a.click()
    setTimeout(() => URL.revokeObjectURL(a.href), 10000)
  } catch (e) {
    console.error(`导出${type}失败:`, e)
    alert(`导出失败：${e.message}`)
  } finally {
    isExporting.value = false
  }
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
          await _downloadExportResult(task.result, pptStore.projectData?.title || 'presentation', 'pptx')
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
          await _downloadExportResult(task.result, pptStore.projectData?.title || 'presentation', 'zip')
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

// 统一导出结果下载（兼容 OSS URL 和 is_local 本地路径）
async function _downloadExportResult(result, basename, ext) {
  const url = result?.url
  if (!url) return
  if (result?.is_local) {
    // OSS 不可达，文件在本地：通过带鉴权的接口下载
    const filename = url.replace(/\\/g, '/').split('/').pop()
    try {
      const res = await authFetch(`/api/v1/ppt/exports/local/${encodeURIComponent(filename)}`)
      if (!res.ok) { alert('本地文件下载失败，OSS 服务不可用'); return }
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${basename}.${ext}`
      a.click()
      setTimeout(() => URL.revokeObjectURL(a.href), 10000)
    } catch (e) {
      alert('下载失败：' + e.message)
    }
  } else {
    window.open(url, '_blank')
  }
}

// -------- 单页在线编辑 --------

async function submitEditInstruction() {
  if (!editInstruction.value.trim() || !currentPage.value?.id) return
  editStatus.value = 'processing'
  editErrorMsg.value = ''
  editTaskId.value = null
  try {
    const contextImages = {
      use_template: contextUseTemplate.value,
      desc_image_urls: [],
      uploaded_image_ids: contextMaterialIds.value.map(String),
      uploaded_files: contextUploadedFiles.value,
      selection_bbox: selectionBBox.value
    }
    const res = await editPageImage(pptStore.projectId, currentPage.value.id, editInstruction.value, contextImages)
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
        await reloadPreviewData()
        if (showVersionPanel.value) {
          await loadVersions()
        }
      } else if (task.status === 'FAILED') {
        clearInterval(editPollTimer)
        editStatus.value = 'error'
        editErrorMsg.value = task.result?.error || '编辑失败，请重试'
        await reloadPreviewData()
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
  contextUploadedFiles.value = []
  resetRegionSelection()
  if (showVersionPanel.value) {
    await loadVersions()
  }
})

onUnmounted(() => {
  clearInterval(editPollTimer)
  clearInterval(editableExportPollTimer)
  clearInterval(imagesExportPollTimer)
  clearInterval(materialPollTimer)
  contextUploadedFileUrls.value.forEach(url => URL.revokeObjectURL(url))
  unbindHeaderQuickActions()
})

// -------- 模板切换逻辑 --------

async function openTemplateModal() {
  showTemplateModal.value = true
  templatesLoading.value = true
  try {
    const [presets, userTpls] = await Promise.all([getPresetTemplates(), getUserTemplates()])
    presetTemplates.value = Array.isArray(presets) ? presets : []
    userTemplatesList.value = Array.isArray(userTpls) ? userTpls : []
  } catch (e) {
    console.error('加载模板失败:', e)
  } finally {
    templatesLoading.value = false
  }
}

async function selectTemplate(templateUrl) {
  if (!pptStore.projectId || !templateUrl) return
  try {
    await updateProjectSettings(pptStore.projectId, {
      template_image_url: templateUrl,
      template_oss_key: null
    })
    const nextSettings = { ...pptStore.projectSettings, template_image_url: templateUrl }
    delete nextSettings.template_oss_key
    pptStore.projectSettings = nextSettings
    showTemplateModal.value = false
  } catch (e) {
    console.error('设置模板失败:', e)
    alert('设置模板失败：' + e.message)
  }
}

async function handleUploadTemplate(file) {
  if (!pptStore.projectId || !file) return
  try {
    const res = await uploadProjectTemplate(pptStore.projectId, file)
    pptStore.projectSettings = {
      ...pptStore.projectSettings,
      template_image_url: res.template_url || res.url,
      template_oss_key: res.oss_key || pptStore.projectSettings?.template_oss_key
    }
    // reload template lists
    await openTemplateModal()
  } catch (e) {
    console.error('上传模板失败:', e)
    alert('上传模板失败：' + e.message)
  }
}

// -------- renovation 单页再生 --------

async function handleRenovateCurrentPage() {
  if (!pptStore.projectId || !currentPage.value?.id || renovationRegenerating.value) return
  renovationRegenerating.value = true
  try {
    await regeneratePageRenovation(pptStore.projectId, currentPage.value.id)
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (e) {
    console.error('翻新再生成失败:', e)
    alert('翻新再生成失败：' + e.message)
  } finally {
    renovationRegenerating.value = false
  }
}

// -------- 素材库逻辑 --------

async function loadMaterials() {
  if (!pptStore.projectId) return
  try {
    const res = await getMaterials(pptStore.projectId)
    materials.value = Array.isArray(res) ? res : (res?.materials || [])
  } catch (e) {
    console.error('加载素材失败:', e)
  }
}

async function handleGenerateMaterial() {
  if (!materialPrompt.value.trim() || !pptStore.projectId) return
  materialGenerating.value = true
  try {
    const res = await generateMaterial(pptStore.projectId, materialPrompt.value.trim(), materialAspectRatio.value)
    materialTaskId.value = res.task_id || res.id || null
    if (materialTaskId.value) {
      _pollMaterialTask()
    } else {
      // 同步完成
      await loadMaterials()
      materialGenerating.value = false
      materialPrompt.value = ''
    }
  } catch (e) {
    console.error('生成素材失败:', e)
    materialGenerating.value = false
  }
}

function _pollMaterialTask() {
  clearInterval(materialPollTimer)
  materialPollTimer = setInterval(async () => {
    try {
      const task = await getTask(pptStore.projectId, materialTaskId.value)
      if (task.status === 'COMPLETED') {
        clearInterval(materialPollTimer)
        materialGenerating.value = false
        materialPrompt.value = ''
        await loadMaterials()
      } else if (task.status === 'FAILED') {
        clearInterval(materialPollTimer)
        materialGenerating.value = false
      }
    } catch (e) {
      clearInterval(materialPollTimer)
      materialGenerating.value = false
    }
  }, 2000)
}

function toggleMaterialPanel() {
  showMaterialPanel.value = !showMaterialPanel.value
  showEditPanel.value = false
  showVersionPanel.value = false
}

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
        <button class="icon-btn" :class="{ active: showTemplateModal }" title="更换模板" @click="openTemplateModal">
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
            <button class="export-menu-item" :disabled="isExporting" @click="handleExportAll">
              导出 PPTX
              <span v-if="isExporting" class="export-tag">下载中...</span>
            </button>
            <button class="export-menu-item" @click="handleExportEditable">
              导出可编辑 PPTX（Beta）
              <span v-if="editableExportStatus === 'processing'" class="export-tag">处理中...</span>
              <span v-else-if="editableExportStatus === 'done'" class="export-tag done">✓ 完成</span>
              <span v-else-if="editableExportStatus === 'error'" class="export-tag err">失败</span>
            </button>
            <button class="export-menu-item" :disabled="isExporting" @click="handleExportPdf">
              导出 PDF
              <span v-if="isExporting" class="export-tag">下载中...</span>
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
                <img
                  :src="page.thumbnail"
                  :alt="page.title"
                  class="image-reveal revealed"
                >
              </template>
              <template v-else-if="page.status === 'generating'">
                <div class="thumbnail-generating">
                  <div class="shimmer-bg"></div>
                  <div class="thumb-spin-loader"></div>
                </div>
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
              :class="{ 'region-selecting': showEditPanel && isRegionSelectionMode }"
              :style="{ aspectRatio: currentAspectRatioStyle }"
              @mousedown="handleRegionPointerDown"
              @mousemove="handleRegionPointerMove"
              @mouseup="handleRegionPointerUp"
              @mouseleave="handleRegionPointerUp"
            >
              <template v-if="currentPage?.thumbnail">
                <button
                  v-if="showEditPanel"
                  class="region-select-btn"
                  type="button"
                  @mousedown.stop
                  @click.stop="toggleRegionSelectionMode"
                >
                  {{ isRegionSelectionMode ? '结束框选' : '框选编辑区域' }}
                </button>
                <div
                  v-if="showEditPanel && isRegionSelectionMode"
                  class="region-select-hint"
                >
                  在图片上拖动框选，裁剪结果会自动加入右侧参考图
                </div>
                <img
                  ref="previewImageRef"
                  :src="currentPage.imageUrl"
                  :alt="currentPage.title"
                  class="slide-image image-reveal revealed"
                  draggable="false"
                >
                <div
                  v-if="selectionRect && showEditPanel"
                  class="selection-rect"
                  :style="{
                    left: `${selectionRect.left}px`,
                    top: `${selectionRect.top}px`,
                    width: `${selectionRect.width}px`,
                    height: `${selectionRect.height}px`
                  }"
                />
              </template>
              <template v-else>
                <div v-if="currentPage?.status === 'generating'" class="slide-generating">
                  <div class="shimmer-bg"></div>
                  <div class="generating-content">
                    <div class="bouncing-indicator">
                      <span class="bounce-dot">&#9998;</span>
                      <span class="bounce-dot">&#10024;</span>
                      <span class="bounce-dot">&#9998;</span>
                    </div>
                    <p class="generating-text">正在创作中...</p>
                    <div class="generating-spin-wrapper">
                      <div class="spin-loader"></div>
                    </div>
                  </div>
                </div>
                <div v-else class="slide-placeholder">
                  <div class="placeholder-icon">🍌</div>
                  <p class="placeholder-text">尚未生成图片</p>
                  <button
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
                v-if="isRenovationMode"
                class="action-btn secondary"
                :disabled="renovationRegenerating || !currentPage?.id"
                @click="handleRenovateCurrentPage"
              >
                {{ renovationRegenerating ? '再生成中...' : '翻新再生成' }}
              </button>
              <button
                class="action-btn secondary"
                :class="{ active: showMaterialPanel }"
                @click="toggleMaterialPanel"
              >
                素材库
              </button>
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
            rows="4"
          />

          <!-- 参考上下文 -->
          <div class="context-section">
            <div class="context-label">参考上下文</div>
            <label class="context-row">
              <input type="checkbox" v-model="contextUseTemplate" :disabled="!currentTemplateUrl" />
              <span>使用当前模板图</span>
              <img v-if="currentTemplateUrl" :src="currentTemplateUrl" class="context-thumb" />
              <span v-else class="context-none">（未设置模板）</span>
            </label>
            <div v-if="materials.length > 0" class="context-materials">
              <div class="context-label" style="margin-top:6px">从素材库选参考图</div>
              <label
                v-for="mat in materials.slice(0, 8)"
                :key="mat.id"
                class="context-mat-row"
              >
                <input
                  type="checkbox"
                  :value="mat.id"
                  v-model="contextMaterialIds"
                />
                <img v-if="mat.url || mat.image_url" :src="mat.url || mat.image_url" class="context-thumb" />
                <span class="context-mat-label">{{ mat.title || mat.prompt || '素材' + mat.id }}</span>
              </label>
            </div>
            <div class="context-upload-actions">
              <button
                class="action-btn secondary small"
                type="button"
                @click="toggleRegionSelectionMode"
              >
                {{ isRegionSelectionMode ? '结束框选' : '框选参考图' }}
              </button>
              <label class="upload-context-btn">
                上传参考图
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  multiple
                  style="display:none"
                  @change="handleContextFileUpload"
                />
              </label>
            </div>
            <p v-if="isRegionSelectionMode" class="panel-hint muted">
              左侧大图已进入框选模式，拖动后会把选区自动加入参考图
            </p>
            <div v-if="selectionBBox" class="context-selection-card">
              <div class="context-selection-title">已选框选区域</div>
              <div class="context-selection-meta">{{ selectedRegionSummary }}</div>
              <button class="action-btn secondary small" type="button" @click="clearSelectedRegion">
                清除选区
              </button>
            </div>
            <div v-if="contextUploadedFiles.length > 0" class="context-upload-grid">
              <div
                v-for="(file, index) in contextUploadedFiles"
                :key="file.name + index"
                class="context-upload-card"
              >
                <img :src="contextUploadedFileUrls[index]" :alt="file.name" class="context-upload-thumb" />
                <button class="context-upload-remove" type="button" @click="removeContextUploadedFile(index)">×</button>
                <span class="context-upload-name" :title="file.name">{{ file.name }}</span>
              </div>
            </div>
          </div>

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

      <!-- 模板切换 Modal -->
      <div v-if="showTemplateModal" class="modal-overlay" @click.self="showTemplateModal = false">
        <div class="modal-box">
          <div class="modal-header">
            <span>更换模板</span>
            <button class="close-btn" @click="showTemplateModal = false">✕</button>
          </div>

          <!-- 当前模板 -->
          <div v-if="currentTemplateUrl" class="template-current">
            <div class="template-section-label">当前模板</div>
            <img :src="currentTemplateUrl" class="template-current-img" />
          </div>

          <div v-if="templatesLoading" class="panel-hint">加载中...</div>
          <template v-else>
            <!-- 预设模板 -->
            <div class="template-section-label">预设模板</div>
            <div class="template-grid">
              <div
                v-for="tpl in presetTemplates"
                :key="tpl.id"
                class="template-card"
                :class="{ selected: currentTemplateUrl === tpl.thumbnail }"
                @click="selectTemplate(tpl.thumbnail)"
              >
                <img :src="tpl.thumbnail" :alt="tpl.name" class="template-thumb" />
                <div class="template-name">{{ tpl.name }}</div>
                <div class="template-cat">{{ tpl.category }}</div>
              </div>
            </div>

            <!-- 用户模板 -->
            <div v-if="userTemplatesList.length > 0">
              <div class="template-section-label" style="margin-top:16px">我的模板</div>
              <div class="template-grid">
                <div
                  v-for="tpl in userTemplatesList"
                  :key="tpl.id"
                  class="template-card"
                  :class="{ selected: currentTemplateUrl === tpl.cover_url }"
                  @click="selectTemplate(tpl.cover_url)"
                >
                  <img v-if="tpl.cover_url" :src="tpl.cover_url" class="template-thumb" />
                  <div v-else class="template-thumb-placeholder">无图</div>
                  <div class="template-name">{{ tpl.name }}</div>
                </div>
              </div>
            </div>

            <!-- 上传自定义模板 -->
            <div class="template-upload-row">
              <label class="upload-template-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                上传自定义模板
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  style="display:none"
                  @change="e => handleUploadTemplate(e.target.files[0])"
                />
              </label>
            </div>
          </template>
        </div>
      </div>

      <!-- 素材库面板 -->
      <aside v-if="showMaterialPanel" class="right-panel">
        <div class="panel-title">
          <span>AI 素材库</span>
          <button class="close-btn" @click="showMaterialPanel = false">✕</button>
        </div>

        <!-- 生成表单 -->
        <div class="material-generate-form">
          <textarea
            v-model="materialPrompt"
            class="edit-textarea"
            placeholder="描述你想要生成的素材，例如：蓝色抽象背景、箭头流程图..."
            :disabled="materialGenerating"
            rows="3"
          />
          <div class="material-ratio-row">
            <span class="ratio-label">比例</span>
            <div class="ratio-group">
              <button
                v-for="r in ['1:1', '16:9', '4:3']"
                :key="r"
                class="ratio-btn"
                :class="{ active: materialAspectRatio === r }"
                @click="materialAspectRatio = r"
              >{{ r }}</button>
            </div>
          </div>
          <button
            class="action-btn primary full"
            :disabled="!materialPrompt.trim() || materialGenerating"
            @click="handleGenerateMaterial"
          >
            {{ materialGenerating ? 'AI生成中...' : 'AI 生成素材' }}
          </button>
          <div v-if="materialGenerating" class="material-generating-hint">
            <div class="spinner-small"></div>
            <span>素材生成中，完成后自动刷新</span>
          </div>
        </div>

        <!-- 素材画廊 -->
        <div class="material-gallery">
          <div v-if="materials.length === 0 && !materialGenerating" class="panel-hint">
            暂无素材，请先 AI 生成或上传图片
          </div>
          <div v-else class="material-grid">
            <div
              v-for="mat in materials"
              :key="mat.id"
              class="material-card"
            >
              <img v-if="mat.url || mat.image_url" :src="mat.url || mat.image_url" :alt="mat.title || mat.prompt || '素材'" class="material-img" />
              <div v-else class="material-img-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24">
                  <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
                </svg>
              </div>
              <div class="material-card-meta">
                <span class="material-title" :title="mat.title || mat.prompt">{{ mat.title || mat.prompt || '素材' }}</span>
              </div>
            </div>
          </div>
        </div>
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

.preview-slide.region-selecting {
  cursor: crosshair;
}

.slide-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  user-select: none;
}

.region-select-btn {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 3;
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.92);
  color: #1e3a8a;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
}

.region-select-hint {
  position: absolute;
  left: 12px;
  bottom: 12px;
  z-index: 3;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.72);
  color: white;
  font-size: 12px;
  line-height: 1.4;
}

.selection-rect {
  position: absolute;
  z-index: 2;
  border: 2px solid #2563eb;
  background: rgba(37, 99, 235, 0.14);
  box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.12);
  pointer-events: none;
}

/* ---- 图片生成动画 ---- */
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

.shimmer-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, #f0f4ff 0%, #f0f4ff 40%, #e0ebff 50%, #f0f4ff 60%, #f0f4ff 100%);
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.slide-generating {
  width: 100%;
  height: 100%;
  min-height: 300px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 12px;
}

.generating-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.bouncing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bounce-dot {
  display: inline-block;
  font-size: 24px;
  animation: bounce 1.2s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
}

.bounce-dot:nth-child(2) {
  animation-delay: 0.15s;
  font-size: 28px;
}

.bounce-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-14px); }
}

.generating-text {
  color: #475569;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  animation: textPulse 2s ease-in-out infinite;
}

@keyframes textPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.generating-spin-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spin-loader {
  width: 28px;
  height: 28px;
  border: 3px solid #e0ebff;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.thumbnail-generating {
  width: 100%;
  height: 100%;
  min-height: 80px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 6px;
}

.thumb-spin-loader {
  position: relative;
  z-index: 1;
  width: 20px;
  height: 20px;
  border: 2.5px solid #dbeafe;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.image-reveal {
  opacity: 0;
  transform: scale(0.95);
  filter: blur(8px);
  transition: all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.image-reveal.revealed {
  opacity: 1;
  transform: scale(1);
  filter: blur(0);
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

/* Material panel */
.material-generate-form {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.material-ratio-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
}

.ratio-label {
  font-size: 12px;
  color: #64748b;
  flex-shrink: 0;
}

.ratio-group {
  display: flex;
  gap: 4px;
}

.ratio-btn {
  padding: 3px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.ratio-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.material-generating-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  margin-top: 8px;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.material-gallery {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.material-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.15s;
  cursor: pointer;
}

.material-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.material-img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  display: block;
  background: #f1f5f9;
}

.material-img-placeholder {
  width: 100%;
  aspect-ratio: 1;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.material-card-meta {
  padding: 4px 6px;
  background: #fafafa;
}

.material-title {
  font-size: 11px;
  color: #64748b;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Context images in edit panel */
.context-section {
  padding: 10px 16px;
  border-top: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 8px;
}

.context-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.context-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #374151;
  cursor: pointer;
  padding: 2px 0;
}

.context-row input[type=checkbox] { cursor: pointer; }
.context-thumb { width: 28px; height: 18px; object-fit: cover; border-radius: 3px; border: 1px solid #e5e7eb; }
.context-none { font-size: 11px; color: #94a3b8; }

.context-materials {
  margin-top: 4px;
  max-height: 120px;
  overflow-y: auto;
}

.context-mat-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #374151;
  cursor: pointer;
  padding: 2px 0;
}

.context-mat-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.context-upload-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.upload-context-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.context-upload-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px;
}

.context-selection-card {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #bfdbfe;
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
}

.context-selection-title {
  font-size: 0;
  color: transparent;
}

.context-selection-title::after {
  content: 'Selected Region';
  font-size: 12px;
  font-weight: 600;
  color: #1e3a8a;
}

.context-selection-meta {
  margin: 4px 0 10px;
  font-size: 12px;
  color: #475569;
}

.context-upload-card {
  position: relative;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  padding: 6px;
}

.context-upload-thumb {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.context-upload-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.82);
  color: white;
  cursor: pointer;
}

.context-upload-name {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Template modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-box {
  background: white;
  border-radius: 16px;
  width: 680px;
  max-width: 95vw;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  padding: 24px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
}

.template-current {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.template-current-img {
  width: 120px;
  height: 80px;
  object-fit: cover;
  border-radius: 8px;
  border: 2px solid #3b82f6;
  margin-top: 8px;
}

.template-section-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 10px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 10px;
  margin-bottom: 8px;
}

.template-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.15s;
}

.template-card:hover { border-color: #93c5fd; box-shadow: 0 2px 8px rgba(59,130,246,0.15); }
.template-card.selected { border-color: #3b82f6; }

.template-thumb {
  width: 100%;
  aspect-ratio: 16/9;
  object-fit: cover;
  display: block;
  background: #f1f5f9;
}

.template-thumb-placeholder {
  width: 100%;
  aspect-ratio: 16/9;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #94a3b8;
}

.template-name {
  font-size: 11px;
  font-weight: 500;
  color: #374151;
  padding: 4px 6px 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-cat {
  font-size: 10px;
  color: #94a3b8;
  padding: 0 6px 4px;
}

.template-upload-row {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.upload-template-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px dashed #e5e7eb;
  border-radius: 8px;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.upload-template-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}
</style>
