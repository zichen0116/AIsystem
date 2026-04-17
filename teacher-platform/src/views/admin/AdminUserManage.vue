<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const PAGE_SIZE = 8

const ROLE_OPTIONS = ['高级教师', '备课教师', '教研组长', '平台管理员', '年级组长']

/** @typedef {{ id: number; name: string; employeeId: string; department: string; role: string; lastActive: string; status: 'active' | 'pending' | 'disabled'; avatarClass: string }} Teacher */

/** @type {import('vue').Ref<Teacher[]>} */
const teachers = ref([
  { id: 1, name: '陈明华', employeeId: 'T20236901', department: '数学教研组', role: '高级教师', lastActive: '2026-04-01 09:15', status: 'active', avatarClass: 'avatar-blue' },
  { id: 2, name: '周丽君', employeeId: 'T20236789', department: '生物教研组', role: '备课教师', lastActive: '2026-04-02 08:45', status: 'active', avatarClass: 'avatar-green' },
  { id: 3, name: '何建国', employeeId: 'T20235990', department: '历史教研组', role: '教研组长', lastActive: '2026-04-03 17:20', status: 'active', avatarClass: 'avatar-orange' },
  { id: 4, name: '刘晓彤', employeeId: 'T20234881', department: '信息技术组', role: '平台管理员', lastActive: '2026-04-04 11:05', status: 'active', avatarClass: 'avatar-blue' },
  { id: 5, name: '李春彤', employeeId: 'T20236445', department: '语文教研组', role: '备课教师', lastActive: '2026-04-05 16:40', status: 'active', avatarClass: 'avatar-green' },
  { id: 6, name: '王小波', employeeId: 'T20231802', department: '英语教研组', role: '年级组长', lastActive: '2026-04-06 10:22', status: 'disabled', avatarClass: 'avatar-orange' },
  { id: 7, name: '张凯齐', employeeId: 'T20231555', department: '物理教研组', role: '备课教师', lastActive: '2026-04-07 14:30', status: 'active', avatarClass: 'avatar-blue' },
  { id: 8, name: '孙艺宁', employeeId: 'T20237012', department: '化学教研组', role: '备课教师', lastActive: '2026-04-08 08:10', status: 'active', avatarClass: 'avatar-green' },
  { id: 9, name: '赵文博', employeeId: 'T20237120', department: '地理教研组', role: '备课教师', lastActive: '2026-04-09 10:02', status: 'pending', avatarClass: 'avatar-orange' },
  { id: 10, name: '钱思远', employeeId: 'T20237121', department: '政治教研组', role: '教研组长', lastActive: '2026-04-10 11:18', status: 'active', avatarClass: 'avatar-blue' },
  { id: 11, name: '冯雨晴', employeeId: 'T20237122', department: '音乐教研组', role: '备课教师', lastActive: '2026-04-01 08:30', status: 'active', avatarClass: 'avatar-green' },
  { id: 12, name: '韩雪松', employeeId: 'T20237123', department: '体育教研组', role: '高级教师', lastActive: '2026-04-02 09:45', status: 'active', avatarClass: 'avatar-orange' },
  { id: 13, name: '杨若溪', employeeId: 'T20237124', department: '美术教研组', role: '备课教师', lastActive: '2026-04-03 14:00', status: 'pending', avatarClass: 'avatar-blue' },
  { id: 14, name: '许嘉怡', employeeId: 'T20237125', department: '心理健康中心', role: '备课教师', lastActive: '2026-04-04 08:12', status: 'active', avatarClass: 'avatar-green' },
  { id: 15, name: '邓志强', employeeId: 'T20237126', department: '通用技术组', role: '年级组长', lastActive: '2026-04-05 15:22', status: 'active', avatarClass: 'avatar-orange' },
  { id: 16, name: '曹婉清', employeeId: 'T20237127', department: '图书馆 / 阅读课', role: '备课教师', lastActive: '2026-04-06 10:05', status: 'disabled', avatarClass: 'avatar-blue' },
  { id: 17, name: 'James Porter', employeeId: 'T20238001', department: 'English Dept.', role: '备课教师', lastActive: '2026-04-07 16:40', status: 'active', avatarClass: 'avatar-green' },
  { id: 18, name: 'Sarah Mitchell', employeeId: 'T20238002', department: 'International Programs', role: '教研组长', lastActive: '2026-04-08 09:00', status: 'active', avatarClass: 'avatar-orange' },
  { id: 19, name: 'Elena Vogt', employeeId: 'T20238003', department: '德语兴趣班', role: '备课教师', lastActive: '2026-04-09 11:30', status: 'pending', avatarClass: 'avatar-blue' },
  { id: 20, name: 'Marc Dubois', employeeId: 'T20238004', department: '法语选修', role: '备课教师', lastActive: '2026-04-10 08:50', status: 'active', avatarClass: 'avatar-green' },
  { id: 21, name: 'Yuki Tanaka', employeeId: 'T20238005', department: '日语第二外语', role: '高级教师', lastActive: '2026-04-01 13:15', status: 'active', avatarClass: 'avatar-orange' },
  { id: 22, name: '罗宇航', employeeId: 'T20237128', department: '创客 / 机器人实验室', role: '平台管理员', lastActive: '2026-04-02 09:20', status: 'active', avatarClass: 'avatar-blue' },
  { id: 23, name: '方雅琳', employeeId: 'T20237129', department: 'STEM 中心', role: '备课教师', lastActive: '2026-04-03 11:05', status: 'active', avatarClass: 'avatar-green' },
  { id: 24, name: '史俊杰', employeeId: 'T20237130', department: '德育处', role: '年级组长', lastActive: '2026-04-04 08:00', status: 'active', avatarClass: 'avatar-orange' },
  { id: 25, name: '丁佳慧', employeeId: 'T20237131', department: '团委 / 社团指导', role: '备课教师', lastActive: '2026-04-05 08:00', status: 'pending', avatarClass: 'avatar-blue' },
  { id: 26, name: '崔明轩', employeeId: 'T20237132', department: '总务后勤', role: '备课教师', lastActive: '2026-04-06 07:45', status: 'disabled', avatarClass: 'avatar-green' },
  { id: 27, name: 'Anna Kowalski', employeeId: 'T20238006', department: 'STEM Center (Co-teach)', role: '备课教师', lastActive: '2026-04-07 10:10', status: 'active', avatarClass: 'avatar-orange' },
  { id: 28, name: '龚子墨', employeeId: 'T20237133', department: '书法与传统文化', role: '高级教师', lastActive: '2026-04-08 14:28', status: 'active', avatarClass: 'avatar-blue' },
  { id: 29, name: '梁诗涵', employeeId: 'T20237134', department: '戏剧与影视', role: '备课教师', lastActive: '2026-04-09 14:28', status: 'active', avatarClass: 'avatar-green' },
  { id: 30, name: '邱振华', employeeId: 'T20237135', department: '竞赛教练组', role: '教研组长', lastActive: '2026-04-10 18:00', status: 'active', avatarClass: 'avatar-orange' },
  { id: 31, name: '赖思琪', employeeId: 'T20237136', department: '校本课程开发', role: '备课教师', lastActive: '2026-04-01 09:00', status: 'pending', avatarClass: 'avatar-blue' },
  { id: 32, name: '钟伟杰', employeeId: 'T20237137', department: '实验室安全督导', role: '平台管理员', lastActive: '2026-04-02 09:20', status: 'active', avatarClass: 'avatar-green' }
])

