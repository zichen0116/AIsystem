<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { listProjects, deleteProject, batchDeleteProjects } from '@/api/ppt'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, ArrowRight, Document, Clock } from '@element-plus/icons-vue'

const pptStore = usePptStore()

const _allProjects = ref([])
const projects = ref([])
const total = ref(0)
const isLoading = ref(false)
const selectedIds = ref([])
const isDeleting = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(Number(localStorage.getItem('ppt_history_page_size')) || 5)
const pageSizeOptions = [5, 10, 20, 50]
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const isAllSelected = computed(() =>
  projects.value.length > 0 && selectedIds.value.length === projects.value.length
)
const isIndeterminate = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < projects.value.length
)

onMounted(() => loadProjects())

async function loadProjects() {
  isLoading.value = true
  try {
    const data = await listProjects()
    const all = Array.isArray(data) ? data : (data?.projects || [])
    _allProjects.value = all
    total.value = all.length
    applyPage()
  } catch (e) {
    ElMessage.error('加载历史项目失败，请重试')
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

function applyPage() {
  const start = (currentPage.value - 1) * pageSize.value
  projects.value = _allProjects.value.slice(start, start + pageSize.value)
  selectedIds.value = []
}

function handlePageChange(page) {
  currentPage.value = page
  applyPage()
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  localStorage.setItem('ppt_history_page_size', String(size))
  applyPage()
}

function toggleSelectAll(val) {
  selectedIds.value = val ? projects.value.map(p => p.id) : []
}

function getStatusText(project) {
  const s = project.status
  const ct = project.creation_type

  // 文件生成中
  if (ct === 'file' && (s === 'GENERATING' || s === 'PARSE')) return '文件解析中'
  // 翻新中
  if (ct === 'renovation' && (s === 'GENERATING' || s === 'PARSE')) return '翻新解析中'

  if (s === 'COMPLETED' || s === 'EXPORTED') return '已完成'
  if (s === 'INTENT_CONFIRMED') return '待生成大纲'
  if (project.page_count > 0 && project.cover_image_url) return '已完成'
  if (project.page_count > 0) return '待生成图片'

  if (ct === 'file') return '文件生成'
  if (ct === 'renovation') return 'PPT翻新'

  return '待生成描述'
}

function getStatusType(project) {
  const text = getStatusText(project)
  if (text === '已完成') return 'success'
  if (text === '待生成图片') return 'warning'
  if (text.includes('解析中')) return 'warning'
  return 'info'
}

function getProjectPhase(project) {
  const ct = project.creation_type

  if (project.cover_image_url) return 'preview'

  // file 项目进入 outline（不走 dialog）
  if (ct === 'file') return 'outline'
  // renovation 项目直接进入 description（跳过 outline）
  if (ct === 'renovation') return 'description'

  if (project.status === 'INTENT_CONFIRMED') return 'outline'
  if (project.page_count > 0) return 'outline'
  if (ct === 'dialog') return 'dialog'
  return 'outline'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function openProject(project) {
  try {
    await pptStore.loadProjectWorkspace(project.id)
    pptStore.setPhase(getProjectPhase(project))
  } catch (e) {
    ElMessage.error('打开项目失败')
    console.error(e)
  }
}

async function handleDelete(project) {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目「${project.title || '未命名项目'}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteProject(project.id)
    ElMessage.success('删除成功')
    await loadProjects()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(e)
    }
  }
}

async function handleBatchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 个项目吗？此操作不可恢复。`,
      '批量删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    isDeleting.value = true
    await batchDeleteProjects([...selectedIds.value])
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    await loadProjects()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败')
      console.error(e)
    }
  } finally {
    isDeleting.value = false
  }
}

function goHome() {
  pptStore.resetState()
}
</script>

<template>
  <div class="history-page">
    <div class="history-content">
      <!-- 标题区 -->
      <div class="history-header">
        <div class="header-left">
          <h1 class="history-title">历史项目</h1>
          <p class="history-subtitle">查看和管理你的所有项目</p>
        </div>
        <el-button @click="goHome">
          返回首页
        </el-button>
      </div>

      <!-- 工具栏 -->
      <div class="toolbar">
        <el-checkbox
          :model-value="isAllSelected"
          :indeterminate="isIndeterminate"
          @change="toggleSelectAll"
        >
          全选
        </el-checkbox>

        <transition name="fade">
          <div v-if="selectedIds.length > 0" class="batch-area">
            <span class="batch-count">已选择 {{ selectedIds.length }} 项</span>
            <el-button size="small" @click="selectedIds = []">取消选择</el-button>
            <el-button
              size="small"
              type="danger"
              :loading="isDeleting"
              @click="handleBatchDelete"
            >
              批量删除
            </el-button>
          </div>
        </transition>
      </div>

      <!-- 加载中 -->
      <div v-if="isLoading" class="state-center">
        <el-icon class="spin-icon" :size="32"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" opacity=".25"/><path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/></svg></el-icon>
        <p style="color:#9ca3af;margin:8px 0 0">加载中...</p>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else-if="_allProjects.length === 0"
        description="暂无历史项目，快去创建第一个吧"
        :image-size="80"
      >
        <el-button type="primary" @click="goHome">创建项目</el-button>
      </el-empty>

      <!-- 项目列表 -->
      <template v-else>
        <div class="project-list">
          <div
            v-for="project in projects"
            :key="project.id"
            class="project-card"
            :class="{ 'is-selected': selectedIds.includes(project.id) }"
            @click="openProject(project)"
          >
            <!-- 复选框 -->
            <div class="card-check" @click.stop>
              <el-checkbox
                :model-value="selectedIds.includes(project.id)"
                @change="val => {
                  if (val) selectedIds = [...selectedIds, project.id]
                  else selectedIds = selectedIds.filter(id => id !== project.id)
                }"
              />
            </div>

            <!-- 主信息 -->
            <div class="card-body">
              <div class="card-title">{{ project.title || '未命名项目' }}</div>
              <div class="card-meta">
                <span v-if="project.creation_type === 'file'" class="meta-item meta-type">文件生成</span>
                <span v-else-if="project.creation_type === 'renovation'" class="meta-item meta-type">PPT翻新</span>
                <span class="meta-item">
                  <el-icon><Document /></el-icon>
                  {{ project.page_count || 0 }} 页
                </span>
                <span class="meta-item">
                  <el-icon><Clock /></el-icon>
                  {{ formatDate(project.updated_at) }}
                </span>
              </div>
            </div>

            <!-- 右侧 -->
            <div class="card-right">
              <el-tag :type="getStatusType(project)" size="small" round>
                {{ getStatusText(project) }}
              </el-tag>

              <!-- 封面缩略图 -->
              <div class="card-cover">
                <img v-if="project.cover_image_url" :src="project.cover_image_url" :alt="project.title" loading="lazy" />
                <div v-else class="cover-empty">
                  <el-icon :size="24" color="#d1d5db"><Document /></el-icon>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="card-actions" @click.stop>
                <el-button
                  circle
                  size="small"
                  type="danger"
                  plain
                  :icon="Delete"
                  title="删除"
                  @click="handleDelete(project)"
                />
                <el-button
                  circle
                  size="small"
                  plain
                  :icon="ArrowRight"
                  title="进入项目"
                  @click="openProject(project)"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="pageSizeOptions"
            :total="total"
            layout="prev, pager, next, sizes, total"
            background
            small
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* 整体铺满父容器，可滚动 */
.history-page {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
  box-sizing: border-box;
  padding: 32px 0 48px;
}

/* 居中内容区，约 2/3 宽度 */
.history-content {
  width: 66%;
  min-width: 640px;
  max-width: 1000px;
  margin: 0 auto;
}

/* 标题区 */
.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.history-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 4px;
}

.history-subtitle {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0 12px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 12px;
  min-height: 36px;
}

.batch-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-count {
  font-size: 13px;
  color: #6b7280;
}

/* fade 动画 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* 状态 */
.state-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 12px;
}

.spin-icon {
  color: #9ca3af;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 列表 */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 卡片 */
.project-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.project-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0,0,0,0.08);
  border-color: #d1d5db;
}

.project-card.is-selected {
  border-color: #a5b4fc;
  background: #f5f3ff;
}

/* 复选框区域 */
.card-check {
  flex-shrink: 0;
}

/* 主信息 */
.card-body {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 14px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #9ca3af;
}

.meta-type {
  color: #3b82f6;
  font-weight: 500;
  padding: 1px 6px;
  background: #dbeafe;
  border-radius: 4px;
}

/* 右侧区域 */
.card-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

/* 封面缩略图 */
.card-cover {
  width: 112px;
  height: 72px;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: #f3f4f6;
  flex-shrink: 0;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.card-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

/* 分页 */
.pagination-wrap {
  display: flex;
  justify-content: center;
  padding-top: 20px;
}
</style>
