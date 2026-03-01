<script setup>
import { ref, computed, inject, watch } from 'vue'
import { useUserStore } from '../stores/user'
import { useCoursewareStore } from '../stores/courseware'

const userStore = useUserStore()
const coursewareStore = useCoursewareStore()
const openLoginModal = inject('openLoginModal', null)
const activeSideItem = ref('profile')
const sidebarCollapsed = ref(false)
const favoriteFilter = ref('all')
const viewMode = ref('grid')
const currentPage = ref(1)
const itemsPerPage = 8 // 4列 x 2行
const showPasswordModal = ref(false)
const show2FAModal = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showCurrentPwd = ref(false)
const showNewPwd = ref(false)
const showConfirmPwd = ref(false)
const twoFACode = ref(['', '', '', '', '', ''])
const resendCountdown = ref(59)

const sideItems = [
  { id: 'profile', label: '个人信息', icon: '👤' },
  { id: 'security', label: '账号安全', icon: '🔒' },
  { id: 'favorites', label: '我的收藏', icon: '❤️' }
]

const favoritesList = computed(() => coursewareStore.favoritedList)

const favoriteFilters = computed(() => {
  const list = favoritesList.value
  return [
    { id: 'all', label: '全部', count: list.length },
    { id: 'pdf', label: 'PDF', count: list.filter(i => i.type === 'pdf').length },
    { id: 'ppt', label: 'PPT', count: list.filter(i => i.type === 'ppt').length },
    { id: 'video', label: '视频', count: list.filter(i => i.type === 'video').length },
    { id: 'word', label: 'Word', count: list.filter(i => i.type === 'word').length }
  ]
})

const filteredFavorites = computed(() => {
  const list = favoritesList.value
  if (favoriteFilter.value === 'all') return list
  return list.filter(i => i.type === favoriteFilter.value)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredFavorites.value.length / itemsPerPage)))

const paginatedFavorites = computed(() => {
  const list = filteredFavorites.value
  const start = (currentPage.value - 1) * itemsPerPage
  return list.slice(start, start + itemsPerPage)
})

function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) currentPage.value = page
}

watch([favoriteFilter, filteredFavorites], () => {
  currentPage.value = 1
})

function getTypeTag(type) {
  const map = { pdf: 'PDF', ppt: 'PPT', video: '视频', word: 'Word' }
  return map[type] || type
}

function getTypeTagClass(type) {
  const map = { pdf: 'tag-pdf', ppt: 'tag-ppt', video: 'tag-video', word: 'tag-word' }
  return map[type] || ''
}

function getThumbnailBg(type) {
  const map = {
    pdf: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
    ppt: 'linear-gradient(135deg, #fed7aa 0%, #fdba74 100%)',
    video: 'linear-gradient(135deg, #bfdbfe 0%, #93c5fd 100%)',
    word: 'linear-gradient(135deg, #93c5fd 0%, #60a5fa 100%)'
  }
  return map[type] || '#f1f5f9'
}

function toggleFavorite(item) {
  coursewareStore.toggleFavorite(item.id)
}

const loginHistory = [
  { device: 'MacBook Pro / Chrome', location: '芝加哥，美国', ip: '192.168.1.45', time: '刚刚', status: '成功' },
  { device: 'iPhone 14 / Safari', location: '芝加哥，美国', ip: '172.56.21.90', time: '2 小时前', status: '成功' },
  { device: 'Windows PC / Edge', location: '芝加哥，美国', ip: '10.0.42.115', time: '昨天 14:20', status: '成功' }
]

function logout() {
  userStore.logout()
}

const passwordStrength = computed(() => {
  const p = newPassword.value
  if (!p) return { level: 0, label: '弱' }
  let score = 0
  if (p.length >= 8) score++
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score++
  if (/\d/.test(p)) score++
  if (/[^a-zA-Z0-9]/.test(p)) score++
  if (p.length >= 12) score++
  const labels = ['弱', '弱', '中', '强', '强']
  return { level: Math.min(score, 4), label: labels[Math.min(score, 4)] }
})

function openPasswordModal() {
  showPasswordModal.value = true
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
}

function open2FAModal() {
  show2FAModal.value = true
  twoFACode.value = ['', '', '', '', '', '']
  resendCountdown.value = 59
}

