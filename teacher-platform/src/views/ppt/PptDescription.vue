<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { refineDescriptions } from '@/api/ppt'

const pptStore = usePptStore()

const refineInput = ref('')
const isGenerating = ref(false)
const isRefining = ref(false)
const showSettings = ref(false)
const showRequirements = ref(false)
const requirements = ref('')

// Extra fields configuration
const extraFields = ref([
  { key: 'visual_element', label: '视觉元素', active: true, icon: 'image', image_prompt: true },
  { key: 'visual_focus', label: '视觉焦点', active: true, icon: 'focus', image_prompt: true },
  { key: 'layout', label: '排版布局', active: true, icon: 'layout', image_prompt: true },
  { key: 'notes', label: '演讲者备注', active: true, icon: 'message', image_prompt: false }
])

// Field management
const newFieldLabel = ref('')
const showAddField = ref(false)
const dragSrcIndex = ref(null)

function addField() {
  const label = newFieldLabel.value.trim()
  if (!label) return
  const key = 'custom_' + Date.now()
  extraFields.value.push({ key, label, active: true, icon: 'message', image_prompt: true })
  newFieldLabel.value = ''
  showAddField.value = false
}

function removeField(index) {
  extraFields.value.splice(index, 1)
}

function toggleFieldActive(index) {
  extraFields.value[index].active = !extraFields.value[index].active
}

function toggleFieldImagePrompt(index) {
  extraFields.value[index].image_prompt = !extraFields.value[index].image_prompt
}

function onFieldDragStart(e, index) {
  dragSrcIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
}

function onFieldDragOver(e, index) {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
}

function onFieldDrop(e, index) {
  e.preventDefault()
  if (dragSrcIndex.value === null || dragSrcIndex.value === index) return
  const arr = [...extraFields.value]
  const [moved] = arr.splice(dragSrcIndex.value, 1)
  arr.splice(index, 0, moved)
  extraFields.value = arr
  dragSrcIndex.value = null
}

// Generation mode
const generationMode = ref('stream')

// detail_level: concise | default | detailed
// 从 projectSettings 读取，统一口径与后端 GenerateDescriptionsStreamRequest 一致
const DETAIL_LEVEL_MAP = {
  brief: 'concise',    // 兼容旧 settings 值
  normal: 'default',   // 兼容旧 settings 值
  concise: 'concise',
  default: 'default',
  detailed: 'detailed',
}
const detailLevel = ref(
  DETAIL_LEVEL_MAP[pptStore.projectSettings?.detail_level] || 'default'
)

// Pages data
const pages = ref([])

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
  pages.value = pptStore.outlinePages.map(p => {
    let displayDesc = p.description || ''
    if (displayDesc) {
      try {
        const parsed = JSON.parse(displayDesc)
        if (Array.isArray(parsed)) displayDesc = ''
      } catch (e) {}
    }
    return {
      id: p.id,
      pageNumber: p.pageNumber,
      title: p.title,
      description: displayDesc,
      status: displayDesc ? 'completed' : (p.status === 'generating' ? 'generating' : 'pending'),
      extraFields: {
        visual_element: p.visual_element || '',
        visual_focus: p.visual_focus || '',
        layout: p.layout || '',
        notes: p.notes || ''
      }
    }
  })
}

const completedCount = computed(() => {
  return pages.value.filter(p => p.status === 'completed').length
})

