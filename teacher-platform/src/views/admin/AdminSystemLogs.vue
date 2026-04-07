<template>
  <div class="admin-page">
    <section class="logs-charts" aria-label="系统日志数据概览">
      <div class="logs-chart-card">
        <div ref="chartLevelRef" class="chart-el" role="img" aria-label="日志级别分布柱状图" />
      </div>
      <div class="logs-chart-card">
        <div ref="chartTrendRef" class="chart-el" role="img" aria-label="近 7 日日志趋势折线图" />
      </div>
      <div class="logs-chart-card">
        <div ref="chartIpRef" class="chart-el chart-el-ip" role="img" aria-label="IP 访问占比饼图" />
      </div>
    </section>

    <section class="filter-bar">
      <div class="filter-group">
        <button type="button" class="chip" :class="{ active: levelFilter === 'all' }" @click="setLevel('all')">全部日志</button>
        <button type="button" class="chip normal" :class="{ active: levelFilter === 'ok' }" @click="setLevel('ok')">正常</button>
        <button type="button" class="chip warn" :class="{ active: levelFilter === 'warn' }" @click="setLevel('warn')">警告</button>
        <button type="button" class="chip error" :class="{ active: levelFilter === 'error' }" @click="setLevel('error')">错误</button>
      </div>
      <div class="filter-group right">
        <span class="filter-label">日期范围：</span>
        <input v-model="startDate" type="date" class="date-input" />
        <span>至</span>
        <input v-model="endDate" type="date" class="date-input" />
        <button type="button" class="primary-btn logs-export-btn">导出日志数据</button>
      </div>
    </section>

    <section class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>操作人</th>
            <th>操作内容</th>
            <th>日志级别</th>
            <th>IP 地址</th>
            <th>时间戳</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="pagedLogs.length === 0">
            <td colspan="6" class="empty-cell">没有匹配的日志记录，请调整筛选条件。</td>
          </tr>

          <tr v-for="log in pagedLogs" :key="log.id" :class="{ 'row-warn': log.level === 'warn' }">
            <td>
              <div class="user-cell">
                <span class="user-avatar" :class="log.avatarClass">{{ log.avatarText }}</span>
                <span class="user-name">{{ log.actor }}</span>
              </div>
            </td>
            <td>{{ log.action }}</td>
            <td>
              <span class="level-tag" :class="log.level">
                {{ log.levelLabel }}
              </span>
            </td>
            <td><span class="ip-tag">{{ log.ip }}</span></td>
            <td>{{ log.timeText }}</td>
            <td class="col-actions">
              <button type="button" class="icon-btn" title="查看详情" @click="openDetail(log)">👁</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <span class="footer-text">显示 {{ rangeText }} 条 / 共 {{ totalFiltered.toLocaleString() }} 条日志记录</span>
        <div class="pagination">
          <button type="button" class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">‹</button>
          <template v-for="p in paginationPages" :key="`pg-${p}`">
            <button type="button" class="page-btn" :class="{ active: p === currentPage }" @click="goPage(p)">{{ p }}</button>
          </template>
          <span v-if="totalPages > (paginationPages[paginationPages.length - 1] || 0)" class="page-ellipsis">…</span>
          <button type="button" class="page-btn" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">›</button>
        </div>
      </div>
    </section>

    <div v-if="detailOpen" class="modal-overlay" role="dialog" aria-modal="true" @click.self="closeDetail">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">日志详情</h3>
          <button type="button" class="modal-close" @click="closeDetail">×</button>
        </div>
        <div v-if="selectedLog" class="modal-body">
          <div class="detail-grid">
            <div class="detail-item"><span class="detail-k">操作人</span><span class="detail-v">{{ selectedLog.actor }}</span></div>
            <div class="detail-item"><span class="detail-k">级别</span><span class="detail-v">{{ selectedLog.levelLabel }}</span></div>
            <div class="detail-item"><span class="detail-k">IP</span><span class="detail-v">{{ selectedLog.ip }}</span></div>
            <div class="detail-item"><span class="detail-k">时间</span><span class="detail-v">{{ selectedLog.timeText }}</span></div>
          </div>
          <div class="detail-content">
            <div class="detail-k">内容</div>
            <div class="detail-v mono">{{ selectedLog.detail }}</div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn primary" @click="closeDetail">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'

const chartLevelRef = ref(null)
const chartTrendRef = ref(null)
const chartIpRef = ref(null)

// —— 日志表：筛选/日期/翻页/详情 —— 
const PAGE_SIZE = 8
const levelFilter = ref('all') // all | ok | warn | error
const startDate = ref('')
const endDate = ref('')
const currentPage = ref(1)

