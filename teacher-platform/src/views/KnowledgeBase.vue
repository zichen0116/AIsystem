<script setup>
import { ref, computed, watch } from 'vue'

const systemSearch = ref('')
const personalSearch = ref('')

const systemResources = ref([
  { id: 1, title: '十年级数学课程标准', desc: '代数官方课程指南与评估标准。', tags: ['数学', '课程'], time: '2天前更新', iconType: 'book' },
  { id: 2, title: '高中实验室安全规范', desc: '标准实验室安全清单与应急流程。', tags: ['科学', '安全'], time: '1个月前更新', iconType: 'clipboard' },
  { id: 3, title: '文学论文评分标准', desc: '分析性文学论文的整体评分框架。', tags: ['语文', '评分'], time: '2周前更新', iconType: 'doc' }
])

const personalResources = ref([
  { id: 1, title: '第4周 - 几何入门笔记', desc: '文本文档 · 今日修改', iconType: 'file' },
  { id: 2, title: '文艺复兴艺术展示.pdf', desc: 'PDF文件 · 2.4 MB · 3天前', iconType: 'pdf' },
  { id: 3, title: '化学YouTube播放列表', desc: '外部链接 · 上周修改', iconType: 'link' }
])

const systemPage = ref(1)
const pageSize = 4

function matchSearch(text, q) {
  if (!q || !q.trim()) return true
  return (text || '').toLowerCase().includes(q.trim().toLowerCase())
}

const filteredSystemList = computed(() => {
  const q = systemSearch.value
  return systemResources.value.filter(r =>
    matchSearch(r.title, q) || matchSearch(r.desc, q) || (r.tags && r.tags.some(t => matchSearch(t, q)))
  )
})

const filteredPersonalList = computed(() => {
  const q = personalSearch.value
  return personalResources.value.filter(r =>
    matchSearch(r.title, q) || matchSearch(r.desc, q)
  )
})

const systemTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredSystemList.value.length / pageSize))
)

const paginatedSystemList = computed(() => {
  const start = (systemPage.value - 1) * pageSize
  return filteredSystemList.value.slice(start, start + pageSize)
})

function goToSystemPage(p) {
  const n = systemTotalPages.value
  if (p >= 1 && p <= n) systemPage.value = p
}

watch(systemSearch, () => { systemPage.value = 1 })

const showAddModal = ref(false)
const addTarget = ref('system') // 'system' | 'personal'
const addForm = ref({ title: '', desc: '', tags: '' })
const addModalFiles = ref([])
const addModalFileInputRef = ref(null)
const isEditMode = ref(false)
const editingId = ref(null)
const editingTarget = ref(null) // 'system' | 'personal'

function openAddModal(target) {
  isEditMode.value = false
  editingId.value = null
  editingTarget.value = null
  addTarget.value = target
  addForm.value = { title: '', desc: '', tags: '' }
  addModalFiles.value = []
  showAddModal.value = true
}

function openEditModal(target, item) {
  isEditMode.value = true
  editingId.value = item.id
  editingTarget.value = target
  addTarget.value = target
  addForm.value = {
    title: item.title,
    desc: item.desc || '',
    tags: (item.tags && item.tags.length) ? item.tags.join(', ') : ''
  }
  addModalFiles.value = []
  showAddModal.value = true
}

function triggerAddModalFileSelect() {
  addModalFileInputRef.value?.click()
}

function onAddModalFileChange(e) {
  const files = e.target.files
  if (files?.length) addModalFiles.value = Array.from(files)
  e.target.value = ''
}

function submitAdd() {
  const { title, desc, tags } = addForm.value
  if (!title.trim()) return
  const fileNames = addModalFiles.value.map(f => f.name)
  const descWithFiles = fileNames.length
    ? (desc || '').trim() + (desc ? '；' : '') + '已选文件: ' + fileNames.join(', ')
    : (desc || '').trim() || '—'
  const nextId = (arr) => Math.max(0, ...arr.map(r => r.id || 0)) + 1

  if (isEditMode.value && editingId.value != null && editingTarget.value) {
    const list = editingTarget.value === 'system' ? systemResources.value : personalResources.value
    const idx = list.findIndex(r => r.id === editingId.value)
    if (idx !== -1) {
      if (editingTarget.value === 'system') {
        systemResources.value[idx] = {
          ...systemResources.value[idx],
          title: title.trim(),
          desc: descWithFiles,
          tags: tags ? tags.split(/[,，\s]+/).filter(Boolean) : []
        }
      } else {
        personalResources.value[idx] = {
          ...personalResources.value[idx],
          title: title.trim(),
          desc: descWithFiles
        }
      }
    }
  } else {
    if (addTarget.value === 'system') {
      systemResources.value.unshift({
        id: nextId(systemResources.value),
        title: title.trim(),
        desc: descWithFiles,
        tags: tags ? tags.split(/[,，\s]+/).filter(Boolean) : [],
        time: '刚刚',
        iconType: 'book'
      })
    } else {
      personalResources.value.unshift({
        id: nextId(personalResources.value),
        title: title.trim(),
        desc: descWithFiles,
        iconType: 'file'
      })
    }
  }
  showAddModal.value = false
}

