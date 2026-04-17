<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const openLoginModal = inject('openLoginModal', null)
const router = useRouter()
const userStore = useUserStore()

const heroScrollProgress = ref(0)
const heroReady = ref(false)

const badges = ['MULTIMODAL AI', 'RAG ENGINE']

const visionPills = ['意图理解', '多模态融合', '全息生成']

const features = [
  {
    titleEn: 'RAG KNOWLEDGE BASE',
    titleCn: '领域知识增强',
    desc: '基于本地专业知识库的大模型检索增强，确保生成内容具备专业性与准确性。',
  },
  {
    titleEn: 'MULTIMODAL INTERACTION',
    titleCn: '多模态意图解析',
    desc: '支持文本、语音和多种文档输入，通过多轮对话理解教学目标。',
  },
  {
    titleEn: 'GENERATIVE ENGINE',
    titleCn: '课件教案全息生成',
    desc: '一键生成 PPT、教案与互动创意，服务完整备课流程。',
  },
  {
    titleEn: 'ITERATIVE LOOP',
    titleCn: '闭环反馈优化',
    desc: '通过预览与对话式修改形成生成、反馈、再生成的闭环。',
  },
]

const userInitial = computed(() => {
  const raw = userStore.userInfo?.name || userStore.userInfo?.phone || ''
  const text = String(raw).trim()
  if (!text) return '我'
  return /[a-zA-Z]/.test(text[0]) ? text[0].toUpperCase() : text[0]
})

const curtainStyles = computed(() => {
  const progress = heroScrollProgress.value
  const heroOpacity = Math.min(1, Math.max(0, (progress - 0.08) / 0.42))
  const heroTranslate = 50 - progress * 50
  const heroScale = 0.9 + progress * 0.1

  return {
    left: {
      transform: `translateX(${(-100 * progress).toFixed(2)}%) scaleX(${(1 - progress * 0.5).toFixed(3)}) skewX(${(3 - progress * 15).toFixed(2)}deg)`,
    },
    right: {
      transform: `translateX(${(100 * progress).toFixed(2)}%) scaleX(${(1 - progress * 0.5).toFixed(3)}) skewX(${(-3 + progress * 15).toFixed(2)}deg)`,
    },
    hero: {
      opacity: `${heroOpacity}`,
      transform: `translateY(${heroTranslate.toFixed(2)}px) scale(${heroScale.toFixed(3)})`,
    },
  }
})

function syncScrollProgress() {
  const maxScroll = Math.max(window.innerHeight * 1.8, 1)
  heroScrollProgress.value = Math.min(1, Math.max(0, window.scrollY / maxScroll))
  heroReady.value = true
}

function goTeacherPath(path) {
  if (userStore.isLoggedIn) {
    router.push(path)
  } else {
    router.push({ path: '/login', query: { redirect: path } })
  }
}

function goLessonPrep() {
  goTeacherPath('/lesson-prep')
}

function handleAvatarClick() {
  if (!userStore.isLoggedIn) {
    openLoginModal?.()
    return
  }

  if (userStore.userInfo?.is_admin) {
    router.push('/admin/profile')
  } else {
    router.push('/personal-center')
  }
}

onMounted(() => {
  syncScrollProgress()
  window.addEventListener('scroll', syncScrollProgress, { passive: true })
  window.addEventListener('resize', syncScrollProgress)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', syncScrollProgress)
  window.removeEventListener('resize', syncScrollProgress)
})
</script>

