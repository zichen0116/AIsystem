# 课堂预演第二阶段：前端渲染与页面打磨 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将课堂预演从"能跑的 MVP"打磨为产品化的教师端页面，包括新建 Lab 入口页、播放页交互打磨、侧边栏入口、历史页合并。

**Architecture:** 纯前端改动。新建 RehearsalLab.vue 作为主入口（毛玻璃风格），改造 PlaybackControls 增加进度条和全屏，打磨 RehearsalPlay 视觉层次，调整 RehearsalNew 支持 query 参数和轮询，删除独立 RehearsalHistory 页。

**Tech Stack:** Vue 3 Composition API, Pinia, Vue Router 4, Element Plus, CSS3 (backdrop-filter, gradient)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/router/index.js` | Modify | 添加 /rehearsal 路由，删除 /rehearsal/history |
| `src/components/LayoutWithNav.vue` | Modify | 添加课堂预演一级菜单项 |
| `src/views/rehearsal/RehearsalLab.vue` | Create | Lab 入口页：品牌 Logo + 输入卡片 + 我的课程 |
| `src/views/rehearsal/RehearsalNew.vue` | Modify | 支持 query 参数 + 已有会话轮询 |
| `src/components/rehearsal/PlaybackControls.vue` | Modify | 新增进度条 + 全屏按钮 |
| `src/views/rehearsal/RehearsalPlay.vue` | Modify | 视觉打磨：顶部栏、加载/错误状态、返回目标 |
| `src/views/rehearsal/RehearsalHistory.vue` | Delete | 功能合并到 Lab 页 |

---

### Task 1: 路由与侧边栏入口

**Files:**
- Modify: `teacher-platform/src/router/index.js:80-97`
- Modify: `teacher-platform/src/components/LayoutWithNav.vue:18-24`

- [ ] **Step 1: 修改路由配置**

在 `src/router/index.js` 中，将 rehearsal 相关路由替换为：

```javascript
// 替换第 80-97 行的 3 个 rehearsal 路由为：
  {
    path: '/rehearsal',
    name: 'RehearsalLab',
    component: () => import('../views/rehearsal/RehearsalLab.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/rehearsal/new',
    name: 'RehearsalNew',
    component: () => import('../views/rehearsal/RehearsalNew.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/rehearsal/play/:id',
    name: 'RehearsalPlay',
    component: () => import('../views/rehearsal/RehearsalPlay.vue'),
    meta: { requiresAuth: true }
  },
```

- [ ] **Step 2: 添加侧边栏菜单项**

在 `src/components/LayoutWithNav.vue` 第 20 行（`courseware` 之后）插入新菜单项：

```javascript
const primaryItems = [
  { id: 'lesson-prep', path: '/lesson-prep', label: '备课中心', icon: 'lesson' },
  { id: 'courseware', path: '/courseware', label: '课件管理', icon: 'folder' },
  { id: 'rehearsal', path: '/rehearsal', label: '课堂预演', icon: 'rehearsal' },
  { id: 'knowledge-base', path: '/knowledge-base', label: '知识库', icon: 'graph' },
  { id: 'question', path: '/question-gen', label: '试题生成', icon: 'exam' },
  { id: 'resource', path: '/resource-search', label: '资源搜索', icon: 'search' }
]
```

在模板 `<!-- 其它一级入口 -->` 部分的 SVG 图标区域（约第 283-420 行之间），添加 `rehearsal` 图标的 SVG（播放按钮风格）：

```html
<!-- 课堂预演：播放按钮 -->
<svg
  v-else-if="item.icon === 'rehearsal'"
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.8"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <polygon points="5 3 19 12 5 21 5 3" />
</svg>
```

将此 SVG 块插入到 `item.icon === 'graph'` 条件之前（即 `folder` 图标之后）。

- [ ] **Step 3: 验证构建**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功，无报错。

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/router/index.js teacher-platform/src/components/LayoutWithNav.vue
git commit -m "feat(rehearsal): add sidebar entry and update routes for phase 2"
```

---

### Task 2: RehearsalLab 入口页

**Files:**
- Create: `teacher-platform/src/views/rehearsal/RehearsalLab.vue`

- [ ] **Step 1: 创建 RehearsalLab.vue**

```vue
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
```

- [ ] **Step 2: 验证构建**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalLab.vue
git commit -m "feat(rehearsal): add Lab entry page with glassmorphism design"
```

---

### Task 3: RehearsalNew 支持 query 参数与轮询

**Files:**
- Modify: `teacher-platform/src/views/rehearsal/RehearsalNew.vue`

- [ ] **Step 1: 改造 RehearsalNew.vue**

完全替换 `src/views/rehearsal/RehearsalNew.vue` 的 `<script setup>` 部分，支持从 URL query 接收 `topic` 和 `sessionId`，并在 sessionId 模式下轮询会话状态：

```vue
<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { fetchSession } from '../../api/rehearsal.js'

const router = useRouter()
const route = useRoute()
const store = useRehearsalStore()

const topic = ref('')
const language = ref('zh-CN')
const enableTTS = ref(true)
let pollTimer = null

const isGenerating = computed(() => store.generatingStatus === 'generating')

const progressPercent = computed(() => {
  if (!store.totalScenes) return 10
  // 只计算已完成（ready/failed）的页数，排除 pending/generating
  const done = store.sceneStatuses.filter(s => s.status === 'ready' || s.status === 'failed').length
  return Math.round((done / store.totalScenes) * 90) + 10
})

const progressStatus = computed(() => {
  if (store.generatingStatus === 'error') return 'exception'
  if (store.generatingStatus === 'complete') return 'success'
  if (store.generatingStatus === 'partial' || store.generatingStatus === 'failed') return 'warning'
  return undefined
})

onMounted(async () => {
  const queryTopic = route.query.topic
  const querySessionId = route.query.sessionId

  if (querySessionId) {
    // 从已有会话进入：加载状态并轮询
    await loadExistingSession(Number(querySessionId))
  } else if (queryTopic) {
    // 从 Lab 页跳转：自动开始生成
    topic.value = queryTopic
    handleGenerate()
  }
})

onUnmounted(() => {
  stopPolling()
})

async function loadExistingSession(sessionId) {
  try {
    const data = await fetchSession(sessionId)
    store.currentSession = { id: data.id, title: data.title, status: data.status }
    store.totalScenes = data.total_scenes || 0
    store.sceneStatuses = (data.scenes || []).map(s => ({
      sceneIndex: s.scene_order,
      status: s.scene_status,
      title: s.title,
      sceneId: s.id,
    }))

    // 加载已就绪的场景
    store.scenes = (data.scenes || [])
      .filter(s => s.scene_status === 'ready')
      .map(s => ({
        sceneOrder: s.scene_order,
        title: s.title,
        slideContent: s.slide_content,
        actions: s.actions,
        keyPoints: s.key_points,
        sceneStatus: s.scene_status,
        audioStatus: s.audio_status,
      }))

    if (data.status === 'generating') {
      store.generatingStatus = 'generating'
      const doneCount = store.sceneStatuses.filter(s => s.status === 'ready' || s.status === 'failed').length
      store.generatingProgress = `已完成 ${doneCount}/${store.totalScenes} 页...`
      startPolling(sessionId)
    } else if (data.status === 'ready') {
      store.generatingStatus = 'complete'
      store.generatingProgress = '生成完成'
    } else if (data.status === 'partial') {
      store.generatingStatus = 'partial'
      store.generatingProgress = '部分页面生成失败，可重试失败页面'
    } else {
      store.generatingStatus = 'failed'
      store.generatingProgress = '生成失败'
    }
  } catch (e) {
    store.generatingStatus = 'error'
    store.generatingProgress = `加载失败: ${e.message}`
  }
}

function startPolling(sessionId) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const data = await fetchSession(sessionId)
      store.totalScenes = data.total_scenes || 0
      store.sceneStatuses = (data.scenes || []).map(s => ({
        sceneIndex: s.scene_order,
        status: s.scene_status,
        title: s.title,
        sceneId: s.id,
      }))

      store.scenes = (data.scenes || [])
        .filter(s => s.scene_status === 'ready')
        .map(s => ({
          sceneOrder: s.scene_order,
          title: s.title,
          slideContent: s.slide_content,
          actions: s.actions,
          keyPoints: s.key_points,
          sceneStatus: s.scene_status,
          audioStatus: s.audio_status,
        }))

      const doneCount = store.sceneStatuses.filter(s => s.status !== 'pending' && s.status !== 'generating').length
      const failedCount = store.sceneStatuses.filter(s => s.status === 'failed').length
      store.generatingProgress = `已完成 ${doneCount}/${store.totalScenes} 页`
        + (failedCount > 0 ? `（${failedCount} 页失败）` : '') + '...'

      if (data.status !== 'generating') {
        if (data.status === 'ready') {
          store.generatingStatus = 'complete'
          store.generatingProgress = '生成完成'
        } else if (data.status === 'partial') {
          store.generatingStatus = 'partial'
          store.generatingProgress = '部分页面生成失败，可重试失败页面'
        } else {
          store.generatingStatus = 'failed'
          store.generatingProgress = '生成失败'
        }
        store.currentSession.status = data.status
        stopPolling()
      }
    } catch (e) {
      console.error('Polling failed:', e)
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleGenerate() {
  store.$reset()
  await store.startGenerate({
    topic: topic.value.trim(),
    language: language.value,
    enable_tts: enableTTS.value,
    voice: 'Cherry',
    speed: 1.0,
  })
}

async function handleRetry(sceneOrder) {
  if (!store.currentSession?.id) return
  const newStatus = await store.retryFailedScene(store.currentSession.id, sceneOrder)
  // 重试后重新拉取会话以刷新汇总状态
  await loadExistingSession(store.currentSession.id)
}

function goToPlay() {
  if (store.currentSession?.id) {
    router.push(`/rehearsal/play/${store.currentSession.id}`)
  }
}
</script>
```

同时修改模板中表单部分，当有 `sessionId` 或已在生成时隐藏表单输入：

替换模板中 `<div class="rehearsal-new">` 内的内容为：

```html
<div class="new-card">
  <h2>课堂预演</h2>
  <p class="desc">输入教学主题，AI 为您生成可播放的课堂预演</p>

  <!-- 表单输入：仅在无 sessionId 且未生成时显示 -->
  <template v-if="!route.query.sessionId && !store.generatingStatus">
    <div class="form-group">
      <label>教学主题</label>
      <el-input v-model="topic" type="textarea" :rows="3"
        placeholder="例：高中物理 - 牛顿第二定律" :disabled="isGenerating" />
    </div>

    <div class="form-row">
      <div class="form-group half">
        <label>语言</label>
        <el-select v-model="language" :disabled="isGenerating">
          <el-option label="中文" value="zh-CN" />
          <el-option label="English" value="en-US" />
        </el-select>
      </div>
      <div class="form-group half">
        <label>语音合成</label>
        <el-switch v-model="enableTTS" :disabled="isGenerating" />
      </div>
    </div>

    <el-button type="primary" :loading="isGenerating"
      :disabled="!topic.trim() || isGenerating" @click="handleGenerate" style="width:100%">
      {{ isGenerating ? '生成中...' : '开始生成' }}
    </el-button>
  </template>

  <!-- 生成进度 -->
  <div v-if="store.generatingStatus" class="progress-section">
    <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="8" />
    <p class="progress-text">{{ store.generatingProgress }}</p>

    <!-- 页级状态列表 -->
    <div v-if="store.sceneStatuses.length" class="scene-status-list">
      <div v-for="s in store.sceneStatuses" :key="s.sceneIndex" class="scene-status-item">
        <span class="scene-title">{{ s.sceneIndex + 1 }}. {{ s.title }}</span>
        <el-tag :type="s.status === 'ready' ? 'success' : s.status === 'failed' ? 'danger' : 'info'" size="small">
          {{ s.status === 'ready' ? '就绪' : s.status === 'failed' ? '失败' : '生成中' }}
        </el-tag>
        <el-button v-if="s.status === 'failed'" size="small" text type="primary"
          @click="handleRetry(s.sceneIndex)">
          重试
        </el-button>
      </div>
    </div>

    <el-button v-if="store.scenes.length > 0 && store.currentSession"
      type="success" @click="goToPlay" style="width:100%;margin-top:12px">
      开始播放（{{ store.scenes.length }} 页就绪）
    </el-button>

    <el-button @click="router.push('/rehearsal')" style="width:100%;margin-top:8px">
      返回
    </el-button>
  </div>
</div>
```

- [ ] **Step 2: 验证构建**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalNew.vue
git commit -m "feat(rehearsal): support query params and polling in RehearsalNew"
```

---

### Task 4: PlaybackControls 增加进度条与全屏

**Files:**
- Modify: `teacher-platform/src/components/rehearsal/PlaybackControls.vue`

- [ ] **Step 1: 重写 PlaybackControls.vue**

完全替换 `src/components/rehearsal/PlaybackControls.vue` 的内容：

```vue
<template>
  <div class="playback-controls">
    <div class="controls-center">
      <button class="ctrl-btn" :disabled="currentIndex <= 0" @click="$emit('prev')" title="上一页">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>

      <button class="ctrl-btn play-btn" @click="$emit(isPlaying ? 'pause' : 'play')" :title="isPlaying ? '暂停' : '播放'">
        <svg v-if="!isPlaying" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
      </button>

      <button class="ctrl-btn" :disabled="currentIndex >= totalCount - 1" @click="$emit('next')" title="下一页">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    </div>

    <div class="progress-bar">
      <div class="progress-dots">
        <button
          v-for="i in totalCount"
          :key="i"
          class="dot"
          :class="{ active: i - 1 === currentIndex, done: i - 1 < currentIndex }"
          @click="$emit('jump', i - 1)"
          :title="`第 ${i} 页`"
        ></button>
      </div>
      <span class="page-text">{{ currentIndex + 1 }} / {{ totalCount }}</span>
    </div>

    <div class="controls-right">
      <button class="ctrl-btn" @click="toggleFullscreen" title="全屏">
        <svg v-if="!isFullscreen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

defineProps({
  isPlaying: { type: Boolean, default: false },
  currentIndex: { type: Number, default: 0 },
  totalCount: { type: Number, default: 0 },
})
defineEmits(['prev', 'next', 'play', 'pause', 'jump'])

const isFullscreen = ref(false)

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
  } else {
    document.exitFullscreen().catch(() => {})
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
})
onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})
</script>

<style scoped>
.playback-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: #161b22;
  border-top: 1px solid #30363d;
  gap: 16px;
}

.controls-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ctrl-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: #e6edf3;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.ctrl-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.ctrl-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.ctrl-btn svg {
  width: 18px;
  height: 18px;
}

.play-btn {
  width: 44px;
  height: 44px;
  background: #e6edf3;
  color: #0d1117;
  border-radius: 50%;
}

.play-btn:hover {
  background: #ffffff !important;
}

.play-btn svg {
  width: 20px;
  height: 20px;
}

.progress-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.progress-dots {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.progress-dots::-webkit-scrollbar {
  display: none;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none;
  background: #30363d;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
  padding: 0;
}

.dot:hover {
  background: #8b949e;
  transform: scale(1.3);
}

.dot.done {
  background: #58a6ff;
}

.dot.active {
  background: #e6edf3;
  transform: scale(1.5);
  box-shadow: 0 0 6px rgba(230, 237, 243, 0.4);
}

.page-text {
  color: #8b949e;
  font-size: 13px;
  white-space: nowrap;
}

.controls-right {
  display: flex;
  align-items: center;
}
</style>
```

- [ ] **Step 2: 在 RehearsalPlay.vue 中传递新的 jump 事件**

在 `src/views/rehearsal/RehearsalPlay.vue` 模板中，给 `<PlaybackControls>` 添加 `@jump` 事件处理：

将：
```html
    <PlaybackControls
      :isPlaying="store.isPlaying"
      :currentIndex="store.currentSceneIndex"
      :totalCount="store.totalScenesCount"
      @play="handlePlay"
      @pause="engine.pause()"
      @prev="engine.prevScene()"
      @next="engine.nextScene()"
    />
```

替换为：
```html
    <PlaybackControls
      :isPlaying="store.isPlaying"
      :currentIndex="store.currentSceneIndex"
      :totalCount="store.totalScenesCount"
      @play="handlePlay"
      @pause="engine.pause()"
      @prev="engine.prevScene()"
      @next="engine.nextScene()"
      @jump="engine.jumpToScene($event)"
    />
```

- [ ] **Step 3: 验证构建**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功。

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/components/rehearsal/PlaybackControls.vue teacher-platform/src/views/rehearsal/RehearsalPlay.vue
git commit -m "feat(rehearsal): add progress dots and fullscreen to PlaybackControls"
```

---

### Task 5: RehearsalPlay 播放页视觉打磨

**Files:**
- Modify: `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`

- [ ] **Step 1: 重写 RehearsalPlay.vue**

完全替换 `src/views/rehearsal/RehearsalPlay.vue`：

```vue
<template>
  <div class="rehearsal-play">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>正在加载预演...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <p class="error-icon">!</p>
      <p class="error-text">{{ error }}</p>
      <div class="error-actions">
        <button class="error-btn primary" @click="retryLoad">重试</button>
        <button class="error-btn" @click="goBack">返回</button>
      </div>
    </div>

    <!-- 播放界面 -->
    <template v-else>
      <!-- Top bar -->
      <div class="top-bar">
        <button class="back-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          <span class="back-label">当前场景</span>
        </button>
        <span class="scene-title">{{ store.currentScene?.title || '' }}</span>
        <div class="top-spacer"></div>
      </div>

      <!-- Slide area -->
      <div class="slide-area">
        <div class="slide-container">
          <SlideRenderer v-if="store.currentScene" :slide="store.currentScene.slideContent" ref="slideRef">
            <SpotlightOverlay :target="store.spotlightTarget" :canvasRef="canvasEl" />
            <LaserPointer :target="store.laserTarget" :canvasRef="canvasEl" />
          </SlideRenderer>
          <div v-else class="empty-slide">
            <p>暂无内容</p>
          </div>
        </div>
      </div>

      <!-- Subtitle -->
      <SubtitlePanel :text="store.currentSubtitle" />

      <!-- Controls -->
      <PlaybackControls
        :isPlaying="store.isPlaying"
        :currentIndex="store.currentSceneIndex"
        :totalCount="store.totalScenesCount"
        @play="handlePlay"
        @pause="engine.pause()"
        @prev="engine.prevScene()"
        @next="engine.nextScene()"
        @jump="engine.jumpToScene($event)"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { usePlaybackEngine } from '../../composables/usePlaybackEngine.js'
import SlideRenderer from '../../components/rehearsal/SlideRenderer.vue'
import SpotlightOverlay from '../../components/rehearsal/SpotlightOverlay.vue'
import LaserPointer from '../../components/rehearsal/LaserPointer.vue'
import SubtitlePanel from '../../components/rehearsal/SubtitlePanel.vue'
import PlaybackControls from '../../components/rehearsal/PlaybackControls.vue'

const route = useRoute()
const router = useRouter()
const store = useRehearsalStore()
const engine = usePlaybackEngine()
const slideRef = ref(null)
const loading = ref(true)
const error = ref('')

const canvasEl = computed(() => slideRef.value?.canvasRef || null)

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) {
    error.value = '无效的预演 ID'
    loading.value = false
    return
  }
  try {
    if (!store.currentSession || store.currentSession.id !== id) {
      await store.loadSession(id)
    }
    if (store.scenes.length === 0) {
      error.value = '该预演暂无可播放的内容'
    }
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  engine.cleanup()
  store.savePlaybackProgress()
})

