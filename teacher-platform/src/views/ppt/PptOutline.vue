<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { generateOutlineStream, createPage, deletePage, updatePage, reorderPages, refineOutline } from '@/api/ppt'

const pptStore = usePptStore()

const ideaPrompt = ref('')        // 左侧构想框 - 显示意图摘要
const topAiPrompt = ref('')       // 顶部AI优化框 - 仅用于手动修改大纲
const isGenerating = ref(false)
const isRefining = ref(false)
const selectedCardId = ref(null)
const showRequirements = ref(false)
const requirements = ref('')
const isPanelOpen = ref(true)
const isInputDirty = ref(false)
const saveTimer = ref(null)
const outlinePages = ref([])

// 按part分组的结构化数据（用于展示带分组的目录）
const groupedPages = computed(() => {
  const groups = []
  const partMap = new Map()

  for (const page of outlinePages.value) {
    const partKey = page.part || '__no_part__'
    if (!partMap.has(partKey)) {
      const group = { part: page.part || '', pages: [] }
      partMap.set(partKey, group)
      groups.push(group)
    }
    partMap.get(partKey).pages.push(page)
  }
  return groups
})

// Simplified page data structure
onMounted(async () => {
  if (pptStore.projectId) {
    // 加载已确认的意图摘要（如果store中没有，从后端获取）
    if (!pptStore.confirmedIntent || Object.keys(pptStore.confirmedIntent).length === 0) {
      await pptStore.fetchIntent(pptStore.projectId)
    }

    // 构建意图摘要用于左侧构想框
    const confirmedIntent = pptStore.confirmedIntent
    if (confirmedIntent && Object.keys(confirmedIntent).length > 0) {
      ideaPrompt.value = buildIntentDisplay(confirmedIntent)
    }

    await pptStore.fetchPages(pptStore.projectId)
    syncOutlinePages()

    // 如果有已确认的意图摘要但还没有大纲，自动生成
    if (confirmedIntent && Object.keys(confirmedIntent).length > 0 && outlinePages.value.length === 0) {
      const prompt = buildIntentPrompt(confirmedIntent)
      await handleGenerateOutline(prompt)
    }
  }
})

// Watch for store changes
watch(() => pptStore.outlinePages, () => {
  syncOutlinePages()
}, { deep: true })

function syncOutlinePages() {
  outlinePages.value = pptStore.outlinePages.map((p, index) => ({
    id: p.id,
    pageNumber: Number(p.pageNumber) || (index + 1),
    title: p.title,
    points: p.points || [],
    part: p.part || '',
    outline_content: p.outline_content || { title: p.title, points: p.points || [] }
  }))
}

const pageCount = computed(() => outlinePages.value.length)

// 构建意图摘要用于左侧构想框展示
function buildIntentDisplay(intent) {
  if (!intent || Object.keys(intent).length === 0) return ''
  const parts = []
  if (intent.topic) parts.push(`主题：${intent.topic}`)
  if (intent.audience) parts.push(`受众：${intent.audience}`)
  if (intent.goal) parts.push(`目标：${intent.goal}`)
  if (intent.duration) parts.push(`课时：${intent.duration}`)
  if (intent.constraints) parts.push(`页数：${intent.constraints}`)
  if (intent.style) parts.push(`风格：${intent.style}`)
  if (intent.interaction) parts.push(`互动：${intent.interaction}`)
  if (intent.extra) parts.push(`其他：${intent.extra}`)
  return parts.join('\n\n')
}

// 构建生成大纲用的提示词
function buildIntentPrompt(intent) {
  if (!intent || Object.keys(intent).length === 0) return ''
  const parts = []
  if (intent.topic) parts.push(`主题：${intent.topic}`)
  if (intent.audience) parts.push(`受众：${intent.audience}`)
  if (intent.goal) parts.push(`目标：${intent.goal}`)
  if (intent.duration) parts.push(`课时：${intent.duration}`)
  if (intent.constraints) parts.push(`页数：${intent.constraints}`)
  if (intent.style) parts.push(`风格：${intent.style}`)
  if (intent.interaction) parts.push(`互动：${intent.interaction}`)
  if (intent.extra) parts.push(`其他：${intent.extra}`)
  return parts.join('\n')
}

