<template>
  <div class="knowledge-modal" @click.self="$emit('close')">
    <div ref="dialogRef" class="knowledge-dialog" role="dialog" aria-modal="true">
      <div class="knowledge-dialog-head">
        <div class="knowledge-title">选择知识库</div>
        <button class="knowledge-close" type="button" @click="$emit('close')" aria-label="关闭">&times;</button>
      </div>
      <div class="knowledge-dialog-body">
        <div class="knowledge-subtitle">
          可多选知识库，AI 将优先引用已勾选来源（已选 {{ selectedIds.length }} 项）
        </div>

        <div v-if="loading" class="kb-loading">加载中...</div>
        <div v-else class="knowledge-groups">
          <!-- 系统知识库 -->
          <section class="knowledge-group">
            <div class="group-header">
              <div class="group-title-row">
                <span class="group-title">系统知识库</span>
                <span class="group-tag">官方</span>
              </div>
              <span class="group-count">{{ systemSelected }}/{{ systemLibraries.length }}</span>
            </div>
            <div class="group-list">
              <label
                v-for="lib in systemLibraries"
                :key="lib.id"
                class="knowledge-card"
                :class="{ selected: selectedIds.includes(lib.id) }"
              >
                <input type="checkbox" :checked="selectedIds.includes(lib.id)" @change="toggle(lib.id)" />
                <span class="kb-icon">{{ lib.icon || '📘' }}</span>
                <span class="kb-meta">
                  <span class="kb-name">{{ lib.name }}</span>
                  <span class="kb-desc">{{ lib.description || `${lib.asset_count || 0} 个文件` }}</span>
                </span>
                <span class="kb-check" />
              </label>
            </div>
          </section>

          <!-- 用户知识库 -->
          <section class="knowledge-group">
            <div class="group-header">
              <div class="group-title-row">
                <span class="group-title">用户知识库</span>
                <span class="group-tag">我的</span>
              </div>
              <span class="group-create">+ 新建知识库</span>
            </div>
            <div class="group-list">
              <label
                v-for="lib in userLibraries"
                :key="lib.id"
                class="knowledge-card"
                :class="{ selected: selectedIds.includes(lib.id) }"
              >
                <input type="checkbox" :checked="selectedIds.includes(lib.id)" @change="toggle(lib.id)" />
                <span class="kb-icon">{{ lib.icon || '📒' }}</span>
                <span class="kb-meta">
                  <span class="kb-name">{{ lib.name }}</span>
                  <span class="kb-desc">{{ lib.description || `${lib.asset_count || 0} 个文件` }}</span>
                </span>
                <span class="kb-check" />
              </label>
              <div v-if="!userLibraries.length" class="kb-empty-hint">暂无用户知识库</div>
            </div>
          </section>
        </div>
      </div>
      <div class="knowledge-dialog-actions">
        <button class="modal-btn" type="button" @click="$emit('close')">取消</button>
        <button class="modal-btn primary" type="button" @click="confirm">确定</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { apiRequest } from '../../api/http.js'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  triggerEl: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'close'])

const dialogRef = ref(null)
const libraries = ref([])
const loading = ref(false)
const selectedIds = ref([...props.modelValue])

const systemLibraries = computed(() => libraries.value.filter(l => l.is_system))
const userLibraries = computed(() => libraries.value.filter(l => !l.is_system))
const systemSelected = computed(() => systemLibraries.value.filter(l => selectedIds.value.includes(l.id)).length)

async function loadLibraries() {
  loading.value = true
  try {
    const data = await apiRequest('/api/v1/libraries/')
    libraries.value = (data || []).map(lib => ({
      ...lib,
      is_system: lib.is_system ?? false,
      icon: lib.icon || (lib.is_system ? '📘' : '📒'),
    }))
  } catch (e) {
    console.error('加载知识库失败:', e)
  } finally {
    loading.value = false
  }
}