function handlePlay() {
  if (store.isPaused) {
    engine.resume()
  } else {
    engine.start()
  }
}

async function retryLoad() {
  loading.value = true
  error.value = ''
  try {
    const id = Number(route.params.id)
    await store.loadSession(id)
    if (store.scenes.length === 0) {
      error.value = '该预演暂无可播放的内容'
    }
  } catch (e) {
    error.value = `加载失败: ${e.message}`
  } finally {
    loading.value = false
  }
}

function goBack() {
  engine.stop()
  router.push('/rehearsal')
}
</script>

<style scoped>
.rehearsal-play {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

/* 加载状态 */
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #8b949e;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #30363d;
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误状态 */
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.error-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.error-text {
  color: #8b949e;
  font-size: 15px;
  margin: 0;
}

.error-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.error-btn {
  padding: 8px 24px;
  border: 1px solid #30363d;
  background: transparent;
  color: #e6edf3;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s;
}

.error-btn:hover {
  background: #161b22;
  border-color: #8b949e;
}

.error-btn.primary {
  background: #58a6ff;
  border-color: #58a6ff;
  color: #0d1117;
}

.error-btn.primary:hover {
  background: #79b8ff;
  border-color: #79b8ff;
}

/* Top bar */
.top-bar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #21262d;
  min-height: 48px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: #8b949e;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  transition: all 0.15s;
}

