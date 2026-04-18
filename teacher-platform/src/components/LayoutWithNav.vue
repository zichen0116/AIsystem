<script setup>
import { ref, provide, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useAdminDigitalHumanStore } from '../stores/adminDigitalHuman'
import ThemeToggle from './ThemeToggle.vue'
import DigitalHumanAssistant from './DigitalHumanAssistant.vue'

// 全局侧栏折叠状态（提供给子组件注入使用）
const sidebarCollapsed = ref(false)
provide('sidebarCollapsed', sidebarCollapsed)

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const adminDigitalHumanStore = useAdminDigitalHumanStore()

const primaryItems = [
  { id: 'lesson-prep', path: '/lesson-prep', label: '备课中心', icon: 'lesson' },
  { id: 'courseware', path: '/courseware', label: '课件管理', icon: 'folder' },
  { id: 'rehearsal', path: '/rehearsal', label: '课堂预演', icon: 'rehearsal' },
  { id: 'knowledge-base', path: '/knowledge-base', label: '知识库', icon: 'graph' },
  { id: 'question', path: '/question-gen', label: '试题生成', icon: 'exam' },
  { id: 'resource', path: '/resource-search', label: '资源搜索', icon: 'search' }
]

const isAdmin = computed(() => userStore.userInfo?.is_admin === true)

const otherPrimaryItems = computed(() => {
  if (isAdmin.value) {
    return [
      { id: 'admin-data', path: '/admin', label: '数据中台', icon: 'dashboard' },
      {
        id: 'admin-digital-human',
        path: '/admin',
        label: adminDigitalHumanStore.visible ? '隐藏数字人' : '显示数字人',
        icon: 'digital-human'
      },
      { id: 'knowledge-base', path: '/knowledge-base', label: '知识库', icon: 'graph' },
      { id: 'admin-users', path: '/admin/users', label: '用户管理', icon: 'admin-users' },
      { id: 'admin-audit', path: '/admin/audit', label: '资源审计', icon: 'admin-audit' },
      { id: 'admin-logs', path: '/admin/logs', label: '系统日志', icon: 'admin-logs' },
      { id: 'personal-center', path: '/admin/profile', label: '个人中心', icon: 'user' }
    ]
  }
  return primaryItems.filter(i => i.id !== 'lesson-prep')
})

function isPrimaryActive(item) {
  if (item.id === 'admin-data') {
    return route.path === '/admin'
  }
  if (item.id === 'admin-users') {
    return route.path === '/admin/users' || route.path.startsWith('/admin/users/')
  }
  if (item.id === 'admin-audit') {
    return route.path === '/admin/audit' || route.path.startsWith('/admin/audit/')
  }
  if (item.id === 'admin-logs') {
    return route.path === '/admin/logs' || route.path.startsWith('/admin/logs/')
  }
  if (item.id === 'personal-center' && isAdmin.value) {
    return route.path.startsWith('/admin/profile')
  }
  if (item.id === 'admin-digital-human') {
    return adminDigitalHumanStore.visible
  }
  return route.path.startsWith(item.path)
}

function goToPrimary(path) {
  if (!path.startsWith('/lesson-prep')) lessonPrepOpen.value = false
  router.push(path)
}

const lessonPrepTabs = [
  { id: 'ppt', label: 'PPT生成', icon: 'ppt' },
  { id: 'lesson-plan', label: '教案生成', icon: 'lesson-plan' },
  { id: 'animation', label: '动游制作', icon: 'animation' },
  { id: 'knowledge', label: '知识图谱', icon: 'knowledge' },
  { id: 'mindmap', label: '思维导图', icon: 'mindmap' },
  { id: 'data', label: '数据分析', icon: 'data' }
]

const isLessonPrepRoute = computed(() => route.path.startsWith('/lesson-prep'))
const activeLessonPrepTab = computed(() => {
  const t = route.query.tab
  const tab = typeof t === 'string' ? t : ''
  const valid = lessonPrepTabs.map(i => i.id)
  return valid.includes(tab) ? tab : 'ppt'
})

const lessonPrepOpen = ref(false)
const lessonPrepIsOpen = computed(() => lessonPrepOpen.value)

function toggleLessonPrep() {
  const next = !lessonPrepOpen.value
  lessonPrepOpen.value = next
  if (next && !isLessonPrepRoute.value) {
    router.push({ path: '/lesson-prep', query: { tab: activeLessonPrepTab.value } })
  }
}

