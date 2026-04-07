<template>
  <div class="admin-page">
    <header class="page-header">
      <div />
    </header>

    <section class="audit-charts" aria-label="资源审计数据概览">
      <div class="audit-charts-row">
        <div class="audit-kpis">
          <div class="kpi-item">
            <span class="kpi-label">本月共待审</span>
            <span class="kpi-value">{{ kpiPending }}</span>
          </div>
          <div class="kpi-item">
            <span class="kpi-label">本月已通过</span>
            <span class="kpi-value ok">{{ kpiApproved }}</span>
          </div>
          <div class="kpi-item">
            <span class="kpi-label">本月已驳回</span>
            <span class="kpi-value reject">{{ kpiRejected }}</span>
          </div>
          <div class="kpi-item">
            <span class="kpi-label">文件合规率</span>
            <span class="kpi-value">{{ kpiCompliance }}</span>
          </div>
        </div>

        <div ref="chartTypeRef" class="chart-el" role="img" aria-label="按类型与状态的审核数量堆叠条形图" />
        <div ref="chartStatusRef" class="chart-el" role="img" aria-label="近 7 日审核数量趋势折线图" />
      </div>
    </section>

    <section class="tabs-row">
      <div class="tabs-left">
        <button
          type="button"
          class="tab"
          :class="{ active: activeTab === 'all' }"
          @click="activeTab = 'all'"
        >
          全部待审（{{ tabCounts.all }}）
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: activeTab === '文档' }"
          @click="activeTab = '文档'"
        >
          文档资源（{{ tabCounts.文档 }}）
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: activeTab === '视频' }"
          @click="activeTab = '视频'"
        >
          视频资源（{{ tabCounts.视频 }}）
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: activeTab === '课件' }"
          @click="activeTab = '课件'"
        >
          课件 PPT（{{ tabCounts.课件 }}）
        </button>
      </div>
      <div class="tabs-actions">
        <button type="button" class="outline-btn">导出审核记录</button>
        <button type="button" class="primary-btn">全部通过</button>
      </div>
    </section>

    <section class="table-card">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" v-model="searchQuery" placeholder="搜索资源名称、上传教师或标签" />
        </div>
        <div class="toolbar-actions">
          <select class="filter-select" v-model="sortKey">
            <option value="submit_time">按提交时间</option>
            <option value="type">按资源类型</option>
            <option value="uploader">按上传教师</option>
          </select>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>资源名称 &amp; 说明</th>
            <th>类型</th>
            <th>上传教师</th>
            <th>提交时间</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="pagedResources.length === 0">
            <td colspan="5" class="empty-cell">没有匹配的资源，请调整搜索或筛选条件。</td>
          </tr>

          <tr v-for="r in pagedResources" :key="r.id">
            <td>
              <div class="res-cell">
                <span
                  class="res-icon"
                  :class="r.type === '视频' ? 'green' : r.type === '文档' ? 'orange' : 'blue'"
                >
                  {{ r.iconLabel }}
                </span>
                <div>
                  <p class="res-title">{{ r.title }}</p>
                  <p class="res-sub">
                    {{ r.sizeMB }} MB · {{ r.extLabel }}
                  </p>
                </div>
              </div>
            </td>

            <td>
              <span
                class="type-tag"
                :class="r.type === '视频' ? 'green' : r.type === '文档' ? 'orange' : ''"
              >
                {{ r.typeLabel }}
              </span>
            </td>

            <td>
              <div class="user-cell">
                <span
                  class="user-avatar"
                  :class="r.type === '视频' ? 'avatar-green' : r.type === '文档' ? 'avatar-orange' : 'avatar-blue'"
                >
                  {{ r.uploaderName.slice(0, 1) }}
                </span>
                <span class="user-name">{{ r.uploaderName }}（{{ r.uploaderDept }}）</span>
              </div>
            </td>

            <td>{{ r.submitTime }}</td>

            <td class="col-actions">
              <button type="button" class="btn-pass" @click="approve(r)">通过</button>
              <button type="button" class="btn-reject" @click="reject(r)">驳回</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <span class="footer-text">显示 {{ rangeText }} 条，共 {{ totalFiltered }} 份待审资源</span>
        <div class="pagination">
          <button type="button" class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">‹</button>
          <template v-for="(p, i) in paginationPages" :key="`pg-${p}`">
            <span v-if="i === 0 && p > 1" class="page-ellipsis">…</span>
            <button type="button" class="page-btn" :class="{ active: p === currentPage }" @click="goPage(p)">
              {{ p }}
            </button>
          </template>
          <span
            v-if="paginationPages[paginationPages.length - 1] < totalPages"
            class="page-ellipsis"
          >…</span>
          <button
            type="button"
            class="page-btn"
            :disabled="currentPage >= totalPages"
            @click="goPage(currentPage + 1)"
          >
            ›
          </button>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'

