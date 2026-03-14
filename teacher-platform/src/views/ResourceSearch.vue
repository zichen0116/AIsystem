<script setup>
import { ref, computed } from 'vue'

const query = ref('')
const committedQuery = ref('')
const grade = ref('全部年级')
const subject = ref('全部学科')
const fileType = ref('全部类型')
const sortBy = ref('相关度优先')

const resources = ref([
  {
    id: 1,
    title: '基因编辑',
    tag: '生物',
    desc:
      '介绍基因编辑的基础概念、典型案例与伦理思考，可用于高中生物选修课的探究活动。',
    icon: '🧬'
  },
  {
    id: 2,
    title: '量子计算',
    tag: '物理 / 信息技术',
    desc:
      '面向信息技术社团的入门读物，涵盖量子比特、叠加与纠缠等核心概念，并附带课堂小实验建议。',
    icon: '⚛️'
  },
  {
    id: 3,
    title: '人工智能导论',
    tag: '信息技术',
    desc:
      '讲解机器学习、深度学习与大模型的基本概念，配有可直接使用的课堂案例与讨论问题。',
    icon: '🤖'
  },
  {
    id: 4,
    title: '共享经济案例库',
    tag: '政治 / 经济',
    desc:
      '整理滴滴出行、爱彼迎等共享经济平台的典型案例，可用于经济生活与社会热点课程。',
    icon: '📊'
  },
  {
    id: 5,
    title: '电子民主与网络舆论',
    tag: '政治',
    desc:
      '聚焦网络时代公民参与与民主表达的方式，配套课堂辩论与写作任务设计。',
    icon: '🌐'
  },
  {
    id: 6,
    title: '中国共享发展报告选读',
    tag: '综合阅读',
    desc:
      '节选权威报告中的关键章节，适合作为阅读理解与时事政策主题写作素材。',
    icon: '📘'
  },
  {
    id: 7,
    title: '应用生物催化实验',
    tag: '化学 / 生物',
    desc:
      '围绕酶催化和绿色化学设计的系列实验活动，适合作为选修课程或科学社团项目。',
    icon: '🧪'
  },
  {
    id: 8,
    title: '数字素养与信息安全',
    tag: '信息技术 / 班会',
    desc:
      '通过案例分析与情景讨论，引导学生认识网络安全、隐私保护与数字公民责任。',
    icon: '🔐'
  },
  {
    id: 9,
    title: '跨学科项目：智慧城市',
    tag: '综合实践',
    desc:
      '整合地理、信息技术与社会研究的项目式任务，让学生围绕“智慧城市”设计方案与展示。',
    icon: '🏙️'
  }
])

const filteredResources = computed(() => {
  const q = committedQuery.value.trim().toLowerCase()
  if (!q) return resources.value
  return resources.value.filter((item) => {
    const text = `${item.title} ${item.tag} ${item.desc}`.toLowerCase()
    return text.includes(q)
  })
})

function runSearch() {
  committedQuery.value = query.value
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
          @keyup.enter="runSearch"
        />
        <button type="button" class="search-btn" @click="runSearch">
          <span class="search-icon">🔍</span>
        </button>
      </div>

      <div class="filter-row">
        <div class="filter-group">
          <button type="button" class="filter-pill">
            {{ grade }}
            <span class="chevron">▾</span>
          </button>
          <button type="button" class="filter-pill">
            {{ subject }}
            <span class="chevron">▾</span>
          </button>
          <button type="button" class="filter-pill">
            {{ fileType }}
            <span class="chevron">▾</span>
          </button>
        </div>
        <div class="sort-group">
          <span class="sort-label">排序方式：</span>
          <button type="button" class="sort-pill">
            {{ sortBy }}
            <span class="chevron">▾</span>
          </button>
        </div>
      </div>
    </section>

    <!-- 结果推荐区（图2） -->
    <section class="results">
      <p class="results-tip">根据以上筛选条件为你推荐</p>
      <div class="card-grid">
        <article v-for="item in filteredResources" :key="item.id" class="resource-card">
          <div class="card-header">
            <div class="icon-pill">
              <span class="icon-text">{{ item.icon }}</span>
            </div>
            <div class="card-title-wrap">
              <h3 class="card-title">{{ item.title }}</h3>
              <span class="card-tag">{{ item.tag }}</span>
            </div>
          </div>
          <p class="card-desc">
            {{ item.desc }}
          </p>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-wrap {
  min-height: 100%;
  padding: 32px 40px 40px;
  background: #f4f7fb;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero {
  max-width: 1040px;
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

.filter-row {
  max-width: 1040px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.filter-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
}

.chevron {
  font-size: 10px;
  color: #9ca3af;
}

.sort-group {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.sort-label {
  font-size: 14px;
  color: #9ca3af;
}

.sort-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 14px;
  color: #2563eb;
  cursor: pointer;
}

.results {
  max-width: 1100px;
  margin: 0 auto;
}

.results-tip {
  text-align: center;
  margin: 4px 0 18px;
  font-size: 14px;
  color: #9ca3af;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px 18px;
}

.resource-card {
  background: #ffffff;
  border-radius: 18px;
  padding: 14px 16px 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  border: 1px solid #edf0f5;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.icon-pill {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #f3f4ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-text {
  font-size: 18px;
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
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.card-tag {
  font-size: 13px;
  color: #9ca3af;
}

.card-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #4b5563;
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

  .filter-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .card-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

