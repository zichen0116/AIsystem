<template>
  <div class="rehearsal-lab">
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
        <input
          ref="fileInput"
          class="file-input"
          type="file"
          accept=".pdf,.ppt,.pptx"
          @change="handleFileChange"
        />
      </div>

      <div v-if="selectedFile" class="upload-preview">
        <div class="upload-preview-main">
          <div class="upload-file-name">{{ selectedFile.name }}</div>
          <div class="upload-file-meta">{{ selectedFileExtensionLabel }} · {{ selectedFileSizeText }}</div>
          <div class="upload-file-hint">支持 PDF / PPT / PPTX，单个文件不超过 50MB</div>
        </div>
        <div class="upload-preview-actions">
          <button class="upload-cancel-btn" :disabled="isUploadingFile" @click="clearSelectedFile">取消</button>
          <button class="upload-confirm-btn" :disabled="isUploadingFile" @click="handleUploadConfirm">
            {{ isUploadingFile ? '上传中...' : '确认上传' }}
          </button>
        </div>
      </div>

      <div class="card-footer">
        <div class="footer-icons">
          <button class="icon-btn" title="上传 PDF / PPT / PPTX" @click="openFilePicker">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <button
            v-if="isSupported"
            class="icon-btn"
            :class="{ recording: isRecording }"
            :title="isRecording ? '停止语音输入' : '语音输入'"
            @click="toggleRecording"
          >
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

    <div class="my-courses">
      <div class="courses-header">
        <span class="courses-tab active">我的课程</span>
      </div>

      <div v-if="store.sessionsLoading" class="courses-loading">
        <div v-for="i in 3" :key="i" class="skeleton-card"></div>
      </div>

      <div v-else-if="store.sessions.length === 0" class="courses-empty">
        <p>还没有课程，输入主题或上传文件开始预演吧</p>
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
            <span class="card-scenes">{{ sessionPageCount(session) }} pages</span>
            <span class="card-dot">|</span>
            <span class="card-source">{{ session.source === 'upload' ? 'FILE' : 'TOPIC' }}</span>
            <span class="card-dot">|</span>
            <span class="card-date">{{ formatDate(session.created_at) }}</span>
          </div>
          <div class="card-bottom">
            <span :class="['status-tag', `status-${session.status}`]">{{ statusLabel(session.status) }}</span>
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
import { useVoiceInput } from '../../composables/useVoiceInput.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const MAX_UPLOAD_SIZE = 50 * 1024 * 1024
const ALLOWED_UPLOAD_EXTENSIONS = ['pdf', 'ppt', 'pptx']

const router = useRouter()
const store = useRehearsalStore()
const userStore = useUserStore()

const topic = ref('')
const fileInput = ref(null)
const selectedFile = ref(null)
const isUploadingFile = ref(false)
const { isRecording, isSupported, toggleRecording } = useVoiceInput(topic)

const avatarLetter = computed(() => {
  const name = userStore.userInfo?.username || '老师'
  return name.charAt(0)
})

const selectedFileSizeText = computed(() => formatFileSize(selectedFile.value?.size || 0))
const selectedFileExtensionLabel = computed(() => selectedFile.value?.name?.split('.').pop()?.toUpperCase() || 'FILE')

onMounted(() => {
  store.loadSessions()
})

function handleSubmit() {
  if (!topic.value.trim()) return
  router.push({ path: '/rehearsal/new', query: { topic: topic.value.trim() } })
}

function openFilePicker() {
  fileInput.value?.click()
}

function handleFileChange(event) {
  const file = event.target?.files?.[0]
  if (!file) return

  const errorMessage = validateUploadFile(file)
  if (errorMessage) {
    clearSelectedFile()
    ElMessage.error(errorMessage)
    return
  }

  selectedFile.value = file
}

function validateUploadFile(file) {
  const extension = file.name.split('.').pop()?.toLowerCase() || ''
  if (!ALLOWED_UPLOAD_EXTENSIONS.includes(extension)) {
    return '文件类型不支持'
  }
  if (file.size > MAX_UPLOAD_SIZE) {
    return '文件大小超过50MB'
  }
  return ''
}