/** @typedef {{ id:number; actor:string; avatarText:string; avatarClass:string; level:'ok'|'warn'|'error'; levelLabel:string; ip:string; timeTs:number; timeText:string; action:string; detail:string }} LogRow */
const logs = ref(
  /** @type {LogRow[]} */ ([
    {
      id: 1,
      actor: '张晓华',
      avatarText: '张',
      avatarClass: 'avatar-blue',
      level: 'ok',
      levelLabel: '正常',
      ip: '192.168.1.124',
      timeTs: new Date('2026-04-06T14:32:01').getTime(),
      timeText: '2026-04-06 14:32:01',
      action: '成功登录教学系统 · 认证模块',
      detail: '用户张晓华通过账号密码登录，认证模块校验通过（token 已签发）。'
    },
    {
      id: 2,
      actor: '系统通知',
      avatarText: '系',
      avatarClass: 'avatar-gray',
      level: 'warn',
      levelLabel: '警告',
      ip: '127.0.0.1',
      timeTs: new Date('2026-04-06T04:00:15').getTime(),
      timeText: '2026-04-06 04:00:15',
      action: '每日自动备份任务失败',
      detail: '备份任务在 step=upload 时超时，建议检查存储服务与网络连通性。'
    },
    {
      id: 3,
      actor: '李教务',
      avatarText: '李',
      avatarClass: 'avatar-blue',
      level: 'ok',
      levelLabel: '正常',
      ip: '10.0.24.56',
      timeTs: new Date('2026-04-01T11:20:44').getTime(),
      timeText: '2026-04-01 11:20:44',
      action: '尝试修改高三数学教学文件夹',
      detail: '权限校验通过，目录配置写入成功。'
    },
    {
      id: 4,
      actor: '王管理员',
      avatarText: '王',
      avatarClass: 'avatar-blue',
      level: 'ok',
      levelLabel: '正常',
      ip: '114.22.45.19',
      timeTs: new Date('2026-04-05T18:05:32').getTime(),
      timeText: '2026-04-05 18:05:32',
      action: '重置了个人主页面布局配置',
      detail: '重置为默认布局：导航栏/卡片布局已恢复。'
    },
    {
      id: 5,
      actor: '赵敏',
      avatarText: '赵',
      avatarClass: 'avatar-blue',
      level: 'ok',
      levelLabel: '正常',
      ip: '192.168.1.35',
      timeTs: new Date('2026-04-05T15:44:12').getTime(),
      timeText: '2026-04-05 15:44:12',
      action: '重置了学生账户（ID: 8823）的密码',
      detail: '管理员触发密码重置，已生成一次性临时密码（需首次登录修改）。'
    },
    {
      id: 6,
      actor: '系统任务',
      avatarText: '系',
      avatarClass: 'avatar-gray',
      level: 'ok',
      levelLabel: '正常',
      ip: '127.0.0.1',
      timeTs: new Date('2026-04-05T03:10:02').getTime(),
      timeText: '2026-04-05 03:10:02',
      action: '自动清理过期会话 · 42 条记录被移除',
      detail: '会话清理任务执行完成，已删除过期 session=42 条。'
    },
    {
      id: 7,
      actor: '周教务',
      avatarText: '周',
      avatarClass: 'avatar-blue',
      level: 'ok',
      levelLabel: '正常',
      ip: '10.0.12.8',
      timeTs: new Date('2026-04-04T16:32:40').getTime(),
      timeText: '2026-04-04 16:32:40',
      action: '批量导入 60 名新生账号',
      detail: '导入任务完成：成功 60，失败 0。'
    },
    {
      id: 8,
      actor: '曾运维',
      avatarText: '曾',
      avatarClass: 'avatar-blue',
      level: 'ok',
      levelLabel: '正常',
      ip: '192.168.2.10',
      timeTs: new Date('2026-04-04T09:18:21').getTime(),
      timeText: '2026-04-04 09:18:21',
      action: '手动触发系统健康检查 · 所有服务正常',
      detail: '健康检查通过：auth/api/db/cache 全部 OK。'
    },
    {
      id: 9,
      actor: '系统告警',
      avatarText: '系',
      avatarClass: 'avatar-gray',
      level: 'error',
      levelLabel: '错误',
      ip: '127.0.0.1',
      timeTs: new Date('2026-04-03T22:41:08').getTime(),
      timeText: '2026-04-03 22:41:08',
      action: '资源解析服务异常退出（code=137）',
      detail: '进程被系统 OOM Killer 终止（疑似内存不足）。建议限制并发或增加内存。'
    },
    {
      id: 10,
      actor: '韩雪松',
      avatarText: '韩',
      avatarClass: 'avatar-blue',
      level: 'warn',
      levelLabel: '警告',
      ip: '192.168.1.90',
      timeTs: new Date('2026-04-02T10:12:33').getTime(),
      timeText: '2026-04-02 10:12:33',
      action: '重复提交课件资源（疑似网络抖动）',
      detail: '同一资源在 30s 内重复提交 3 次，系统已自动去重。'
    }
  ])
)

