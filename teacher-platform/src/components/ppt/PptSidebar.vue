<template>
  <aside class="ppt-sidebar" :class="{ collapsed }" :style="{ width: collapsed ? '52px' : sidebarWidth + 'px' }">
    <div class="sidebar-header">
      <button class="new-btn" @click="$emit('new-session')">+ 新建PPT</button>
      <button class="toggle-btn" @click="$emit('toggle')">{{ collapsed ? '☰' : '☰' }}</button>
    </div>
    <div v-if="!collapsed" class="history-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="history-item"
        :class="{ active: s.id === activeId }"
        @click="$emit('select', s.id)"
      >
        <div class="history-top">
          <div class="history-title">{{ s.title }}</div>
          <button
            class="delete-btn"
            title="删除会话"
            @click.stop="$emit('delete', s.id)"
          >&times;</button>
        </div>
        <div class="history-time">{{ formatTime(s.updated_at) }}</div>
      </div>
      <div v-if="!sessions.length" class="history-empty">暂无历史会话</div>
    </div>
    <div
      v-if="!collapsed"
      class="sidebar-resize-handle"
      :class="{ dragging: isResizing }"
      @mousedown.prevent="startResize"
    />
  </aside>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: Number, default: null },
  collapsed: { type: Boolean, default: false },
})
defineEmits(['new-session', 'select', 'toggle', 'delete'])

const sidebarWidth = ref(260)
const isResizing = ref(false)

function startResize() {
  isResizing.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

function onResize(e) {
  const next = Math.max(220, Math.min(420, e.clientX))
  sidebarWidth.value = next
}

function stopResize() {
  isResizing.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.ppt-sidebar {
  height: 100%;
  background: #fff;
  border-right: 1px solid #e5e5e5;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
  position: relative;
}
.ppt-sidebar.collapsed { width: 52px !important; }
.sidebar-header {
  padding: 14px;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  align-items: center;
  gap: 8px;
}
.new-btn {
  flex: 1;
  padding: 10px;
  background: #3a61ea;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}
.collapsed .new-btn { display: none; }
.new-btn:hover { background: #2a4bcc; }
.toggle-btn {
  width: 38px;
  height: 38px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 18px;
  color: #666;
  flex-shrink: 0;
  transition: all 0.2s;
}
.toggle-btn:hover {
  color: #3a61ea;
  border-color: #3a61ea;
}
.history-list { flex: 1; overflow-y: auto; padding: 12px; }
.history-item {
  padding: 12px;
  margin-bottom: 8px;
  background: #f9f9f9;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.history-item:hover { background: #f0f0f0; }
.history-item.active { background: #e9f0fe; border-left: 3px solid #3a61ea; }
.history-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}
.history-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}
.delete-btn {
  display: none;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: #999;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  border-radius: 4px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.history-item:hover .delete-btn {
  display: inline-flex;
}
.delete-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}
.history-time { font-size: 12px; color: #999; }
.history-empty { padding: 20px; text-align: center; color: #ccc; font-size: 13px; }

.sidebar-resize-handle {
  position: absolute;
  right: -2px;
  top: 0;
  width: 4px;
  height: 100%;
  background: #f3f4f6;
  cursor: col-resize;
  transition: background 0.2s;
  z-index: 10;
}
.sidebar-resize-handle:hover,
.sidebar-resize-handle.dragging {
  background: #3a61ea;
}
</style>
