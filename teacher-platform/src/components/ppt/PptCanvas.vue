<template>
  <div class="ppt-canvas" ref="canvasContainer">
    <div v-if="!pptxProperty" class="canvas-empty">
      <div v-if="generating" class="canvas-progress">
        <div class="progress-spinner" />
        <p>PPT 生成中... {{ currentPage }}/{{ totalPages }}</p>
      </div>
      <p v-else class="canvas-hint">选择模板并生成PPT后，预览将在此显示</p>
    </div>
    <div v-else class="canvas-render" ref="renderArea">
      <!-- ppt2svg 渲染到这里 -->
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  pptxProperty: { type: String, default: '' },
  slideIndex: { type: Number, default: 0 },
  editMode: { type: Boolean, default: false },
  generating: { type: Boolean, default: false },
  currentPage: { type: Number, default: 0 },
  totalPages: { type: Number, default: 0 },
})
const emit = defineEmits(['change', 'edit-change'])

const canvasContainer = ref(null)
const renderArea = ref(null)
</script>

<style scoped>
.ppt-canvas {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  overflow: auto;
  padding: 24px;
  min-height: 0;
}
.canvas-empty {
  text-align: center;
  color: #999;
}
.canvas-hint { font-size: 14px; }
.canvas-progress { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.progress-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e5e7eb;
  border-top-color: #3a61ea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.canvas-render {
  width: 100%;
  max-width: 900px;
  aspect-ratio: 16/9;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  overflow: hidden;
}
</style>
