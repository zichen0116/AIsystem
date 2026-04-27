<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useKnowledgeStore } from '../stores/knowledge'

const router = useRouter()
const userStore = useUserStore()
const store = useKnowledgeStore()
const isAdmin = computed(() => userStore.userInfo?.is_admin === true)

// ---- Filter state ----
const activeFilter = ref('all')
const searchQuery = ref('')
const selectedTagFilter = ref('')

// ---- Fetch data ----
async function loadData() {
  await Promise.all([
    store.fetchLibraries({
      scope: activeFilter.value,
      search: searchQuery.value,
      tag: selectedTagFilter.value,
    }),
    store.fetchUserTags(),
  ])
}

onMounted(loadData)

// Debounced search
let searchTimer = null
watch(searchQuery, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.fetchLibraries({
      scope: activeFilter.value,
      search: searchQuery.value,
      tag: selectedTagFilter.value,
    })
  }, 300)
})

watch(activeFilter, () => {
  store.fetchLibraries({
    scope: activeFilter.value,
    search: searchQuery.value,
    tag: selectedTagFilter.value,
  })
})

watch(selectedTagFilter, () => {
  store.fetchLibraries({
    scope: activeFilter.value,
    search: searchQuery.value,
    tag: selectedTagFilter.value,
  })
})

// ---- Computed ----
const filteredResources = computed(() => {
  return store.libraries.map(lib => ({
    id: lib.id,
    type: lib.is_system ? 'system' : 'personal',
    title: lib.name,
    desc: lib.description || '',
    tags: lib.tags || [],
    time: lib.updated_at ? new Date(lib.updated_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) + '更新' : '',
    iconColor: lib.is_system ? '#2563EB' : '#F59E0B',
    fileCount: lib.asset_count || 0,
    charCount: 0,
    _raw: lib,
  }))
})

// ---- Tag filter dropdown ----
const showTagFilterDropdown = ref(false)

const availableFilterTags = computed(() => {
  return store.userTags || []
})

function selectTagFilter(tag) {
  selectedTagFilter.value = tag
  showTagFilterDropdown.value = false
}

// ---- More menu (card actions) ----
const activeMenuId = ref(null)

function toggleMenu(id, e) {
  e.stopPropagation()
  activeMenuId.value = activeMenuId.value === id ? null : id
}

function closeAllMenus() {
  activeMenuId.value = null
  showTagFilterDropdown.value = false
}

// ---- Tag Popover ----
const activeTagPopoverId = ref(null)
const tagSearchQuery = ref('')

function toggleTagPopover(id, e) {
  e.stopPropagation()
  if (activeTagPopoverId.value === id) {
    activeTagPopoverId.value = null
  } else {
    activeTagPopoverId.value = id
    tagSearchQuery.value = ''
  }
}

const filteredTagOptions = computed(() => {
  const q = tagSearchQuery.value.trim().toLowerCase()
  if (!q) return store.userTags
  return store.userTags.filter(t => t.toLowerCase().includes(q))
})

async function addTagToResource(resource, tag) {
  const currentTags = [...(resource.tags || [])]
  if (currentTags.includes(tag)) return
  currentTags.push(tag)
  await store.updateLibrary(resource.id, { tags: currentTags })
  await loadData()
}

async function createAndAddTag(resource) {
  const name = tagSearchQuery.value.trim()
  if (!name) return
  const currentTags = [...(resource.tags || [])]
  if (!currentTags.includes(name)) currentTags.push(name)
  await store.updateLibrary(resource.id, { tags: currentTags })
  tagSearchQuery.value = ''
  await loadData()
}

async function removeTagFromResource(resource, tag) {
  const currentTags = (resource.tags || []).filter(t => t !== tag)
  await store.updateLibrary(resource.id, { tags: currentTags })
  await loadData()
}

// ---- Tag Management Modal ----
const showTagManager = ref(false)
const tagManagerSearch = ref('')
const editingTag = ref(null)
const editingTagName = ref('')