async function handleGenerateOutline(prompt) {
  if (!prompt || !prompt.trim()) return

  isGenerating.value = true
  try {
    await pptStore.generateOutlineStream(pptStore.projectId, prompt)
    await pptStore.fetchPages(pptStore.projectId)
    syncOutlinePages()
  } catch (error) {
    console.error('生成大纲失败:', error)
  } finally {
    isGenerating.value = false
  }
}

async function handleRefineOutline() {
  if (!topAiPrompt.value.trim()) return

  isRefining.value = true
  try {
    await refineOutline(pptStore.projectId, topAiPrompt.value)
    await pptStore.fetchPages(pptStore.projectId)
    syncOutlinePages()
  } catch (error) {
    console.error('优化大纲失败:', error)
  } finally {
    isRefining.value = false
  }
}

function selectCard(id) {
  selectedCardId.value = id
}

function addPage() {
  const newPage = {
    id: Date.now(),
    pageNumber: outlinePages.value.length + 1,
    title: '新页面',
    points: [],
    part: '',
    outline_content: { title: '新页面', points: [] }
  }
  outlinePages.value.push(newPage)
}

async function deletePageById(id) {
  if (outlinePages.value.length <= 1) return

  if (id <= 1000000000 && pptStore.projectId) {
    try {
      await deletePage(pptStore.projectId, id)
    } catch (error) {
      console.error('删除页面失败:', error)
    }
  }
  outlinePages.value = outlinePages.value.filter(p => p.id !== id)
  renumberPages()
}

function renumberPages() {
  outlinePages.value.forEach((p, idx) => {
    p.pageNumber = idx + 1
  })
}

function addPoint(pageIndex) {
  if (!outlinePages.value[pageIndex].points) {
    outlinePages.value[pageIndex].points = []
  }
  outlinePages.value[pageIndex].points.push('')
  // Sync to outline_content
  outlinePages.value[pageIndex].outline_content = {
    title: outlinePages.value[pageIndex].title,
    points: outlinePages.value[pageIndex].points
  }
}

function updatePoint(pageIndex, pointIndex, value) {
  outlinePages.value[pageIndex].points[pointIndex] = value
  outlinePages.value[pageIndex].outline_content = {
    title: outlinePages.value[pageIndex].title,
    points: outlinePages.value[pageIndex].points
  }
}

function updateTitle(pageIndex, value) {
  outlinePages.value[pageIndex].title = value
  outlinePages.value[pageIndex].outline_content = {
    title: value,
    points: outlinePages.value[pageIndex].points
  }
}

function updatePart(pageIndex, value) {
  outlinePages.value[pageIndex].part = value
}

async function saveChanges() {
  if (!pptStore.projectId) return

  const realIds = []
  for (const page of outlinePages.value) {
    if (page.id > 1000000000) {
      // New page
      try {
        const created = await createPage(pptStore.projectId, {
          page_number: page.pageNumber,
          title: page.title,
          outline_content: page.outline_content,
          part: page.part
        })
        page.id = created.id
      } catch (e) {
        console.error('创建页面失败:', e)
      }
    } else {
      try {
        await updatePage(pptStore.projectId, page.id, {
          title: page.title,
          outline_content: page.outline_content,
          part: page.part
        })
      } catch (e) {
        console.error('更新页面失败:', e)
      }
    }
    realIds.push(page.id)
  }
  try {
    await reorderPages(pptStore.projectId, realIds)
  } catch (e) {
    console.error('重排页面失败:', e)
  }
}

// Drag and drop
const dragIndex = ref(null)

function handleDragStart(index) {
  dragIndex.value = index
}

function handleDragOver(event, index) {
  event.preventDefault()
  if (dragIndex.value === null || dragIndex.value === index) return

  const draggedItem = outlinePages.value[dragIndex.value]
  outlinePages.value.splice(dragIndex.value, 1)
  outlinePages.value.splice(index, 0, draggedItem)
  renumberPages()
  dragIndex.value = index
}

function handleDragEnd() {
  dragIndex.value = null
}

async function goToDescription() {
  await saveChanges()
  pptStore.setPhase('description')
}

