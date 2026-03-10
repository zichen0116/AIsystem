<script setup>
import { ref, provide, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import ThemeToggle from './ThemeToggle.vue'

// 全局侧栏折叠状态（提供给子组件注入使用）
const sidebarCollapsed = ref(false)
provide('sidebarCollapsed', sidebarCollapsed)

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const primaryItems = [
  { id: 'lesson-prep', path: '/lesson-prep', label: '备课中心', icon: 'lesson' },
  { id: 'courseware', path: '/courseware', label: '课件管理', icon: 'folder' },
  { id: 'knowledge-base', path: '/knowledge-base', label: '知识库', icon: 'graph' }
]

function goToPrimary(path) {
  router.push(path)
}

function handleAvatarClick() {
  if (userStore.isLoggedIn) {
    router.push('/personal-center')
  } else {
    router.push('/login')
  }
}
</script>

<template>
  <div class="layout">
    <!-- 一级侧边栏 -->
    <aside class="primary">
      <div class="primary-top" @click="router.push('/')" role="button" tabindex="0">
        <div class="brand-icon" aria-hidden="true">📖</div>
        <div class="brand-text">
          <div class="brand-name">EduPrep</div>
        </div>
      </div>

      <nav class="primary-nav">
        <button
          v-for="item in primaryItems"
          :key="item.id"
          type="button"
          class="primary-item"
          :class="{ active: route.path.startsWith(item.path) }"
          @click="goToPrimary(item.path)"
        >
          <span class="pi-icon" aria-hidden="true">
            <!-- 备课中心：显示器+文档（沿用之前 LessonPrep 风格） -->
            <svg v-if="item.icon === 'lesson'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <path d="M8 21h8M12 17v4"/>
              <path d="M14 8h2a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" fill="currentColor" fill-opacity="0.25"/>
            </svg>
            <!-- 课件管理：文件夹 -->
            <svg v-else-if="item.icon === 'folder'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6a2 2 0 0 1 2-2h5l2 2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z"/>
              <path d="M3 10h18"/>
            </svg>
            <!-- 知识库：节点连线（沿用之前风格） -->
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="6" height="6" rx="1"/>
              <rect x="15" y="3" width="6" height="6" rx="1"/>
              <rect x="9" y="15" width="6" height="6" rx="1"/>
              <path d="M9 18H6a3 3 0 0 1 0-6h0M15 18h3a3 3 0 0 0 0-6h0M9 15V9a3 3 0 0 1 6 0v6"/>
            </svg>
          </span>
          <span class="pi-label">{{ item.label }}</span>
        </button>

        <button type="button" class="primary-item" :class="{ active: route.path.startsWith('/personal-center') }" @click="handleAvatarClick">
          <span class="pi-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </span>
          <span class="pi-label">个人中心</span>
        </button>
      </nav>

      <div class="primary-bottom">
        <div class="bottom-row">
          <div class="sidebar-theme-toggle">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </aside>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.layout {
  height: 100vh;
  display: flex;
  flex-direction: row;
  background: #f8fafc;
  overflow: hidden; /* 只允许内容区滚动 */
}

.main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto; /* 只滚页面内容，不滚导航 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge legacy */
}

.main::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.primary {
  width: 180px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.primary-top {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 17px 10px 10px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
}

.brand-icon {
  width: 30px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  font-size: 26px;
}

.brand-name {
  font-size: 21px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.1;
}

.primary-nav {
  padding: 10px 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.primary-nav::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.primary-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 8px 9px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  color: #334155;
  font-size: 16px;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}

.primary-item:hover {
  background: #f1f5f9;
}

.primary-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

.pi-icon {
  width: 20px;
  display: inline-flex;
  justify-content: center;
  color: inherit;
}

.pi-icon svg {
  width: 20px;
  height: 20px;
}

.primary-bottom {
  margin-top: auto;
  padding: 10px 8px 12px;
  border-top: 1px solid #f1f5f9;
}

.bottom-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.sidebar-theme-toggle {
  font-size: 0; /* 去掉多余间距，仅影响内部尺寸 */
}


</style>