.back-btn:hover {
  color: #e6edf3;
  background: rgba(255, 255, 255, 0.06);
}

.back-btn svg {
  width: 16px;
  height: 16px;
}

.scene-title {
  flex: 1;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #e6edf3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 16px;
}

.top-spacer {
  width: 100px; /* 平衡返回按钮宽度，使标题居中 */
}

/* Slide area */
.slide-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 32px;
  min-height: 0;
}

.slide-container {
  max-width: 960px;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  position: relative;
}

.empty-slide {
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #161b22;
  color: #8b949e;
  border-radius: 12px;
}
</style>
```

- [ ] **Step 2: 验证构建**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalPlay.vue
git commit -m "feat(rehearsal): polish playback page with loading/error states"
```

---

### Task 6: 删除 RehearsalHistory 并清理引用

**Files:**
- Delete: `teacher-platform/src/views/rehearsal/RehearsalHistory.vue`

- [ ] **Step 1: 删除 RehearsalHistory.vue**

```bash
rm teacher-platform/src/views/rehearsal/RehearsalHistory.vue
```

- [ ] **Step 2: 验证没有剩余引用**

搜索项目中是否还有对 `RehearsalHistory` 或 `/rehearsal/history` 的引用：

```bash
cd teacher-platform && grep -r "rehearsal/history\|RehearsalHistory" src/ --include="*.vue" --include="*.js"
```

Expected: 无匹配结果（路由已在 Task 1 中删除，Play 页返回目标已在 Task 5 改为 `/rehearsal`）。

- [ ] **Step 3: 验证构建**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功。

- [ ] **Step 4: Commit**

```bash
git add -A teacher-platform/src/views/rehearsal/
git commit -m "refactor(rehearsal): remove RehearsalHistory, merged into Lab page"
```

---

### Task 7: 最终验证

- [ ] **Step 1: 完整构建验证**

```bash
cd teacher-platform && npm run build
```

Expected: 构建成功，无警告。

- [ ] **Step 2: 检查路由正确性**

在构建产物中确认路由 chunk 已生成：

```bash
ls teacher-platform/dist/assets/ | grep -i "rehearsal"
```

Expected: 应有 RehearsalLab、RehearsalNew、RehearsalPlay 对应的 chunk 文件。

- [ ] **Step 3: 验证没有死引用**

```bash
cd teacher-platform && grep -r "RehearsalHistory\|rehearsal/history" src/ --include="*.vue" --include="*.js" --include="*.ts"
```

Expected: 无匹配结果。