const searchQuery = ref('')
const filterRole = ref('')
const filterStatus = ref('')
const currentPage = ref(1)

const toast = ref('')
function showToast(msg) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 2600)
}

function surnameOf(name) {
  return (name && name[0]) || '?'
}

const filteredTeachers = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return teachers.value.filter((t) => {
    if (q) {
      const blob = `${t.name} ${t.employeeId} ${t.department}`.toLowerCase()
      if (!blob.includes(q)) return false
    }
    if (filterRole.value && t.role !== filterRole.value) return false
    if (filterStatus.value) {
      if (filterStatus.value === 'active' && t.status !== 'active') return false
      if (filterStatus.value === 'pending' && t.status !== 'pending') return false
      if (filterStatus.value === 'disabled' && t.status !== 'disabled') return false
    }
    return true
  })
})

watch([searchQuery, filterRole, filterStatus], () => {
  currentPage.value = 1
})

const totalFiltered = computed(() => filteredTeachers.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalFiltered.value / PAGE_SIZE)))

watch(totalPages, (tp) => {
  if (currentPage.value > tp) currentPage.value = tp
})

const pagedTeachers = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredTeachers.value.slice(start, start + PAGE_SIZE)
})

const rangeText = computed(() => {
  if (totalFiltered.value === 0) return '0-0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = Math.min(currentPage.value * PAGE_SIZE, totalFiltered.value)
  return `${start}-${end}`
})

