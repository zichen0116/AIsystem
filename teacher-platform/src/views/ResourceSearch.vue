<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import lottie from 'lottie-web'
import { apiRequest } from '../api/http.js'
import resourceLoadingAnimation from '../assets/resource-loading.json'

const query = ref('')

const resources = ref([])
const loading = ref(false)
const errorMsg = ref('')
const searched = ref(false)
const loadingAnimationRef = ref(null)
let loadingAnimation = null

const hotResources = [
  {
    id: 'hot-1',
    title: '国家智慧教育公共服务平台',
    tag: '官方平台',
    desc: '汇聚基础教育、职业教育与高等教育课程资源，覆盖课程、教材与专题活动。',
    icon: '🏫',
    url: 'https://www.smartedu.cn/'
  },
  {
    id: 'hot-2',
    title: '中国大学MOOC（慕课）',
    tag: '高校课程',
    desc: '国内高校精品在线课程平台，涵盖计算机、数学、外语、经管等热门学科。',
    icon: '🎓',
    url: 'https://www.icourse163.org/'
  },
  {
    id: 'hot-3',
    title: '哔哩哔哩学习资源（高等数学）',
    tag: '视频课程',
    desc: '聚合高等数学相关课程与讲解视频，适合用于课堂导入、课后巩固与拓展学习。',
    icon: '📺',
    url: 'https://search.bilibili.com/all?keyword=%E9%AB%98%E7%AD%89%E6%95%B0%E5%AD%A6'
  },
  {
    id: 'hot-4',
    title: '学堂在线',
    tag: '高校公开课',
    desc: '提供清华等高校公开课与专业课程，支持在线学习与教学参考。',
    icon: '📚',
    url: 'https://www.xuetangx.com/'
  },
  {
    id: 'hot-5',
    title: '国家中小学智慧教育平台',
    tag: '基础教育',
    desc: '覆盖小学至高中学段，提供同步课程、德育与专题教育等优质资源。',
    icon: '🧒',
    url: 'https://basic.smartedu.cn/'
  },
  {
    id: 'hot-6',
    title: '人民网教育频道',
    tag: '教育资讯',
    desc: '聚合教育政策解读、教学案例与热点专题，可辅助备课与时事拓展。',
    icon: '📰',
    url: 'http://edu.people.com.cn/'
  }
]

const filteredResources = computed(() => resources.value)
const displayResources = computed(() => (searched.value ? filteredResources.value : hotResources))

function mountLoadingAnimation() {
  if (!loadingAnimationRef.value) return
  if (loadingAnimation) {
    loadingAnimation.destroy()
    loadingAnimation = null
  }
  loadingAnimation = lottie.loadAnimation({
    container: loadingAnimationRef.value,
    renderer: 'svg',
    loop: true,
    autoplay: true,
    animationData: resourceLoadingAnimation
  })
}

function destroyLoadingAnimation() {
  if (!loadingAnimation) return
  loadingAnimation.destroy()
  loadingAnimation = null
}

watch(loading, async (isLoading) => {
  if (isLoading) {
    await nextTick()
    mountLoadingAnimation()
    return
  }
  destroyLoadingAnimation()
})

onBeforeUnmount(() => {
  destroyLoadingAnimation()
})

/** 展示用：去掉 [标题](url) 中的链接语法，保留标题文字 */
function stripMarkdownLinks(text) {
  if (!text) return ''
  return String(text).replace(/\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)/gi, '$1')
}

/**
 * 若某项无 url 但 desc 里含 Markdown 链接，拆成多条（兼容旧接口或兜底卡片）
 */
function expandItemsWithEmbeddedLinks(items) {
  const re = /\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)/gi
  const out = []
  for (const it of items) {
    const url = (it.url || '').trim()
    if (url) {
      out.push({ ...it, url })
      continue
    }
    const desc = it.desc || ''
    const matches = [...desc.matchAll(new RegExp(re.source, 'gi'))]
    if (matches.length) {
      matches.forEach((m, j) => {
        out.push({
          id: `${it.id}-link-${j}`,
          title: (m[1] || '').trim() || it.title || `资源 ${j + 1}`,
          tag: it.tag || '',
          desc: '',
          icon: it.icon || '📚',
          url: m[2].trim()
        })
      })
    } else {
      out.push({ ...it })
    }
  }
  return out
}