/** @typedef {{ id: number; type: '文档'|'视频'|'课件'; status: 'pending'|'approved'|'rejected' }} AuditItem */

// 模拟：资源审计统计数据（用于图表展示）
const auditItems = ref(
  /** @type {AuditItem[]} */ ([
    { id: 1, type: '课件', status: 'pending' },
    { id: 2, type: '课件', status: 'approved' },
    { id: 3, type: '课件', status: 'approved' },
    { id: 4, type: '课件', status: 'rejected' },
    { id: 5, type: '文档', status: 'pending' },
    { id: 6, type: '文档', status: 'pending' },
    { id: 7, type: '文档', status: 'approved' },
    { id: 8, type: '文档', status: 'rejected' },
    { id: 9, type: '视频', status: 'pending' },
    { id: 10, type: '视频', status: 'approved' },
    { id: 11, type: '视频', status: 'approved' },
    { id: 12, type: '视频', status: 'approved' },
    // 扩充一些，让数据更丰满
    { id: 13, type: '课件', status: 'approved' },
    { id: 14, type: '课件', status: 'approved' },
    { id: 15, type: '课件', status: 'pending' },
    { id: 16, type: '课件', status: 'approved' },
    { id: 17, type: '文档', status: 'approved' },
    { id: 18, type: '文档', status: 'approved' },
    { id: 19, type: '文档', status: 'pending' },
    { id: 20, type: '视频', status: 'pending' },
    { id: 21, type: '视频', status: 'approved' },
    { id: 22, type: '视频', status: 'rejected' },
    { id: 23, type: '课件', status: 'rejected' },
    { id: 24, type: '文档', status: 'rejected' },
    { id: 25, type: '文档', status: 'pending' },
    { id: 26, type: '视频', status: 'pending' },
    { id: 27, type: '课件', status: 'pending' },
    { id: 28, type: '文档', status: 'pending' },
    { id: 29, type: '课件', status: 'rejected' },
    { id: 30, type: '视频', status: 'pending' },
    { id: 31, type: '文档', status: 'approved' },
    { id: 32, type: '课件', status: 'pending' },
    { id: 33, type: '视频', status: 'approved' },
    { id: 34, type: '文档', status: 'pending' },
    { id: 35, type: '课件', status: 'pending' },
    { id: 36, type: '视频', status: 'pending' },
    { id: 37, type: '文档', status: 'rejected' },
    { id: 38, type: '课件', status: 'approved' },
    { id: 39, type: '视频', status: 'pending' },
    { id: 40, type: '文档', status: 'pending' },
    { id: 41, type: '课件', status: 'pending' },
    { id: 42, type: '视频', status: 'approved' },
    { id: 43, type: '文档', status: 'pending' },
    { id: 44, type: '视频', status: 'pending' },
    { id: 45, type: '课件', status: 'rejected' }
  ])
)

const kpiPending = computed(() => auditItems.value.filter((x) => x.status === 'pending').length + 20)
const kpiApproved = computed(() => auditItems.value.filter((x) => x.status === 'approved').length + 80)
const kpiRejected = computed(() => auditItems.value.filter((x) => x.status === 'rejected').length + 12)
const kpiCompliance = computed(() => `${Math.round((kpiApproved.value / (kpiApproved.value + kpiRejected.value)) * 1000) / 10}%`)

// —— 资源审计表：搜索/筛选/翻页（前端内存模拟）——
const PAGE_SIZE = 5
const searchQuery = ref('')
const sortKey = ref('submit_time') // submit_time | type | uploader
const activeTab = ref('all') // all | 文档 | 视频 | 课件
const currentPage = ref(1)

const uploaderNames = ['李泽洋', '王志琪', '陈佳欣', '赵立新', '孙雅宁', '钱思远', '冯雨晴', '韩雪松', '杨若溪', '许嘉怡']
const uploaderDepts = ['数学组', '英语组', '物理组', '地理组', '语文组', '政治组', '音乐组', '体育教研组', '美术教研组', '心理健康中心']