// 仪表区使用的虚拟统计数据（与下方真实表格解耦）
const totalTeachersStat = ref(260)
const activeCount = ref(196)
const pendingCount = ref(38)
const disabledCount = ref(14)

/** 按角色聚合（含编辑后新增角色） */
const roleDistribution = computed(() => {
  const m = {}
  for (const t of teachers.value) {
    m[t.role] = (m[t.role] || 0) + 1
  }
  return Object.keys(m)
    .sort((a, b) => m[b] - m[a])
    .map((name) => ({ name, value: m[name] }))
})

// 柱状图使用的虚拟人数（与下方真实表格解耦）
const roleChartCategories = computed(() => ROLE_OPTIONS)
const roleChartValues = ref([63, 115, 40, 18, 24])

const chartRoleRef = ref(null)
const chartStatusRef = ref(null)
let chartRoleInstance = null
let chartStatusInstance = null

function renderUserCharts() {
  const roleEl = chartRoleRef.value
  const statusEl = chartStatusRef.value
  if (!roleEl || !statusEl) return

  if (!chartRoleInstance) chartRoleInstance = echarts.init(roleEl)
  if (!chartStatusInstance) chartStatusInstance = echarts.init(statusEl)

  const roleNames = roleChartCategories.value
  const roleValues = roleChartValues.value.slice(0, roleNames.length)
  chartRoleInstance.setOption({
    title: {
      text: '系统角色分布',
      left: 'center',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' }
    },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '6%', right: '6%', bottom: '3%', top: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: roleNames,
      axisLabel: { rotate: 0, interval: 0, fontSize: 13, color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitNumber: 6,
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } }
    },
    series: [
      {
        name: '人数',
        type: 'bar',
        barMaxWidth: 36,
        data: roleValues,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#60a5fa' },
            { offset: 1, color: '#2563eb' }
          ])
        },
        label: { show: true, position: 'top', fontSize: 11, color: '#475569', formatter: '{c} 人' }
      }
    ]
  })

  chartStatusInstance.setOption({
    title: {
      text: '账号状态',
      left: '38%',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' }
    },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      orient: 'vertical',
      right: 44,
      top: 'middle',
      textStyle: { fontSize: 12 }
    },
    series: [
      {
        name: '状态',
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['46%', '60%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { fontSize: 12, formatter: '{b}\n{c} ({d}%)' },
        data: [
          { value: activeCount.value, name: '已激活', itemStyle: { color: '#22c55e' } },
          { value: pendingCount.value, name: '待审核', itemStyle: { color: '#f97316' } },
          { value: disabledCount.value, name: '已停用', itemStyle: { color: '#ef4444' } }
        ]
      }
    ]
  })
}

function resizeCharts() {
  chartRoleInstance?.resize()
  chartStatusInstance?.resize()
}

onMounted(() => {
  nextTick(() => {
    renderUserCharts()
    window.addEventListener('resize', resizeCharts)
  })
})

watch(
  teachers,
  () => {
    nextTick(() => renderUserCharts())
  },
  { deep: true }
)

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  chartRoleInstance?.dispose()
  chartStatusInstance?.dispose()
  chartRoleInstance = null
  chartStatusInstance = null
})

/** 页码按钮：只展示 3 个页码，末尾用省略号营造“很多页” */
const paginationPages = computed(() => {
  const tp = totalPages.value
  if (tp <= 0) return []
  const cur = currentPage.value
  const start = Math.max(1, Math.min(cur - 1, tp - 2))
  const end = Math.min(tp, start + 2)
  const pages = []
  for (let p = start; p <= end; p++) pages.push(p)
  return pages
})

function goPage(p) {
  if (p < 1 || p > totalPages.value) return
  currentPage.value = p
}

