<template>
  <div class="rehearsal-lab">
    <!-- 品牌 Logo -->
    <div class="brand-logo">
      <div class="logo-icon">
        <div class="cube cube-pink"></div>
        <div class="cube cube-yellow"></div>
      </div>
      <div class="logo-text">
        <span class="logo-lesson">Lesson</span>
        <span class="logo-rehearsal">Rehearsal</span>
      </div>
    </div>

    <!-- 核心输入卡片 -->
    <div class="input-card">
      <div class="card-header">
        <div class="user-avatar">
          <img v-if="userStore.userInfo?.avatar" :src="userStore.userInfo.avatar" alt="" />
          <div v-else class="avatar-placeholder">{{ avatarLetter }}</div>
        </div>
        <span class="greeting">嗨，老师</span>
      </div>

      <div class="input-area">
        <textarea
          v-model="topic"
          class="topic-input"
          placeholder="输入您要预演的教学主题，例如：&#10;「中国历史文化发展课程预演」&#10;「数据结构红黑树课程预演」"
          rows="4"
          @keydown.enter.ctrl="handleSubmit"
        ></textarea>
      </div>

      <div class="card-footer">
        <div class="footer-icons">
          <button class="icon-btn" title="附件上传（敬请期待）" @click="showComingSoon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <button class="icon-btn" title="语音输入（敬请期待）" @click="showComingSoon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>
        </div>
        <button class="submit-btn" :disabled="!topic.trim()" @click="handleSubmit">确认</button>
      </div>
    </div>

    <!-- 我的课程 -->
    <div class="my-courses">
      <div class="courses-header">
        <span class="courses-tab active">我的课程</span>
      </div>

      <div v-if="store.sessionsLoading" class="courses-loading">
        <div v-for="i in 3" :key="i" class="skeleton-card"></div>
      </div>

      <div v-else-if="store.sessions.length === 0" class="courses-empty">
        <p>还没有课程，输入主题开始预演吧</p>
      </div>

      <div v-else class="courses-grid">
        <div
          v-for="session in store.sessions"
          :key="session.id"
          class="course-card"
          @click="handleCardClick(session)"
        >
          <div class="card-top">
            <span class="card-title">{{ session.title }}</span>
            <button class="card-delete" @click.stop="handleDelete(session.id)" title="删除">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
          <div class="card-body">
            <span class="card-scenes">{{ session.total_scenes || 0 }} 页</span>
            <span class="card-dot">·</span>
            <span class="card-date">{{ formatDate(session.created_at) }}</span>
          </div>
          <div class="card-bottom">
            <span :class="['status-tag', `status-${session.status}`]">{{ statusLabel(session.status) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { useUserStore } from '../../stores/user.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const store = useRehearsalStore()
const userStore = useUserStore()

const topic = ref('')

const avatarLetter = computed(() => {
  const name = userStore.userInfo?.username || '老师'
  return name.charAt(0)
})

onMounted(() => {
  store.loadSessions()
})

function handleSubmit() {
  if (!topic.value.trim()) return
  router.push({ path: '/rehearsal/new', query: { topic: topic.value.trim() } })
}

function showComingSoon() {
  ElMessage.info('敬请期待')
}

function handleCardClick(session) {
  if (session.status === 'ready') {
    router.push(`/rehearsal/play/${session.id}`)
  } else {
    router.push({ path: '/rehearsal/new', query: { sessionId: String(session.id) } })
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该预演？', '提示', { type: 'warning' })
    await store.removeSession(id)
  } catch { /* cancelled */ }
}

function statusLabel(status) {
  return { generating: '生成中', partial: '部分完成', ready: '已就绪', failed: '生成失败' }[status] || status
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.rehearsal-lab {
  min-height: 100vh;
  background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 30%, #fff1f2 60%, #ffffff 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px 60px;
}

/* 品牌 Logo */
.brand-logo {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 36px;
}

.logo-icon {
  position: relative;
  width: 40px;
  height: 40px;
}

.cube {
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 5px;
  transform: rotate(-10deg);
}

.cube-pink {
  background: #ec4899;
  top: 0;
  left: 0;
}

.cube-yellow {
  background: #f59e0b;
  bottom: 0;
  right: 0;
  transform: rotate(8deg);
}

.logo-text {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.logo-lesson {
  color: #1e293b;
}

.logo-rehearsal {
  color: #ec4899;
}

/* 输入卡片 */
.input-card {
  width: 100%;
  max-width: 640px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  margin-bottom: 40px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #ec4899, #f59e0b);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
}

.greeting {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.topic-input {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.7;
  color: #334155;
  background: transparent;
  font-family: inherit;
}

.topic-input::placeholder {
  color: #94a3b8;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.footer-icons {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 10px;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.icon-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #64748b;
}

.icon-btn svg {
  width: 20px;
  height: 20px;
}

.submit-btn {
  padding: 10px 28px;
  border: none;
  background: #ec4899;
  color: white;
  font-size: 15px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.submit-btn:hover:not(:disabled) {
  background: #db2777;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 我的课程 */
.my-courses {
  width: 100%;
  max-width: 900px;
}

.courses-header {
  margin-bottom: 20px;
}

.courses-tab {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  padding-bottom: 8px;
  border-bottom: 2px solid #ec4899;
}

.courses-loading {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.skeleton-card {
  height: 140px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  animation: skeleton-pulse 1.5s infinite ease-in-out;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}

.courses-empty {
  text-align: center;
  padding: 48px 0;
  color: #94a3b8;
  font-size: 15px;
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.course-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-delete {
  border: none;
  background: transparent;
  color: #cbd5e1;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.15s;
  flex-shrink: 0;
}

.card-delete:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

.card-body {
  font-size: 13px;
  color: #ec4899;
  margin-bottom: 12px;
}

.card-dot {
  margin: 0 4px;
}

.card-bottom {
  display: flex;
  align-items: center;
}

.status-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 20px;
  font-weight: 500;
}

.status-ready {
  background: #dcfce7;
  color: #16a34a;
}

.status-generating {
  background: #dbeafe;
  color: #2563eb;
  animation: status-blink 1.5s infinite;
}

@keyframes status-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.status-partial {
  background: #fef3c7;
  color: #d97706;
}

.status-failed {
  background: #fef2f2;
  color: #dc2626;
}

/* 响应式 */
@media (max-width: 640px) {
  .rehearsal-lab {
    padding: 32px 16px 48px;
  }
  .input-card {
    padding: 20px;
    border-radius: 16px;
  }
  .logo-text {
    font-size: 22px;
  }
}
</style>