function deleteResource(target, id) {
  if (target === 'system') {
    systemResources.value = systemResources.value.filter(r => r.id !== id)
  } else {
    personalResources.value = personalResources.value.filter(r => r.id !== id)
  }
}
</script>

<template>
  <div class="knowledge-page">
    <div class="knowledge-content">
      <!-- Two Columns -->
      <div class="two-columns">
        <!-- System Knowledge Base -->
        <div class="column system-column">
          <div class="column-header">
            <h3 class="column-title">
              <span class="column-title-icon kb-icon-outline"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span>
              系统知识库
            </h3>
            <span class="item-count">{{ filteredSystemList.length }} 项</span>
            <button type="button" class="add-kb-btn" @click="openAddModal('system')">添加知识库</button>
          </div>
          <div class="search-bar">
            <span class="search-icon kb-icon-outline"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg></span>
            <input v-model="systemSearch" type="text" placeholder="搜索精选资源..." />
          </div>
          <div class="resource-cards">
            <div v-for="(r, i) in paginatedSystemList" :key="r.id" class="resource-card system-card">
              <div class="card-toolbar">
                <button type="button" class="card-action-btn" title="编辑" @click.stop="openEditModal('system', r)">编辑</button>
                <button type="button" class="card-action-btn delete" title="删除" @click.stop="deleteResource('system', r.id)">删除</button>
              </div>
              <div class="card-icon kb-icon-wrap" :class="['icon-' + (i % 3)]">
                <svg v-if="r.iconType === 'book'" class="kb-icon-outline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M8 7h8"/><path d="M8 11h8"/></svg>
                <svg v-else-if="r.iconType === 'clipboard'" class="kb-icon-outline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M9 14h6"/><path d="M9 18h6"/></svg>
                <svg v-else-if="r.iconType === 'doc'" class="kb-icon-outline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
              </div>
              <h4 class="card-title">{{ r.title }}</h4>
              <p class="card-desc">{{ r.desc }}</p>
              <div class="card-tags">
                <span v-for="tag in r.tags" :key="tag" class="tag">{{ tag }}</span>
              </div>
              <span class="card-time">🕐 {{ r.time }}</span>
            </div>
          </div>
          <div v-if="systemTotalPages > 1" class="pagination-wrap">
            <button type="button" class="page-btn" :disabled="systemPage <= 1" @click="goToSystemPage(systemPage - 1)">‹</button>
            <button
              v-for="p in systemTotalPages"
              :key="p"
              type="button"
              class="page-btn"
              :class="{ active: systemPage === p }"
              @click="goToSystemPage(p)"
            >
              {{ p }}
            </button>
            <button type="button" class="page-btn" :disabled="systemPage >= systemTotalPages" @click="goToSystemPage(systemPage + 1)">›</button>
          </div>
        </div>

        <!-- Personal Knowledge Base -->
        <div class="column personal-column">
          <div class="column-header">
            <h3 class="column-title">
              <span class="column-title-icon kb-icon-outline"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></span>
              个人知识库
            </h3>
            <span class="item-count">{{ filteredPersonalList.length }} 项</span>
            <button type="button" class="add-kb-btn" @click="openAddModal('personal')">添加知识库</button>
          </div>
          <div class="search-bar">
            <span class="search-icon kb-icon-outline"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg></span>
            <input v-model="personalSearch" type="text" placeholder="搜索我的笔记和文件..." />
          </div>
          <div class="resource-cards">
            <div v-for="(r, i) in filteredPersonalList" :key="r.id" class="resource-card personal-card">
              <div class="card-actions">
                <button type="button" class="card-action-btn" title="编辑" @click.stop="openEditModal('personal', r)">编辑</button>
                <button type="button" class="card-action-btn delete" title="删除" @click.stop="deleteResource('personal', r.id)">删除</button>
              </div>
              <div class="card-icon personal-icon kb-icon-wrap">
                <svg v-if="r.iconType === 'file'" class="kb-icon-outline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
                <svg v-else-if="r.iconType === 'pdf'" class="kb-icon-outline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M10 17H8"/><path d="M16 17h-4"/></svg>
                <svg v-else-if="r.iconType === 'link'" class="kb-icon-outline" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
              </div>
              <h4 class="card-title">{{ r.title }}</h4>
              <p class="card-desc">{{ r.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showAddModal" class="add-modal-overlay" @click.self="showAddModal = false">
        <div class="add-modal-box">
          <h3>{{ isEditMode ? '编辑知识库' : (addTarget === 'system' ? '添加系统知识库' : '添加个人知识库') }}</h3>
          <div class="add-form">
            <label>标题</label>
            <input v-model="addForm.title" type="text" placeholder="输入标题" />
            <label>描述</label>
            <input v-model="addForm.desc" type="text" placeholder="选填" />
            <label v-if="addTarget === 'system'">标签（逗号分隔）</label>
            <input v-if="addTarget === 'system'" v-model="addForm.tags" type="text" placeholder="数学, 课程" />
            <label>选择本地文件（选填）</label>
            <input
              ref="addModalFileInputRef"
              type="file"
              multiple
              class="file-input-hidden"
              @change="onAddModalFileChange"
            />
            <button type="button" class="select-file-btn" @click="triggerAddModalFileSelect">选择文件</button>
            <span v-if="addModalFiles.length" class="selected-files-names">已选 {{ addModalFiles.length }} 个文件</span>
          </div>
          <div class="add-modal-actions">
            <button type="button" class="cancel-btn" @click="showAddModal = false">取消</button>
            <button type="button" class="confirm-btn" @click="submitAdd">{{ isEditMode ? '保存' : '添加' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.knowledge-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.knowledge-content {
  flex: 1;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-left {
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 0.9rem;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  padding: 10px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.action-btn.primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.column {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.add-kb-btn {
  padding: 6px 14px;
  border: 1px solid #3b82f6;
  background: #fff;
  color: #3b82f6;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}

.add-kb-btn:hover {
  background: #eff6ff;
}

.column-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-title-icon {
  display: inline-flex;
  width: 20px;
  height: 20px;
  color: #475569;
}

.column-title-icon svg {
  width: 100%;
  height: 100%;
}

.search-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: #64748b;
}

.search-icon svg {
  width: 100%;
  height: 100%;
}

.kb-icon-outline {
  width: 24px;
  height: 24px;
  color: inherit;
}

.kb-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.kb-icon-wrap .kb-icon-outline {
  width: 24px;
  height: 24px;
}

.item-count {
  font-size: 0.875rem;
  color: #94a3b8;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 20px;
}


.search-bar input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
}

.resource-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.resource-card {
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  transition: all 0.2s;
}

.resource-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.system-card {
  position: relative;
}

.card-toolbar {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-link-icon {
  font-size: 0.875rem;
  color: #94a3b8;
  cursor: pointer;
}

.card-action-btn {
  padding: 2px 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #64748b;
  cursor: pointer;
}

.card-action-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.card-action-btn.delete:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  border-radius: 8px;
  margin-bottom: 12px;
}

.card-icon.icon-0 {
  background: #dbeafe;
  color: #2563eb;
}

.card-icon.icon-1 {
  background: #dcfce7;
  color: #16a34a;
}

.card-icon.icon-2 {
  background: #ede9fe;
  color: #7c3aed;
}

.card-icon.personal-icon {
  background: #f1f5f9;
  color: #64748b;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 6px;
}

.card-desc {
  font-size: 0.875rem;
  color: #64748b;
  line-height: 1.4;
  margin-bottom: 10px;
}

.card-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.tag {
  padding: 4px 10px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 0.75rem;
  border-radius: 4px;
}

.card-time {
  font-size: 0.75rem;
  color: #94a3b8;
}

.personal-card {
  position: relative;
}

.card-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
  color: #94a3b8;
  cursor: pointer;
}

.card-actions .card-action-btn {
  padding: 2px 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #64748b;
  cursor: pointer;
}

.card-actions .card-action-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.card-actions .card-action-btn.delete:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.pagination-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
}

.page-btn {
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

.page-btn:hover:not(:disabled) {
  border-color: #cbd5e1;
  color: #1e293b;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.add-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.add-modal-box {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}

.add-modal-box h3 {
  margin: 0 0 20px;
  font-size: 1.1rem;
  color: #1e293b;
}

.add-form label {
  display: block;
  font-size: 0.875rem;
  color: #475569;
  margin-bottom: 6px;
  margin-top: 12px;
}

.add-form label:first-of-type {
  margin-top: 0;
}

.add-form input[type="text"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}

.file-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.select-file-btn {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
}

.select-file-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.selected-files-names {
  margin-left: 10px;
  font-size: 0.875rem;
  color: #64748b;
}

.add-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.add-modal-actions .cancel-btn {
  padding: 8px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.add-modal-actions .confirm-btn {
  padding: 8px 20px;
  border: none;
  background: #3b82f6;
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

@media (max-width: 900px) {
  .two-columns {
    grid-template-columns: 1fr;
  }
}
</style>