// —— 编辑 ——
const editOpen = ref(false)
/** @type {import('vue').Ref<Teacher | null>} */
const editing = ref(null)
const editForm = ref({
  name: '',
  employeeId: '',
  department: '',
  role: '备课教师',
  lastActive: '',
  status: 'active'
})

function openEdit(t) {
  editing.value = t
  editForm.value = {
    name: t.name,
    employeeId: t.employeeId,
    department: t.department,
    role: t.role,
    lastActive: t.lastActive,
    status: t.status
  }
  editOpen.value = true
}

function closeEdit() {
  editOpen.value = false
  editing.value = null
}

function saveEdit() {
  const t = editing.value
  if (!t) return
  const f = editForm.value
  if (!f.name?.trim() || !f.employeeId?.trim()) {
    showToast('请填写姓名与工号')
    return
  }
  const idx = teachers.value.findIndex((x) => x.id === t.id)
  if (idx === -1) return
  teachers.value[idx] = {
    ...teachers.value[idx],
    name: f.name.trim(),
    employeeId: f.employeeId.trim(),
    department: f.department.trim() || '未分配',
    role: f.role,
    lastActive: f.lastActive.trim() || teachers.value[idx].lastActive,
    status: f.status
  }
  showToast('已保存修改')
  closeEdit()
}

// —— 删除 ——
const deleteOpen = ref(false)
/** @type {import('vue').Ref<Teacher | null>} */
const deleting = ref(null)

function openDelete(t) {
  deleting.value = t
  deleteOpen.value = true
}

function closeDelete() {
  deleteOpen.value = false
  deleting.value = null
}

function confirmDelete() {
  const t = deleting.value
  if (!t) return
  teachers.value = teachers.value.filter((x) => x.id !== t.id)
  if (pagedTeachers.value.length === 0 && currentPage.value > 1) {
    currentPage.value -= 1
  }
  showToast(`已删除「${t.name}」`)
  closeDelete()
}

// —— 新增 ——
const addOpen = ref(false)
const addForm = ref({
  name: '',
  employeeId: '',
  department: '',
  role: '备课教师',
  status: 'active'
})

function openAdd() {
  addForm.value = { name: '', employeeId: '', department: '', role: '备课教师', status: 'active' }
  addOpen.value = true
}

function closeAdd() {
  addOpen.value = false
}

function saveAdd() {
  const f = addForm.value
  if (!f.name?.trim() || !f.employeeId?.trim()) {
    showToast('请填写姓名与工号')
    return
  }
  if (teachers.value.some((x) => x.employeeId === f.employeeId.trim())) {
    showToast('工号已存在')
    return
  }
  const id = Math.max(0, ...teachers.value.map((x) => x.id)) + 1
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const lastActive = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
  const avatars = ['avatar-blue', 'avatar-green', 'avatar-orange']
  teachers.value.unshift({
    id,
    name: f.name.trim(),
    employeeId: f.employeeId.trim(),
    department: f.department.trim() || '未分配',
    role: f.role,
    lastActive,
    status: f.status,
    avatarClass: avatars[id % 3]
  })
  currentPage.value = 1
  searchQuery.value = ''
  filterRole.value = ''
  filterStatus.value = ''
  showToast('已添加教师')
  closeAdd()
}
</script>

