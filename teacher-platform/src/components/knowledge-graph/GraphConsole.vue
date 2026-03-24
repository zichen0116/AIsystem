<template>
  <div class="graph-console">
    <!-- 节点网格 -->
    <div class="node-grid">
      <div
        v-for="node in nodes"
        :key="node.id"
        class="node-item"
        @click="$emit('focusNode', node)"
      >
        <span
          class="node-dot"
          :style="{ backgroundColor: getCategoryColor(node.category) }"
        ></span>
        <span class="node-name">{{ node.name }}</span>
        <span class="node-count">{{ node.val || 0 }}</span>
      </div>
    </div>

    <!-- 功能按钮 -->
    <div class="console-actions">
      <button class="console-btn" @click="$emit('toggleRotation')">
        {{ isRotating ? '停止旋转' : '开始旋转' }}
      </button>
      <button class="console-btn" @click="showFilter = !showFilter">
        标签筛选
      </button>
      <button class="console-btn" @click="showSearch = !showSearch">
        搜索名字
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
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 50%;
  background: rgba(10, 15, 30, 0.85);
  border: 1px solid rgba(100, 116, 139, 0.25);
  border-radius: 12px;
  padding: 14px 18px;
  backdrop-filter: blur(8px);
  z-index: 10;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px 12px;
  margin-bottom: 10px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.node-item:hover {
  background: rgba(51, 65, 85, 0.4);
}

.node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-name {
  color: rgba(226, 232, 240, 0.9);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.node-count {
  color: rgba(100, 116, 139, 0.7);
  font-size: 10px;
  flex-shrink: 0;
}

.console-actions {
  display: flex;
  gap: 8px;
}

.console-btn {
  flex: 1;
  background: rgba(51, 65, 85, 0.4);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 6px;
  padding: 6px 0;
  color: rgba(148, 163, 184, 0.9);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.console-btn:hover {
  background: rgba(71, 85, 105, 0.5);
}

/* ── 小屏适配 ── */
@media (max-width: 768px) {
  .graph-console {
    width: 90%;
    padding: 10px 12px;
  }

  .node-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  /* 小屏只显示 Top 10 */
  .node-item:nth-child(n+11) {
    display: none;
  }

  .console-btn {
    font-size: 0;
    padding: 8px;
  }

  /* 图标替代文字 */
  .console-btn::before {
    font-size: 14px;
  }

  .console-btn:nth-child(1)::before { content: '⏸'; }
  .console-btn:nth-child(2)::before { content: '🏷'; }
  .console-btn:nth-child(3)::before { content: '🔍'; }
}
</style>