const filteredManagerTags = computed(() => {
  const q = tagManagerSearch.value.trim().toLowerCase()
  if (!q) return store.userTags
  return store.userTags.filter(t => t.toLowerCase().includes(q))
})

function openTagManager() {
  activeTagPopoverId.value = null
  showTagManager.value = true
  tagManagerSearch.value = ''
}

function startRenameTag(tag) {
  editingTag.value = tag
  editingTagName.value = tag
}

async function confirmRenameTag() {
  const oldName = editingTag.value
  const newName = editingTagName.value.trim()
  editingTag.value = null
  if (!newName || newName === oldName) return
  await store.renameTag(oldName, newName)
  if (selectedTagFilter.value === oldName) selectedTagFilter.value = newName
  await loadData()
}

async function deleteGlobalTag(tag) {
  const libsWithTag = store.libraries.filter(lib => (lib.tags || []).includes(tag))
  for (const lib of libsWithTag) {
    const newTags = lib.tags.filter(t => t !== tag)
    await store.updateLibrary(lib.id, { tags: newTags })
  }
  if (selectedTagFilter.value === tag) selectedTagFilter.value = ''
  await loadData()
}

function createTagFromManager() {
  tagManagerSearch.value = ''
}

// ---- Add/Edit Modal ----
const showAddModal = ref(false)
const addForm = ref({ title: '', desc: '', tags: '', isPublic: false })
const isEditMode = ref(false)
const editingId = ref(null)

function openAddModal() {
  isEditMode.value = false
  editingId.value = null
  addForm.value = { title: '', desc: '', tags: '', isPublic: false }
  showAddModal.value = true
}

function openEditModal(resource, e) {
  if (e) e.stopPropagation()
  activeMenuId.value = null
  isEditMode.value = true
  editingId.value = resource.id
  addForm.value = {
    title: resource.title,
    desc: resource.desc || '',
    tags: (resource.tags || []).join(', '),
    isPublic: resource._raw?.is_public === true,
  }
  showAddModal.value = true
}

async function submitAdd() {
  const { title, desc, tags, isPublic } = addForm.value
  if (!title.trim()) return
  const parsedTags = tags ? tags.split(/[,，\s]+/).filter(Boolean) : []

  try {
    if (isEditMode.value && editingId.value != null) {
      await store.updateLibrary(editingId.value, {
        name: title.trim(),
        description: desc.trim() || null,
        tags: parsedTags,
        isPublic: isAdmin.value ? isPublic : undefined,
      })
    } else {
      await store.createLibrary({
        name: title.trim(),
        description: desc.trim() || null,
        tags: parsedTags,
        isPublic: isAdmin.value ? isPublic : undefined,
      })
    }
    showAddModal.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '操作失败')
  }
}

