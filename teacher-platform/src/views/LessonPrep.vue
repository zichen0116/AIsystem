<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LessonPrepPpt from './LessonPrepPpt.vue'
import LessonPrepLessonPlan from './LessonPrepLessonPlan.vue'
import LessonPrepAnimation from './LessonPrepAnimation.vue'
import LessonPrepKnowledge from './LessonPrepKnowledge.vue'
import LessonPrepData from './LessonPrepData.vue'

const route = useRoute()
const router = useRouter()

const resetKeys = ref({
  ppt: 0,
  'lesson-plan': 0,
  animation: 0,
  knowledge: 0,
  data: 0
})

const tabs = [
  { id: 'ppt', label: 'PPT生成' },
  { id: 'lesson-plan', label: '教案生成' },
  { id: 'animation', label: '动游制作' },
  { id: 'knowledge', label: '知识图谱' },
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
    'lesson-plan': LessonPrepLessonPlan,
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

.main-content-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