<template>
  <div class="home-page">
    <header class="landing-topbar">
      <div class="brand-lockup">
        <img
          data-test="brand-logo"
          class="brand-logo"
          src="/logo-character.svg"
          alt="智课坊 | EDU Prep"
        />
      </div>

      <button
        v-if="!userStore.isLoggedIn"
        data-test="home-login"
        class="topbar-action login-btn"
        type="button"
        @click="openLoginModal?.()"
      >
        登录
      </button>

      <button
        v-else
        class="topbar-action user-avatar-btn"
        type="button"
        @click="handleAvatarClick"
      >
        {{ userInitial }}
      </button>
    </header>

    <main class="page-main">
      <section
        data-test="curtain-hero"
        class="curtain-hero"
        :data-scroll-ready="heroReady ? 'true' : 'false'"
      >
        <div class="hero-grid"></div>
        <div class="hero-orb"></div>

        <div class="hero-sticky">
          <div class="hero-content" :style="curtainStyles.hero">
            <div class="hero-badges">
              <span v-for="badge in badges" :key="badge" class="hero-badge">{{ badge }}</span>
            </div>

            <h1 class="hero-title">
              <span class="hero-title-top">智课坊</span>
              <span class="gradient-text">EDU Prep</span>
            </h1>

            <p class="hero-tagline">
              重塑教育边界，智启未来课堂
              <span class="hero-tagline-en">The Next Generation Teaching Agent Paradigm</span>
            </p>

            <button
              data-test="hero-cta"
              class="hero-cta"
              type="button"
              @click="goLessonPrep"
            >
              开启智能备课
            </button>
          </div>

          <div class="curtain curtain-left" :style="curtainStyles.left"></div>
          <div class="curtain curtain-right" :style="curtainStyles.right"></div>
        </div>
      </section>

      <section class="vision-section">
        <div class="vision-copy">
          <p class="section-kicker">Paradigm Shift</p>
          <h2 class="section-title">
            从割裂的工具
            <br />
            <span>到统一的智能体</span>
          </h2>
          <p class="section-body">
            传统备课往往在多个工具之间切换。EDU Prep 通过多模态理解、知识增强与生成闭环，
            让教师回到真正重要的教学设计。
          </p>

          <div class="vision-pills">
            <span v-for="pill in visionPills" :key="pill" class="vision-pill">{{ pill }}</span>
          </div>
        </div>

        <div class="vision-visual">
          <div class="vision-visual-shell">
            <img
              data-test="vision-image"
              src="/home-preview.png"
              alt="EDU Prep dashboard preview"
            />
          </div>
        </div>
      </section>

      <section class="features-section">
        <p class="section-kicker center">Core Capabilities</p>
        <h2 class="section-title centered">核心能力矩阵</h2>
        <p class="section-intro">
          构建以教师思路为驱动的共创系统，突破传统工具的单向指令限制。
        </p>

        <div class="feature-grid">
          <article v-for="feature in features" :key="feature.titleEn" class="feature-card">
            <div class="feature-icon"></div>
            <p class="feature-en">{{ feature.titleEn }}</p>
            <h3 class="feature-title">{{ feature.titleCn }}</h3>
            <p class="feature-desc">{{ feature.desc }}</p>
          </article>
        </div>
      </section>

      <section class="closing-section">
        <span class="closing-kicker">Closing Manifesto</span>
        <h2 class="closing-title">
          把时间还给教学设计，
          <br />
          把创造力留给教师。
        </h2>
        <p class="closing-subtitle">Crafted for the future of lesson preparation.</p>
      </section>
    </main>

    <footer class="page-footer">
      <div class="footer-brand">
        <img
          class="footer-logo"
          src="/logo-character.svg"
          alt="鏅鸿鍧?| EDU Prep"
        />
      </div>
      <div class="footer-meta">
        <span>Creators: LZC, ZZT, MCM, YCX</span>
        <span>&copy; 2026 EDU Prep. All rights reserved.</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  color: #f8fafc;
  background:
    radial-gradient(circle at top, rgba(0, 240, 255, 0.12), transparent 28%),
    linear-gradient(180deg, #050505 0%, #030712 100%);
}

.landing-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 32px;
  backdrop-filter: blur(18px);
  background: rgba(5, 5, 5, 0.72);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-lockup {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  display: block;
  height: 64px;
  width: auto;
}

.footer-logo {
  display: block;
  height: 52px;
  width: auto;
}

.topbar-action {
  border: none;
  cursor: pointer;
}

.login-btn,
.hero-cta {
  padding: 0.9rem 1.5rem;
  border-radius: 999px;
  color: #050505;
  background: #00f0ff;
  font-weight: 800;
  letter-spacing: 0.03em;
  box-shadow: 0 14px 40px rgba(0, 240, 255, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.login-btn:hover,
.hero-cta:hover,
.user-avatar-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 46px rgba(0, 240, 255, 0.2);
}

.user-avatar-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(12px);
  font-weight: 700;
}

.page-main {
  overflow: clip;
}

.curtain-hero {
  position: relative;
  height: 360vh;
}

.hero-grid {
  position: absolute;
  inset: 0;
  opacity: 0.16;
  background-image: linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 32px 32px;
}

.hero-orb {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 440px;
  height: 440px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 240, 255, 0.12);
  filter: blur(72px);
}

