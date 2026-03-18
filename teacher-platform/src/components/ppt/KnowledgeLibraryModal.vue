<template>
  <div class="kb-modal-overlay" @click.self="$emit('close')">
    <div class="kb-modal">
      <div class="kb-header">
        <h3>选择知识库</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>
      <div v-if="loading" class="kb-loading">加载中...</div>
      <div v-else-if="!libraries.length" class="kb-empty">暂无知识库</div>
      <div v-else class="kb-list">
        <label
          v-for="lib in libraries"
          :key="lib.id"
          class="kb-item"
          :class="{ selected: selectedIds.includes(lib.id) }"
        >
          <input
            type="checkbox"
            :checked="selectedIds.includes(lib.id)"
            @change="toggle(lib.id)"
          />
          <span class="kb-name">{{ lib.name }}</span>
          <span class="kb-count">{{ lib.asset_count || 0 }} 个文件</span>
        </label>
      </div>
      <div class="kb-footer">
        <button class="kb-cancel" @click="$emit('close')">取消</button>
        <button class="kb-confirm" @click="confirm">确定 ({{ selectedIds.length }})</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiRequest } from '../../api/http.js'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue', 'close'])

const libraries = ref([])
const loading = ref(false)
const selectedIds = ref([...props.modelValue])

async function loadLibraries() {
  loading.value = true
  try {
    const data = await apiRequest('/api/v1/libraries/')
    libraries.value = data || []
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

onMounted(loadLibraries)
</script>

<style scoped>
.kb-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.kb-modal {
  background: #fff;
  border-radius: 12px;
  width: 480px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e5e5;
}
.kb-header h3 { margin: 0; font-size: 16px; }
.close-btn { border: none; background: none; font-size: 20px; color: #666; cursor: pointer; }
.kb-loading, .kb-empty { padding: 40px; text-align: center; color: #999; }
.kb-list { flex: 1; overflow-y: auto; padding: 12px 20px; }
.kb-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  transition: background 0.15s;
}
.kb-item:hover { background: #f5f7fa; }
.kb-item.selected { background: #eef3ff; }
.kb-name { flex: 1; font-size: 14px; color: #333; }
.kb-count { font-size: 12px; color: #999; }
.kb-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #e5e5e5;
}
.kb-cancel {
  padding: 8px 20px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.kb-confirm {
  padding: 8px 20px;
  border: none;
  background: #3a61ea;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
</style>
