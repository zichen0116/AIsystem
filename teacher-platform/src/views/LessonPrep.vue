<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LessonPrepPpt from './ppt/PptIndex.vue'
import LessonPlanPage from './LessonPlanPage.vue'
import LessonPrepAnimation from './LessonPrepAnimation.vue'
import LessonPrepKnowledge from './LessonPrepKnowledge.vue'
import LessonPrepMindmap from './LessonPrepMindmap.vue'
import LessonPrepData from './LessonPrepData.vue'
import { usePptStore } from '../stores/ppt'

const route = useRoute()
const router = useRouter()
const pptStore = usePptStore()

const resetKeys = ref({
  ppt: 0,
  'lesson-plan': 0,
  animation: 0,
  knowledge: 0,
  mindmap: 0,
  data: 0
})

const tabs = [
  { id: 'ppt', label: 'PPT生成' },
  { id: 'lesson-plan', label: '教案生成' },
  { id: 'animation', label: '动游制作' },
  { id: 'knowledge', label: '知识图谱' },
  { id: 'mindmap', label: '思维导图' },
  { id: 'data', label: '数据分析' }
]

const validTabs = tabs.map(t => t.id)
const activeTab = computed(() => {
  const t = route.query.tab
  const tab = typeof t === 'string' ? t : ''
  return validTabs.includes(tab) ? tab : 'ppt'
})

const routeProjectId = computed(() => route.query.projectId || null)
const routeLessonPlanId = computed(() => route.query.lessonPlanId || null)

const currentComponent = computed(() => {
  const map = {
    ppt: LessonPrepPpt,
    'lesson-plan': LessonPlanPage,
    animation: LessonPrepAnimation,
    knowledge: LessonPrepKnowledge,
    mindmap: LessonPrepMindmap,
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

// Watch for projectId query param to open a PPT project directly
watch(routeProjectId, async (newId) => {
  if (newId && activeTab.value === 'ppt') {
    try {
      await pptStore.fetchProject(Number(newId))
      await pptStore.fetchPages(Number(newId))

      // Determine phase using same logic as PptHistory.getProjectPhase()
      const project = pptStore.projectData
      let phase = 'outline'
      if (project?.cover_image_url) {
        phase = 'preview'
      } else if (pptStore.outlinePages.length === 0 && project?.creation_type === 'dialog') {
        phase = 'dialog'
      }
      pptStore.setPhase(phase)
    } catch (e) {
      console.error('Failed to load PPT project from route:', e)
    }

    // Clear query params to avoid re-triggering
    router.replace({ query: { tab: 'ppt' } })
  }
}, { immediate: true })
</script>

<template>
  <div class="lesson-prep-page">
    <div class="lesson-prep-body">
      <main class="main-content">
        <div class="main-content-body">
          <keep-alive>
            <component
              :is="currentComponent"
              :reset-key="currentResetKey"
              :initial-project-id="routeProjectId"
              :initial-lesson-plan-id="routeLessonPlanId"
            />
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