function on2FACodeInput(index, e) {
  const val = e.target.value.replace(/\D/g, '').slice(-1)
  const arr = [...twoFACode.value]
  arr[index] = val
  twoFACode.value = arr
  if (val && index < 5) {
    const next = e.target.nextElementSibling
    if (next) next.focus()
  }
}

function on2FACodeKeydown(index, e) {
  if (e.key === 'Backspace' && !twoFACode.value[index] && index > 0) {
    const prev = e.target.previousElementSibling
    if (prev) prev.focus()
  }
}
</script>

<template>
  <div class="personal-page">
    <div v-if="userStore.isLoggedIn" class="personal-layout">
      <div class="main-layout">
        <!-- 左侧导航 -->
        <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
          <div class="sidebar-header">
            <button type="button" class="sidebar-toggle" title="伸缩侧栏" @click="sidebarCollapsed = !sidebarCollapsed" aria-label="伸缩侧栏">
              <svg class="toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="4" x2="12" y2="20"/>
                <path d="M8 9l-3 3 3 3"/>
                <path d="M16 9l3 3-3 3"/>
              </svg>
            </button>
          </div>
          <nav class="side-nav">
            <button
              v-for="item in sideItems"
              :key="item.id"
              class="side-item"
              :class="{ active: activeSideItem === item.id }"
              @click="activeSideItem = item.id"
            >
              <span class="side-icon">{{ item.icon }}</span>
              <span class="side-label">{{ item.label }}</span>
            </button>
            <button class="side-item sign-out" @click="logout">
              <span class="side-icon">🚪</span>
              <span class="side-label">退出登录</span>
            </button>
          </nav>

          <!-- 安全强度（仅账号安全页显示） -->
          <div v-if="activeSideItem === 'security'" class="security-strength-card">
            <h4 class="strength-title">安全强度</h4>
            <div class="progress-bar">
              <div class="progress-fill" style="width: 75%"></div>
            </div>
            <p class="strength-text">您的账号安全状况良好。开启双重认证可进一步提升安全性。</p>
          </div>

          <!-- 快捷筛选（仅收藏页显示） -->
          <div v-if="activeSideItem === 'favorites'" class="quick-filters">
            <h4 class="filters-title">快捷筛选</h4>
            <button
              v-for="f in favoriteFilters"
              :key="f.id"
              class="filter-item"
              :class="{ active: favoriteFilter === f.id }"
              @click="favoriteFilter = f.id"
            >
              {{ f.label }} ({{ f.count }})
            </button>
          </div>
        </aside>

        <!-- 主内容区 -->
        <main class="main-content">
          <!-- 个人信息 -->
          <div v-if="activeSideItem === 'profile'" class="content-panel">

            <div class="profile-header-row">
              <div class="profile-avatar">
                {{ userStore.userInfo?.name?.[0] || '用' }}
              </div>
              <div class="profile-info">
                <h2 class="profile-name">{{ userStore.userInfo?.name || userStore.userInfo?.phone || '用户' }}</h2>
                <p class="profile-title">高级数学教师 | 10-12年级</p>
              </div>
              <button class="change-photo-btn">📷 更换照片</button>
            </div>

            <div class="form-grid">
              <div class="form-group">
                <label>姓名</label>
                <input type="text" :value="userStore.userInfo?.name || userStore.userInfo?.phone || '未设置'" />
              </div>
              <div class="form-group">
                <label>任教科目</label>
                <select>
                  <option>数学</option>
                  <option>物理</option>
                  <option>化学</option>
                  <option>语文</option>
                </select>
              </div>
              <div class="form-group">
                <label>学校名称</label>
                <input type="text" value="北景国际学院" />
              </div>
              <div class="form-group">
                <label>邮箱</label>
                <input type="text" :value="userStore.userInfo?.email || '未绑定'" />
              </div>
              <div class="form-group">
                <label>手机号</label>
                <input type="text" :value="userStore.userInfo?.phone || '未绑定'" />
              </div>
              <div class="form-group">
                <label>工号</label>
                <input type="text" value="EDU-94823" readonly class="readonly" />
              </div>
            </div>

            <div class="form-group full">
              <label>专业简介</label>
              <textarea rows="4">专注数学教育15年，主攻高等微积分与统计建模。目前负责 STEM 课程数字化转型。</textarea>
            </div>

            <div class="action-buttons">
              <button class="cancel-btn">取消</button>
              <button class="save-btn">保存修改</button>
            </div>
          </div>

          <!-- 账号安全 -->
          <div v-if="activeSideItem === 'security'" class="content-panel">

            <div class="setting-block setting-block-row">
              <div class="block-icon">🔒</div>
              <div class="block-content">
                <h4>登录密码</h4>
                <p>显示现在密码</p>
              </div>
              <button class="outline-btn" @click="openPasswordModal">修改密码</button>
            </div>

            <div class="setting-block">
              <div class="block-icon">👥</div>
              <div class="block-content">
                <h4>关联联系方式</h4>
                <div class="contact-row">
                  <div class="contact-item">
                    <span class="contact-label">邮箱</span>
                    <span class="contact-value">j.smith@northview.edu</span>
                    <a href="#" class="link-btn primary">更换</a>
                  </div>
                  <div class="contact-item">
                    <span class="contact-label">手机号</span>
                    <span class="contact-value">+1 (555) ....78</span>
                    <a href="#" class="link-btn primary">管理</a>
                  </div>
                </div>
              </div>
            </div>

            <div class="setting-block setting-block-row">
              <div class="block-icon">🛡️</div>
              <div class="block-content">
                <h4>双重认证 (2FA) <span class="disabled-tag">未开启</span></h4>
                <p>通过邮箱验证码为账号增加一层安全保护。</p>
              </div>
              <button class="primary-btn" @click="open2FAModal">开启 2FA</button>
            </div>

            <div class="setting-block">
              <div class="block-content full-width">
                <div class="block-header-row">
                  <h4>登录历史</h4>
                  <a href="#" class="link-btn primary">查看全部活动</a>
                </div>
                <table class="history-table">
                  <thead>
                    <tr>
                      <th>设备与浏览器</th>
                      <th>位置</th>
                      <th>IP 地址</th>
                      <th>时间</th>
                      <th>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, i) in loginHistory" :key="i">
                      <td>{{ row.device }}</td>
                      <td>{{ row.location }}</td>
                      <td>{{ row.ip }}</td>
                      <td>{{ row.time }}</td>
                      <td><span class="status-ok">{{ row.status }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- 我的收藏 -->
          <div v-if="activeSideItem === 'favorites'" class="content-panel">
            <div class="panel-header favorites-header">
              <div class="header-actions">
                <div class="view-toggles">
                  <button class="view-btn" :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'">⊞</button>
                  <button class="view-btn" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">☰</button>
                </div>
                <select class="sort-select">
                  <option>按最近排序</option>
                </select>
              </div>
            </div>

            <div class="favorites-grid" :class="viewMode">
              <div v-for="item in paginatedFavorites" :key="item.id" class="favorite-card courseware-style">
                <div class="card-thumbnail" :style="{ background: getThumbnailBg(item.type) }">
                  <span :class="['type-tag', getTypeTagClass(item.type)]">{{ getTypeTag(item.type) }}</span>
                </div>
                <div class="card-body">
                  <div class="card-header-row">
                    <h3 class="card-title">{{ item.name }}</h3>
                    <button class="card-menu">⋮</button>
                  </div>
                  <p class="card-subject">{{ item.subject }} · {{ item.grade }}</p>
                  <div class="card-footer-row">
                    <p class="card-meta">🕐 {{ item.modifyDate }} · {{ item.size }}</p>
                    <button
                      class="favorite-btn favorited"
                      @click.stop="toggleFavorite(item)"
                      title="取消收藏"
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1" stroke-linejoin="round" stroke-linecap="round">
                        <path d="M12 2l2.4 7.4H22l-6 4.6 2.3 7.4L12 17.8l-6.3 4.6 2.3-7.4-6-4.6h7.6L12 2z"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="totalPages > 1" class="pagination">
              <button type="button" class="page-btn" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">‹</button>
              <button
                v-for="p in totalPages"
                :key="p"
                type="button"
                class="page-btn"
                :class="{ active: currentPage === p }"
                @click="goToPage(p)"
              >
                {{ p }}
              </button>
              <button type="button" class="page-btn" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">›</button>
            </div>
          </div>
        </main>
      </div>
    </div>

    <div v-else class="login-prompt">
      <p>请先登录</p>
      <button class="login-redirect" @click="openLoginModal?.()">前往登录</button>
    </div>

    <!-- 修改密码弹框 -->
    <Teleport to="body">
      <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
        <div class="modal-box password-modal">
          <div class="modal-header">
            <h3>修改密码</h3>
            <button class="modal-close" @click="showPasswordModal = false">×</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>当前密码</label>
              <div class="input-wrap">
                <input v-model="currentPassword" :type="showCurrentPwd ? 'text' : 'password'" placeholder="请输入当前密码" />
                <button type="button" class="eye-btn" @click="showCurrentPwd = !showCurrentPwd">{{ showCurrentPwd ? '🙈' : '👁' }}</button>
              </div>
            </div>
            <div class="form-group">
              <label>新密码</label>
              <div class="input-wrap">
                <input v-model="newPassword" :type="showNewPwd ? 'text' : 'password'" placeholder="至少 8 个字符" />
                <button type="button" class="eye-btn" @click="showNewPwd = !showNewPwd">{{ showNewPwd ? '🙈' : '👁' }}</button>
              </div>
            </div>
            <div class="strength-bar">
              <span class="strength-label">强度：{{ passwordStrength.label }}</span>
              <div class="strength-track">
                <div class="strength-fill" :style="{ width: (passwordStrength.level / 4 * 100) + '%' }"></div>
              </div>
            </div>
            <div class="form-group">
              <label>确认新密码</label>
              <div class="input-wrap">
                <input v-model="confirmPassword" :type="showConfirmPwd ? 'text' : 'password'" placeholder="请再次输入新密码" />
                <button type="button" class="eye-btn" @click="showConfirmPwd = !showConfirmPwd">{{ showConfirmPwd ? '🙈' : '👁' }}</button>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="cancel-btn" @click="showPasswordModal = false">取消</button>
            <button class="save-btn">更新密码</button>
          </div>
        </div>
      </div>

      <!-- 2FA 验证弹框 -->
      <div v-if="show2FAModal" class="modal-overlay" @click.self="show2FAModal = false">
        <div class="modal-box twofa-modal">
          <div class="modal-header">
            <h3>邮件 2FA 验证</h3>
            <button class="modal-close" @click="show2FAModal = false">×</button>
          </div>
          <div class="modal-body">
            <div class="twofa-icon">✉️ ✓</div>
            <h4 class="twofa-title">请查收您的邮件</h4>
            <p class="twofa-desc">验证码已发送到您注册的邮箱 (t***@school.edu)</p>
            <div class="code-inputs">
              <input
                v-for="(_, i) in 6"
                :key="i"
                :value="twoFACode[i]"
                type="text"
                inputmode="numeric"
                maxlength="1"
                class="code-input"
                @input="on2FACodeInput(i, $event)"
                @keydown="on2FACodeKeydown(i, $event)"
              />
            </div>
            <p class="resend-text">
              未收到验证码？
              <a href="#" class="resend-link">重新发送验证码</a>
              <span class="countdown">(0:{{ String(resendCountdown).padStart(2, '0') }})</span>
            </p>
          </div>
          <div class="modal-footer">
            <button class="cancel-btn" @click="show2FAModal = false">返回</button>
            <button class="save-btn">验证并启用 →</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.personal-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.personal-layout {
  flex: 1;
  padding: 24px;
}

.main-layout {
  display: flex;
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.sidebar {
  width: 220px;
  min-width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  transition: width 0.2s, min-width 0.2s;
}

.sidebar.collapsed {
  width: 56px;
  min-width: 56px;
}

.sidebar-header {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 10px;
  margin-bottom: 8px;
}

.sidebar-toggle {
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: transparent;
  color: #475569;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-toggle:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.sidebar .toggle-icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s;
}

.sidebar.collapsed .toggle-icon {
  transform: rotate(180deg);
}

.sidebar.collapsed .side-label {
  overflow: hidden;
  width: 0;
  opacity: 0;
  white-space: nowrap;
}

.sidebar.collapsed .side-nav {
  padding: 12px 8px;
}

.sidebar.collapsed .side-item {
  padding: 10px;
  justify-content: center;
}

.sidebar.collapsed .security-strength-card,
.sidebar.collapsed .quick-filters {
  padding: 12px 8px;
}

.sidebar.collapsed .security-strength-card h4,
.sidebar.collapsed .security-strength-card p,
.sidebar.collapsed .quick-filters h4,
.sidebar.collapsed .quick-filters .filter-item {
  display: none;
}

.side-nav {
  background: #fff;
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
}

.side-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  border-radius: 8px;
  text-align: left;
  transition: all 0.2s;
}

.side-item:hover {
  background: #f1f5f9;
}

.side-item.active {
  background: #eff6ff;
  color: #3b82f6;
  font-weight: 500;
}

.side-item.sign-out {
  color: #dc2626;
}

.side-item.sign-out:hover {
  background: #fef2f2;
}

.side-icon {
  font-size: 1rem;
}

.security-strength-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.strength-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 10px;
}