function formatSubmitTime(ts) {
  const d = new Date(ts)
  const pad = (n) => `${n}`.padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function buildRowFromAudit(item, idx) {
  const type = item.type
  const uploaderName = uploaderNames[idx % uploaderNames.length]
  const uploaderDept = uploaderDepts[(idx + 3) % uploaderDepts.length]

  const base = new Date('2023-11-01T00:00:00Z').getTime()
  const dayOffset = idx % 26
  const hour = (idx * 7) % 24
  const min = (idx * 13) % 60
  const submitTs = base + dayOffset * 86400000 + hour * 3600000 + min * 60000

  const sizeMB = Math.round(((idx * 7) % 210) / 10 * 10) / 10
  const typeLabel = type === '课件' ? '课件' : type === '视频' ? '视频' : '文档'
  const iconLabel = type === '课件' ? 'PPT' : type === '视频' ? 'MP4' : 'PDF'
  const extLabel = type === '课件' ? 'PowerPoint 文件' : type === '视频' ? 'MP4 视频 · 4K' : 'PDF 文档'
  const titleBase =
    type === '课件'
      ? '高中数学学习-函数专题课件'
      : type === '视频'
        ? '英语口语课堂-情景对话示范视频'
        : '初中物理实验-电路串并联教案'

  return {
    ...item,
    uploaderName,
    uploaderDept,
    submitTs,
    submitTime: formatSubmitTime(submitTs),
    sizeMB,
    typeLabel,
    iconLabel,
    extLabel,
    title: `${titleBase}（${item.id}）`
  }
}

const resourceRows = computed(() => auditItems.value.map((it, idx) => buildRowFromAudit(it, idx)))

const tabTypeFilter = computed(() => {
  if (activeTab.value === 'all') return null
  if (activeTab.value === '文档') return '文档'
  if (activeTab.value === '视频') return '视频'
  if (activeTab.value === '课件') return '课件'
  return null
})

const tabCounts = computed(() => {
  const pending = resourceRows.value.filter((r) => r.status === 'pending')
  const countAll = pending.length
  const countDoc = pending.filter((r) => r.type === '文档').length
  const countVideo = pending.filter((r) => r.type === '视频').length
  const countPpt = pending.filter((r) => r.type === '课件').length
  return { all: countAll, 文档: countDoc, 视频: countVideo, 课件: countPpt }
})

const filteredResources = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const typeFilter = tabTypeFilter.value
  let arr = resourceRows.value.filter((r) => r.status === 'pending')

  if (typeFilter) arr = arr.filter((r) => r.type === typeFilter)
  if (q) {
    arr = arr.filter((r) => {
      const hay = `${r.title} ${r.uploaderName} ${r.uploaderDept}`.toLowerCase()
      return hay.includes(q)
    })
  }

  const sorted = [...arr]
  if (sortKey.value === 'submit_time') {
    sorted.sort((a, b) => b.submitTs - a.submitTs)
  } else if (sortKey.value === 'type') {
    const order = { 课件: 0, 视频: 1, 文档: 2 }
    sorted.sort((a, b) => order[a.type] - order[b.type])
  } else if (sortKey.value === 'uploader') {
    sorted.sort((a, b) => a.uploaderName.localeCompare(b.uploaderName))
  }
  return sorted
})

const totalFiltered = computed(() => filteredResources.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalFiltered.value / PAGE_SIZE)))

watch(totalPages, (tp) => {
  if (currentPage.value > tp) currentPage.value = tp
})

watch(
  () => [activeTab.value, searchQuery.value, sortKey.value],
  () => {
    currentPage.value = 1
  }
)

const pagedResources = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredResources.value.slice(start, start + PAGE_SIZE)
})

const rangeText = computed(() => {
  const tf = totalFiltered.value
  if (tf === 0) return '0-0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = Math.min(currentPage.value * PAGE_SIZE, tf)
  return `${start}-${end}`
})

const paginationPages = computed(() => {
  const tp = totalPages.value
  const cur = currentPage.value
  if (tp <= 3) return Array.from({ length: tp }, (_, i) => i + 1)
  const start = Math.max(1, Math.min(cur - 1, tp - 2))
  return [start, start + 1, start + 2].filter((n) => n >= 1 && n <= tp)
})

function goPage(p) {
  if (p < 1 || p > totalPages.value) return
  currentPage.value = p
}

function approve(row) {
  const idx = auditItems.value.findIndex((x) => x.id === row.id)
  if (idx === -1) return
  auditItems.value[idx].status = 'approved'
}