function goToLessonPrepTab(id) {
  lessonPrepOpen.value = true
  router.push({ path: '/lesson-prep', query: { ...route.query, tab: id } })
}

watch(
  () => route.path,
  (p) => {
    if (!p.startsWith('/lesson-prep')) lessonPrepOpen.value = false
  }
)

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  if (sidebarCollapsed.value) lessonPrepOpen.value = false
}

function handleAvatarClick() {
  lessonPrepOpen.value = false
  if (userStore.isLoggedIn) {
    if (isAdmin.value) {
      router.push('/admin/profile')
    } else {
      router.push('/personal-center')
    }
  } else {
    router.push('/login')
  }
}

function toggleAdminDigitalHumanVisible() {
  adminDigitalHumanStore.toggleVisible()
}

function toggleAdminDigitalHumanVoice() {
  adminDigitalHumanStore.toggleVoiceMode()
}
</script>

<template>
  <div class="layout">
    <!-- 一级侧边栏 -->
    <aside class="primary" :class="{ collapsed: sidebarCollapsed }">
      <div class="primary-top" @click="router.push('/')" role="button" tabindex="0">
        <div class="brand-icon" aria-hidden="true">
          <img data-test="sidebar-brand-logo" class="brand-logo" src="/logo-character.svg" alt="" />
        </div>
        <div v-if="!sidebarCollapsed" class="brand-text">
          <div data-test="sidebar-brand-name" class="brand-name">智课坊</div>
        </div>
      </div>

      <nav class="primary-nav">
        <!-- 备课中心：折叠列表（教师端可见） -->
        <div v-if="!isAdmin" class="nav-group" :class="{ active: isLessonPrepRoute }">
          <button type="button" class="primary-item has-children" :class="{ active: isLessonPrepRoute }" @click="toggleLessonPrep">
            <span class="pi-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
                <path d="M14 8h2a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" fill="currentColor" fill-opacity="0.25"/>
              </svg>
            </span>
            <span class="pi-label">备课中心</span>
            <span v-if="!sidebarCollapsed" class="pi-chevron" aria-hidden="true" :class="{ open: lessonPrepIsOpen }">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </span>
          </button>

          <div v-show="lessonPrepIsOpen && !sidebarCollapsed" class="sub-list">
            <button
              v-for="t in lessonPrepTabs"
              :key="t.id"
              type="button"
              class="sub-item"
              :class="{ active: isLessonPrepRoute && activeLessonPrepTab === t.id }"
              @click="goToLessonPrepTab(t.id)"
            >
              <span class="sub-icon" aria-hidden="true">
                <!-- PPT与教案：显示器+文档 -->
                <svg
                  v-if="t.icon === 'ppt'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                  <path d="M14 8h2a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" fill="currentColor" fill-opacity="0.18" />
                </svg>
                <!-- 教案生成：文档+笔 -->
                <svg
                  v-else-if="t.icon === 'lesson-plan'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6" />
                  <path d="M8 13h8M8 17h5" />
                </svg>
                <!-- 动画与游戏制作：手柄 -->
                <svg
                  v-else-if="t.icon === 'animation'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M6 12h4M8 10v4M15 13h.01M18 11h.01M17 15h.01M20 10h.01" />
                  <path d="M4 8a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v4a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8z" />
                </svg>
                <!-- 知识图谱构建：节点连线 -->
                <svg
                  v-else-if="t.icon === 'knowledge'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="3" y="3" width="6" height="6" rx="1" />
                  <rect x="15" y="3" width="6" height="6" rx="1" />
                  <rect x="9" y="15" width="6" height="6" rx="1" />
                  <path d="M9 18H6a3 3 0 0 1 0-6h0M15 18h3a3 3 0 0 0 0-6h0M9 15V9a3 3 0 0 1 6 0v6" />
                </svg>
                <!-- 思维导图：中心节点辐射 -->
                <svg
                  v-else-if="t.icon === 'mindmap'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <circle cx="12" cy="12" r="3" />
                  <circle cx="5" cy="7" r="2" />
                  <circle cx="19" cy="7" r="2" />
                  <circle cx="6" cy="18" r="2" />
                  <circle cx="18" cy="18" r="2" />
                  <path d="M10.5 10.5 6.5 8.5M13.5 10.5l4-2M11 14l-3.5 3M13 14l3.5 3" />
                </svg>
                <!-- 数据分析：柱状图 -->
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M3 3v18h18" />
                  <path d="M7 16v-5M11 16v-8M15 16v-11M19 16v-3" />
                </svg>
              </span>
              <span class="sub-label">{{ t.label }}</span>
            </button>
          </div>
        </div>

        <!-- 其它一级入口 -->
        <button
          v-for="item in otherPrimaryItems"
          :key="item.id"
          type="button"
          class="primary-item"
          :class="{ active: isPrimaryActive(item) }"
          @click="item.id === 'personal-center' ? handleAvatarClick() : item.id === 'admin-digital-human' ? toggleAdminDigitalHumanVisible() : goToPrimary(item.path)"
        >
          <span class="pi-icon" aria-hidden="true">
            <!-- 课件管理 / 数据中台：文件夹 / 柱状图 -->
            <svg
              v-if="item.icon === 'folder'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M3 6a2 2 0 0 1 2-2h5l2 2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z" />
              <path d="M3 10h18" />
            </svg>
            <svg
              v-else-if="item.icon === 'dashboard'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M3 3v18h18" />
              <path d="M7 16v-5M11 16v-8M15 16v-11M19 16v-3" />
            </svg>
            <!-- 课堂预演：播放按钮 -->
            <svg
              v-else-if="item.icon === 'rehearsal'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <!-- 知识库：节点连线 -->
            <svg
              v-else-if="item.icon === 'graph'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="3" y="3" width="6" height="6" rx="1" />
              <rect x="15" y="3" width="6" height="6" rx="1" />
              <rect x="9" y="15" width="6" height="6" rx="1" />
              <path d="M9 18H6a3 3 0 0 1 0-6h0M15 18h3a3 3 0 0 0 0-6h0M9 15V9a3 3 0 0 1 6 0v6" />
            </svg>
            <!-- 试题生成：文档+勾选 -->
            <svg
              v-else-if="item.icon === 'exam'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="4" y="3" width="16" height="18" rx="2" />
              <path d="M8 8h8M8 12h5" />
              <path d="m9 16 2 2 4-4" />
            </svg>
            <!-- 资源搜索：放大镜 / 个人中心：头像 -->
            <svg
              v-else-if="item.icon === 'search'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <circle cx="11" cy="11" r="5" />
              <path d="M16 16l4 4" />
            </svg>
            <svg
              v-else-if="item.icon === 'digital-human'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="4" y="4" width="16" height="16" rx="4" />
              <circle cx="9" cy="10" r="1.2" fill="currentColor" stroke="none" />
              <circle cx="15" cy="10" r="1.2" fill="currentColor" stroke="none" />
              <path d="M8 15c1.1 1 2.4 1.5 4 1.5s2.9-.5 4-1.5" />
            </svg>
            <!-- 用户管理：多人 -->
            <svg
              v-else-if="item.icon === 'admin-users'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <!-- 资源审计：剪贴板 -->
            <svg
              v-else-if="item.icon === 'admin-audit'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
              <rect x="9" y="3" width="6" height="4" rx="1" />
              <path d="m9 12 2 2 4-4" />
            </svg>
            <!-- 系统日志：列表 -->
            <svg
              v-else-if="item.icon === 'admin-logs'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
              <path d="M8 13h8M8 17h8M8 9h2" />
            </svg>
            <svg
              v-else-if="item.icon === 'user'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </span>
          <span class="pi-label">{{ item.label }}</span>
          <button
            v-if="item.id === 'admin-digital-human'"
            type="button"
            class="nav-mic-btn"
            :class="{ on: adminDigitalHumanStore.voiceMode }"
            :title="adminDigitalHumanStore.voiceMode ? '结束通话' : '开始通话'"
            @click.stop="toggleAdminDigitalHumanVoice"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 14a3 3 0 0 0 3-3V7a3 3 0 0 0-6 0v4a3 3 0 0 0 3 3z" />
              <path d="M19 11a7 7 0 0 1-14 0" />
              <path d="M12 19v3" />
            </svg>
          </button>
        </button>

        <button
          v-if="!isAdmin"
          type="button"
          class="primary-item"
          :class="{ active: route.path.startsWith('/personal-center') }"
          @click="handleAvatarClick"
        >
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
          <button type="button" class="collapse-btn" @click="toggleSidebar" :title="sidebarCollapsed ? '展开导航栏' : '收起导航栏'">
            <!-- 展开状态：向左收起箭头 -->
            <svg
              v-if="!sidebarCollapsed"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M14 6L8 12l6 6" />
            </svg>
            <!-- 收起状态：向右展开箭头 -->
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M10 6l6 6-6 6" />
            </svg>
          </button>
          <div v-if="!sidebarCollapsed" class="sidebar-theme-toggle">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </aside>

    <main class="main">
      <slot />
    </main>

    <!-- 教师端：可拖动数字人入口 + 右侧抽屉（管理员端不展示） -->
    <DigitalHumanAssistant v-if="!isAdmin" />
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
  display: flex;
  flex-direction: column;
  overflow: auto; /* 只滚页面内容，不滚导航 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge legacy */
}