async function deleteResource(resource, e) {
  if (e) e.stopPropagation()
  activeMenuId.value = null
  if (!confirm(`确定要删除知识库「${resource.title}」吗？`)) return
  try {
    await store.deleteLibrary(resource.id)
    await loadData()
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

function openDetail(resource) {
  router.push({
    path: `/knowledge-base/${resource.id}`,
    query: { title: resource.title }
  })
}

// ---- Click outside handler ----
function handleDocClick() {
  if (activeMenuId.value !== null) activeMenuId.value = null
  if (activeTagPopoverId.value !== null) activeTagPopoverId.value = null
  if (showTagFilterDropdown.value) showTagFilterDropdown.value = false
}

onMounted(() => document.addEventListener('click', handleDocClick))
onBeforeUnmount(() => document.removeEventListener('click', handleDocClick))

function getIconLetter(title) {
  return (title || 'K').charAt(0).toUpperCase()
}
</script>

<template>
  <div class="kb-page">
    <!-- Top bar -->
    <div class="kb-topbar">
      <div class="kb-filters">
        <!-- Type filter buttons -->
        <div class="filter-group">
          <button
            class="filter-btn"
            :class="{ active: activeFilter === 'all' }"
            @click="activeFilter = 'all'"
          >全部</button>
          <button
            class="filter-btn"
            :class="{ active: activeFilter === 'system' }"
            @click="activeFilter = 'system'"
          >系统知识库</button>
          <button
            class="filter-btn"
            :class="{ active: activeFilter === 'personal' }"
            @click="activeFilter = 'personal'"
          >{{ isAdmin ? '用户知识库' : '个人知识库' }}</button>
        </div>

        <!-- Tag filter dropdown -->
        <div class="tag-filter-wrap" @click.stop>
          <button class="tag-filter-btn" @click="showTagFilterDropdown = !showTagFilterDropdown">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            {{ selectedTagFilter || '全部标签' }}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <div v-if="showTagFilterDropdown" class="tag-filter-dropdown">
            <div class="tag-dd-item" :class="{ active: !selectedTagFilter }" @click="selectTagFilter('')">全部标签</div>
            <div
              v-for="tag in availableFilterTags"
              :key="tag"
              class="tag-dd-item"
              :class="{ active: selectedTagFilter === tag }"
              @click="selectTagFilter(tag)"
            >{{ tag }}</div>
          </div>
        </div>

        <!-- Search -->
        <div class="kb-search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input v-model="searchQuery" type="text" placeholder="搜索..." />
        </div>
      </div>

      <!-- Add button -->
      <button class="add-btn" @click="openAddModal()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        创建知识库
      </button>
    </div>

    <!-- Card grid -->
    <div class="kb-grid">
      <div
        v-for="resource in filteredResources"
        :key="resource.id"
        class="kb-card"
        @click="openDetail(resource)"
      >
        <!-- More button -->
        <button class="card-more-btn" @click.stop="toggleMenu(resource.id, $event)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
        </button>

        <!-- More dropdown -->
        <div v-if="activeMenuId === resource.id" class="card-menu" @click.stop>
          <button class="menu-item" @click="openEditModal(resource, $event)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            编辑
          </button>
          <button class="menu-item danger" @click="deleteResource(resource, $event)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            删除
          </button>
        </div>

        <!-- Icon -->
        <div class="card-icon" :style="{ backgroundColor: resource.iconColor + '18', color: resource.iconColor }">
          <span class="icon-letter">{{ getIconLetter(resource.title) }}</span>
        </div>

        <!-- Title + meta -->
        <div class="card-header">
          <h4 class="card-title">{{ resource.title }}</h4>
          <span class="card-type-badge" :class="resource.type">{{ resource.type === 'system' ? '系统' : '个人' }}</span>
        </div>

        <!-- Existing tags -->
        <div class="card-tags-row">
          <span v-for="tag in (resource.tags || [])" :key="tag" class="card-tag">
            {{ tag }}
            <button class="tag-remove" @click.stop="removeTagFromResource(resource, tag)" title="移除标签">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </span>
        </div>

        <!-- Description -->
        <p class="card-desc">{{ resource.desc }}</p>

        <!-- Add tag button + popover -->
        <div class="tag-popover-anchor" @click.stop>
          <button class="add-tag-btn" @click.stop="toggleTagPopover(resource.id, $event)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            添加标签
          </button>

          <!-- Tag popover -->
          <div v-if="activeTagPopoverId === resource.id" class="tag-popover" @click.stop>
            <div class="tag-pop-search">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input
                v-model="tagSearchQuery"
                type="text"
                placeholder="搜索或创建标签"
                @keydown.enter.prevent="createAndAddTag(resource)"
              />
              <button v-if="tagSearchQuery" class="clear-search" @click="tagSearchQuery = ''">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              </button>
            </div>

            <div class="tag-pop-body">
              <!-- No search: show existing tags or empty -->
              <template v-if="!tagSearchQuery.trim()">
                <template v-if="filteredTagOptions.length">
                  <button
                    v-for="t in filteredTagOptions"
                    :key="t"
                    class="tag-option"
                    :class="{ selected: (resource.tags || []).includes(t) }"
                    @click="addTagToResource(resource, t)"
                  >{{ t }}</button>
                </template>
                <div v-else class="tag-empty">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#C0C4CC" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                  <span>没有标签</span>
                </div>
              </template>

              <!-- Has search: show matches + create option -->
              <template v-else>
                <button
                  v-for="t in filteredTagOptions"
                  :key="t"
                  class="tag-option"
                  :class="{ selected: (resource.tags || []).includes(t) }"
                  @click="addTagToResource(resource, t)"
                >{{ t }}</button>
                <button
                  v-if="!store.userTags.includes(tagSearchQuery.trim())"
                  class="tag-option create"
                  @click="createAndAddTag(resource)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  创建 '{{ tagSearchQuery.trim() }}'
                </button>
              </template>
            </div>

            <!-- Divider + manage tags -->
            <div class="tag-pop-footer">
              <button class="manage-tags-btn" @click="openTagManager">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                管理标签
              </button>
            </div>
          </div>
        </div>

        <!-- Bottom info -->
        <!-- <div class="card-footer">
          <span class="card-stat">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
            {{ resource.fileCount || 0 }}
          </span>
          <span class="card-stat">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/></svg>
            {{ resource.charCount || 0 }}
          </span>
          <span class="card-time-sep">·</span>
          <span class="card-time">{{ resource.time }}</span>
        </div> -->
      </div>

      <!-- Empty state -->
      <div v-if="filteredResources.length === 0" class="kb-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
        <p>暂无知识库</p>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <Teleport to="body">
      <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
        <div class="modal-box">
          <h3>{{ isEditMode ? '编辑知识库' : '创建知识库' }}</h3>
          <div class="modal-form">
            <label for="kb-title">知识库名称</label>
            <input id="kb-title" v-model="addForm.title" type="text" placeholder="请输入知识库名称" />
            <label for="kb-desc">描述</label>
            <input id="kb-desc" v-model="addForm.desc" type="text" placeholder="选填" />
            <label for="kb-tags">标签（多个标签用逗号分隔）</label>
            <input id="kb-tags" v-model="addForm.tags" type="text" placeholder="教学设计, 语文" />
            <label v-if="isAdmin" class="modal-checkbox">
              <input v-model="addForm.isPublic" type="checkbox" />
              <span>公开知识库</span>
            </label>
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showAddModal = false">取消</button>
            <button class="btn-confirm" @click="submitAdd">{{ isEditMode ? '保存' : '添加' }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Tag Management Modal -->
    <Teleport to="body">
      <div v-if="showTagManager" class="modal-overlay" @click.self="showTagManager = false">
        <div class="modal-box tag-manager-modal">
          <h3>管理标签</h3>
          <div class="tm-search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <input v-model="tagManagerSearch" type="text" placeholder="搜索或创建标签..." @keydown.enter.prevent="createTagFromManager" />
          </div>
          <div class="tm-list">
            <div v-for="tag in filteredManagerTags" :key="tag" class="tm-item">
              <template v-if="editingTag === tag">
                <input
                  v-model="editingTagName"
                  class="tm-rename-input"
                  @keydown.enter.prevent="confirmRenameTag"
                  @keydown.escape="editingTag = null"
                  @blur="confirmRenameTag"
                />
              </template>
              <template v-else>
                <span class="tm-tag-name">{{ tag }}</span>
                <div class="tm-actions">
                  <button class="tm-act-btn" @click="startRenameTag(tag)" title="重命名">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button class="tm-act-btn danger" @click="deleteGlobalTag(tag)" title="删除">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </div>
              </template>
            </div>
            <div v-if="filteredManagerTags.length === 0 && !tagManagerSearch.trim()" class="tm-empty">暂无标签</div>
            <button
              v-if="tagManagerSearch.trim() && !store.userTags.includes(tagManagerSearch.trim())"
              class="tm-create-btn"
              @click="createTagFromManager"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              创建 '{{ tagManagerSearch.trim() }}'
            </button>
          </div>
          <div class="modal-actions">
            <button class="btn-confirm" @click="showTagManager = false">完成</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* ===== Page ===== */
.kb-page {
  min-height: 100%;
  background: #F8FAFC;
  padding: 24px 32px;
}

/* ===== Top bar ===== */
.kb-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.kb-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  overflow: hidden;
}

.filter-btn {
  padding: 8px 16px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #64748B;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.filter-btn:not(:last-child) {
  border-right: 1px solid #E5E7EB;
}

.filter-btn:hover {
  background: #F1F5F9;
  color: #1E293B;
}

.filter-btn.active {
  background: #2563EB;
  color: #fff;
}

/* Tag filter dropdown */
.tag-filter-wrap {
  position: relative;
}

.tag-filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: border-color 0.2s;
  white-space: nowrap;
}

.tag-filter-btn:hover {
  border-color: #CBD5E1;
}

.tag-filter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 160px;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  z-index: 50;
  max-height: 240px;
  overflow-y: auto;
  padding: 4px;
}