// Card editing state
const editingCardId = ref(null)
const editTitle = ref('')
const editPoints = ref('')
const editPart = ref('')

function startEditCard(page, index) {
  editingCardId.value = page.id
  editTitle.value = page.title
  editPoints.value = page.points?.join('\n') || ''
  editPart.value = page.part || ''
}

function cancelEditCard() {
  editingCardId.value = null
}

async function saveCard(index) {
  const page = outlinePages.value[index]
  const points = editPoints.value.split('\n').filter(p => p.trim())

  page.title = editTitle.value
  page.points = points
  page.part = editPart.value
  page.outline_content = { title: editTitle.value, points }

  editingCardId.value = null

  // Save to backend
  if (pptStore.projectId && page.id <= 1000000000) {
    try {
      await updatePage(pptStore.projectId, page.id, {
        title: page.title,
        outline_content: page.outline_content,
        part: page.part
      })
    } catch (e) {
      console.error('保存页面失败:', e)
    }
  }
}
</script>

<template>
  <div class="ppt-outline">
    <!-- 顶栏 -->
    <header class="header">
      <div class="header-inner">
        <!-- 左侧：Logo 和标题 -->
        <div class="header-left">
          <button class="back-btn" @click="pptStore.setPhase('dialog')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
          <div class="logo">
            <span class="logo-text">AI备课</span>
          </div>
          <span class="header-divider">|</span>
          <span class="header-title">编辑大纲</span>
        </div>

        <!-- 中间：AI 修改输入框 -->
        <div class="header-center">
          <div class="ai-input-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="ai-icon">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
            </svg>
            <input
              v-model="topAiPrompt"
              type="text"
              class="ai-input"
              placeholder="例如：增加一页关于XXX的内容、删除第3页、合并前两页... · Ctrl+Enter提交"
              @keydown.ctrl.enter="handleRefineOutline"
            >
            <button
              class="ai-submit-btn"
              :disabled="isRefining || !ideaPrompt.trim()"
              @click="handleRefineOutline"
            >
              {{ isRefining ? '优化中...' : 'AI优化' }}
            </button>
          </div>
        </div>

        <!-- 右侧：下一步按钮 -->
        <div class="header-right">
          <button class="next-btn" @click="goToDescription">
            下一步
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
        <button class="action-btn primary" @click="addPage">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          添加页面
        </button>
        <button
          class="action-btn secondary"
          :disabled="isGenerating"
          @click="outlinePages.length === 0 ? handleGenerateOutline(buildIntentPrompt(pptStore.confirmedIntent || {})) : handleGenerateOutline(topAiPrompt || ideaPrompt)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
          </svg>
          {{ isGenerating ? '生成中...' : outlinePages.length === 0 ? '自动生成大纲' : '重新生成' }}
        </button>
        <button class="action-btn secondary" @click="saveChanges">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          保存
        </button>
        <span class="page-count">{{ pageCount }} 页</span>
      </div>
    </div>

    <!-- 大纲生成要求（可折叠） -->
    <div class="requirements-section">
      <button class="requirements-toggle" :class="{ open: showRequirements }" @click="showRequirements = !showRequirements">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
        <span>大纲生成要求</span>
        <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </button>
      <div class="requirements-content" :class="{ open: showRequirements }">
        <div class="requirements-inner">
          <textarea
            v-model="requirements"
            class="requirements-textarea"
            placeholder="例如：限制在10页以内、每页要点不超过3条、多使用图表..."
          ></textarea>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 左侧面板（可收起） -->
      <div class="left-panel" :class="{ collapsed: !isPanelOpen }">
        <!-- 收起/展开按钮（始终在顶部） -->
        <button class="toggle-btn" @click="isPanelOpen = !isPanelOpen">
          <svg v-if="isPanelOpen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M13 17l5-5-5-5M6 17l5-5-5-5"/>
          </svg>
        </button>

        <div class="panel-container" v-if="isPanelOpen">
          <div class="input-card">
            <div class="input-card-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" class="ai-icon">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
              </svg>
              <span class="input-card-title">PPT 构想</span>
            </div>
            <div class="input-card-body">
              <textarea
                v-model="ideaPrompt"
                class="input-textarea"
                placeholder="输入你的 PPT 构想...
