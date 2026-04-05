<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { listProjects, deleteProject, batchDeleteProjects } from '@/api/ppt'

const pptStore = usePptStore()

const projects = ref([])
const isLoading = ref(false)
const errorMsg = ref('')
const selectedIds = ref(new Set())
const isDeleting = ref(false)

const isBatchMode = computed(() => selectedIds.value.size > 0)

onMounted(async () => {
  await loadProjects()
})

async function loadProjects() {
  isLoading.value = true
  errorMsg.value = ''
  try {
    const data = await listProjects()
    projects.value = Array.isArray(data) ? data : (data?.projects || [])
  } catch (e) {
    errorMsg.value = '加载历史项目失败，请重试'
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

function getStatusText(project) {
  const s = project.status
  if (s === 'COMPLETED' || s === 'EXPORTED') return '已完成'
  if (s === 'INTENT_CONFIRMED') return '待生成大纲'
  if (project.page_count > 0 && project.cover_image_url) return '已完成'
  if (project.page_count > 0) return '待生成图片'
  return '进行中'
}

function getStatusClass(project) {
  const text = getStatusText(project)
  if (text === '已完成') return 'status-completed'
  if (text === '待生成图片') return 'status-pending-images'
  return 'status-in-progress'
}

function getProjectPhase(project) {
  if (project.cover_image_url) return 'preview'
  if (project.page_count > 0) return 'outline'
  if (project.creation_type === 'dialog') return 'dialog'
  return 'outline'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

async function openProject(project) {
  if (isBatchMode.value) {
    toggleSelect(project.id)
    return
  }
  try {
    await pptStore.fetchProject(project.id)
    await pptStore.fetchPages(project.id)

    // 恢复意图
    if (project.creation_type === 'dialog') {
      try {
        await pptStore.fetchIntent(project.id)
      } catch (e) {
        // 意图可能不存在
      }
    }

    const phase = getProjectPhase(project)
    pptStore.setPhase(phase)
  } catch (e) {
    console.error('打开项目失败:', e)
  }
}

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

function toggleSelectAll() {
  if (selectedIds.value.size === projects.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(projects.value.map(p => p.id))
  }
}

async function handleDelete(e, project) {
  e.stopPropagation()
  if (!confirm(`确定要删除项目「${project.title}」吗？此操作不可恢复。`)) return
  try {
    await deleteProject(project.id)
    await loadProjects()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

async function handleBatchDelete() {
  const count = selectedIds.value.size
  if (!confirm(`确定要删除选中的 ${count} 个项目吗？此操作不可恢复。`)) return
  isDeleting.value = true
  try {
    await batchDeleteProjects([...selectedIds.value])
    selectedIds.value = new Set()
    await loadProjects()
  } catch (e) {
    console.error('批量删除失败:', e)
  } finally {
    isDeleting.value = false
  }
}

function goHome() {
  pptStore.setPhase('home')
}
</script>

<template>
  <div class="ppt-history">
    <!-- Header -->
    <header class="history-header">
      <div class="header-left">
        <button class="back-btn" @click="goHome">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回首页
        </button>
        <h1>历史项目</h1>
        <p class="subtitle">查看和管理你的所有项目</p>
      </div>
    </header>

    <!-- Batch Actions -->
    <div class="batch-bar">
      <label class="select-all" @click="toggleSelectAll">
        <span class="checkbox-icon" :class="{ checked: selectedIds.size === projects.length && projects.length > 0 }">
          <svg v-if="selectedIds.size === projects.length && projects.length > 0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </span>
        全选
      </label>
      <div v-if="isBatchMode" class="batch-actions">
        <span class="batch-count">已选择 {{ selectedIds.size }} 项</span>
        <button class="batch-cancel" @click="selectedIds = new Set()">取消选择</button>
        <button class="batch-delete-btn" :disabled="isDeleting" @click="handleBatchDelete">
          {{ isDeleting ? '删除中...' : '批量删除' }}
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="history-content">
      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spin-loader"></div>
        <p>加载中...</p>
      </div>

      <!-- Error -->
      <div v-else-if="errorMsg" class="error-state">
        <p>{{ errorMsg }}</p>
        <button @click="loadProjects">重试</button>
      </div>

      <!-- Empty -->
      <div v-else-if="projects.length === 0" class="empty-state">
        <div class="empty-icon">📊</div>
        <h3>暂无历史项目</h3>
        <p>创建你的第一个项目开始使用吧</p>
        <button class="create-btn" @click="goHome">创建项目</button>
      </div>

      <!-- Project List -->
      <div v-else class="project-list">
        <div
          v-for="project in projects"
          :key="project.id"
          class="project-card"
          :class="{ 'card-selected': selectedIds.has(project.id) }"
          @click="openProject(project)"
        >
          <!-- Checkbox -->
          <div class="card-checkbox" @click.stop="toggleSelect(project.id)">
            <span class="checkbox-icon" :class="{ checked: selectedIds.has(project.id) }">
              <svg v-if="selectedIds.has(project.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </span>
          </div>

          <!-- Info -->
          <div class="card-info">
            <h3 class="card-title">{{ project.title || '未命名项目' }}</h3>
            <div class="card-meta">
              <span class="meta-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <line x1="3" y1="9" x2="21" y2="9"/>
                </svg>
                {{ project.page_count || 0 }} 页
              </span>
              <span class="meta-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                {{ formatDate(project.updated_at) }}
              </span>
            </div>
            <span class="status-badge" :class="getStatusClass(project)">
              {{ getStatusText(project) }}
            </span>
          </div>

          <!-- Cover Image -->
          <div class="card-cover">
            <template v-if="project.cover_image_url">
              <img :src="project.cover_image_url" :alt="project.title" loading="lazy">
            </template>
            <template v-else>
              <div class="cover-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <polyline points="21 15 16 10 5 21"/>
                </svg>
              </div>
            </template>
          </div>

          <!-- Actions -->
          <div class="card-actions">
            <button class="delete-btn" title="删除" @click="handleDelete($event, project)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
            <div class="enter-arrow">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ppt-history {
  min-height: 100%;
  background: #111827;
  color: #e5e7eb;
  padding: 24px 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.history-header {
  margin-bottom: 20px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 800;
  color: #f9fafb;
  margin: 12px 0 4px;
}

.subtitle {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #374151;
  border-radius: 8px;
  background: #1f2937;
  color: #d1d5db;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.back-btn:hover {
  border-color: #6b7280;
  background: #374151;
  color: #f9fafb;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0 16px;
  border-bottom: 1px solid #1f2937;
  margin-bottom: 16px;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #9ca3af;
  cursor: pointer;
  user-select: none;
}

.checkbox-icon {
  width: 18px;
  height: 18px;
  border: 2px solid #4b5563;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.checkbox-icon.checked {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.batch-count {
  font-size: 13px;
  color: #60a5fa;
}

.batch-cancel {
  border: 1px solid #374151;
  border-radius: 6px;
  background: transparent;
  color: #9ca3af;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  font-family: inherit;
}

.batch-delete-btn {
  border: 1px solid #7f1d1d;
  border-radius: 6px;
  background: #7f1d1d;
  color: #fca5a5;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  font-family: inherit;
}

.batch-delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state, .error-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 12px;
  color: #9ca3af;
}

.spin-loader {
  width: 28px;
  height: 28px;
  border: 3px solid #374151;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
}

.create-btn {
  margin-top: 8px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  font-family: inherit;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-card:hover {
  border-color: #4b5563;
  background: #283444;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.project-card.card-selected {
  border-color: #3b82f6;
  background: #1e2a3e;
}

.card-checkbox {
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #9ca3af;
}

.meta-item svg {
  flex-shrink: 0;
}

.status-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
}

.status-completed {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-pending-images {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.status-in-progress {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(96, 165, 250, 0.3);
}

.card-cover {
  width: 180px;
  height: 108px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  background: #111827;
  border: 1px solid #374151;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b5563;
}

.card-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.delete-btn {
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.15s;
}

.delete-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.enter-arrow {
  color: #6b7280;
  transition: color 0.15s;
}

.project-card:hover .enter-arrow {
  color: #d1d5db;
}

@media (max-width: 768px) {
  .ppt-history {
    padding: 16px;
  }

  .project-card {
    flex-wrap: wrap;
    padding: 16px;
  }

  .card-cover {
    width: 100%;
    height: 140px;
    order: -1;
  }

  .card-actions {
    flex-direction: row;
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
