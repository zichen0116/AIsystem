<template>
  <div class="knowledge-graph-page">
    <!-- 3D 图谱容器 -->
    <div ref="graphContainer" class="graph-container"></div>

    <!-- 底部控制台 -->
    <GraphConsole
      :nodes="topNodes"
      :categories="kg.categories.value"
      :hidden-categories="kg.hiddenCategories.value"
      :is-rotating="kg.isRotating.value"
      :get-category-color="kg.getCategoryColor"
      @focus-node="kg.focusNode"
      @toggle-rotation="kg.toggleRotation"
      @toggle-category="kg.toggleCategory"
      @search="kg.searchNode"
    />
  </div>
</template>

<script setup>
import { ref, computed, provide, onMounted, onActivated, onDeactivated, onUnmounted } from 'vue'
import { apiRequest } from '../api/http.js'
import { useKnowledgeGraph } from '../composables/useKnowledgeGraph.js'
import GraphConsole from '../components/knowledge-graph/GraphConsole.vue'

const graphContainer = ref(null)
const kg = useKnowledgeGraph(graphContainer)

// provide 给子组件（SearchPopover 等）使用，必须在 setup 顶层同步调用
provide('graphData', kg.graphData)
provide('getCategoryColor', kg.getCategoryColor)

// Top 20 节点（按关联数降序）
const topNodes = computed(() => {
  const nodes = [...(kg.graphData.value.nodes || [])]
  nodes.sort((a, b) => (b.val || 0) - (a.val || 0))
  return nodes.slice(0, 20)
})

// 加载数据
async function loadGraphData() {
  try {
    const data = await apiRequest('/api/v1/knowledge/graph?limit=100')
    kg.initGraph(data)
  } catch (err) {
    console.error('Failed to load knowledge graph:', err)
  }
}

onMounted(() => {
  loadGraphData()
})

onActivated(() => {
  kg.resume()
})

onDeactivated(() => {
  kg.pause()
})

onUnmounted(() => {
  kg.destroy()
})
</script>

<style scoped>
.knowledge-graph-page {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000000;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
}

/* 覆盖 3d-force-graph 默认的 tooltip 样式 */
.graph-container :deep(.graph-tooltip) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  pointer-events: none;
}
</style>