例如：
- 主题：人工智能发展历程
- 受众：大学生和科技爱好者
- 页数：8-10页
- 风格：科技感、简约专业"
              ></textarea>
            </div>
          </div>

          <!-- 参考文件 -->
          <div class="ref-files-card">
            <div class="ref-files-header">参考文件</div>
            <div v-if="pptStore.referenceFiles.length === 0" class="ref-files-empty">
              暂无参考文件
            </div>
            <div v-else class="ref-files-list">
              <div v-for="file in pptStore.referenceFiles" :key="file.id" class="ref-file-item">
                <div class="ref-file-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <div class="ref-file-info">
                  <div class="ref-file-name">{{ file.name }}</div>
                  <div class="ref-file-meta">{{ (file.size / 1024 / 1024).toFixed(2) }} MB</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧大纲列表 -->
      <div class="right-panel">
        <div v-if="outlinePages.length === 0 && !isGenerating" class="empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="40" height="40">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <h3 class="empty-title">还没有页面</h3>
          <p class="empty-desc">点击「添加页面」手动创建，或「自动生成大纲」让 AI 帮你完成</p>
        </div>

        <div v-else class="outline-list">
          <template v-for="group in groupedPages" :key="group.part || 'no-part'">
            <!-- 分组标题 -->
            <div v-if="group.part" class="part-header">{{ group.part }}</div>

            <div
              v-for="(page, pageIndex) in group.pages"
              :key="page.id"
              class="outline-card"
              :class="{
                selected: selectedCardId === page.id,
                editing: editingCardId === page.id,
                'drag-over': false
              }"
              draggable="true"
              @dragstart="handleDragStart(outlinePages.indexOf(page))"
              @dragover="handleDragOver($event, outlinePages.indexOf(page))"
              @dragend="handleDragEnd"
              @click="selectCard(page.id)"
            >
              <!-- 查看模式 -->
              <div v-if="editingCardId !== page.id" class="outline-card-content">
                <div class="drag-handle">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/>
                    <circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/>
                  </svg>
                </div>

                <div class="page-meta">
                  <span class="page-badge">第{{ page.pageNumber }}页</span>
                  <span v-if="outlinePages.indexOf(page) === 0" class="cover-badge">封面</span>
                  <span v-if="page.part" class="part-badge">{{ page.part }}</span>
                </div>

                <div class="page-info">
                  <h4 class="page-title">{{ page.title || '未命名' }}</h4>
                  <div class="page-points" v-if="page.points && page.points.length > 0">
                    <div v-for="(point, pIdx) in page.points.slice(0, 3)" :key="pIdx" class="point-item">
                      <span class="point-bullet"></span>
                      <span class="point-text">{{ point }}</span>
                    </div>
                    <div v-if="page.points.length > 3" class="points-more">
                      还有 {{ page.points.length - 3 }} 条...
                    </div>
                  </div>
                </div>

                <div class="card-actions">
                  <button class="action-icon-btn edit" @click.stop="startEditCard(page, outlinePages.indexOf(page))" title="编辑">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                  <button
                    class="action-icon-btn delete"
                    @click.stop="deletePageById(page.id)"
                    :disabled="outlinePages.length <= 1"
                    title="删除"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                </div>
              </div>

              <!-- 编辑模式 -->
              <div v-else class="edit-form" @click.stop>
                <div class="edit-row">
                  <input
                    v-model="editPart"
                    type="text"
                    class="part-input"
                    placeholder="章节（可选）"
                  >
                </div>
                <input
                  v-model="editTitle"
                  type="text"
                  class="title-input"
                  placeholder="页面标题"
                >
                <textarea
                  v-model="editPoints"
                  class="points-input"
                  placeholder="要点（每行一个）"
                  rows="5"
                ></textarea>
                <div class="edit-actions">
                  <button class="cancel-btn" @click="cancelEditCard">取消</button>
                  <button class="save-btn" @click="saveCard(outlinePages.indexOf(page))">保存</button>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.ppt-outline {
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

.ai-submit-btn {
  padding: 6px 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  font-family: inherit;
}

.ai-submit-btn:hover:not(:disabled) {
  background: #2563eb;
}

.ai-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.header-right {
  flex-shrink: 0;
}

.next-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
  font-family: inherit;
}