.tag-dd-item {
  padding: 8px 12px;
  font-size: 13px;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.tag-dd-item:hover {
  background: #F1F5F9;
}

.tag-dd-item.active {
  color: #2563EB;
  font-weight: 500;
}

/* Search */
.kb-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #fff;
  min-width: 320px;
  transition: border-color 0.2s;
}

.kb-search:focus-within {
  border-color: #2563EB;
}

.kb-search svg {
  color: #94A3B8;
  flex-shrink: 0;
}

.kb-search input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  outline: none;
  color: #1E293B;
}

.kb-search input::placeholder {
  color: #94A3B8;
}

/* Add button */
.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: #2563EB;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.add-btn:hover {
  background: #1D4ED8;
}

/* ===== Card Grid ===== */
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.kb-card {
  position: relative;
  background: #fff;
  border: 1px solid #F0F0F0;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.kb-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}

/* More button */
.card-more-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #F5F5F5;
  border-radius: 6px;
  cursor: pointer;
  color: #94A3B8;
  opacity: 0;
  transition: opacity 0.2s, background 0.15s;
}

.kb-card:hover .card-more-btn {
  opacity: 1;
}

.card-more-btn:hover {
  background: #E5E7EB;
  color: #475569;
}

/* Card menu */
.card-menu {
  position: absolute;
  top: 42px;
  right: 12px;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  z-index: 40;
  padding: 4px;
  min-width: 120px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  font-size: 13px;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.menu-item:hover {
  background: #F1F5F9;
}

.menu-item.danger {
  color: #EF4444;
}

.menu-item.danger:hover {
  background: #FEF2F2;
}

/* Card icon */
.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  font-weight: 700;
  font-size: 18px;
}