function clearNativeFileInput() {
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function clearSelectedFile() {
  selectedFile.value = null
  clearNativeFileInput()
}

async function handleUploadConfirm() {
  if (!selectedFile.value || isUploadingFile.value) return

  isUploadingFile.value = true
  try {
    const payload = await store.uploadSessionFile(selectedFile.value)
    const sessionId = payload?.session_id
    clearSelectedFile()

    if (!sessionId) {
      throw new Error('上传成功但未返回会话ID')
    }

    router.push({
      path: '/rehearsal/new',
      query: {
        sessionId: String(sessionId),
        source: 'upload',
      },
    })
  } catch (error) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    isUploadingFile.value = false
  }
}

function handleCardClick(session) {
  if (session.status === 'ready') {
    router.push(`/rehearsal/play/${session.id}`)
    return
  }

  router.push({
    path: '/rehearsal/new',
    query: {
      sessionId: String(session.id),
      ...(session.source === 'upload' ? { source: 'upload' } : {}),
    },
  })
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该预演？', '提示', { type: 'warning' })
    await store.removeSession(id)
  } catch {
    // cancelled
  }
}

function statusLabel(status) {
  return {
    processing: '处理中',
    generating: '生成中',
    partial: '部分完成',
    ready: '已就绪',
    failed: '生成失败',
  }[status] || status
}

function sessionPageCount(session) {
  return session.total_pages || session.total_scenes || 0
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} B`
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.rehearsal-lab {
  --rehearsal-bg:
    radial-gradient(circle at top, rgba(114, 46, 209, 0.12), transparent 34%),
    radial-gradient(circle at 85% 12%, rgba(99, 102, 241, 0.1), transparent 26%),
    linear-gradient(180deg, #fafbff 0%, #f5f7fc 100%);
  --rehearsal-card-bg: rgba(255, 255, 255, 0.92);
  --rehearsal-card-border: rgba(220, 226, 239, 0.95);
  --rehearsal-card-shadow: 0 18px 48px rgba(37, 45, 82, 0.1);
  --rehearsal-accent: #f6b73c;
  --rehearsal-accent-strong: #ea580c;
  --rehearsal-accent-soft: rgba(249, 115, 22, 0.14);
  --rehearsal-text: #111827;
  --rehearsal-muted: #667085;
  --rehearsal-muted-soft: #98a2b3;
  min-height: 100vh;
  background: var(--rehearsal-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px 60px;
}

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
  color: var(--rehearsal-text);
}

.logo-rehearsal {
  color: #ec4899;
}

.input-card {
  width: 100%;
  max-width: 640px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  padding: 28px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
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
  color: var(--rehearsal-text);
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

.file-input {
  display: none;
}

.upload-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(249, 115, 22, 0.08);
  border: 1px solid rgba(249, 115, 22, 0.16);
}

.upload-preview-main {
  min-width: 0;
  flex: 1;
}

.upload-file-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--rehearsal-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-file-meta,
.upload-file-hint {
  font-size: 12px;
  color: var(--rehearsal-muted);
}

.upload-file-meta {
  margin-top: 4px;
}

.upload-file-hint {
  margin-top: 6px;
}

.upload-preview-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.upload-cancel-btn,
.upload-confirm-btn {
  border: none;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.upload-cancel-btn {
  background: rgba(255, 255, 255, 0.82);
  color: var(--rehearsal-muted);
}

.upload-cancel-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 1);
  color: var(--rehearsal-text);
}

.upload-confirm-btn {
  background: var(--rehearsal-accent);
  color: #fff;
}

.upload-confirm-btn:hover:not(:disabled) {
  background: var(--rehearsal-accent-strong);
}

.upload-cancel-btn:disabled,
.upload-confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.icon-btn.recording {
  background: var(--rehearsal-accent);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(212, 162, 76, 0.24);
}

.icon-btn svg {
  width: 20px;
  height: 20px;
}

.submit-btn {
  padding: 10px 28px;
  border: none;
  background: var(--rehearsal-accent);
  color: white;
  font-size: 15px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.submit-btn:hover:not(:disabled) {
  background: var(--rehearsal-accent-strong);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

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
  color: var(--rehearsal-text);
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
  color: var(--rehearsal-muted);
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
  color: var(--rehearsal-text);
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
  color: var(--rehearsal-muted-soft);
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

.card-source {
  color: #7c3aed;
  font-weight: 600;
  letter-spacing: 0.04em;
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

.status-processing,
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

  .upload-preview {
    flex-direction: column;
    align-items: stretch;
  }

  .upload-preview-actions {
    width: 100%;
  }

  .upload-cancel-btn,
  .upload-confirm-btn {
    flex: 1;
  }
}
</style>
