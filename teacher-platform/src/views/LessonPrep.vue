<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LessonPrepPpt from './LessonPrepPpt.vue'
import LessonPrepAnimation from './LessonPrepAnimation.vue'
import LessonPrepKnowledge from './LessonPrepKnowledge.vue'
import LessonPrepData from './LessonPrepData.vue'

const route = useRoute()
const router = useRouter()

const resetKeys = ref({
  ppt: 0,
  animation: 0,
  knowledge: 0,
  data: 0
})

const tabs = [
  { id: 'ppt', label: 'PPT与教案生成' },
  { id: 'animation', label: '动画与游戏制作' },
  { id: 'knowledge', label: '知识图谱构建' },
  { id: 'data', label: '数据分析' }
]

const validTabs = tabs.map(t => t.id)
const activeTab = computed(() => {
  const t = route.query.tab
  const tab = typeof t === 'string' ? t : ''
  return validTabs.includes(tab) ? tab : 'ppt'
})

const currentComponent = computed(() => {
  const map = {
    ppt: LessonPrepPpt,
    animation: LessonPrepAnimation,
    knowledge: LessonPrepKnowledge,
    data: LessonPrepData
  }
  return map[activeTab.value]
})

const currentResetKey = computed(() => resetKeys.value[activeTab.value])

function startNewConversation() {
  const id = activeTab.value
  resetKeys.value[id] = (resetKeys.value[id] || 0) + 1
}

function setTab(id) {
  if (!validTabs.includes(id)) return
  router.replace({ path: '/lesson-prep', query: { ...route.query, tab: id } })
}
</script>

<template>
  <div class="lesson-prep-page">
    <div class="lesson-prep-body">
      <main class="main-content">
        <header class="prep-header">
          <nav class="prep-tabs">
            <button
              v-for="t in tabs"
              :key="t.id"
              type="button"
              class="prep-tab"
              :class="{ active: activeTab === t.id }"
              @click="setTab(t.id)"
            >
              <span class="prep-tab-icon" aria-hidden="true">
                <!-- PPT与教案：显示器+文档 -->
                <svg
                  v-if="t.id === 'ppt'"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                  <path
                    d="M14 8h2a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"
                    fill="currentColor"
                    fill-opacity="0.25"
                  />
                </svg>
                <!-- 动画与游戏制作：手柄 -->
                <svg
                  v-else-if="t.id === 'animation'"
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
                  v-else-if="t.id === 'knowledge'"
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
              <span class="prep-tab-label">{{ t.label }}</span>
            </button>
          </nav>
        </header>

        <div class="main-content-body">
          <keep-alive>
            <component :is="currentComponent" :reset-key="currentResetKey" />
          </keep-alive>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.lesson-prep-page {
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg,rgba(248, 251, 255, 0.57) 0%,rgb(240, 246, 255) 100%);
  display: flex;
  flex-direction: column;
}

.lesson-prep-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.main-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.prep-header {
  padding: 10px 32px 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.prep-tabs {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.prep-tab {
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 16px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.prep-tab:hover {
  background: #e5edff;
  color: #2563eb;
}

.prep-tab.active {
  background: transparent;
  color: #2563eb;
  border-color: transparent;
}

.prep-tab::after {
  content: '';
  position: absolute;
  left: 18%;
  right: 18%;
  bottom: -4px;
  height: 2px;
  border-radius: 999px;
  background: transparent;
  transition: background 0.15s ease;
}

.prep-tab.active::after {
  background: #2563eb;
}

.prep-tab-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-right: 6px;
}

.prep-tab-icon svg {
  width: 18px;
  height: 18px;
}

.prep-tab-label {
  white-space: nowrap;
}

.main-content-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