.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e 0%, #4ade80 100%);
  border-radius: 4px;
}

.strength-text {
  font-size: 0.8rem;
  color: #64748b;
}

.quick-filters {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.filters-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.filter-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  border-radius: 6px;
  text-align: left;
  margin-bottom: 4px;
}

.filter-item:hover,
.filter-item.active {
  background: #eff6ff;
  color: #3b82f6;
}

.main-content {
  flex: 1;
  min-width: 0;
}

.content-panel {
  background: #fff;
  padding: 32px;
}

.panel-header {
  margin-bottom: 28px;
}

.panel-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px;
}

.panel-subtitle {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.profile-header-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 28px;
}

.profile-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  color: #fff;
  font-size: 2rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.profile-info {
  flex: 1;
}

.profile-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 4px;
}

.profile-title {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.change-photo-btn {
  padding: 10px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  flex-shrink: 0;
}

.change-photo-btn:hover {
  background: #f8fafc;
}

.link-btn {
  font-size: 14px;
  text-decoration: none;
  cursor: pointer;
}

.link-btn.primary {
  color: #3b82f6;
}

.link-btn.danger {
  color: #dc2626;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 24px;
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group.full {
  grid-column: 1 / -1;
  margin-bottom: 20px;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.form-group input.readonly {
  background: #f8fafc;
  color: #94a3b8;
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn {
  padding: 10px 24px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.save-btn {
  padding: 10px 24px;
  background: #3b82f6;
  border: none;
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.setting-block {
  display: flex;
  gap: 20px;
  padding: 24px 0;
  border-bottom: 1px solid #f1f5f9;
}

.setting-block:last-of-type {
  border-bottom: none;
}

.setting-block-row {
  align-items: center;
}

.setting-block-row .block-content {
  flex: 1;
}

.setting-block-row .block-content p {
  margin-bottom: 0;
}

.setting-block-row .outline-btn,
.setting-block-row .primary-btn {
  flex-shrink: 0;
}

.block-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.block-content {
  flex: 1;
}

.block-content.full-width {
  width: 100%;
}

.block-content h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 6px;
}

.block-content p {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0 0 12px;
}

.disabled-tag {
  font-size: 0.8rem;
  font-weight: 400;
  color: #94a3b8;
}

.outline-btn {
  padding: 8px 16px;
  border: 1px solid #3b82f6;
  background: transparent;
  color: #3b82f6;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.primary-btn {
  padding: 8px 16px;
  border: none;
  background: #3b82f6;
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.block-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.block-header-row h4 {
  margin: 0;
}

.contact-row {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.contact-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  width: 80px;
}

.contact-value {
  flex: 1;
  font-size: 0.9rem;
  color: #1e293b;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.history-table th,
.history-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #f1f5f9;
}

.history-table th {
  font-weight: 600;
  color: #64748b;
}

.status-ok {
  color: #22c55e;
}

.favorites-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.view-toggles {
  display: flex;
  gap: 4px;
}

.view-btn {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
}

.view-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.sort-select {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.favorites-grid.list {
  grid-template-columns: 1fr;
}

.favorites-grid.list .favorite-card.courseware-style {
  flex-direction: row;
}

.favorites-grid.list .favorite-card.courseware-style .card-thumbnail {
  width: 120px;
  height: 90px;
  flex-shrink: 0;
}

.favorite-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #f1f5f9;
  transition: box-shadow 0.2s;
}

.favorite-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.favorite-card.courseware-style {
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.favorite-card.courseware-style .card-thumbnail {
  height: 140px;
  position: relative;
}

.favorite-card.courseware-style .type-tag {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}

.favorite-card.courseware-style .tag-pdf { background: #fecaca; color: #b91c1c; }
.favorite-card.courseware-style .tag-ppt { background: #fed7aa; color: #c2410c; }
.favorite-card.courseware-style .tag-video { background: #bfdbfe; color: #1d4ed8; }
.favorite-card.courseware-style .tag-word { background: #93c5fd; color: #1d4ed8; }

.favorite-card.courseware-style .card-body {
  padding: 16px;
}

.favorite-card.courseware-style .card-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.favorite-card.courseware-style .card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.favorite-card.courseware-style .card-menu {
  padding: 4px;
  border: none;
  background: transparent;
  font-size: 1rem;
  color: #94a3b8;
  cursor: pointer;
  flex-shrink: 0;
}

.favorite-card.courseware-style .card-subject {
  font-size: 0.8rem;
  color: #64748b;
  margin: 6px 0 4px;
}

.favorite-card.courseware-style .card-footer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.favorite-card.courseware-style .card-meta {
  font-size: 0.75rem;
  color: #94a3b8;
  margin: 0;
}

.favorite-card.courseware-style .favorite-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #eab308;
  cursor: pointer;
  transition: all 0.2s;
}

.favorite-card.courseware-style .favorite-btn:hover {
  background: #fef3c7;
}

.card-color-bar {
  height: 80px;
  position: relative;
}

.card-type-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 0.7rem;
  font-weight: 600;
  color: #475569;
}

.heart-icon {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 1rem;
}

.card-icon-large {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin: -24px 16px 0;
  position: relative;
  z-index: 1;
}

.favorite-card .card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
  margin: 12px 16px 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-date {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0 16px 12px;
}

.view-link {
  display: inline-block;
  margin: 0 16px 16px;
  font-size: 0.85rem;
  color: #3b82f6;
  text-decoration: none;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.page-btn {
  padding: 8px 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
}

.page-btn:hover:not(:disabled) {
  border-color: #cbd5e1;
  color: #1e293b;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.login-prompt {
  text-align: center;
  padding: 80px 24px;
  color: #64748b;
  flex: 1;
}

.login-redirect {
  margin-top: 16px;
  padding: 10px 24px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  width: 420px;
  max-width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.modal-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 1.5rem;
  color: #94a3b8;
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  padding: 24px;
}

.modal-body .form-group {
  margin-bottom: 16px;
}

.modal-body .form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  display: block;
  margin-bottom: 6px;
}

.modal-body .form-group:last-of-type {
  margin-bottom: 0;
}

.input-wrap {
  position: relative;
  display: flex;
}

.input-wrap input {
  flex: 1;
  padding: 10px 44px 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.eye-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  font-size: 1rem;
  cursor: pointer;
}

.strength-bar {
  margin: 12px 0 20px;
}

.strength-label {
  font-size: 0.75rem;
  color: #64748b;
  display: block;
  margin-bottom: 6px;
}

.strength-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%);
  border-radius: 3px;
  transition: width 0.2s;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
}

.twofa-modal .modal-body {
  text-align: center;
}

.twofa-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.twofa-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 8px;
}

.twofa-desc {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0 0 24px;
}

.code-inputs {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 20px;
}

.code-input {
  width: 44px;
  height: 48px;
  text-align: center;
  font-size: 1.25rem;
  font-weight: 600;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.code-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.resend-text {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.resend-link {
  color: #3b82f6;
  text-decoration: none;
  margin: 0 4px;
}

.countdown {
  color: #94a3b8;
}

@media (max-width: 900px) {
  .main-layout {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .favorites-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .favorites-grid {
    grid-template-columns: 1fr;
  }
}
</style>
