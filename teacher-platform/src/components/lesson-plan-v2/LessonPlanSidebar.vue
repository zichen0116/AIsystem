<template>
  <div class="sidebar-wrapper">
    <transition name="sidebar-slide">
      <div v-if="!collapsed" class="lesson-sidebar" :class="{ overlay: isOverlay }">
        <div class="sidebar-header">
          <button class="new-btn" @click="$emit('new-conversation')">＋ 新建对话</button>
          <button class="collapse-btn" @click="$emit('toggle')" title="收起侧边栏">‹</button>
        </div>
        <div class="history-list">
          <div
            v-for="item in mockHistory"
            :key="item.id"
            class="history-item"
            :class="{ active: item.id === activeId }"
            @click="activeId = item.id"
          >
            <div class="history-title">{{ item.title }}</div>
            <div class="history-time">{{ item.time }}</div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Expand button (shown when collapsed) -->
    <button v-if="collapsed" class="sidebar-toggle" @click="$emit('toggle')">›</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  collapsed: { type: Boolean, default: false },
  isOverlay: { type: Boolean, default: false },
})

defineEmits(['new-conversation', 'toggle'])

const activeId = ref(1)

const mockHistory = [
  { id: 1, title: '小学数学分数教案', time: '今天 14:30', preview: '三年级分数的初步认识...' },
  { id: 2, title: '高中物理力学教案', time: '昨天 09:15', preview: '牛顿第二定律应用...' },
  { id: 3, title: '初中英语阅读课', time: '3月12日', preview: 'Reading comprehension...' },
  { id: 4, title: '七年级生物细胞结构', time: '3月10日', preview: '动物细胞与植物细胞...' },
]
</script>

<style scoped>
.sidebar-wrapper {
  position: relative;
}
.lesson-sidebar {
  width: 240px;
  min-width: 240px;
  background: #fff;
  border-right: 1px solid #eaedf0;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  height: 100%;
}
.lesson-sidebar.overlay {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
  box-shadow: 4px 0 16px rgba(0, 0, 0, 0.08);
}
.new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  flex: 1;
  transition: all 0.2s;
}
.new-btn:hover {
  background: #1d4ed8;
}
.sidebar-header {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: stretch;
}
.collapse-btn {
  width: 36px;
  background: #f7f8fa;
  border: 1px solid #e0e3e8;
  border-radius: 8px;
  cursor: pointer;
  color: #999;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.collapse-btn:hover {
  color: #2563eb;
  border-color: #2563eb;
  background: #f0f5ff;
}
.history-list {
  flex: 1;
  overflow-y: auto;
}
.history-item {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: #444;
  cursor: pointer;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.2s;
}
.history-item:hover {
  background: #f0f5ff;
}
.history-item.active {
  background: #e8f0fe;
  color: #2563eb;
  font-weight: 500;
}
.history-time {
  font-size: 11px;
  color: #aaa;
  margin-top: 2px;
}
.sidebar-toggle {
  position: absolute;
  left: 0;
  top: 12px;
  z-index: 30;
  width: 24px;
  height: 40px;
  background: #fff;
  border: 1px solid #eaedf0;
  border-left: none;
  border-radius: 0 6px 6px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aaa;
  font-size: 12px;
  transition: all 0.2s;
}
.sidebar-toggle:hover {
  color: #2563eb;
  background: #f0f5ff;
}

/* Sidebar slide transition */
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 300ms ease, opacity 300ms ease;
}
.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}
</style>