<template>
  <div class="admin-page">
    <div v-if="toast" class="toast" role="status">{{ toast }}</div>



    <section class="charts-section" aria-label="用户数据概览">
      <div class="charts-row">
        <div class="charts-summary">
          <span>总教师 <strong>{{ totalTeachersStat }}</strong></span>
          <span>已激活 <strong class="sum-ok">{{ activeCount }}</strong></span>
          <span>待审核 <strong class="sum-pending">{{ pendingCount }}</strong></span>
          <span>当前在线 <strong class="sum-online">42</strong></span>
        </div>
        <div ref="chartRoleRef" class="chart-el" role="img" aria-label="按系统角色人数柱状图" />
        <div ref="chartStatusRef" class="chart-el" role="img" aria-label="账号状态占比饼图" />
      </div>
    </section>

    <section class="table-card">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon" aria-hidden="true">🔍</span>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="搜索教师姓名、工号或所属部门"
            autocomplete="off"
          />
        </div>
        <div class="toolbar-actions">
          <select v-model="filterRole" class="filter-select" aria-label="按角色筛选">
            <option value="">全部角色</option>
            <option v-for="r in ROLE_OPTIONS" :key="r" :value="r">{{ r }}</option>
          </select>
          <select v-model="filterStatus" class="filter-select" aria-label="按账号状态筛选">
            <option value="">账号状态</option>
            <option value="active">已激活</option>
            <option value="pending">待审核</option>
            <option value="disabled">已禁用</option>
          </select>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>教师姓名</th>
            <th>工号</th>
            <th>所属部门</th>
            <th>系统角色</th>
            <th>最近活跃时间</th>
            <th>状态</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="pagedTeachers.length === 0">
            <td colspan="7" class="empty-cell">没有匹配的教师，请调整搜索或筛选条件。</td>
          </tr>
          <tr v-for="t in pagedTeachers" :key="t.id">
            <td>
              <div class="user-cell">
                <span class="user-avatar" :class="t.avatarClass">{{ surnameOf(t.name) }}</span>
                <span class="user-name">{{ t.name }}</span>
              </div>
            </td>
            <td>{{ t.employeeId }}</td>
            <td>{{ t.department }}</td>
            <td><span class="role-tag">{{ t.role }}</span></td>
            <td>{{ t.lastActive }}</td>
            <td>
              <span v-if="t.status === 'active'" class="status-tag ok">已激活</span>
              <span v-else-if="t.status === 'pending'" class="status-tag pending">待审核</span>
              <span v-else class="status-tag disabled">已停用</span>
            </td>
            <td class="col-actions">
              <button type="button" class="icon-btn" title="编辑" @click="openEdit(t)">✏️</button>
              <button type="button" class="icon-btn danger" title="删除" @click="openDelete(t)">⛔</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <span class="footer-text">显示 {{ rangeText }} 条，共 {{ totalFiltered }} 条教师记录</span>
        <div class="pagination">
          <button type="button" class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">‹</button>
          <template v-for="p in paginationPages" :key="`pg-${p}`">
            <button
              type="button"
              class="page-btn"
              :class="{ active: p === currentPage }"
              @click="goPage(p)"
            >
              {{ p }}
            </button>
          </template>
          <span v-if="totalPages > (paginationPages[paginationPages.length - 1] || 0)" class="page-ellipsis">…</span>
          <button type="button" class="page-btn" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">›</button>
        </div>
      </div>
    </section>

    <!-- 编辑 -->
    <div v-if="editOpen" class="modal-overlay" role="dialog" aria-modal="true" @click.self="closeEdit">
      <div class="modal">
        <h2 class="modal-title">编辑教师</h2>
        <div class="modal-body">
          <label class="field">
            <span>姓名</span>
            <input v-model="editForm.name" type="text" />
          </label>
          <label class="field">
            <span>工号</span>
            <input v-model="editForm.employeeId" type="text" />
          </label>
          <label class="field">
            <span>所属部门</span>
            <input v-model="editForm.department" type="text" />
          </label>
          <label class="field">
            <span>系统角色</span>
            <select v-model="editForm.role">
              <option v-for="r in ROLE_OPTIONS" :key="r" :value="r">{{ r }}</option>
            </select>
          </label>
          <label class="field">
            <span>最近活跃时间</span>
            <input v-model="editForm.lastActive" type="text" placeholder="如 2026-04-08 09:15" />
          </label>
          <label class="field">
            <span>账号状态</span>
            <select v-model="editForm.status">
              <option value="active">已激活</option>
              <option value="pending">待审核</option>
              <option value="disabled">已停用</option>
            </select>
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn ghost" @click="closeEdit">取消</button>
          <button type="button" class="btn primary" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除确认 -->
    <div v-if="deleteOpen" class="modal-overlay" role="dialog" aria-modal="true" @click.self="closeDelete">
      <div class="modal modal-sm">
        <h2 class="modal-title">确认删除</h2>
        <p class="modal-text">
          确定删除教师「{{ deleting?.name }}」（{{ deleting?.employeeId }}）？此操作在本页为本地数据删除，无法撤销。
        </p>
        <div class="modal-actions">
          <button type="button" class="btn ghost" @click="closeDelete">取消</button>
          <button type="button" class="btn danger" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>

    <!-- 新增 -->
    <div v-if="addOpen" class="modal-overlay" role="dialog" aria-modal="true" @click.self="closeAdd">
      <div class="modal">
        <h2 class="modal-title">新增教师</h2>
        <div class="modal-body">
          <label class="field">
            <span>姓名</span>
            <input v-model="addForm.name" type="text" />
          </label>
          <label class="field">
            <span>工号</span>
            <input v-model="addForm.employeeId" type="text" />
          </label>
          <label class="field">
            <span>所属部门</span>
            <input v-model="addForm.department" type="text" placeholder="可选" />
          </label>
          <label class="field">
            <span>系统角色</span>
            <select v-model="addForm.role">
              <option v-for="r in ROLE_OPTIONS" :key="r" :value="r">{{ r }}</option>
            </select>
          </label>
          <label class="field">
            <span>账号状态</span>
            <select v-model="addForm.status">
              <option value="active">已激活</option>
              <option value="pending">待审核</option>
              <option value="disabled">已停用</option>
            </select>
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn ghost" @click="closeAdd">取消</button>
          <button type="button" class="btn primary" @click="saveAdd">添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  flex: 1;
  min-height: 100%;
  padding: 15px 32px 32px;
  background: #f4f7fb;
  position: relative;
}

.toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  padding: 10px 18px;
  border-radius: 10px;
  background: #0f172a;
  color: #fff;
  font-size: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
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
  padding: 10px 18px;
  background: #2563eb;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.charts-section {
  margin-bottom: 14px;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  padding: 14px 16px 16px;
}

.charts-summary {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0;
  margin: 0 16px 0 0;
  height: 100%;
  padding: 6px 0;
  font-size: 16px;
  color: #64748b;
}

.charts-summary strong {
  color: #0f172a;
  font-weight: 700;
  font-size: 22px;
}

.charts-summary .sum-ok {
  color: #16a34a;
}

.charts-summary .sum-pending {
  color: #ea580c;
}

.charts-summary .sum-online {
  color: #16a34a;
}

.charts-row {
  display: grid;
  grid-template-columns: auto 1.15fr 0.85fr;
  align-items: stretch;
  gap: 12px;
  min-height: 0;
}

.chart-el {
  width: 100%;
  height:185px;
  min-height: 185px;
  min-width: 0;
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

.empty-cell {
  text-align: center;
  color: #94a3b8;
  padding: 24px !important;
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

.role-tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 12px;
}

.status-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
}

.status-tag.ok {
  background: #dcfce7;
  color: #15803d;
}

.status-tag.pending {
  background: #fef9c3;
  color: #a16207;
}

.status-tag.disabled {
  background: #fee2e2;
  color: #b91c1c;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  margin-left: 4px;
}

.icon-btn.danger:hover {
  opacity: 0.85;
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
  flex-wrap: wrap;
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

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.page-ellipsis {
  font-size: 12px;
  color: #9ca3af;
  padding: 0 2px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal {
  width: 100%;
  max-width: 440px;
  background: #fff;
  border-radius: 16px;
  padding: 20px 22px 18px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
}

.modal-sm {
  max-width: 400px;
}

.modal-title {
  margin: 0 0 14px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.modal-text {
  margin: 0 0 18px;
  font-size: 14px;
  color: #475569;
  line-height: 1.5;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #64748b;
}

.field input,
.field select {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
  color: #0f172a;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn {
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn.primary {
  background: #2563eb;
  color: #fff;
}

.btn.ghost {
  background: #f1f5f9;
  color: #334155;
}

.btn.danger {
  background: #dc2626;
  color: #fff;
}

@media (max-width: 1100px) {
  .admin-page { padding: 20px 20px 24px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .charts-row { grid-template-columns: 1fr; }
  .table-toolbar { flex-direction: column; align-items: stretch; }
}

@media (max-width: 720px) {
  .admin-page { padding: 16px 12px 20px; }
  .page-title { font-size: 20px; }
  .chart-el { height: 260px; }
  .table-card { padding: 12px; overflow-x: auto; }
  .data-table { min-width: 680px; font-size: 13px; }
  .table-footer { flex-direction: column; gap: 8px; align-items: flex-start; }
}

@media (max-width: 480px) {
  .admin-page { padding: 12px 10px 16px; }
  .page-title { font-size: 18px; }
}
</style>
