<script setup>
import { ref, provide } from 'vue'
import { useUserStore } from '../stores/user'
import LoginRegisterModal from '../components/LoginRegisterModal.vue'
import LottiePlayer from '../components/LottiePlayer.vue'
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

const featureCards = [
  {
    id: 'lesson-prep',
    icon: '✏️',
    title: '备课中心',
    desc: '借助AI辅助设计完整教案。根据您的教学目标，秒级生成测验、摘要和活动创意。',
    color: 'blue',
    link: '了解更多 →'
  },
  {
    id: 'courseware',
    icon: '📁',
    title: '课件管理',
    desc: '在结构化资源库中管理所有教学材料。支持拖拽上传、版本控制，一键分享给学生或同事。',
    color: 'orange',
    link: '了解更多 →'
  },
  {
    id: 'knowledge-base',
    icon: '📚',
    title: '知识库',
    desc: '访问海量学术资源、标准化题库和互动教材。用经过验证的教育内容丰富您的课堂。',
    color: 'purple',
    link: '了解更多 →'
  }
]

const stats = [
  { value: '40%', title: '备课提速', desc: '使用智能模板和AI助手，减少人工文档整理时间。' },
  { value: '10k+', title: '资源库', desc: '集成经过验证的学术数据库和教学材料。' },
  { value: '98%', title: '教师满意度', desc: '由教育者打造，为教育者服务。在易用性和可靠性方面评分最高。' }
]

function setSection(id) {
  activeSection.value = id
}

function handleAvatarClick() {
  activeSection.value = 'personal-center'
}

provide('openLoginModal', () => { showLoginModal.value = true })
provide('goToHome', () => { activeSection.value = 'home' })
</script>

<template>
  <div class="home-page">
    <header class="top-nav">
      <div class="nav-left">
        <div class="logo-wrap">
          <span class="logo-icon">📖</span>
          <h1 class="logo">EduPrep</h1>
        </div>
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
          <span class="avatar-initial">{{ userStore.userInfo?.name?.[0] || '用' }}</span>
        </div>
      </nav>
    </header>

    <main class="content-area">
      <div v-show="activeSection === 'home'" class="home-content">
        <!-- Hero Section -->
        <section class="hero-section">
          <div class="hero-left">
            <h2 class="hero-title">
              <span class="line1">提升备课效率，</span>
              <span class="line2">实现智能备课</span>
            </h2>
            <p class="hero-desc">
              专为现代教师打造的一站式平台。
              创建精彩内容、管理课程体系，借助AI取回您最宝贵的时间资源。
            </p>
            <div class="hero-btns">
              <button class="btn-primary" @click="setSection('lesson-prep')">一键备课</button>
            </div>
            <div class="hero-tags">
              <span class="tag">⚡ 高效</span>
              <span class="tag">🤖 AI驱动</span>
              <span class="tag">📚 知识管理</span>
            </div>
          </div>
          <div class="hero-right">
            <div class="hero-visual">
              <LottiePlayer src="/isometric-animation.json" />
            </div>
          </div>
        </section>

        <!-- Feature Cards -->
        <section class="features-section">
          <h3 class="section-title">一站式满足您的所有需求</h3>
          <p class="section-subtitle">专为教学卓越打造的精简工具。</p>
          <div class="feature-cards">
            <div
              v-for="card in featureCards"
              :key="card.id"
              class="feature-card"
              @click="setSection(card.id)"
            >
              <div class="card-icon" :class="card.color">{{ card.icon }}</div>
              <h4 class="card-title">{{ card.title }}</h4>
              <p class="card-desc">{{ card.desc }}</p>
              <a class="card-link" :class="card.color">{{ card.link }}</a>
            </div>
          </div>
        </section>

        <!-- Stats -->
        <section class="stats-section">
          <div v-for="(stat, i) in stats" :key="i" class="stat-item">
            <span class="stat-value">{{ stat.value }}</span>
            <h4 class="stat-title">{{ stat.title }}</h4>
            <p class="stat-desc">{{ stat.desc }}</p>
          </div>
        </section>
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
  background: #fff;
  display: flex;
  flex-direction: column;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 48px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.nav-left {
  display: flex;
  align-items: center;
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  font-size: 1.5rem;
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
  background: #e5e7eb;
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
  overflow-y: auto;
  overflow-x: hidden;
}

.home-content {
  min-height: 100%;
}

/* Hero */
.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 42px 48px 41px;
  max-width: 1200px;
  margin: 0 auto;
  gap: 48px;
}

.hero-left {
  flex: 1;
  max-width: 520px;
}

.hero-title {
  font-size: 3.65rem;
  font-weight: 800;
  color: #1e293b;
  line-height: 1.4;
  margin-bottom: 16px;
}

.hero-title .line1 {
  display: block;
}

.hero-title .line2 {
  display: block;
  color: #2563eb;
}

.hero-desc {
  font-size: 1.20rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 20px;
}

.hero-btns {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.btn-primary {
  padding: 12px 22px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 17px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-outline {
  padding: 12px 24px;
  background: #fff;
  color: #6b7280;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.hero-tags {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.tag {
  font-size: 1.05rem;
  color: #6b7280;
}

.hero-right {
  flex-shrink: 0;
}

.hero-visual {
  position: relative;
  width: 450px;
  height: 450px;
}

/* Features */
.features-section {
  padding: 32px 48px 40px;
  background: #f9fafb;
}

.section-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
  margin-bottom: 8px;
}

.section-subtitle {
  font-size: 1rem;
  color: #64748b;
  text-align: center;
  margin-bottom: 28px;
}

.feature-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

.feature-card {
  background: #fff;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.2s;
}

.feature-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  border-radius: 10px;
  margin-bottom: 16px;
}

.card-icon.blue {
  background: #dbeafe;
  color: #2563eb;
}

.card-icon.orange {
  background: #ffedd5;
  color: #ea580c;
}

.card-icon.purple {
  background: #ede9fe;
  color: #7c3aed;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.card-desc {
  font-size: 0.9rem;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 16px;
}

.card-link {
  font-size: 0.9rem;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
}

.card-link.blue {
  color: #2563eb;
}

.card-link.orange {
  color: #ea580c;
}

.card-link.purple {
  color: #7c3aed;
}

.card-link:hover {
  text-decoration: underline;
}

/* Stats */
.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 38px;
  padding: 38px 48px 50px;
  max-width: 1000px;
  margin: 0 auto;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 2.5rem;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 8px;
}

.stat-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
}

.stat-desc {
  font-size: 0.9rem;
  color: #64748b;
  line-height: 1.5;
}

.embed-content {
  height: 100%;
  min-height: calc(100vh - 72px);
}

@media (max-width: 900px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
  }

  .hero-left {
    max-width: none;
  }

  .hero-btns {
    justify-content: center;
  }

  .hero-tags {
    justify-content: center;
  }

  .hero-visual {
    width: 380px;
    height: 380px;
  }

  .feature-cards {
    grid-template-columns: 1fr;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }
}
</style>