function setLevel(lv) {
  levelFilter.value = lv
}

function dayStartTs(dateStr) {
  if (!dateStr) return null
  return new Date(`${dateStr}T00:00:00`).getTime()
}

function dayEndTs(dateStr) {
  if (!dateStr) return null
  return new Date(`${dateStr}T23:59:59`).getTime()
}

const filteredLogs = computed(() => {
  const lv = levelFilter.value
  const s = dayStartTs(startDate.value)
  const e = dayEndTs(endDate.value)
  let arr = logs.value

  if (lv !== 'all') arr = arr.filter((x) => x.level === lv)
  if (s != null) arr = arr.filter((x) => x.timeTs >= s)
  if (e != null) arr = arr.filter((x) => x.timeTs <= e)

  return [...arr].sort((a, b) => b.timeTs - a.timeTs)
})

const totalFiltered = computed(() => filteredLogs.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalFiltered.value / PAGE_SIZE)))

watch(totalPages, (tp) => {
  if (currentPage.value > tp) currentPage.value = tp
})

watch(
  () => [levelFilter.value, startDate.value, endDate.value],
  () => {
    currentPage.value = 1
  }
)

const pagedLogs = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredLogs.value.slice(start, start + PAGE_SIZE)
})

const rangeText = computed(() => {
  if (totalFiltered.value === 0) return '0-0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = Math.min(currentPage.value * PAGE_SIZE, totalFiltered.value)
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

const detailOpen = ref(false)
const selectedLog = ref(null)
function openDetail(log) {
  selectedLog.value = log
  detailOpen.value = true
}
function closeDetail() {
  detailOpen.value = false
  selectedLog.value = null
}

let chartLevelInstance = null
let chartTrendInstance = null
let chartIpInstance = null

function renderCharts() {
  const levelEl = chartLevelRef.value
  const trendEl = chartTrendRef.value
  const ipEl = chartIpRef.value
  if (!levelEl || !trendEl || !ipEl) return

  if (!chartLevelInstance) chartLevelInstance = echarts.init(levelEl)
  if (!chartTrendInstance) chartTrendInstance = echarts.init(trendEl)
  if (!chartIpInstance) chartIpInstance = echarts.init(ipEl)

  const levelLabels = ['正常', '警告', '错误']
  const levelValues = [920, 52, 18]

  chartLevelInstance.setOption({
    title: {
      text: '日志级别分布',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, fontWeight: 700, color: '#0f172a' }
    },
    tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
    legend: { orient: 'vertical', right: 0, top: 44, textStyle: { fontSize: 12 } },
    series: [
      {
        name: '日志级别',
        type: 'pie',
        radius: ['36%', '58%'],
        center: ['44%', '60%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { fontSize: 12, formatter: '{b}\n{d}%' },
        data: [
          { name: levelLabels[0], value: levelValues[0], itemStyle: { color: '#60a5fa' } },
          { name: levelLabels[1], value: levelValues[1], itemStyle: { color: '#fdba74' } },
          { name: levelLabels[2], value: levelValues[2], itemStyle: { color: '#fca5a5' } }
        ]
      }
    ]
  })

  const trendLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const trendOk = [120, 132, 128, 146, 160, 140, 154]
  const trendWarn = [8, 12, 10, 9, 14, 11, 13]

  chartTrendInstance.setOption({
    title: {
      text: '近 7 日日志趋势',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, fontWeight: 700, color: '#0f172a' }
    },
    tooltip: { trigger: 'axis' },
    legend: { top: 34, left: 'center', textStyle: { fontSize: 12 } },
    grid: { left: '8%', right: '6%', bottom: '0%', top: 58, containLabel: true },
    xAxis: { type: 'category', data: trendLabels, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } } },
    series: [
      {
        name: '正常',
        type: 'line',
        smooth: true,
        data: trendOk,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37,99,235,0.35)' },
            { offset: 1, color: 'rgba(37,99,235,0.02)' }
          ])
        },
        itemStyle: { color: '#2563eb' }
      },
      {
        name: '警告',
        type: 'line',
        smooth: true,
        data: trendWarn,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(249,115,22,0.28)' },
            { offset: 1, color: 'rgba(249,115,22,0.02)' }
          ])
        },
        itemStyle: { color: '#f97316' }
      }
    ]
  })

  const ipNames = ['10.0.12.8', '192.168.1.124', '127.0.0.1', '114.22.45.19', '10.0.24.56', '其他']
  const ipValues = [340, 220, 96, 74, 62, 120]

  chartIpInstance.setOption({
    title: { text: 'Top IP 访问', left: 'center', top: 10, textStyle: { fontSize: 14, fontWeight: 700, color: '#0f172a' } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '6%', right: '8%', bottom: '6%', top: 52, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } }
    },
    yAxis: {
      type: 'category',
      data: ipNames,
      axisLabel: { color: '#64748b', fontSize: 12 }
    },
    series: [
      {
        name: '访问次数',
        type: 'bar',
        barWidth: 18,
        data: ipValues,
        itemStyle: {
          borderRadius: [999, 999, 999, 999],
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
            { offset: 0, color: '#60a5fa' },
            { offset: 1, color: '#2563eb' }
          ])
        },
        label: { show: true, position: 'right', formatter: '{c} 次', color: '#334155', fontSize: 12 }
      }
    ]
  })
}

