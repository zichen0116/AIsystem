<script setup>
import { computed, watch } from 'vue'
import { usePptStore } from '@/stores/ppt'
import PptHome from './PptHome.vue'
import PptDialog from './PptDialog.vue'
import PptOutline from './PptOutline.vue'
import PptDescription from './PptDescription.vue'
import PptPreview from './PptPreview.vue'

const pptStore = usePptStore()

const currentPhase = computed(() => {
  if (!pptStore.projectId) return 'home'
  return pptStore.currentPhase
})

const phaseComponent = computed(() => {
  const map = {
    home: PptHome,
    dialog: PptDialog,
    outline: PptOutline,
    description: PptDescription,
    preview: PptPreview
  }
  return map[currentPhase.value] || PptHome
})

// Watch for creation type and auto-navigate
watch(() => pptStore.creationType, (type) => {
  if (type === 'dialog' && pptStore.projectId && pptStore.currentPhase === 'home') {
    // Dialog mode starts with dialog phase
    pptStore.setPhase('dialog')
  } else if (type === 'file' && pptStore.projectId && pptStore.currentPhase === 'home') {
    // File mode goes directly to outline
    pptStore.setPhase('outline')
  } else if (type === 'renovation' && pptStore.projectId && pptStore.currentPhase === 'home') {
    // Renovation mode goes to outline
    pptStore.setPhase('outline')
  }
}, { immediate: true })
</script>

<template>
  <div class="ppt-index">
    <component :is="phaseComponent" />
  </div>
</template>

<style scoped>
.ppt-index {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