function reject(row) {
  const idx = auditItems.value.findIndex((x) => x.id === row.id)
  if (idx === -1) return
  auditItems.value[idx].status = 'rejected'
}

// 类型 × 状态分布，用于横向堆叠条形图
const statusPerType = computed(() => {
  const base = {
    文档: { approved: 0, pending: 0, rejected: 0 },
    视频: { approved: 0, pending: 0, rejected: 0 },
    课件: { approved: 0, pending: 0, rejected: 0 }
  }
  for (const x of auditItems.value) {
    const bucket = base[x.type]
    if (!bucket) continue
    bucket[x.status === 'approved' ? 'approved' : x.status === 'pending' ? 'pending' : 'rejected']++
  }
  // 轻微放大数量，避免柱子太小
  for (const type of Object.keys(base)) {
    base[type].approved = base[type].approved * 4 + 40
    base[type].pending = base[type].pending * 4 + 16
    base[type].rejected = base[type].rejected * 4 + 10
  }
  return base
})

// 近 7 日审核趋势（虚拟数据）
const trendLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const trendApproved = [32, 46, 40, 52, 61, 38, 44]
const trendPending = [18, 14, 12, 16, 10, 8, 9]

const chartTypeRef = ref(null)
const chartStatusRef = ref(null)
let chartTypeInstance = null
let chartStatusInstance = null

function renderAuditCharts() {
  const typeEl = chartTypeRef.value
  const statusEl = chartStatusRef.value
  if (!typeEl || !statusEl) return

  if (!chartTypeInstance) chartTypeInstance = echarts.init(typeEl)
  if (!chartStatusInstance) chartStatusInstance = echarts.init(statusEl)

  const perType = statusPerType.value
  const typeNames = Object.keys(perType)
  chartTypeInstance.setOption({
    title: {
      text: '按类型 · 审核状态分布',
      left: 'center',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' }
    },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      top: 32,
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    grid: { left: '6%', right: '10%', bottom: '6%', top: 64, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } }
    },
    yAxis: {
      type: 'category',
      data: typeNames,
      axisLabel: { fontSize: 13, color: '#64748b' }
    },
    series: [
      {
        name: '已通过',
        type: 'bar',
        stack: 'total',
        barWidth: 22,
        data: typeNames.map((n) => perType[n].approved),
        itemStyle: { color: '#4ade80', borderRadius: [999, 0, 0, 999] }
      },
      {
        name: '待审核',
        type: 'bar',
        stack: 'total',
        barWidth: 22,
        data: typeNames.map((n) => perType[n].pending),
        itemStyle: { color: '#fdba74' }
      },
      {
        name: '已驳回',
        type: 'bar',
        stack: 'total',
        barWidth: 22,
        data: typeNames.map((n) => perType[n].rejected),
        itemStyle: {
          color: '#fca5a5',
          borderRadius: [0, 999, 999, 0]
        }
      }
    ]
  })

  chartStatusInstance.setOption({
    title: {
      text: '近 7 日审核趋势',
      left: 'center',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' }
    },
    tooltip: { trigger: 'axis' },
    legend: {
      top: 32,
      left: 'center',
      textStyle: { fontSize: 12 }
    },
    grid: { left: '8%', right: '6%', bottom: '8%', top: 64, containLabel: true },
    xAxis: {
      type: 'category',
      data: trendLabels,
      boundaryGap: true,
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } }
    },
    series: [
      {
        name: '已通过',
        type: 'line',
        smooth: true,
        data: trendApproved,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(74,222,128,0.35)' },
            { offset: 1, color: 'rgba(74,222,128,0.02)' }
          ])
        },
        itemStyle: { color: '#4ade80' }
      },
      {
        name: '待审核',
        type: 'line',
        smooth: true,
        data: trendPending,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(253,186,116,0.35)' },
            { offset: 1, color: 'rgba(253,186,116,0.02)' }
          ])
        },
        itemStyle: { color: '#fdba74' }
      }
    ]
  })
}

function resizeCharts() {
  chartTypeInstance?.resize()
  chartStatusInstance?.resize()
}

