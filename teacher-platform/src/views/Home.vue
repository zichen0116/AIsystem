<script setup>
import { inject } from 'vue'
import LottiePlayer from '../components/LottiePlayer.vue'
const openLoginModal = inject('openLoginModal', null)

const featureCards = [
  {
    id: 'lesson-prep',
    icon: '✏️',
    title: '智能备课',
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
</script>

<template>
  <div class="home-page">
    <header class="landing-topbar">
      <div class="logo-wrap">
        <span class="logo-icon">📖</span>
        <h1 class="logo">EduPrep</h1>
      </div>
      <button class="login-btn" type="button" @click="openLoginModal?.()">
        <span class="login-btn-text">登录</span>
      </button>
    </header>

    <main class="content-area">
      <div class="home-content">
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
              <button class="hero-btn-primary" type="button" @click="openLoginModal?.()">
                <span class="hero-btn-text">立即备课</span>
              </button>
            </div>
            <div class="hero-tags">
              <span class="tag"><span class="tag-check">✓</span>高效</span>
              <span class="tag"><span class="tag-check">✓</span>AI驱动</span>
              <span class="tag"><span class="tag-check">✓</span>知识管理</span>
            </div>
          </div>
          <div class="hero-right">
            <div class="hero-visual">
              <LottiePlayer src="/isometric-animation.json" />
            </div>
          </div>
        </section>

        <section class="features-section">
          <h3 class="section-title">核心功能</h3>
          <p class="section-subtitle">全方位满足您的所有备课需求</p>
          <div class="feature-cards">
            <div v-for="card in featureCards" :key="card.id" class="feature-card" @click="openLoginModal?.()">
              <div class="card-icon" :class="card.color">{{ card.icon }}</div>
              <h4 class="card-title">{{ card.title }}</h4>
              <p class="card-desc">{{ card.desc }}</p>
              <a class="card-link" :class="card.color">{{ card.link }}</a>
            </div>
          </div>
        </section>

        <section class="stats-section">
          <div v-for="(stat, i) in stats" :key="i" class="stat-item">
            <span class="stat-value">{{ stat.value }}</span>
            <h4 class="stat-title">{{ stat.title }}</h4>
            <p class="stat-desc">{{ stat.desc }}</p>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(to bottom, #fff 0%, #eff6ff 40%, #dbeafe 100%);
  display: flex;
  flex-direction: column;
}

.landing-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 48px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
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

.login-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 22px;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.15);
  background: radial-gradient(circle at 0 0, rgba(191, 219, 254, 0.8), transparent 55%),
    linear-gradient(135deg, #2563eb, #3b82f6);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.35);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.4);
  border-color: rgba(37, 99, 235, 0.35);
}

.login-btn:active {
  transform: translateY(0);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.32);
}

.login-btn-text {
  position: relative;
  z-index: 1;
  letter-spacing: 0.02em;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.home-content {
  min-height: 100%;
}

/* Hero */
.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 45px 4vw 41px;
  max-width: 1200px;
  margin: 0 auto;
  gap: 48px;
  flex-wrap: wrap;
}

.hero-left {
  flex: 1;
  min-width: 260px;
  max-width: 560px;
}

.hero-title {
  font-size: 3.9rem;
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
  font-size: 1.28rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 20px;
}

.hero-btns {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.hero-btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 30px;
  font-weight: 600;
  font-size: 1.15rem;
  color: #2563eb;
  background: #fff;
  border: 1px solid #93c5fd;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
}

.hero-btn-primary:hover {
  background: #eff6ff;
  border-color: #60a5fa;
  transform: translateY(-1px);
}

.hero-btn-primary:active {
  transform: translateY(0);
}

.hero-btn-text {
  color: #2563eb;
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
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 1.08rem;
  color: #374151;
}

.tag-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background:rgb(80, 216, 130);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
}

.hero-right {
  flex-shrink: 0;
}

.hero-visual {
  position: relative;
  width: min(480px, 42vw);
  aspect-ratio: 1 / 1;
}

/* Features */
.features-section {
  padding: 32px 48px 40px;
  background:rgb(250, 252, 255);
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

@media (max-width: 900px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
    padding: 40px 20px 32px;
  }

  .hero-left {
    max-width: 640px;
  }

  .hero-btns {
    justify-content: center;
  }

  .hero-tags {
    justify-content: center;
  }

  .hero-visual {
    width: min(380px, 80vw);
    height: auto;
  }

  .feature-cards {
    grid-template-columns: 1fr;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }
}
</style>
