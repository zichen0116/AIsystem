<template>
  <aside class="ppt-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <button class="new-btn" @click="$emit('new-session')">+ 新建PPT</button>
      <button class="toggle-btn" @click="$emit('toggle')">{{ collapsed ? '→' : '←' }}</button>
    </div>
    <div v-if="!collapsed" class="history-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="history-item"
        :class="{ active: s.id === activeId }"
        @click="$emit('select', s.id)"
      >
        <div class="history-title">{{ s.title }}</div>
        <div class="history-time">{{ formatTime(s.updated_at) }}</div>
      </div>
      <div v-if="!sessions.length" class="history-empty">暂无历史会话</div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: Number, default: null },
  collapsed: { type: Boolean, default: false },
})
defineEmits(['new-session', 'select', 'toggle'])

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.ppt-sidebar {
  width: 260px;
  height: 100%;
  background: #fff;
  border-right: 1px solid #e5e5e5;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
}
.ppt-sidebar.collapsed { width: 52px; }
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
}
.collapsed .new-btn { display: none; }
.new-btn:hover { background: #2a4bcc; }
.toggle-btn {
  width: 34px;
  height: 34px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  flex-shrink: 0;
}
.history-list { flex: 1; overflow-y: auto; padding: 10px; }
.history-item {
  padding: 10px 12px;
  margin-bottom: 6px;
  background: #f9f9f9;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.history-item:hover { background: #f0f0f0; }
.history-item.active { background: #e9f0fe; border-left: 3px solid #3a61ea; }
.history-title { font-size: 14px; font-weight: 500; color: #333; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.history-time { font-size: 12px; color: #999; }
.history-empty { padding: 20px; text-align: center; color: #ccc; font-size: 13px; }
</style>