onMounted(() => {
  nextTick(() => {
    renderAuditCharts()
    window.addEventListener('resize', resizeCharts)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  chartTypeInstance?.dispose()
  chartStatusInstance?.dispose()
  chartTypeInstance = null
  chartStatusInstance = null
})
</script>

<style scoped>
.admin-page {
  flex: 1;
  min-height: 100%;
  padding: 0px 32px 32px;
  background: #f4f7fb;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  font-size: 15px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.primary-btn {
  border: none;
  border-radius: 999px;
  padding: 8px 16px;
  background: #2563eb;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.outline-btn {
  border-radius: 999px;
  padding: 9px 16px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #0f172a;
  font-size: 15px;
  cursor: pointer;
}

.tabs-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.audit-charts {
  margin-bottom: 10px;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  padding: 14px 16px 16px;
}

.audit-charts-row {
  display: grid;
  grid-template-columns: auto 1.25fr 0.85fr;
  gap: 12px;
  align-items: stretch;
}

.audit-kpis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 6px 8px 2px;
  min-width: 140px;
}

.kpi-item {
  display: flex;
  align-items: baseline;
  justify-content: flex-start;
  gap: 12px;
}

.kpi-label {
  font-size: 15px;
  color: #64748b;
}

.kpi-value {
  font-size: 21px;
  font-weight: 800;
  color: #0f172a;
}

.kpi-value.ok {
  color: #16a34a;
}

.kpi-value.reject {
  color: #dc2626;
}

.chart-el {
  width: 100%;
  height: 195px;
  min-height: 195px;
  min-width: 0;
}

.tabs-left {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tabs-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.tab {
  border-radius: 999px;
  border: none;
  padding: 7px 14px;
  background: #e5e7eb;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
}

.tab.active {
  background: #2563eb;
  color: #ffffff;
}

.table-card {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 15px 20px 22px;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.search-icon {
  font-size: 14px;
}

.search-box input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 14px;
  color: #4b5563;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table thead {
  background: #f8fafc;
}

.data-table th,
.data-table td {
  padding: 9px 10px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.data-table th {
  font-weight: 600;
  color: #64748b;
}

.res-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.res-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #ffffff;
}

.res-icon.blue {
  background: #2563eb;
}

.res-icon.green {
  background: #16a34a;
}

.res-icon.orange {
  background: #f97316;
}

.res-title {
  margin: 0 0 2px;
  color: #0f172a;
}

.res-sub {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}

.type-tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e5e7eb;
  font-size: 12px;
  color: #4b5563;
}

.type-tag.green {
  background: #dcfce7;
  color: #15803d;
}

.type-tag.orange {
  background: #fee2e2;
  color: #b91c1c;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #ffffff;
}

.avatar-blue {
  background: #3b82f6;
}

.avatar-green {
  background: #10b981;
}

.avatar-orange {
  background: #f97316;
}

.user-name {
  color: #0f172a;
}

.btn-pass,
.btn-reject {
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  border: none;
  cursor: pointer;
  margin-left: 4px;
}

.btn-pass {
  background: #dcfce7;
  color: #15803d;
}

.btn-reject {
  background: #fee2e2;
  color: #b91c1c;
}

.row-highlight {
  background: #fefce8;
}

.col-actions {
  text-align: center;
  white-space: nowrap;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  font-size: 13px;
  color: #9ca3af;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-btn {
  min-width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

.page-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.page-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.page-ellipsis {
  color: #9ca3af;
  padding: 0 2px;
  user-select: none;
}

.empty-cell {
  text-align: center;
  padding: 18px 10px;
  color: #64748b;
  font-size: 13px;
}

.bottom-stats {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.bottom-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
}

.bottom-label {
  margin: 0 0 4px;
  font-size: 13px;
  color: #64748b;
}

.bottom-value {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
}

@media (max-width: 1100px) {
  .admin-page { padding: 20px 20px 24px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .tabs-row { flex-wrap: wrap; gap: 6px; }
  .tabs-actions { width: 100%; justify-content: flex-end; }
  .audit-charts-row { grid-template-columns: 1fr; }
  .audit-kpis { flex-direction: row; flex-wrap: wrap; gap: 10px 14px; min-width: 0; }
  .kpi-item { min-width: 130px; }
  .bottom-stats { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 720px) {
  .admin-page { padding: 16px 12px 20px; }
  .page-title { font-size: 20px; }
  .header-actions { flex-wrap: wrap; }
  .table-card { padding: 12px; overflow-x: auto; }
  .data-table { min-width: 620px; font-size: 13px; }
  .table-toolbar { flex-direction: column; align-items: stretch; }
  .bottom-stats { grid-template-columns: 1fr; }
  .table-footer { flex-direction: column; gap: 8px; align-items: flex-start; }
}

@media (max-width: 480px) {
  .admin-page { padding: 12px 10px 16px; }
  .page-title { font-size: 18px; }
}
</style>

