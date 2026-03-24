<template>
  <Teleport to="body">
    <div class="search-backdrop" @click.self="$emit('close')">
      <div class="search-popover">
        <input
          ref="searchInput"
          v-model="query"
          type="text"
          placeholder="输入节点名字..."
          class="search-input"
          @keyup.enter="handleSearch"
          @input="handleInput"
        />
        <div v-if="results.length" class="search-results">
          <div
            v-for="node in results"
            :key="node.id"
            class="search-item"
            @click="selectNode(node)"
          >
            <span class="search-dot" :style="{ backgroundColor: node._color }"></span>
            <span>{{ node.name }}</span>
            <span class="search-cat">{{ node.category }}</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'

const emit = defineEmits(['search', 'close'])

const query = ref('')
const results = ref([])
const searchInput = ref(null)

// 注入 graphData 从父组件
const graphData = inject('graphData', { value: { nodes: [] } })
const getCategoryColor = inject('getCategoryColor', () => '#fff')

function handleInput() {
  if (!query.value.trim()) {
    results.value = []
    return
  }
  results.value = graphData.value.nodes
    .filter(n => n.name.includes(query.value.trim()))
    .slice(0, 8)
    .map(n => ({ ...n, _color: getCategoryColor(n.category) }))
}

function handleSearch() {
  if (query.value.trim()) {
    emit('search', query.value.trim())
  }
}

function selectNode(node) {
  emit('search', node.name)
}

onMounted(() => {
  searchInput.value?.focus()
})
</script>

<style scoped>
.search-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.search-popover {
  position: fixed;
  bottom: 80px;
  right: 26%;
  background: rgba(10, 15, 30, 0.92);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 10px;
  padding: 10px;
  backdrop-filter: blur(12px);
  min-width: 240px;
}

.search-input {
  width: 100%;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.4);
  border-radius: 6px;
  padding: 8px 12px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.search-input::placeholder {
  color: rgba(100, 116, 139, 0.6);
}

.search-input:focus {
  border-color: rgba(96, 165, 250, 0.5);
}

.search-results {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  color: rgba(203, 213, 225, 0.9);
  font-size: 12px;
  transition: background 0.2s;
}

.search-item:hover {
  background: rgba(51, 65, 85, 0.4);
}

.search-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.search-cat {
  margin-left: auto;
  color: rgba(100, 116, 139, 0.6);
  font-size: 11px;
}
</style>