.main::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.primary {
  width: 200px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  transition: width 0.18s ease;
}

.primary.collapsed {
  width: 64px;
}

.primary.collapsed .brand-text {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}

.primary.collapsed .primary-top {
  justify-content: center;
  padding: 16px 8px 10px;
}

.primary.collapsed .primary-nav {
  padding: 10px 6px;
}

.primary.collapsed .primary-item {
  justify-content: center;
  gap: 0;
  padding: 10px 8px;
}

.primary.collapsed .pi-label {
  display: none;
}

.primary.collapsed .pi-icon {
  width: 22px;
}

.primary.collapsed .primary-item.has-children {
  padding-right: 8px;
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
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  flex: 0 0 auto;
  overflow: hidden;
}

.brand-logo {
  width: 34px;
  height: 34px;
  display: block;
  object-fit: contain;
}

.brand-name {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
  letter-spacing: 0.02em;
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

.nav-mic-btn {
  margin-left: auto;
  width: 28px;
  height: 28px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #ffffff;
  color: #475569;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-mic-btn svg {
  width: 14px;
  height: 14px;
}

.nav-mic-btn:hover {
  border-color: #93c5fd;
  color: #2563eb;
}

.nav-mic-btn.on {
  border-color: #2563eb;
  background: #2563eb;
  color: #ffffff;
}

.primary-item.has-children {
  padding-right: 6px;
}

.pi-chevron {
  margin-left: auto;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: inherit;
  opacity: 0.75;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.pi-chevron svg {
  width: 18px;
  height: 18px;
}

.pi-chevron.open {
  transform: rotate(180deg);
  opacity: 0.95;
}

.sub-list {
  padding: 4px 6px 6px 34px; /* 左侧缩进：对齐图标后 */
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sub-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  color: #64748b;
  font-size: 16px;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}

.sub-item:hover {
  background: transparent;
  color: #334155;
}

.sub-item.active {
  background: transparent;
  color: #2563eb;
  font-weight: 600;
}

.sub-icon {
  width: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: inherit;
}

.sub-icon svg {
  width: 18px;
  height: 18px;
}

.sub-label {
  white-space: nowrap;
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

.collapse-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  margin-right: 13px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 10px;
  color: #475569;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.collapse-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #0f172a;
}

.collapse-btn svg {
  width: 18px;
  height: 18px;
}

.sidebar-theme-toggle {
  font-size: 0; /* 去掉多余间距，仅影响内部尺寸 */
}

/* 自适应：窄屏默认收起侧栏，提供更多内容空间 */
@media (max-width: 1100px) {
  .primary:not(.collapsed) {
    width: 180px;
  }
}

@media (max-width: 900px) {
  .layout {
    min-height: 100vh;
    min-height: 100dvh;
  }
  .primary:not(.collapsed) {
    width: 72px;
  }
  .primary:not(.collapsed) .brand-text,
  .primary:not(.collapsed) .pi-label,
  .primary:not(.collapsed) .sub-list {
    display: none;
  }
  .primary:not(.collapsed) .primary-item {
    justify-content: center;
    padding: 10px 8px;
  }
  .primary:not(.collapsed) .primary-top {
    justify-content: center;
  }
  .primary:not(.collapsed) .pi-chevron {
    display: none;
  }
}

@media (max-width: 600px) {
  .primary {
    width: 56px;
    min-width: 56px;
  }
  .primary.collapsed {
    width: 56px;
  }
  .primary .brand-text,
  .primary .pi-label,
  .primary .sub-list {
    display: none;
  }
  .primary .primary-item {
    justify-content: center;
    padding: 8px 6px;
  }
  .primary .primary-top {
    justify-content: center;
    padding: 12px 6px;
  }
  .primary .pi-chevron {
    display: none;
  }
  .primary .pi-icon,
  .primary.collapsed .pi-icon {
    width: 18px;
  }
  .primary .pi-icon svg,
  .primary.collapsed .pi-icon svg {
    width: 18px;
    height: 18px;
  }
}
</style>
