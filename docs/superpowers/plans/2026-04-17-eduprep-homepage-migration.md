# EDUPrep Homepage Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `teacher-platform` homepage with a Vue implementation of the `EDUPrep` landing page, including the dark visual system, curtain-style hero animation, migrated copy, and existing app navigation/login behavior.

**Architecture:** Keep the change localized to the existing homepage route and implement the new experience directly in `Home.vue`. Add a minimal Vitest setup first so the page can be migrated with TDD, then rebuild the homepage around section-driven data, computed scroll animation styles, and scoped CSS that recreates the target page without introducing a new animation runtime.

**Tech Stack:** Vue 3, vue-router, Pinia, Vite, Vitest, Vue Test Utils, scoped CSS

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `teacher-platform/package.json` | Modify | Add frontend test scripts and test devDependencies |
| `teacher-platform/vite.config.js` | Modify | Add Vitest config for jsdom-based component tests |
| `teacher-platform/src/test/setup.js` | Create | Shared Vitest setup and browser API mocks |
| `teacher-platform/src/views/Home.spec.js` | Create | Regression tests for migrated homepage rendering and behavior |
| `teacher-platform/src/views/Home.vue` | Modify | Full homepage migration: content, scroll animation logic, and dark visual styling |

## Chunk 1: Add a minimal homepage test harness

### Task 1: Add Vitest scripts and config

**Files:**
- Modify: `teacher-platform/package.json`
- Modify: `teacher-platform/vite.config.js`
- Create: `teacher-platform/src/test/setup.js`

- [ ] **Step 1: Add the failing test toolchain dependencies**

Update `teacher-platform/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.2",
    "@vue/test-utils": "^2.4.6",
    "jsdom": "^26.1.0",
    "less": "^4.3.0",
    "vite": "^7.3.1",
    "vitest": "^3.2.4"
  }
}
```

- [ ] **Step 2: Add Vitest config in `vite.config.js`**

Extend `teacher-platform/vite.config.js`:

```js
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
  },
  server: {
    proxy: {
```

- [ ] **Step 3: Create shared test setup**

Create `teacher-platform/src/test/setup.js`:

```js
import { afterEach, vi } from 'vitest'

Object.defineProperty(window, 'scrollY', {
  value: 0,
  writable: true,
})

Object.defineProperty(window, 'innerHeight', {
  value: 1080,
  writable: true,
})

window.scrollTo = vi.fn()

afterEach(() => {
  vi.restoreAllMocks()
})
```

- [ ] **Step 4: Install dependencies**

Run:

```bash
npm install
```

Workdir: `teacher-platform`

Expected: `vitest`, `@vue/test-utils`, and `jsdom` are added without errors.

- [ ] **Step 5: Commit**

```bash
git add teacher-platform/package.json teacher-platform/package-lock.json teacher-platform/vite.config.js teacher-platform/src/test/setup.js
git commit -m "test(frontend): add vitest harness for homepage"
```

## Chunk 2: Write the homepage regression tests first

### Task 2: Add failing tests for the migrated homepage

**Files:**
- Create: `teacher-platform/src/views/Home.spec.js`
- Test: `teacher-platform/src/views/Home.spec.js`

- [ ] **Step 1: Write the failing homepage tests**

Create `teacher-platform/src/views/Home.spec.js`:

```js
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Home from './Home.vue'

const push = vi.fn()
const openLoginModal = vi.fn()

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRouter: () => ({ push }),
  }
})

describe('Home view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockReset()
    openLoginModal.mockReset()
  })

  function mountHome() {
    return mount(Home, {
      global: {
        provide: {
          openLoginModal,
        },
        stubs: {
          LottiePlayer: {
            template: '<div data-test="lottie-stub" />',
          },
        },
      },
    })
  }

  it('renders the migrated EDU Prep hero copy and footer copy', () => {
    const wrapper = mountHome()

    expect(wrapper.text()).toContain('EDU Prep')
    expect(wrapper.text()).toContain('MULTIMODAL AI')
    expect(wrapper.text()).toContain('The Next Generation Teaching Agent Paradigm')
    expect(wrapper.text()).toContain('Creators: LZC, ZZT, MCM, YCX')
  })

  it('shows the login button for logged-out users and opens login flow on click', async () => {
    const wrapper = mountHome()

    await wrapper.get('[data-test="home-login"]').trigger('click')

    expect(openLoginModal).toHaveBeenCalledTimes(1)
  })

  it('routes the primary CTA to lesson prep', async () => {
    const wrapper = mountHome()

    await wrapper.get('[data-test="hero-cta"]').trigger('click')

    expect(push).toHaveBeenCalledWith({ path: '/login', query: { redirect: '/lesson-prep' } })
  })

  it('updates hero animation styles when scrolling', async () => {
    const wrapper = mountHome()

    window.scrollY = 600
    window.dispatchEvent(new Event('scroll'))
    await wrapper.vm.$nextTick()

    const hero = wrapper.get('[data-test="curtain-hero"]')
    expect(hero.attributes('data-scroll-ready')).toBe('true')
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
npm test -- src/views/Home.spec.js
```

Workdir: `teacher-platform`

Expected: FAIL because the current homepage does not render the new content, selectors, or scroll state markers.

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/views/Home.spec.js
git commit -m "test(home): add eduprep homepage regression coverage"
```

## Chunk 3: Rebuild the homepage in Vue

### Task 3: Replace the homepage content model and behavior

**Files:**
- Modify: `teacher-platform/src/views/Home.vue`
- Test: `teacher-platform/src/views/Home.spec.js`

- [ ] **Step 1: Implement the new homepage script logic**

In `teacher-platform/src/views/Home.vue`, replace the existing script with:

```vue
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

