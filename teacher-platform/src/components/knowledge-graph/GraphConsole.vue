<template>
  <div class="graph-console">
    <!-- 节点排行榜 -->
    <div class="node-grid">
      <div
        v-for="(node, i) in nodes"
        :key="node.id"
        class="node-item"
        @click="$emit('focusNode', node)"
      >
        <span class="node-rank">{{ i + 1 }}</span>
        <span
          class="node-dot"
          :style="{ backgroundColor: getCategoryColor(node.category), boxShadow: `0 0 6px ${getCategoryColor(node.category)}` }"
        ></span>
        <span class="node-name">{{ node.name }}</span>
        <span class="node-count">{{ node.val || 0 }}</span>
      </div>
    </div>

    <!-- 功能按钮 -->
    <div class="console-actions">
      <button class="console-btn" :class="{ active: isRotating }" @click="$emit('toggleRotation')">
        {{ isRotating ? '停止旋转' : '开始旋转' }}
      </button>
      <button class="console-btn" :class="{ active: showFilter }" @click="showFilter = !showFilter">
        标签筛选
      </button>
      <button class="console-btn" @click="showSearch = !showSearch">
        搜索节点
      </button>
    </div>

    <!-- 筛选浮层 -->
    <FilterPopover
      v-if="showFilter"
      :categories="categories"
      :hidden-categories="hiddenCategories"
      @toggle="handleToggleCategory"
      @close="showFilter = false"
    />

    <!-- 搜索浮层 -->
    <SearchPopover
      v-if="showSearch"
      @search="handleSearch"
      @close="showSearch = false"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FilterPopover from './FilterPopover.vue'
import SearchPopover from './SearchPopover.vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  hiddenCategories: { type: Object, default: () => new Set() },
  isRotating: { type: Boolean, default: true },
  getCategoryColor: { type: Function, required: true },
})

const emit = defineEmits(['focusNode', 'toggleRotation', 'toggleCategory', 'search'])

const showFilter = ref(false)
const showSearch = ref(false)

function handleToggleCategory(category) {
  emit('toggleCategory', category)
}

function handleSearch(name) {
  emit('search', name)
  showSearch.value = false
}
</script>

<style scoped>
.graph-console {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 52%;
  max-width: 720px;
  background: rgba(0, 0, 0, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 16px 20px;
  backdrop-filter: blur(16px);
  z-index: 10;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px 10px;
  margin-bottom: 12px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.2s, transform 0.15s;
}

.node-item:hover {
  background: rgba(255, 255, 255, 0.06);
  transform: translateX(2px);
}

.node-rank {
  color: rgba(255, 255, 255, 0.2);
  font-size: 10px;
  font-weight: 600;
  min-width: 14px;
  text-align: right;
  flex-shrink: 0;
}

.node-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-name {
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.node-count {
  color: rgba(255, 255, 255, 0.3);
  font-size: 10px;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.console-actions {
  display: flex;
  gap: 8px;
}

.console-btn {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 7px 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}

.console-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
}

.console-btn.active {
  background: rgba(255, 107, 74, 0.15);
  border-color: rgba(255, 107, 74, 0.3);
  color: #ff8a65;
}

/* ── 小屏适配 ── */
@media (max-width: 768px) {
  .graph-console {
    width: 92%;
    padding: 10px 12px;
  }

  .node-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .node-item:nth-child(n+11) {
    display: none;
  }

  .console-btn {
    font-size: 0;
    padding: 8px;
  }

  .console-btn::before {
    font-size: 14px;
  }

  .console-btn:nth-child(1)::before { content: '⏸'; }
  .console-btn:nth-child(2)::before { content: '🏷'; }
  .console-btn:nth-child(3)::before { content: '🔍'; }
}
</style>
