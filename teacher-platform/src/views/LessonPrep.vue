<script setup>
import { ref, computed } from 'vue'
import LessonPrepPpt from './LessonPrepPpt.vue'
import LessonPrepAnimation from './LessonPrepAnimation.vue'
import LessonPrepKnowledge from './LessonPrepKnowledge.vue'
import LessonPrepData from './LessonPrepData.vue'

const activeTab = ref('ppt')
const sidebarCollapsed = ref(false)

const tabs = [
  { id: 'ppt', label: 'PPT与教案生成' },
  { id: 'animation', label: '动画与小游戏制作' },
  { id: 'knowledge', label: '知识图谱构建' },
  { id: 'data', label: '数据分析' }
]

const currentComponent = computed(() => {
  const map = {
    ppt: LessonPrepPpt,
    animation: LessonPrepAnimation,
    knowledge: LessonPrepKnowledge,
    data: LessonPrepData
  }
  return map[activeTab.value]
})
</script>

<template>
  <div class="lesson-prep-page">
    <div class="lesson-prep-body">
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-header">
          <button type="button" class="sidebar-toggle" title="伸缩侧栏" @click="sidebarCollapsed = !sidebarCollapsed" aria-label="伸缩侧栏">
            <svg class="toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="4" x2="12" y2="20"/>
              <path d="M8 9l-3 3 3 3"/>
              <path d="M16 9l3 3-3 3"/>
            </svg>
          </button>
        </div>
        <nav class="sidebar-nav">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="nav-item"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            <span class="nav-icon" aria-hidden="true">
              <!-- PPT与教案：显示器+文档 -->
              <template v-if="tab.id === 'ppt'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4"/>
                  <path d="M14 8h2a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" fill="currentColor" fill-opacity="0.3"/>
                </svg>
              </template>
              <!-- 动画与小游戏：手柄 -->
              <template v-else-if="tab.id === 'animation'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M6 12h4M8 10v4M15 13h.01M18 11h.01M17 15h.01M20 10h.01"/>
                  <path d="M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v4a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8z"/>
                </svg>
              </template>
              <!-- 知识图谱：节点连线 -->
              <template v-else-if="tab.id === 'knowledge'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="3" width="6" height="6" rx="1"/>
                  <rect x="15" y="3" width="6" height="6" rx="1"/>
                  <rect x="9" y="15" width="6" height="6" rx="1"/>
                  <path d="M9 18H6a3 3 0 0 1 0-6h0M15 18h3a3 3 0 0 0 0-6h0M9 15V9a3 3 0 0 1 6 0v6"/>
                </svg>
              </template>
              <!-- 数据分析：柱状图 -->
              <template v-else-if="tab.id === 'data'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 3v18h18"/>
                  <path d="M7 16v-5M11 16v-8M15 16v-11M19 16v-3"/>
                </svg>
              </template>
            </span>
            <span class="nav-label">{{ tab.label }}</span>
          </button>
        </nav>
      </aside>

      <main class="main-content">
        <component :is="currentComponent" />
      </main>
    </div>
  </div>
</template>

<style scoped>
.lesson-prep-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.lesson-prep-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 220px;
  min-width: 220px;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: width 0.2s, min-width 0.2s;
}

.sidebar.collapsed {
  width: 56px;
  min-width: 56px;
}

.sidebar-header {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 10px;
  border-bottom: 1px solid #f1f5f9;
}

.sidebar-toggle {
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: transparent;
  color: #475569;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-toggle:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.toggle-icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s;
}

.sidebar.collapsed .toggle-icon {
  transform: rotate(180deg);
}

.sidebar.collapsed .nav-label {
  overflow: hidden;
  width: 0;
  opacity: 0;
  white-space: nowrap;
}

.sidebar.collapsed .sidebar-nav {
  padding: 12px 8px;
}

.sidebar.collapsed .nav-item {
  padding: 10px;
  justify-content: center;
}

.sidebar-nav {
  padding: 20px 13px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: none;
  background: transparent;
  border-radius: 10px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
  position: relative;
}

.nav-item:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.nav-item.active {
  background: #e8eef7;
  color: #2563eb;
  font-weight: 500;
}

.nav-item.active .nav-icon {
  color: #2563eb;
}

.nav-label {
  display: inline-block;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: inherit;
}

.nav-icon svg {
  width: 100%;
  height: 100%;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
