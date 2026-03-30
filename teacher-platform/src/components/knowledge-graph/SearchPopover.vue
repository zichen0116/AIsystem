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
            <span class="search-dot" :style="{ backgroundColor: node._color, boxShadow: `0 0 4px ${node._color}` }"></span>
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
  right: 24%;
  background: rgba(0, 0, 0, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(16px);
  min-width: 260px;
}

.search-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 9px 14px;
  color: #f0f0f0;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.search-input:focus {
  border-color: rgba(255, 107, 74, 0.5);
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
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  transition: background 0.2s;
}

.search-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.search-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.search-cat {
  margin-left: auto;
  color: rgba(255, 255, 255, 0.3);
  font-size: 11px;
}
</style>