function resizeCharts() {
  chartLevelInstance?.resize()
  chartTrendInstance?.resize()
  chartIpInstance?.resize()
}

onMounted(() => {
  nextTick(() => {
    renderCharts()
    window.addEventListener('resize', resizeCharts)
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  chartLevelInstance?.dispose()
  chartTrendInstance?.dispose()
  chartIpInstance?.dispose()
  chartLevelInstance = null
  chartTrendInstance = null
  chartIpInstance = null
})
</script>

<style scoped>
.admin-page {
  flex: 1;
  min-height: 100%;
  padding: 15px 32px 32px;
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

.primary-btn {
  border: none;
  border-radius: 999px;
  padding: 9px 18px;
  background: #2563eb;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chip {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  padding: 6px 12px;
  background: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

.chip.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.chip.normal {
  color: #16a34a;
}
 
.chip.warn {
  color: #f97316;
}

.chip.error {
  color: #ef4444;
}

.filter-label {
  font-size: 14px;
  color: #64748b;
}

.date-input {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
}

.logs-charts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 4px;
}

.logs-chart-card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  padding: 10px 14px 14px;
  min-height: 240px;
}

.logs-card-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin: 2px 0 10px;
  text-align: center;
}

.chart-el {
  width: 100%;
  height: 205px;
  min-width: 0;
}

.chart-el-ip {
  height: 225px;
}

.logs-export-btn {
  white-space: nowrap;
}

.table-card {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 12px 20px 22px;
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

.avatar-gray {
  background: #94a3b8;
}

.user-name {
  color: #0f172a;
}

.level-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
}

.level-tag.ok {
  background: #dcfce7;
  color: #15803d;
}

.level-tag.warn {
  background: #fef3c7;
  color: #b45309;
}

.level-tag.error {
  background: #fee2e2;
  color: #b91c1c;
}

.ip-tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e5e7eb;
  font-size: 11px;
  color: #374151;
}

.row-warn {
  background: #fff7ed;
}

.col-actions {
  text-align: center;
  font-size: 16px;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
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
  font-size: 13px;
  color: #9ca3af;
}

.empty-cell {
  text-align: center;
  padding: 18px 10px;
  color: #64748b;
  font-size: 13px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 4000;
  padding: 16px;
}

.modal {
  width: min(720px, 96vw);
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.25);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.modal-close {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  color: #64748b;
  line-height: 1;
}

.modal-body {
  padding: 14px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
  margin-bottom: 12px;
}

.detail-item {
  display: flex;
  gap: 10px;
  align-items: baseline;
}

.detail-k {
  min-width: 54px;
  color: #64748b;
  font-size: 13px;
}

.detail-v {
  color: #0f172a;
  font-size: 14px;
}

.detail-content {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
}

.detail-v.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  white-space: pre-wrap;
  word-break: break-word;
  color: #0f172a;
  font-size: 13px;
}

.modal-footer {
  padding: 12px 14px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn.primary {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  background: #2563eb;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 1100px) {
  .admin-page { padding: 20px 20px 24px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .filter-bar { flex-direction: column; align-items: stretch; gap: 10px; }
  .logs-charts { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .admin-page { padding: 16px 12px 20px; }
  .page-title { font-size: 20px; }
  .filter-group { flex-wrap: wrap; }
  .table-card { padding: 12px; overflow-x: auto; }
  .data-table { min-width: 580px; font-size: 13px; }
  .table-footer { flex-direction: column; gap: 8px; align-items: flex-start; }
}

@media (max-width: 480px) {
  .admin-page { padding: 12px 10px 16px; }
  .page-title { font-size: 18px; }
}
</style>