.icon-letter {
  line-height: 1;
}

/* Card header */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1E293B;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  flex-shrink: 0;
}

.card-type-badge.system {
  background: #DBEAFE;
  color: #2563EB;
}

.card-type-badge.personal {
  background: #FEF3C7;
  color: #D97706;
}

/* Card tags row */
.card-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
  min-height: 22px;
}

.card-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: #EFF6FF;
  color: #2563EB;
  font-size: 12px;
  border-radius: 4px;
  line-height: 1.4;
}

.tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  cursor: pointer;
  color: #93C5FD;
  padding: 0;
  width: 14px;
  height: 14px;
  border-radius: 2px;
  transition: color 0.15s;
}

.tag-remove:hover {
  color: #2563EB;
}

/* Description */
.card-desc {
  font-size: 13px;
  color: #64748B;
  line-height: 1.5;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Add tag button + popover */
.tag-popover-anchor {
  position: relative;
  margin-bottom: 12px;
}

.add-tag-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px dashed #D1D5DB;
  border-radius: 4px;
  background: transparent;
  font-size: 12px;
  color: #94A3B8;
  cursor: pointer;
  transition: all 0.15s;
}

.add-tag-btn:hover {
  background: #F5F5F5;
  color: #64748B;
  border-color: #94A3B8;
}

/* Tag popover */
.tag-popover {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 240px;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 60;
  overflow: hidden;
}

.tag-pop-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid #F0F0F0;
}

.tag-pop-search svg {
  color: #94A3B8;
  flex-shrink: 0;
}

