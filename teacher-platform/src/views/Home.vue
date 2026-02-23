<script setup>
import { ref, provide } from 'vue'
import { useUserStore } from '../stores/user'
import LoginRegisterModal from '../components/LoginRegisterModal.vue'
import LessonPrep from './LessonPrep.vue'
import CoursewareManage from './CoursewareManage.vue'
import KnowledgeBase from './KnowledgeBase.vue'
import PersonalCenter from './PersonalCenter.vue'

const userStore = useUserStore()
const showLoginModal = ref(false)
const activeSection = ref('home')

const sections = [
  { id: 'home', label: '首页' },
  { id: 'lesson-prep', label: '备课中心' },
  { id: 'courseware', label: '课件管理' },
  { id: 'knowledge-base', label: '知识库' }
]

function setSection(id) {
  activeSection.value = id
}

function handleAvatarClick() {
  if (userStore.isLoggedIn) {
    activeSection.value = 'personal-center'
  } else {
    showLoginModal.value = true
  }
}

provide('openLoginModal', () => { showLoginModal.value = true })
provide('goToHome', () => { activeSection.value = 'home' })
</script>

<template>
  <div class="home-page">
    <header class="top-nav">
      <div class="nav-left">
        <h1 class="logo">教师备课平台</h1>
      </div>
      <nav class="nav-right">
        <button
          v-for="s in sections"
          :key="s.id"
          class="nav-btn"
          :class="{ active: activeSection === s.id }"
          @click="setSection(s.id)"
        >
          {{ s.label }}
        </button>
        <div
          class="avatar"
          :class="{ 'avatar-logged-in': userStore.isLoggedIn, active: activeSection === 'personal-center' }"
          @click="handleAvatarClick"
        >
          <span v-if="userStore.isLoggedIn" class="avatar-initial">{{ userStore.userInfo?.name?.[0] || '用' }}</span>
          <span v-else class="avatar-icon">👤</span>
        </div>
      </nav>
    </header>

    <main class="content-area">
      <div v-show="activeSection === 'home'" class="hero-section">
        <h2>智能备课，高效教学</h2>
        <p>AI驱动的备课平台，助力教师打造精彩课堂</p>
      </div>
      <LessonPrep v-show="activeSection === 'lesson-prep'" class="embed-content" />
      <CoursewareManage v-show="activeSection === 'courseware'" class="embed-content" />
      <KnowledgeBase v-show="activeSection === 'knowledge-base'" class="embed-content" />
      <PersonalCenter v-show="activeSection === 'personal-center'" class="embed-content" />
    </main>

    <LoginRegisterModal v-model="showLoginModal" />
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  display: flex;
  flex-direction: column;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 48px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.logo {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-btn {
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: #475569;
  font-size: 15px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.nav-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.nav-btn.active {
  color: #3b82f6;
  background: #eff6ff;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.avatar-logged-in {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
}

.avatar.active {
  box-shadow: 0 0 0 2px #3b82f6;
}

.avatar-initial {
  color: #fff;
  font-weight: 600;
  font-size: 1rem;
}

.avatar-icon {
  font-size: 1.2rem;
  opacity: 0.7;
}

.avatar:hover {
  transform: scale(1.05);
}

.content-area {
  flex: 1;
  overflow: auto;
}

.hero-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 24px;
  text-align: center;
}

.hero-section h2 {
  font-size: 2.5rem;
  color: #1e293b;
  margin-bottom: 16px;
}

.hero-section p {
  font-size: 1.125rem;
  color: #64748b;
}

.embed-content {
  height: 100%;
  min-height: calc(100vh - 72px);
}
</style>