function toggle(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function confirm() {
  emit('update:modelValue', [...selectedIds.value])
  emit('close')
}

function placeDialog() {
  if (!dialogRef.value) return
  const dialog = dialogRef.value
  const dw = dialog.offsetWidth
  const dh = dialog.offsetHeight

  if (!props.triggerEl) {
    dialog.style.left = Math.max(16, (window.innerWidth - dw) / 2) + 'px'
    dialog.style.top = Math.max(16, (window.innerHeight - dh) / 2) + 'px'
    return
  }

  const rect = props.triggerEl.getBoundingClientRect()
  let left = rect.left + rect.width / 2 - dw / 2
  left = Math.max(16, Math.min(left, window.innerWidth - dw - 16))
  let top = rect.bottom + 10
  if (top + dh > window.innerHeight - 16) {
    top = Math.max(16, rect.top - dh - 10)
  }
  dialog.style.left = left + 'px'
  dialog.style.top = top + 'px'
}

onMounted(async () => {
  await loadLibraries()
  await nextTick()
  placeDialog()
})
</script>

<style scoped>
.knowledge-modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 300;
}
.knowledge-dialog {
  position: fixed;
  width: min(720px, calc(100vw - 32px));
  background: #fff;
  border-radius: 14px;
  border: 1px solid #dfe6f2;
  box-shadow: 0 18px 42px rgba(20, 26, 44, 0.2);
  overflow: hidden;
}
.knowledge-dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid #e8edf6;
}
.knowledge-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1f35;
}
.knowledge-close {
  border: none;
  background: none;
  color: #9aa4b5;
  font-size: 32px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}
.knowledge-close:hover { color: #4f5f78; }
.knowledge-dialog-body {
  padding: 16px 24px 0;
}
.knowledge-subtitle {
  font-size: 14px;
  color: #6d7689;
  margin-bottom: 14px;
}
.kb-loading {
  padding: 40px;
  text-align: center;
  color: #999;
}
.knowledge-groups {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-height: 420px;
  overflow-y: auto;
  padding-bottom: 18px;
}
.knowledge-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.group-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.group-title {
  font-size: 15px;
  font-weight: 600;
  color: #5f6f8b;
}
.group-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3a61ea;
  font-size: 12px;
  font-weight: 600;
}
.group-create {
  font-size: 12px;
  color: #3a61ea;
  cursor: pointer;
}
.group-create:hover { text-decoration: underline; }
.group-count {
  font-size: 12px;
  color: #8b96aa;
}
.group-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.knowledge-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid #dbe2ef;
  border-radius: 12px;
  background: #fff;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.knowledge-card:hover {
  border-color: #b6c7ff;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08);
}
.knowledge-card.selected {
  border-color: #3a61ea;
  background: #f8fbff;
  box-shadow: 0 0 0 1px rgba(58, 97, 234, 0.16);
}
.knowledge-card input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.kb-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #eef2ff;
  color: #3a61ea;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.kb-meta {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.kb-name {
  font-size: 16px;
  font-weight: 600;
  color: #23293a;
  line-height: 1.2;
}
.kb-desc {
  font-size: 13px;
  color: #74809a;
  line-height: 1.4;
}
.kb-check {
  width: 24px;
  height: 24px;
  border: 2px solid #c7d2e5;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
  transition: all 0.2s;
}
.knowledge-card.selected .kb-check {
  border-color: #3a61ea;
  background: #3a61ea;
}
.knowledge-card.selected .kb-check::before {
  content: "✓";
}
.kb-empty-hint {
  padding: 16px;
  text-align: center;
  color: #999;
  font-size: 13px;
}
.knowledge-dialog-actions {
  border-top: 1px solid #e8edf6;
  padding: 14px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: #fbfcff;
}
.modal-btn {
  min-width: 88px;
  padding: 9px 18px;
  border-radius: 8px;
  font-size: 14px;
  border: 1px solid #d7e0ef;
  background: #fff;
  color: #667084;
  cursor: pointer;
  transition: all 0.2s;
}
.modal-btn:hover {
  border-color: #3a61ea;
  color: #3a61ea;
}
.modal-btn.primary {
  background: #3a61ea;
  border-color: #3a61ea;
  color: #fff;
}
.modal-btn.primary:hover {
  background: #2a4bc8;
  border-color: #2a4bc8;
}
</style>

