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
            <span class="filter-dot" :style="{ backgroundColor: cat.color, boxShadow: `0 0 4px ${cat.color}` }"></span>
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
  background: rgba(0, 0, 0, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 14px 18px;
  backdrop-filter: blur(16px);
  min-width: 220px;
}

.filter-title {
  color: rgba(255, 255, 255, 0.85);
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
  padding: 5px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.filter-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.filter-item input[type="checkbox"] {
  accent-color: #ff6b4a;
  width: 14px;
  height: 14px;
}

.filter-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.filter-name {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}
</style>