.hero-sticky {
  position: sticky;
  top: 0;
  min-height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-content {
  position: relative;
  z-index: 2;
  width: min(980px, calc(100vw - 48px));
  padding: 0 20px;
  text-align: center;
  will-change: transform, opacity;
}

.hero-badges {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}

.hero-badge,
.section-kicker,
.closing-kicker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.48rem 0.9rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.hero-title {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 0 20px;
  font-size: clamp(3.8rem, 10vw, 7.5rem);
  line-height: 0.9;
  font-weight: 900;
  letter-spacing: -0.06em;
}

.hero-title-top {
  color: #f8fafc;
}

.gradient-text {
  background: linear-gradient(180deg, #ffffff 0%, #71717a 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-tagline {
  max-width: 760px;
  margin: 0 auto 32px;
  color: rgba(255, 255, 255, 0.8);
  font-size: clamp(1.05rem, 2vw, 1.45rem);
  line-height: 1.7;
}

.hero-tagline-en {
  display: block;
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.44);
  font-size: 0.8rem;
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.curtain {
  position: absolute;
  top: -10%;
  width: 60%;
  height: 120%;
  transform-origin: top;
  background: repeating-linear-gradient(90deg, #020202 0, #151515 40px, #050505 80px);
  box-shadow: 0 0 60px rgba(0, 0, 0, 0.9);
  will-change: transform;
}

.curtain::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.1;
  background: linear-gradient(rgba(255, 255, 255, 0.2) 1px, transparent 1px);
  background-size: 100% 4px;
}

.curtain-left {
  left: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.14);
}

.curtain-right {
  right: 0;
  border-left: 1px solid rgba(255, 255, 255, 0.14);
}

.vision-section,
.features-section,
.closing-section {
  position: relative;
  z-index: 1;
  width: min(1200px, calc(100vw - 48px));
  margin: 0 auto;
}

.vision-section {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 48px;
  padding: 120px 0 96px;
  align-items: center;
}

.section-kicker {
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 18px;
  font-size: clamp(2.4rem, 4vw, 3.7rem);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.section-title span {
  color: rgba(255, 255, 255, 0.48);
}

.section-body,
.section-intro,
.feature-desc,
.closing-subtitle,
.footer-meta {
  color: rgba(255, 255, 255, 0.62);
  line-height: 1.75;
}

.vision-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 28px;
}

.vision-pill {
  padding: 0.8rem 1rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.vision-visual-shell {
  position: relative;
  padding: 22px;
  border-radius: 28px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.34);
}

.vision-visual-shell::before {
  content: '';
  position: absolute;
  inset: -18px;
  border-radius: 36px;
  background: radial-gradient(circle at top right, rgba(0, 240, 255, 0.12), transparent 58%);
  z-index: -1;
}

.vision-visual img {
  display: block;
  width: 100%;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.02);
}

.features-section {
  padding: 24px 0 120px;
}

.center,
.centered,
.section-intro,
.closing-section {
  text-align: center;
}

.section-intro {
  max-width: 720px;
  margin: 0 auto 36px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.feature-card {
  position: relative;
  overflow: hidden;
  padding: 32px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(18px);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
}

.feature-card::after {
  content: '';
  position: absolute;
  top: -40px;
  right: -60px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.16), transparent 70%);
}

.feature-icon {
  width: 56px;
  height: 56px;
  margin-bottom: 22px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.9), rgba(255, 255, 255, 0.3));
  box-shadow: 0 12px 28px rgba(0, 240, 255, 0.18);
}

.feature-en {
  margin: 0 0 10px;
  color: #00f0ff;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.feature-title {
  margin: 0 0 12px;
  font-size: 1.5rem;
}

.closing-section {
  padding: 24px 0 140px;
}

.closing-title {
  margin: 24px 0 18px;
  font-size: clamp(2.3rem, 4.5vw, 4.6rem);
  line-height: 1.18;
  letter-spacing: -0.04em;
}

.page-footer {
  width: min(1200px, calc(100vw - 48px));
  margin: 0 auto;
  padding: 28px 0 42px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.footer-brand,
.footer-meta {
  display: flex;
  align-items: center;
  gap: 14px;
}

.footer-meta {
  gap: 22px;
  font-size: 0.88rem;
}

@media (max-width: 960px) {
  .vision-section {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .landing-topbar {
    padding: 16px 18px;
  }

  .brand-logo {
    height: 52px;
  }

  .footer-logo {
    height: 42px;
  }

  .page-footer {
    align-items: center;
  }

  .curtain-hero {
    height: auto;
    min-height: 100vh;
  }

  .hero-sticky {
    position: relative;
    min-height: 100vh;
    padding: 120px 0 84px;
  }

  .curtain {
    opacity: 0.18;
    width: 72%;
  }

  .vision-section,
  .features-section,
  .closing-section,
  .page-footer {
    width: min(100vw - 32px, 1200px);
  }

  .page-footer,
  .footer-meta {
    flex-direction: column;
  }
}
</style>