const visionPills = [
  '意图理解',
  '多模态融合',
  '全息生成',
]

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
  return {
    left: {
      transform: `translateX(${(-100 * progress).toFixed(2)}%) scaleX(${(1 - progress * 0.5).toFixed(3)}) skewX(${(3 - progress * 15).toFixed(2)}deg)`,
    },
    right: {
      transform: `translateX(${(100 * progress).toFixed(2)}%) scaleX(${(1 - progress * 0.5).toFixed(3)}) skewX(${(-3 + progress * 15).toFixed(2)}deg)`,
    },
    hero: {
      opacity: `${Math.min(1, Math.max(0, (progress - 0.08) / 0.42))}`,
      transform: `translateY(${(50 - progress * 50).toFixed(2)}px) scale(${(0.9 + progress * 0.1).toFixed(3)})`,
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
```

- [ ] **Step 2: Replace the template with the migrated EDU Prep structure**

In `teacher-platform/src/views/Home.vue`, replace the template with sections containing these required selectors:

```vue
<template>
  <div class="home-page">
    <header class="landing-topbar">
      <div class="brand-lockup">
        <div class="brand-mark">✦</div>
        <div class="brand-copy">
          <span class="brand-name">EDU Prep</span>
        </div>
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

    <main>
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
              <span>智课坊</span>
              <span class="gradient-text">EDU Prep</span>
            </h1>
            <p class="hero-tagline">
              重塑教育边界，智启未来课堂
              <span>The Next Generation Teaching Agent Paradigm</span>
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
          <h2>从割裂的工具<br><span>到统一的智能体</span></h2>
          <p class="section-body">
            传统备课往往在多个工具之间切换。EDU Prep 通过多模态理解、知识增强与生成闭环，
            让教师回到真正重要的教学设计。
          </p>
          <div class="vision-pills">
            <span v-for="pill in visionPills" :key="pill">{{ pill }}</span>
          </div>
        </div>
        <div class="vision-visual">
          <img src="/home-fig1.png" alt="EDU Prep vision illustration" />
        </div>
      </section>

      <section class="features-section">
        <p class="section-kicker center">Core Capabilities</p>
        <h2>核心能力矩阵</h2>
        <p class="section-intro">构建以教师思路为驱动的共创系统，突破传统工具的单向指令限制。</p>
        <div class="feature-grid">
          <article v-for="feature in features" :key="feature.titleEn" class="feature-card">
            <div class="feature-icon"></div>
            <p class="feature-en">{{ feature.titleEn }}</p>
            <h3>{{ feature.titleCn }}</h3>
            <p class="feature-desc">{{ feature.desc }}</p>
          </article>
        </div>
      </section>

      <section class="closing-section">
        <span class="closing-kicker">Closing Manifesto</span>
        <h2>把时间还给教学设计，<br>把创造力留给教师。</h2>
        <p>Crafted for the future of lesson preparation.</p>
      </section>
    </main>

    <footer class="page-footer">
      <div class="footer-brand">
        <div class="footer-mark">✦</div>
        <span>EDU PREP.</span>
      </div>
      <div class="footer-meta">
        <span>Creators: LZC, ZZT, MCM, YCX</span>
        <span>&copy; 2026 EDU Prep. All rights reserved.</span>
      </div>
    </footer>
  </div>
</template>
```

- [ ] **Step 3: Replace the scoped styles with the new dark landing-page system**

In `teacher-platform/src/views/Home.vue`, replace the existing scoped CSS with styles that include:

```css
.home-page {
  min-height: 100vh;
  color: #f8fafc;
  background:
    radial-gradient(circle at top, rgba(0, 240, 255, 0.12), transparent 28%),
    #050505;
}

.curtain-hero {
  position: relative;
  height: 360vh;
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

.curtain {
  position: absolute;
  top: -10%;
  width: 60%;
  height: 120%;
  transform-origin: top;
  background: repeating-linear-gradient(90deg, #020202 0, #151515 40px, #050505 80px);
  border-inline: 1px solid rgba(255, 255, 255, 0.12);
}

.hero-content {
  position: relative;
  z-index: 2;
  width: min(980px, calc(100vw - 48px));
  text-align: center;
}

.gradient-text {
  background: linear-gradient(180deg, #ffffff 0%, #6b7280 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.feature-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(18px);
}

@media (max-width: 900px) {
  .curtain-hero {
    height: auto;
    min-height: 100vh;
  }

  .hero-sticky {
    position: relative;
    padding: 120px 20px 72px;
  }

  .curtain {
    opacity: 0.18;
    width: 72%;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .page-footer,
  .footer-meta {
    flex-direction: column;
  }
}
```

Use the target-page layout and copy from the approved spec, but adapt the right-side visual to `/home-fig1.png` rather than an external Unsplash image.

- [ ] **Step 4: Run the homepage tests to verify they pass**

Run:

```bash
npm test -- src/views/Home.spec.js
```

Workdir: `teacher-platform`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add teacher-platform/src/views/Home.vue teacher-platform/src/views/Home.spec.js
git commit -m "feat(home): migrate homepage to eduprep landing page"
```

## Chunk 4: Verify the integrated page

### Task 4: Run final verification and build checks

**Files:**
- Modify: `teacher-platform/src/views/Home.vue` (only if verification reveals issues)
- Test: `teacher-platform/src/views/Home.spec.js`

- [ ] **Step 1: Run the focused homepage tests**

Run:

```bash
npm test -- src/views/Home.spec.js
```

Workdir: `teacher-platform`

Expected: PASS.

- [ ] **Step 2: Run the production build**

Run:

```bash
npm run build
```

Workdir: `teacher-platform`

Expected: Vite build completes successfully.

- [ ] **Step 3: Sanity-check the changed files**

Run:

```bash
git diff -- teacher-platform/src/views/Home.vue teacher-platform/src/views/Home.spec.js teacher-platform/package.json teacher-platform/vite.config.js
```

Workdir: `d:\123\AIsystem`

Expected: Diff only shows homepage migration and test harness changes.

- [ ] **Step 4: Commit any final verification fixes**

Only if Step 1 or Step 2 reveals issues:

```bash
git add teacher-platform/src/views/Home.vue teacher-platform/src/views/Home.spec.js teacher-platform/package.json teacher-platform/package-lock.json teacher-platform/vite.config.js
git commit -m "fix(home): address homepage migration verification issues"
```
