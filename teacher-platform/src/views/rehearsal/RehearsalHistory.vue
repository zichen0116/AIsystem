<template>
  <div class="rehearsal-history">
    <div class="header">
      <h2>预演历史</h2>
      <el-button type="primary" @click="$router.push('/rehearsal/new')">+ 新建预演</el-button>
    </div>

    <div v-loading="store.sessionsLoading" class="session-list">
      <div v-if="!store.sessionsLoading && store.sessions.length === 0" class="empty">
        <p>暂无预演记录</p>
        <el-button type="primary" @click="$router.push('/rehearsal/new')">创建第一个预演</el-button>
      </div>

      <div v-for="session in store.sessions" :key="session.id" class="session-card">
        <div class="card-info">
          <div class="card-title">{{ session.title }}</div>
          <div class="card-meta">
            {{ session.total_scenes }} 页
            <template v-if="session.ready_count"> · {{ session.ready_count }} 就绪</template>
            <template v-if="session.failed_count"> · {{ session.failed_count }} 失败</template>
            · {{ formatDate(session.created_at) }}
          </div>
        </div>
        <div class="card-actions">
          <el-tag :type="statusTagType(session.status)" size="small">{{ statusLabel(session.status) }}</el-tag>
          <el-button v-if="session.status !== 'generating'" text type="primary" size="small"
            @click="$router.push(`/rehearsal/play/${session.id}`)">
            ▶ 播放
          </el-button>
          <el-button text type="danger" size="small" @click="handleDelete(session.id)">删除</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { ElMessageBox } from 'element-plus'

const store = useRehearsalStore()

onMounted(() => { store.loadSessions() })

function statusLabel(status) {
  return { generating: '生成中', partial: '部分完成', ready: '已完成', failed: '失败' }[status] || status
}

function statusTagType(status) {
  return { generating: 'warning', partial: 'info', ready: 'success', failed: 'danger' }[status] || 'info'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该预演？', '提示', { type: 'warning' })
    await store.removeSession(id)
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.rehearsal-history { max-width: 700px; margin: 40px auto; padding: 0 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h2 { margin: 0; font-size: 20px; }
.session-list { min-height: 200px; }
.empty { text-align: center; padding: 60px 0; color: #8b949e; }
.session-card { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 16px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 15px; font-weight: 500; color: #333; }
.card-meta { font-size: 12px; color: #8b949e; margin-top: 4px; }
.card-actions { display: flex; align-items: center; gap: 8px; }
</style>