.tag-pop-search input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  outline: none;
  color: #1E293B;
}

.tag-pop-search input::placeholder {
  color: #C0C4CC;
}

.clear-search {
  display: flex;
  align-items: center;
  border: none;
  background: none;
  color: #C0C4CC;
  cursor: pointer;
  padding: 0;
}

.clear-search:hover {
  color: #94A3B8;
}

.tag-pop-body {
  padding: 6px;
  max-height: 180px;
  overflow-y: auto;
}

.tag-option {
  display: block;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: none;
  font-size: 13px;
  color: #475569;
  text-align: left;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.tag-option:hover {
  background: #F1F5F9;
}

.tag-option.selected {
  color: #2563EB;
  font-weight: 500;
}

.tag-option.create {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2563EB;
}

.tag-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px 0;
  color: #C0C4CC;
  font-size: 13px;
}

.tag-pop-footer {
  border-top: 1px solid #F0F0F0;
  padding: 6px;
}

.manage-tags-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  background: none;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.manage-tags-btn:hover {
  background: #F1F5F9;
}

/* Card footer */
.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94A3B8;
}

.card-stat {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.card-time-sep {
  color: #D1D5DB;
}

/* Empty state */
.kb-empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
  color: #94A3B8;
  font-size: 14px;
}

/* ===== Modals ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 420px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.15);
}

.modal-box h3 {
  margin: 0 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

.modal-form label {
  display: block;
  font-size: 13px;
  color: #475569;
  margin-bottom: 6px;
  margin-top: 14px;
}

.modal-form label:first-of-type {
  margin-top: 0;
}

.modal-form input[type="text"] {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.2s;
}

.modal-form input[type="text"]:focus {
  border-color: #2563EB;
}

.modal-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  color: #334155;
  cursor: pointer;
}

.modal-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: #2563EB;
}

.modal-checkbox span {
  font-size: 13px;
  line-height: 1.4;
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
  border: 1px solid #E5E7EB;
  background: #F8FAFC;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: border-color 0.2s;
}

.select-file-btn:hover {
  border-color: #2563EB;
  color: #2563EB;
}

.selected-files {
  margin-left: 10px;
  font-size: 13px;
  color: #64748B;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.btn-cancel {
  padding: 8px 20px;
  border: 1px solid #E5E7EB;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-cancel:hover {
  background: #F8FAFC;
}

.btn-confirm {
  padding: 8px 20px;
  border: none;
  background: #2563EB;
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-confirm:hover {
  background: #1D4ED8;
}

/* ===== Tag Manager Modal ===== */
.tag-manager-modal {
  max-width: 480px;
}

.tm-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.tm-search:focus-within {
  border-color: #2563EB;
}

.tm-search svg {
  color: #94A3B8;
  flex-shrink: 0;
}

.tm-search input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  outline: none;
  color: #1E293B;
}

.tm-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 8px;
}

.tm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 6px;
  transition: background 0.15s;
}

.tm-item:hover {
  background: #F8FAFC;
}

.tm-tag-name {
  font-size: 14px;
  color: #1E293B;
}

.tm-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.tm-item:hover .tm-actions {
  opacity: 1;
}

.tm-act-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  color: #94A3B8;
  transition: all 0.15s;
}

.tm-act-btn:hover {
  background: #F1F5F9;
  color: #475569;
}

.tm-act-btn.danger:hover {
  background: #FEF2F2;
  color: #EF4444;
}

.tm-rename-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #2563EB;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.tm-empty {
  text-align: center;
  padding: 24px;
  color: #94A3B8;
  font-size: 13px;
}

.tm-create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  background: none;
  font-size: 13px;
  color: #2563EB;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.tm-create-btn:hover {
  background: #EFF6FF;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .kb-page {
    padding: 16px;
  }
  .kb-topbar {
    flex-direction: column;
    align-items: stretch;
  }
  .kb-filters {
    flex-direction: column;
  }
  .kb-grid {
    grid-template-columns: 1fr;
  }
}
</style>

