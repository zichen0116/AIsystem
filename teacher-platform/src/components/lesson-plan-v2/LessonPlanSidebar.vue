<template>
  <div class="sidebar-wrapper">
    <transition name="sidebar-slide">
      <div v-if="!collapsed" class="lesson-sidebar" :class="{ overlay: isOverlay }">
        <div class="sidebar-header">
          <button class="new-btn" @click="$emit('new-conversation')">＋ 新建对话</button>
          <button class="collapse-btn" @click="$emit('toggle')" title="收起侧边栏">‹</button>
        </div>
        <div class="history-list">
          <div v-if="loading" class="loading-state">加载中...</div>
          <div v-else-if="error" class="error-state">{{ error }}</div>
          <div v-else-if="historyList.length === 0" class="empty-state">暂无历史记录</div>
          <div
            v-else
            v-for="item in historyList"
            :key="item.id"
            class="history-item"
            :class="{ active: item.id === activeId }"
            @click="selectHistory(item)"
          >
            <div class="item-content">
              <div class="history-title">{{ item.title }}</div>
              <div class="history-time">{{ item.time }}</div>
            </div>
            <button
              class="delete-btn"
              @click.stop="handleDelete(item)"
              title="删除"
            >×</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Expand button (shown when collapsed) -->
    <button v-if="collapsed" class="sidebar-toggle" @click="$emit('toggle')">›</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { resolveApiUrl, getToken, authFetch } from '../../api/http.js'

defineProps({
  collapsed: { type: Boolean, default: false },
  isOverlay: { type: Boolean, default: false },
})

const emit = defineEmits(['new-conversation', 'toggle', 'select-history', 'delete-history', 'toast'])

const activeId = ref(null)
const historyList = ref([])
const loading = ref(false)
const error = ref(null)

// 格式化时间显示
function formatTime(isoString) {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else if (diffDays === 1) {
    return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else {
    return `${date.getMonth() + 1}月${date.getDate()}日`
  }
}

// 加载历史列表
async function loadHistory() {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(resolveApiUrl('/api/v1/lesson-plan/list'), {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    })

    if (!response.ok) {
      throw new Error('加载历史失败')
    }

    const data = await response.json()
    historyList.value = data.items.map(item => ({
      id: item.id,
      title: item.title,
      time: formatTime(item.created_at),
      status: item.status,
      sessionId: item.session_id
    }))
  } catch (err) {
    console.error('加载历史失败:', err)
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// 选择历史记录
function selectHistory(item) {
  activeId.value = item.id
  emit('select-history', item)
}

onMounted(() => {
  loadHistory()
})

// 暴露刷新方法供父组件调用
defineExpose({
  refresh: loadHistory
})
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
.loading-state,
.error-state,
.empty-state {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}
.error-state {
  color: #f56c6c;
}
.history-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: #444;
  cursor: pointer;
  margin-bottom: 4px;
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
.item-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.history-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-time {
  font-size: 11px;
  color: #aaa;
  margin-top: 2px;
}
.delete-btn {
  opacity: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: #e0e7ff;
  color: #6366f1;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  margin-left: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}
.history-item:hover .delete-btn {
  opacity: 1;
}
.delete-btn:hover {
  background: #c7d2fe;
  color: #4f46e5;
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
