<template>
  <div class="template-selector" :class="{ inline }">
    <div v-if="!inline" class="template-header">
      <h3>选择模板</h3>
      <button class="close-btn" @click="$emit('close')">&times;</button>
    </div>
    <div v-if="inline" class="section-tabs">
      <div class="tab active">选择模板</div>
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
        <div v-else class="template-preview" :style="gradientStyle(t)">
          {{ t.title || '模板' }}
        </div>
        <div class="template-name">{{ t.title || '未命名模板' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTemplates } from '../../api/ppt.js'

const props = defineProps({
  modelValue: { type: String, default: null },
  inline: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'close', 'select'])

const templates = ref([])
const loading = ref(false)
const selectedId = ref(props.modelValue)

const gradients = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
  'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
  'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)',
]

function gradientStyle(t) {
  const idx = templates.value.indexOf(t) % gradients.length
  return { background: gradients[idx] }
}

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
.template-selector.inline {
  height: auto;
  width: 100%;
  max-width: 1000px;
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
.section-tabs {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  border-bottom: 2px solid #e5e5e5;
}
.tab {
  padding: 12px 0;
  font-size: 15px;
  color: #666;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}
.tab.active {
  color: #3a61ea;
  border-bottom-color: #3a61ea;
  font-weight: 500;
}
.template-loading {
  padding: 40px;
  text-align: center;
  color: #999;
}
.template-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 0;
  overflow-y: auto;
  flex: 1;
}
.template-selector:not(.inline) .template-grid {
  padding: 20px;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
}
.template-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border: 2px solid transparent;
}
.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}
.template-card.selected {
  border-color: #3a61ea;
}
.template-cover {
  width: 100%;
  aspect-ratio: 16/9;
  object-fit: cover;
}
.template-preview {
  width: 100%;
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
}
.template-name {
  padding: 12px;
  font-size: 14px;
  text-align: center;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
