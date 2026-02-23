<script setup>
import { ref, computed } from 'vue'

const coursewareList = ref([
  { id: 1, name: '牛顿力学基础', type: 'pdf', size: '2.4 MB', date: '2025-02-14' },
  { id: 2, name: '量子物理导论', type: 'pptx', size: '5.1 MB', date: '2025-02-13' },
  { id: 3, name: '化学反应方程式', type: 'docx', size: '1.2 MB', date: '2025-02-12' },
  { id: 4, name: '几何证明专题', type: 'pdf', size: '890 KB', date: '2025-02-11' },
  { id: 5, name: '英语语法总结', type: 'pptx', size: '3.6 MB', date: '2025-02-10' }
])

const filterType = ref('all')
const filterDate = ref('all')
const showAddModal = ref(false)

const typeOptions = [
  { value: 'all', label: '全部类型' },
  { value: 'pdf', label: 'PDF' },
  { value: 'pptx', label: 'PPT' },
  { value: 'docx', label: 'Word' }
]

const dateOptions = [
  { value: 'all', label: '全部时间' },
  { value: 'week', label: '近一周' },
  { value: 'month', label: '近一月' },
  { value: 'year', label: '近一年' }
]

const filteredList = computed(() => {
  let list = [...coursewareList.value]
  
  if (filterType.value !== 'all') {
    list = list.filter(item => item.type === filterType.value)
  }
  
  if (filterDate.value !== 'all') {
    const now = new Date()
    list = list.filter(item => {
      const itemDate = new Date(item.date)
      if (filterDate.value === 'week') return (now - itemDate) / (1000 * 60 * 60 * 24) <= 7
      if (filterDate.value === 'month') return (now - itemDate) / (1000 * 60 * 60 * 24) <= 30
      if (filterDate.value === 'year') return (now - itemDate) / (1000 * 60 * 60 * 24) <= 365
      return true
    })
  }
  
  return list
})

function getTypeLabel(type) {
  return typeOptions.find(o => o.value === type)?.label || type
}
</script>

<template>
  <div class="courseware-page">
    <div class="courseware-content">
    <div class="toolbar">
      <div class="filters">
        <select v-model="filterType" class="filter-select">
          <option v-for="opt in typeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <select v-model="filterDate" class="filter-select">
          <option v-for="opt in dateOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <button class="add-btn" @click="showAddModal = true">+ 添加课件</button>
    </div>

    <div class="courseware-grid">
      <div v-for="item in filteredList" :key="item.id" class="courseware-card">
        <div class="card-icon">{{ item.type === 'pdf' ? '📄' : item.type === 'pptx' ? '📊' : '📝' }}</div>
        <h3>{{ item.name }}</h3>
        <p class="meta">{{ getTypeLabel(item.type) }} · {{ item.size }}</p>
        <p class="date">{{ item.date }}</p>
      </div>
      <div class="courseware-card add-card" @click="showAddModal = true">
        <span class="add-icon">+</span>
        <p>添加新课件</p>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
        <div class="modal-box">
          <h3>添加课件</h3>
          <div class="upload-zone">
            <p>拖拽文件到这里或点击上传</p>
            <p class="hint">支持 PDF、PPT、Word 格式</p>
          </div>
          <div class="modal-actions">
            <button class="cancel-btn" @click="showAddModal = false">取消</button>
            <button class="confirm-btn">上传</button>
          </div>
        </div>
      </div>
    </Teleport>
    </div>
  </div>
</template>

<style scoped>
.courseware-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.courseware-content {
  flex: 1;
  padding: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.filters {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  font-size: 14px;
}

.add-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.add-btn:hover {
  background: #2563eb;
}

.courseware-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

.courseware-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
  cursor: pointer;
}

.courseware-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-icon {
  font-size: 2.5rem;
  margin-bottom: 12px;
}

.courseware-card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta, .date {
  font-size: 0.875rem;
  color: #64748b;
}

.add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
}

.add-icon {
  font-size: 2rem;
  color: #94a3b8;
  margin-bottom: 8px;
}

.add-card p {
  color: #94a3b8;
  font-size: 0.9rem;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  width: 400px;
}

.modal-box h3 {
  margin-bottom: 24px;
  color: #1e293b;
}

.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  margin-bottom: 24px;
  background: #f8fafc;
}

.upload-zone p {
  color: #64748b;
}

.upload-zone .hint {
  font-size: 0.875rem;
  margin-top: 8px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn, .confirm-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.cancel-btn {
  background: #f1f5f9;
  border: none;
  color: #475569;
}

.confirm-btn {
  background: #3b82f6;
  border: none;
  color: #fff;
}
</style>
