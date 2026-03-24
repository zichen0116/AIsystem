<template>
  <Teleport to="body">
    <div class="filter-backdrop" @click.self="$emit('close')">
      <div class="filter-popover">
        <div class="filter-title">按分类筛选</div>
        <div class="filter-list">
          <label
            v-for="cat in categories"
            :key="cat.name"
            class="filter-item"
          >
            <input
              type="checkbox"
              :checked="!hiddenCategories.has(cat.name)"
              @change="$emit('toggle', cat.name)"
            />
            <span class="filter-dot" :style="{ backgroundColor: cat.color }"></span>
            <span class="filter-name">{{ cat.name }}</span>
          </label>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  categories: { type: Array, default: () => [] },
  hiddenCategories: { type: Object, default: () => new Set() },
})

defineEmits(['toggle', 'close'])
</script>

<style scoped>
.filter-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.filter-popover {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(10, 15, 30, 0.92);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 10px;
  padding: 12px 16px;
  backdrop-filter: blur(12px);
  min-width: 200px;
}

.filter-title {
  color: rgba(226, 232, 240, 0.9);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}

.filter-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.filter-item:hover {
  background: rgba(51, 65, 85, 0.3);
}

.filter-item input[type="checkbox"] {
  accent-color: #60a5fa;
  width: 14px;
  height: 14px;
}

.filter-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.filter-name {
  color: rgba(203, 213, 225, 0.9);
  font-size: 12px;
}
</style>