async function runSearch() {
  const kw = query.value.trim()
  if (!kw) {
    errorMsg.value = '请输入搜索关键词（学科、主题或知识点）'
    return
  }
  errorMsg.value = ''
  loading.value = true
  searched.value = true
  resources.value = []
  try {
    const data = await apiRequest('/api/v1/resource-search/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keyword: kw,
        grade: '全部年级',
        subject: '全部学科',
        file_type: '全部类型',
        sort_by: '相关度优先'
      })
    })
    const items = Array.isArray(data.items) ? data.items : []
    const mapped = items.map((it, i) => ({
      id: it.id ?? String(i),
      title: it.title ?? '未命名资源',
      tag: it.tag ?? '',
      desc: it.desc ?? '',
      icon: it.icon || '📚',
      url: (it.url && String(it.url).trim()) || ''
    }))
    resources.value = expandItemsWithEmbeddedLinks(mapped)
    if (!resources.value.length) {
      errorMsg.value = '未找到推荐结果，请尝试更换关键词'
    }
  } catch (e) {
    console.error(e)
    resources.value = []
    errorMsg.value =
      typeof e?.message === 'string' ? e.message : '资源推荐失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-wrap">
    <!-- 顶部搜索区（图1） -->
    <section class="hero">
      <h1 class="hero-title">发现优质教学资源</h1>
      <p class="hero-subtitle">
        汇聚海量经过筛选的教材、课件与拓展阅读素材，帮助你快速找到适合课堂的资源。
      </p>

      <div class="search-bar">
        <input
          v-model="query"
          type="text"
          class="search-input"
          placeholder="搜索学科、主题或关键字…"
          :disabled="loading"
          @keyup.enter="runSearch"
        />
        <button type="button" class="search-btn" :disabled="loading" @click="runSearch">
          <span class="search-icon">{{ loading ? '…' : '🔍' }}</span>
        </button>
      </div>

      <p v-if="errorMsg" class="search-error">{{ errorMsg }}</p>
    </section>

    <!-- 结果推荐区（图2） -->
    <section class="results">
      <p class="results-tip" :class="{ 'hot-title': !searched && !loading }">
        {{
          loading
            ? '正在调用智能体检索并生成推荐，请稍候…'
            : searched
              ? '为你推荐以下资源'
              : '热门资源推荐'
        }}
      </p>
      <div v-if="loading" class="loading-animation-wrap">
        <div ref="loadingAnimationRef" class="loading-animation-canvas" />
      </div>
      <div v-else class="card-grid">
        <article v-for="item in displayResources" :key="item.id" class="resource-card">
          <div class="card-header">
            <div class="icon-pill">
              <span class="icon-text">{{ item.icon }}</span>
            </div>
            <div class="card-title-wrap">
              <h3 class="card-title">{{ item.title }}</h3>
              <span class="card-tag">{{ item.tag }}</span>
            </div>
          </div>
          <p v-if="stripMarkdownLinks(item.desc)" class="card-desc">
            {{ stripMarkdownLinks(item.desc) }}
          </p>
          <div class="card-footer">
            <a
              v-if="item.url"
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="detail-link-btn"
            >
              查看资源详情
            </a>
            <span v-else class="no-link-tip">本项无直达链接，请阅读上方说明</span>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-wrap {
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 32px 40px 40px;
  background: #f4f7fb;
  display: flex;
  flex-direction: column;
  gap: 24px;
  box-sizing: border-box;
}

.hero {
  flex-shrink: 0;
  width: 100%;
  max-width: none;
  margin: 0 auto;
  text-align: center;
}

.hero-title {
  margin: 0 0 6px;
  font-size: 30px;
  font-weight: 700;
  color: #0f172a;
}

.hero-subtitle {
  margin: 0 0 20px;
  font-size: 15px;
  color: #64748b;
}

.search-error {
  margin: -8px auto 12px;
  max-width: 720px;
  font-size: 14px;
  color: #dc2626;
  text-align: center;
}

.results-empty-hint {
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.6;
  max-width: 560px;
  margin: 0 auto 8px;
}

.search-bar {
  margin: 0 auto 16px;
  max-width: 720px;
  background: #ffffff;
  border-radius: 999px;
  padding: 6px 8px;
  display: flex;
  align-items: center;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.12);
  border: 1px solid #e2e8f0;
}

.search-icon {
  margin-right: 10px;
  font-size: 16px;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: #111827;
  padding: 8px 12px 8px 18px;
}

.results {
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.loading-animation-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-animation-canvas {
  width: min(680px, 100%);
  height: 360px;
}

.results-tip {
  flex-shrink: 0;
  text-align: center;
  margin: 4px 0 18px;
  font-size: 14px;
  color: #9ca3af;
}

.results-tip.hot-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin: 8px 0 20px;
}

.card-grid {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  align-content: start;
  padding-right: 4px;
}

.resource-card {
  position: relative;
  overflow: hidden;
  background: #ffffff;
  border-radius: 20px;
  padding: 16px 16px 14px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  border: 1px solid #e9eef6;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.resource-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #2563eb, #60a5fa);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.resource-card:hover {
  transform: translateY(-3px);
  border-color: #d7e4f8;
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.12);
}

.resource-card:hover::before {
  opacity: 1;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.icon-pill {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(145deg, #f2f7ff 0%, #e6efff 100%);
  border: 1px solid #dce8ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-text {
  font-size: 20px;
}

.search-btn {
  flex-shrink: 0;
  border: none;
  background: #2563eb;
  color: #ffffff;
  border-radius: 999px;
  padding: 8px 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.35);
}

.search-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  box-shadow: none;
}

.search-btn .search-icon {
  margin: 0;
  font-size: 18px;
}

.card-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tag {
  font-size: 13px;
  color: #94a3b8;
}

.card-desc {
  margin: 0 0 14px;
  font-size: 14px;
  line-height: 1.65;
  color: #4b5563;
  min-height: 72px;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  margin-top: auto;
}

.detail-link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  text-decoration: none;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.3);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.detail-link-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45);
  color: #ffffff;
}

.no-link-tip {
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 960px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .page-wrap {
    padding: 24px 16px 32px;
  }

  .card-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