.next-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
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

.action-btn.primary:hover {
  background: #2563eb;
}

.action-btn.secondary {
  background: white;
  color: #1e293b;
  border: 1px solid #e5e7eb;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #3b82f6;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-count {
  margin-left: auto;
  font-size: 13px;
  color: #94a3b8;
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
  display: flex;
  gap: 20px;
  padding: 20px;
  flex: 1;
  overflow: hidden;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* Left Panel */
.left-panel {
  width: 360px;
  flex-shrink: 0;
  position: relative;
  transition: width 0.3s ease;
}

.left-panel.collapsed {
  width: 0;
  overflow: visible;
}

.left-panel.collapsed .panel-container {
  display: none;
}

.panel-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  overflow: hidden;
  position: relative;
}

.toggle-btn {
  position: absolute;
  right: -14px;
  top: 12px;
  width: 28px;
  height: 36px;
  background: white;
  border: 1px solid #e5e7eb;
  border-left: none;
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  z-index: 101;
  transition: all 0.2s;
  box-shadow: 2px 0 6px rgba(0,0,0,0.08);
}

.toggle-btn:hover {
  color: #3b82f6;
  border-color: #3b82f6;
}

.input-card {
  border-bottom: 1px solid #f1f5f9;
}

.input-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

.input-card-header .ai-icon {
  color: #3b82f6;
}

.input-card-title {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}

.input-card-body {
  padding: 16px;
}

.input-textarea {
  width: 100%;
  min-height: 160px;
  border: none;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  font-family: inherit;
  background: transparent;
}

.input-textarea::placeholder {
  color: #94a3b8;
}

.ref-files-card {
  padding: 16px;
}

.ref-files-header {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 10px;
}

.ref-files-empty {
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 12px;
}

.ref-files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ref-file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
}

.ref-file-icon {
  width: 36px;
  height: 36px;
  background: #dbeafe;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}

.ref-file-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.ref-file-meta {
  font-size: 11px;
  color: #94a3b8;
}

/* Right Panel */
.right-panel {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}

.part-header {
  font-size: 13px;
  font-weight: 600;
  color: #4338ca;
  padding: 8px 12px;
  background: #EEF2FF;
  border-radius: 8px;
  margin-top: 4px;
  margin-bottom: 4px;
  border-left: 3px solid #6366f1;
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  border: 2px solid transparent;
  transition: all 0.2s;
  cursor: pointer;
}

.outline-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

.outline-card.selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.outline-card.drag-over {
  border-color: #3b82f6;
  background: #EFF6FF;
}

.outline-card.editing {
  border-color: #3b82f6;
}

.outline-card-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
}

.drag-handle {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  cursor: grab;
  flex-shrink: 0;
  border-radius: 4px;
  transition: all 0.2s;
}

.drag-handle:hover {
  background: #f8fafc;
  color: #64748b;
}

.page-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
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

.part-badge {
  padding: 3px 8px;
  background: #E0E7FF;
  color: #4338ca;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}

.page-info {
  flex: 1;
  min-width: 0;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.page-points {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.point-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.point-bullet {
  width: 5px;
  height: 5px;
  background: #3b82f6;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.point-text {
  font-size: 13px;
  color: #64748b;
  line-height: 1.4;
}

.points-more {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
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

.action-icon-btn.delete:hover:not(:disabled) {
  color: #ef4444;
  background: #fee2e2;
}

.action-icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Edit Form */
.edit-form {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-row {
  display: flex;
  gap: 8px;
}

.part-input {
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  width: 120px;
  outline: none;
  font-family: inherit;
}

.part-input:focus {
  border-color: #3b82f6;
}

.title-input {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  outline: none;
  font-family: inherit;
}

.title-input:focus {
  border-color: #3b82f6;
}

.points-input {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  outline: none;
  font-family: inherit;
  line-height: 1.5;
}

.points-input:focus {
  border-color: #3b82f6;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.cancel-btn {
  padding: 8px 16px;
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
  padding: 8px 16px;
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
