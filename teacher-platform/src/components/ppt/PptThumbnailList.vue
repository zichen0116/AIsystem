<template>
  <div class="thumbnail-list">
    <div
      v-for="(slide, i) in slides"
      :key="i"
      class="thumb-item"
      :class="{ active: i === activeIndex }"
      @click="$emit('select', i)"
    >
      <span class="thumb-num">{{ i + 1 }}</span>
      <div class="thumb-preview" ref="thumbRefs">
        <!-- ppt2canvas 渲染到这里 -->
      </div>
    </div>
    <div v-if="!slides.length" class="thumb-empty">暂无页面</div>
  </div>
</template>

<script setup>
defineProps({
  slides: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: 0 },
})
defineEmits(['select'])
</script>

<style scoped>
.thumbnail-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  overflow-y: auto;
}
.thumb-item {
  position: relative;
  border: 2px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 16/9;
  background: #f8fafc;
  min-height: 60px;
}
.thumb-item:hover { border-color: #cbd5e1; }
.thumb-item.active { border-color: #3a61ea; box-shadow: 0 0 0 1px #3a61ea; }
.thumb-num {
  position: absolute;
  top: 3px;
  left: 5px;
  font-size: 10px;
  color: #94a3b8;
  z-index: 1;
}
.thumb-preview { width: 100%; height: 100%; }
.thumb-empty { padding: 20px; text-align: center; color: #ccc; font-size: 12px; }
</style>
