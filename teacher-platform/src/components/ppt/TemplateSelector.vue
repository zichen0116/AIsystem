<template>
  <div class="template-selector">
    <div class="template-header">
      <h3>选择模板</h3>
      <button class="close-btn" @click="$emit('close')">&times;</button>
    </div>
    <div v-if="loading" class="template-loading">加载中...</div>
    <div v-else class="template-grid">
      <div
        v-for="t in templates"
        :key="t.id"
        class="template-card"
        :class="{ selected: selectedId === t.id }"
        @click="select(t)"
      >
        <img v-if="t.cover_url" :src="t.cover_url" class="template-cover" alt="" />
        <div v-else class="template-placeholder" />
        <span class="template-title">{{ t.title || '未命名模板' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTemplates } from '../../api/ppt.js'

const props = defineProps({
  modelValue: { type: String, default: null },
})
const emit = defineEmits(['update:modelValue', 'close', 'select'])

const templates = ref([])
const loading = ref(false)
const selectedId = ref(props.modelValue)

async function loadTemplates() {
  loading.value = true
  try {
    const data = await getTemplates(1, 40)
    templates.value = data.templates || []
  } catch (e) {
    console.error('加载模板失败:', e)
  } finally {
    loading.value = false
  }
}

function select(t) {
  selectedId.value = t.id
  emit('update:modelValue', t.id)
  emit('select', t)
}

onMounted(loadTemplates)
</script>

<style scoped>
.template-selector {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.template-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e5e5;
}
.template-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.close-btn {
  border: none;
  background: none;
  font-size: 20px;
  color: #666;
  cursor: pointer;
}
.template-loading {
  padding: 40px;
  text-align: center;
  color: #999;
}
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}
.template-card {
  border: 2px solid transparent;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fff;
}
.template-card:hover {
  border-color: #c5d5f5;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.template-card.selected {
  border-color: #3a61ea;
  box-shadow: 0 0 0 1px #3a61ea;
}
.template-cover {
  width: 100%;
  aspect-ratio: 16/9;
  object-fit: cover;
}
.template-placeholder {
  width: 100%;
  aspect-ratio: 16/9;
  background: linear-gradient(135deg, #e0e7ff, #f0f4ff);
}
.template-title {
  display: block;
  padding: 8px 10px;
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