async function handleBatchGenerate() {
  if (!pptStore.projectId) return

  isGenerating.value = true
  try {
    await pptStore.generateDescriptionsStream(pptStore.projectId, {
      language: 'zh',
      detail_level: detailLevel.value
    })
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (error) {
    console.error('生成描述失败:', error)
  } finally {
    isGenerating.value = false
  }
}

async function handleRefine() {
  if (!refineInput.value.trim() || !pptStore.projectId) return

  isRefining.value = true
  try {
    await refineDescriptions(pptStore.projectId, refineInput.value)
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (error) {
    console.error('优化描述失败:', error)
  } finally {
    isRefining.value = false
  }
}

function toggleField(fieldKey) {
  const field = extraFields.value.find(f => f.key === fieldKey)
  if (field) {
    field.active = !field.active
  }
}

function goToOutline() {
  pptStore.setPhase('outline')
}

function goToPreview() {
  pptStore.setPhase('preview')
}

// Card editing
const editingCardId = ref(null)
const editDescription = ref('')
const editExtraFields = ref({})

function startEdit(page) {
  editingCardId.value = page.id
  editDescription.value = page.description || ''
  editExtraFields.value = { ...page.extraFields }
}

function cancelEdit() {
  editingCardId.value = null
}

async function saveCard(pageIndex) {
  const page = pages.value[pageIndex]
  page.description = editDescription.value
  page.extraFields = { ...editExtraFields.value }
  page.status = editDescription.value ? 'completed' : 'pending'

  editingCardId.value = null

  // Save to backend
  if (pptStore.projectId && page.id <= 1000000000) {
    try {
      await pptStore.updatePage(pptStore.projectId, page.id, {
        description: editDescription.value,
        ...editExtraFields.value
      })
    } catch (e) {
      console.error('保存描述失败:', e)
    }
  }
}

function exportOutline(pageIndex) {
  const page = pages.value[pageIndex]
  const outlineData = {
    title: page.title,
    description: page.description,
    pageNumber: page.pageNumber,
    extraFields: {
      visual_element: page.extraFields?.visual_element || '',
      visual_focus: page.extraFields?.visual_focus || '',
      layout: page.extraFields?.layout || '',
      notes: page.extraFields?.notes || ''
    }
  }

  // Generate markdown format
  const markdown = `# ${outlineData.title}\n\n**页码**: ${outlineData.pageNumber}\n\n## 页面描述\n\n${outlineData.description || '（暂无描述）'}\n\n## 视觉元素\n\n${outlineData.extraFields.visual_element || '（未设置）'}\n\n## 视觉焦点\n\n${outlineData.extraFields.visual_focus || '（未设置）'}\n\n## 排版布局\n\n${outlineData.extraFields.layout || '（未设置）'}\n\n## 演讲者备注\n\n${outlineData.extraFields.notes || '（未设置）'}\n`

  // Create and download file
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `大纲_${outlineData.pageNumber}_${outlineData.title.replace(/[<>:"/\\|?*]/g, '')}.md`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

async function regeneratePage(pageIndex) {
  const page = pages.value[pageIndex]
  if (!page || !page.id || !pptStore.projectId) return

  isGenerating.value = true
  try {
    await pptStore.generateDescriptionsStream(pptStore.projectId, {
      language: 'zh',
      detail_level: detailLevel.value
    })
    await pptStore.fetchPages(pptStore.projectId)
    syncPages()
  } catch (error) {
    console.error('重新生成描述失败:', error)
  } finally {
    isGenerating.value = false
  }
}

// Field icons
function getFieldIcon(iconType) {
  const icons = {
    image: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
    focus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>`,
    layout: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`,
    message: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`
  }
  return icons[iconType] || icons.message
}
</script>

<template>
  <div class="ppt-description">
    <!-- 顶栏 -->
    <header class="header">
      <div class="header-inner">
        <!-- 左侧 -->
        <div class="header-left">
          <button class="back-btn" @click="goToOutline">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
          <div class="logo">
            <span class="logo-text">AI备课</span>
          </div>
          <span class="header-divider">|</span>
          <span class="header-title">编辑页面描述</span>
        </div>

        <!-- 中间：AI 修改输入框 -->
        <div class="header-center">
          <div class="ai-input-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="ai-icon">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
            </svg>
            <input
              v-model="refineInput"
              type="text"
              class="ai-input"
              placeholder="例如：让描述更详细、删除第2页的某个要点、强调XXX的重要性... · Ctrl+Enter提交"
              @keydown.ctrl.enter="handleRefine"
            >
          </div>
        </div>

        <!-- 右侧 -->
        <div class="header-right">
          <button class="nav-btn" @click="goToOutline">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            上一步
          </button>
          <button class="nav-btn primary" @click="goToPreview">
            生成图片
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="action-bar-inner">
        <button class="action-btn primary" :disabled="isGenerating" @click="handleBatchGenerate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
          </svg>
          {{ isGenerating ? '生成中...' : '批量生成描述' }}
        </button>

        <!-- 设置下拉 -->
        <div class="settings-dropdown">
          <button class="action-btn secondary" :class="{ open: showSettings }" @click="showSettings = !showSettings">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            设置
            <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <path d="M6 9l6 6 6-6"/>
            </svg>
          </button>

          <div v-show="showSettings" class="settings-panel" :class="{ open: showSettings }">
            <div class="settings-section">
              <div class="settings-label">生成模式</div>
              <div class="mode-toggle">
                <button
                  class="mode-toggle-btn"
                  :class="{ active: generationMode === 'stream' }"
                  @click="generationMode = 'stream'"
                >
                  流式
                </button>
                <button
                  class="mode-toggle-btn"
                  :class="{ active: generationMode === 'parallel' }"
                  @click="generationMode = 'parallel'"
                >
                  并行
                </button>
              </div>
            </div>

            <div class="settings-section">
              <div class="settings-label">描述详细程度</div>
              <div class="mode-toggle">
                <button
                  class="mode-toggle-btn"
                  :class="{ active: detailLevel === 'concise' }"
                  @click="detailLevel = 'concise'"
                  title="简洁：每页约1-2句核心描述"
                >
                  简洁
                </button>
                <button
                  class="mode-toggle-btn"
                  :class="{ active: detailLevel === 'default' }"
                  @click="detailLevel = 'default'"
                  title="适中：平衡细节与简洁"
                >
                  适中
                </button>
                <button
                  class="mode-toggle-btn"
                  :class="{ active: detailLevel === 'detailed' }"
                  @click="detailLevel = 'detailed'"
                  title="详细：包含更多视觉与布局细节"
                >
                  详细
                </button>
              </div>
            </div>

            <div class="settings-section">
              <div class="settings-label">额外字段</div>
              <div class="fields-list">
                <div
                  v-for="(field, idx) in extraFields"
                  :key="field.key"
                  class="field-row"
                  :class="{ inactive: !field.active }"
                  draggable="true"
                  @dragstart="onFieldDragStart($event, idx)"
                  @dragover="onFieldDragOver($event, idx)"
                  @drop="onFieldDrop($event, idx)"
                >
                  <span class="field-drag-handle" title="拖拽排序">⠿</span>
                  <span class="field-row-label">{{ field.label }}</span>
                  <button
                    class="field-icon-btn"
                    :class="{ active: field.active }"
                    @click="toggleFieldActive(idx)"
                    :title="field.active ? '点击隐藏' : '点击显示'"
                  >
                    <svg v-if="field.active" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  </button>
                  <button
                    class="field-icon-btn"
                    :class="{ 'img-prompt-on': field.image_prompt }"
                    @click="toggleFieldImagePrompt(idx)"
                    :title="field.image_prompt ? '参与图片生成（点击关闭）' : '不参与图片生成（点击开启）'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                  </button>
                  <button class="field-icon-btn delete" @click="removeField(idx)" title="删除字段">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              </div>
              <!-- 添加字段 -->
              <div v-if="showAddField" class="add-field-row">
                <input
                  v-model="newFieldLabel"
                  class="add-field-input"
                  placeholder="字段名称"
                  @keydown.enter="addField"
                  @keydown.escape="showAddField = false"
                  autofocus
                />
                <button class="field-icon-btn" @click="addField" title="确认添加">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="20 6 9 17 4 12"/></svg>
                </button>
                <button class="field-icon-btn delete" @click="showAddField = false; newFieldLabel = ''" title="取消">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
              <button v-else class="add-field-btn" @click="showAddField = true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                添加字段
              </button>
            </div>
          </div>
        </div>

        <button class="action-btn secondary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          导入/导出
        </button>

        <span class="page-count">{{ completedCount }} / {{ pages.length }} 页已完成</span>
      </div>
    </div>

    <!-- 描述生成要求 -->
    <div class="requirements-section">
      <button class="requirements-toggle" :class="{ open: showRequirements }" @click="showRequirements = !showRequirements">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
        <span>描述生成要求</span>
        <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>
      <div class="requirements-content" :class="{ open: showRequirements }">
        <div class="requirements-inner">
          <textarea
            v-model="requirements"
            class="requirements-textarea"
            placeholder="例如：每页描述控制在100字以内、多使用数据和案例、强调关键指标..."
          ></textarea>
        </div>
      </div>
    </div>

    <!-- 主内容区 - 3列网格 -->
    <main class="main-content">
      <div v-if="pages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="40" height="40">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <h3 class="empty-title">还没有页面</h3>
        <p class="empty-desc">请先返回大纲编辑页面添加页面</p>
      </div>

      <div v-else class="description-grid">
        <div
          v-for="(page, index) in pages"
          :key="page.id"
          class="desc-card"
          :class="{
            generating: page.status === 'generating',
            editing: editingCardId === page.id
          }"
        >
          <!-- 卡片头部 -->
          <div class="desc-card-header">
            <div class="header-left">
              <span class="page-badge">第{{ page.pageNumber }}页</span>
              <span v-if="index === 0" class="cover-badge">封面</span>
              <span
                class="status-badge"
                :class="{
                  completed: page.status === 'completed',
                  generating: page.status === 'generating',
                  pending: page.status === 'pending' || !page.status
                }"
              >
                {{ page.status === 'completed' ? '已完成' : page.status === 'generating' ? '生成中...' : '待生成' }}
              </span>
            </div>
            <div class="header-actions" v-if="editingCardId !== page.id">
              <button class="action-icon-btn edit" @click="startEdit(page)" title="编辑">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button class="action-icon-btn refresh" @click="regeneratePage(index)" :disabled="isGenerating" title="重新生成">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <polyline points="23 4 23 10 17 10"/>
                  <polyline points="1 20 1 14 7 14"/>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- 卡片内容 - 查看模式 -->
          <template v-if="editingCardId !== page.id">
            <div class="desc-card-body">
              <h4 class="desc-title">{{ page.title }}</h4>

              <div v-if="page.description" class="desc-content">
                <p>{{ page.description }}</p>
              </div>
              <div v-else class="desc-empty">
                此页面的详细描述尚未生成，请点击"批量生成描述"按钮来生成内容。
              </div>

              <!-- 额外字段 -->
              <div v-if="extraFields.some(f => f.active)" class="desc-extra-fields">
                <template v-for="field in extraFields.filter(f => f.active)" :key="field.key">
                  <div v-if="page.extraFields[field.key]" class="extra-field">
                    <span class="extra-field-label">
                      <span v-html="getFieldIcon(field.icon)"></span>
                      {{ field.label }}
                    </span>
                    <span class="extra-field-value">{{ page.extraFields[field.key] }}</span>
                  </div>
                </template>
              </div>
            </div>
          </template>

          <!-- 卡片内容 - 编辑模式 -->
          <template v-else>
            <div class="edit-card-body">
              <div class="edit-section">
                <label class="edit-label">页面描述</label>
                <textarea
                  v-model="editDescription"
                  class="edit-textarea"
                  placeholder="输入页面描述..."
                  rows="5"
                ></textarea>
              </div>

              <div v-for="field in extraFields.filter(f => f.active)" :key="field.key" class="edit-section">
                <label class="edit-label">{{ field.label }}</label>
                <textarea
                  v-model="editExtraFields[field.key]"
                  class="edit-textarea small"
                  :placeholder="field.label"
                  rows="2"
                ></textarea>
              </div>

              <div class="edit-actions">
                <button class="cancel-btn" @click="cancelEdit">取消</button>
                <button class="save-btn" @click="exportOutline(index)">导出大纲</button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.ppt-description {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 25%, #E0F2FE 50%, #F0F9FF 75%, #F5F3FF 100%);
}

/* Header */
.header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 10px 20px;
  flex-shrink: 0;
}

.header-inner {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.back-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #f8fafc;
  color: #1e293b;
}

.logo {
  display: flex;
  align-items: center;
  gap: 6px;
}

.logo-icon {
  font-size: 20px;
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

.header-center {
  flex: 1;
  max-width: 600px;
}

.ai-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 6px 12px;
}

.ai-icon {
  width: 16px;
  height: 16px;
  color: #3b82f6;
  flex-shrink: 0;
}

.ai-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  font-family: inherit;
  min-width: 0;
}

.ai-input::placeholder {
  color: #94a3b8;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.nav-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #e5e7eb;
  background: white;
  color: #1e293b;
  transition: all 0.2s;
  font-family: inherit;
}

.nav-btn:hover {
  background: #f8fafc;
}

.nav-btn.primary {
  background: #3b82f6;
  color: white;
  border: none;
}

.nav-btn.primary:hover {
  background: #2563eb;
}

/* Action Bar */
.action-bar {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 12px 20px;
  flex-shrink: 0;
}

.action-bar-inner {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  font-family: inherit;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
  border: none;
}

.action-btn.primary:hover:not(:disabled) {
  background: #2563eb;
}

.action-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.secondary {
  background: white;
  color: #1e293b;
  border: 1px solid #e5e7eb;
}

.action-btn.secondary:hover {
  background: #f8fafc;
}

.action-btn .chevron {
  transition: transform 0.2s;
}

.action-btn.open .chevron {
  transform: rotate(180deg);
}

.page-count {
  margin-left: auto;
  font-size: 13px;
  color: #94a3b8;
}

/* Settings Dropdown */
.settings-dropdown {
  position: relative;
}

.settings-panel {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  width: 320px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  padding: 16px;
  z-index: 50;
  display: none;
  max-height: 70vh;
  overflow-y: auto;
}

.settings-panel.open {
  display: block;
}

.settings-section {
  margin-bottom: 16px;
}

.settings-section:last-child {
  margin-bottom: 0;
}

.settings-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  margin-bottom: 8px;
}

.mode-toggle {
  display: flex;
  gap: 4px;
}

.mode-toggle-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: #f8fafc;
  color: #64748b;
  transition: all 0.2s;
  font-family: inherit;
}

.mode-toggle-btn.active {
  background: #3b82f6;
  color: white;
}

.fields-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.15s;
}

.field-row:hover {
  background: #f1f5f9;
}

.field-row.inactive {
  opacity: 0.5;
}

.field-drag-handle {
  color: #94a3b8;
  cursor: grab;
  font-size: 14px;
  line-height: 1;
  flex-shrink: 0;
}

.field-row-label {
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-icon-btn {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  transition: all 0.15s;
  flex-shrink: 0;
  padding: 0;
}

.field-icon-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

.field-icon-btn.active {
  color: #3b82f6;
}

.field-icon-btn.img-prompt-on {
  color: #f59e0b;
}

.field-icon-btn.delete:hover {
  background: #fee2e2;
  color: #ef4444;
}

.add-field-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
}

.add-field-input {
  flex: 1;
  padding: 5px 8px;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  font-size: 12px;
  outline: none;
  font-family: inherit;
}

.add-field-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px dashed #e5e7eb;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
  width: 100%;
  justify-content: center;
}

.add-field-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}

/* Requirements Section */
.requirements-section {
  background: white;
  border-bottom: 1px solid #e5e7eb;
}

.requirements-toggle {
  width: 100%;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.2s;
  font-family: inherit;
}

.requirements-toggle:hover {
  background: #f8fafc;
  color: #64748b;
}

.requirements-toggle .chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.requirements-toggle.open .chevron {
  transform: rotate(180deg);
}

.requirements-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.requirements-content.open {
  max-height: 300px;
}

.requirements-inner {
  padding: 0 20px 16px;
}

.requirements-textarea {
  width: 100%;
  min-height: 80px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  outline: none;
  font-family: inherit;
}

.requirements-textarea:focus {
  border-color: #3b82f6;
}

/* Main Content */
.main-content {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.description-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 1600px;
  margin: 0 auto;
}

@media (max-width: 1200px) {
  .description-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .description-grid {
    grid-template-columns: 1fr;
  }
}

/* Description Card */
.desc-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  border: 2px solid transparent;
  transition: all 0.2s;
  overflow: hidden;
}

.desc-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

.desc-card.generating {
  opacity: 0.7;
}

.desc-card.editing {
  border-color: #3b82f6;
}

.desc-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #fafafa;
  border-bottom: 1px solid #f1f5f9;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-badge {
  padding: 3px 8px;
  background: #dbeafe;
  color: #3b82f6;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.cover-badge {
  padding: 3px 8px;
  background: #FEF3C7;
  color: #92400e;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.status-badge.completed {
  background: #d1fae5;
  color: #059669;
}

.status-badge.generating {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.pending {
  background: #f1f5f9;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.action-icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  transition: all 0.2s;
}

.action-icon-btn:hover:not(:disabled) {
  background: #f1f5f9;
}

.action-icon-btn.edit:hover {
  color: #3b82f6;
  background: #dbeafe;
}

.action-icon-btn.refresh:hover:not(:disabled) {
  color: #3b82f6;
  background: #dbeafe;
}

.action-icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Card Body */
.desc-card-body {
  padding: 14px;
}

.desc-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.desc-content {
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.desc-content p {
  margin: 0;
}

.desc-empty {
  font-size: 13px;
  color: #94a3b8;
  font-style: italic;
}

.desc-extra-fields {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.extra-field {
  display: flex;
  gap: 8px;
}

.extra-field-label {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 70px;
}

.extra-field-value {
  font-size: 12px;
  color: #64748b;
  flex: 1;
}

/* Edit Card Body */
.edit-card-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.edit-label {
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
}

.edit-textarea {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  resize: vertical;
  outline: none;
  font-family: inherit;
  line-height: 1.5;
}

.edit-textarea:focus {
  border-color: #3b82f6;
}

.edit-textarea.small {
  min-height: 50px;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.cancel-btn {
  padding: 8px 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #64748b;
  font-family: inherit;
}

.cancel-btn:hover {
  background: #e5e7eb;
}

.save-btn {
  padding: 8px 14px;
  background: #3b82f6;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  color: white;
  font-family: inherit;
}

.save-btn:hover {
  background: #2563eb;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: #dbeafe;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  color: #3b82f6;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #64748b;
  max-width: 400px;
  margin: 0 auto;
  line-height: 1.6;
}
</style>
