<script setup>
import { ref, provide } from 'vue'
import TopNav from './TopNav.vue'

// 全局侧栏折叠状态（提供给子组件注入使用）
const sidebarCollapsed = ref(false)
provide('sidebarCollapsed', sidebarCollapsed)
</script>

<template>
  <div class="layout">
    <TopNav />
    <!-- 悬浮的侧栏切换按钮，置于页面之上 -->
    <button class="floating-sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'" aria-label="切换侧栏">
      <svg class="floating-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="4" x2="12" y2="20"/>
        <path d="M8 9l-3 3 3 3"/>
        <path d="M16 9l3 3-3 3"/>
      </svg>
    </button>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main {
  flex: 1;
}

.floating-sidebar-toggle {
  position: fixed;
  left: 20px;
  top: 180px;
  z-index: 1200;
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.95);
  border: 1px solid rgba(16,24,40,0.06);
  box-shadow: 0 6px 18px rgba(19,38,70,0.06);
  cursor: pointer;
}

.floating-sidebar-toggle:hover {
  transform: translateY(-2px);
}

.floating-toggle-icon {
  width: 20px;
  height: 20px;
  color: #475569;
}

@media (max-width: 900px) {
  .floating-sidebar-toggle { left: 12px; top: 140px; }
}
</style>
