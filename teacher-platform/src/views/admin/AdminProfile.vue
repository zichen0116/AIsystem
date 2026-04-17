<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

/** 与后端 /auth/me 的 User 对齐：手机号即登录账号 */
function profileFromUser(u) {
  if (!u) {
    return {
      name: '管理员',
      email: '',
      phone: '',
      title: '系统管理员',
    }
  }
  const name = (u.full_name && String(u.full_name).trim()) || '管理员'
  return {
    name,
    email: (u.email && String(u.email).trim()) || '',
    phone: (u.phone && String(u.phone).trim()) || '',
    title: '系统管理员',
  }
}

const profileForm = ref(profileFromUser(null))

watch(
  () => userStore.userInfo,
  (u) => {
    profileForm.value = profileFromUser(u)
  },
  { immediate: true, deep: true }
)

const editOpen = ref(false)
const securityOpen = ref(false)
const editDraft = ref({ ...profileForm.value })
const pwdForm = ref({
  oldPwd: '',
  newPwd: '',
  confirmPwd: ''
})

const avatarLetter = computed(() => profileForm.value.name.slice(0, 1).toUpperCase())

function openEdit() {
  const u = userStore.userInfo
  editDraft.value = {
    ...profileForm.value,
    phone: u?.phone != null && String(u.phone).trim() !== '' ? String(u.phone).trim() : profileForm.value.phone,
  }
  editOpen.value = true
}

function closeEdit() {
  editOpen.value = false
}

function saveProfile() {
  if (!editDraft.value.name.trim()) return
  profileForm.value = {
    ...editDraft.value,
    name: editDraft.value.name.trim(),
    email: editDraft.value.email.trim(),
    phone: editDraft.value.phone.trim(),
    title: editDraft.value.title.trim()
  }
  closeEdit()
}

function openSecurity() {
  pwdForm.value = { oldPwd: '', newPwd: '', confirmPwd: '' }
  securityOpen.value = true
}

function closeSecurity() {
  securityOpen.value = false
}

function saveSecurity() {
  if (!pwdForm.value.oldPwd || !pwdForm.value.newPwd) return
  if (pwdForm.value.newPwd !== pwdForm.value.confirmPwd) return
  closeSecurity()
}

async function handleLogout() {
  await userStore.logout()
  router.push('/')
}
</script>

<template>
  <div class="admin-profile-page">
    <main class="main">
      <!-- 顶部个人信息 -->
      <section class="profile-header">
        <div class="profile-main">
          <div class="avatar-wrap">
            <div class="avatar-circle">{{ avatarLetter }}</div>
          </div>
          <div class="profile-text">
            <h1 class="profile-name">{{ profileForm.name }}</h1>
            <p class="profile-role">{{ profileForm.title }}</p>
          </div>
        </div>
        <div class="profile-actions">
          <button type="button" class="btn secondary" @click="openSecurity">账号安全</button>
          <button type="button" class="btn primary" @click="openEdit">编辑资料</button>
        </div>
      </section>

      <!-- 关键指标 -->
      <section class="stats-row">
        <div class="stat-card">
          <p class="stat-label">管理教师数</p>
          <p class="stat-value">1,240</p>
          <p class="stat-trend positive">+12% 较上月</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">已上传资源</p>
          <p class="stat-value">8,432</p>
          <p class="stat-trend positive">+5% 本周增长</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">系统健康度</p>
          <p class="stat-value">99.9%</p>
          <p class="stat-tag">所有服务正常</p>
        </div>
        <div class="stat-card">
          <p class="stat-label">活跃用户</p>
          <p class="stat-value">452</p>
          <p class="stat-trend positive">+8% 实时在线</p>
        </div>
      </section>

      <section class="content-grid">
        <!-- 左侧：最近活动 -->
        <section class="module-card">
          <div class="activity-header">
            <h2 class="section-title">最近活动</h2>
            <button type="button" class="link-btn">查看全部</button>
          </div>
          <ul class="activity-list">
            <li class="activity-item">
              <span class="dot dot-blue" />
              <div class="activity-text">
                <p class="activity-title">已审批 24 份新的教案</p>
                <p class="activity-sub">数学组 · 2 小时前</p>
              </div>
            </li>
            <li class="activity-item">
              <span class="dot dot-orange" />
              <div class="activity-text">
                <p class="activity-title">系统提醒：数据库备份告警</p>
                <p class="activity-sub">基础设施 · 5 小时前</p>
              </div>
            </li>
            <li class="activity-item">
              <span class="dot dot-green" />
              <div class="activity-text">
                <p class="activity-title">新增 5 个教师账号</p>
                <p class="activity-sub">用户管理 · 昨天</p>
              </div>
            </li>
            <li class="activity-item">
              <span class="dot dot-gray" />
              <div class="activity-text">
                <p class="activity-title">更新安全策略到版本 2.4</p>
                <p class="activity-sub">系统设置 · 2 天前</p>
              </div>
            </li>
            <li class="activity-item">
              <span class="dot dot-blue" />
              <div class="activity-text">
                <p class="activity-title">完成资源搜索模块 UI 调整</p>
                <p class="activity-sub">前端团队 · 3 天前</p>
              </div>
            </li>
            <li class="activity-item">
              <span class="dot dot-orange" />
              <div class="activity-text">
                <p class="activity-title">重启消息队列服务以恢复任务消费</p>
                <p class="activity-sub">运维中心 · 4 天前</p>
              </div>
            </li>
            <li class="activity-item">
              <span class="dot dot-green" />
              <div class="activity-text">
                <p class="activity-title">通过 3 个新的学校接入申请</p>
                <p class="activity-sub">渠道合作 · 上周</p>
              </div>
            </li>
          </ul>
        </section>

        <!-- 个人设置 -->
        <aside class="settings-card">
          <h2 class="section-title">个人设置</h2>
          <ul class="settings-list">
            <li class="settings-item">
              <div>
                <p class="settings-label">修改密码</p>
                <p class="settings-sub">最近一次修改：3 个月前</p>
              </div>
              <span class="settings-arrow">›</span>
            </li>
            <li class="settings-item">
              <div>
                <p class="settings-label">邮件通知</p>
                <p class="settings-sub">每周发送系统报告</p>
              </div>
              <span class="settings-switch on">开</span>
            </li>
            <li class="settings-item">
              <div>
                <p class="settings-label">两步验证</p>
                <p class="settings-sub">短信或验证器 App</p>
              </div>
              <span class="settings-switch off">关</span>
            </li>
            <li class="settings-item">
              <div>
                <p class="settings-label">当前会话</p>
                <p class="settings-sub">3 台设备已登录</p>
              </div>
              <span class="settings-arrow">›</span>
            </li>
          </ul>
          <button type="button" class="logout-btn" @click="handleLogout">退出登录</button>
        </aside>
      </section>
    </main>

    <div v-if="editOpen" class="modal-overlay" role="dialog" aria-modal="true" @click.self="closeEdit">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">编辑资料</h3>
          <button type="button" class="modal-close" @click="closeEdit">×</button>
        </div>
        <div class="modal-body">
          <label class="field">
            <span>姓名</span>
            <input v-model="editDraft.name" type="text" />
          </label>
          <label class="field">
            <span>邮箱</span>
            <input v-model="editDraft.email" type="email" />
          </label>
          <label class="field">
            <span>手机号</span>
            <input
              v-model="editDraft.phone"
              type="text"
              readonly
              class="input-readonly"
              title="与登录账号一致，如需更换请在账号安全中走手机号变更流程"
            />
          </label>
          <label class="field">
            <span>职务</span>
            <input v-model="editDraft.title" type="text" />
          </label>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secondary" @click="closeEdit">取消</button>
          <button type="button" class="btn primary" @click="saveProfile">保存</button>
        </div>
      </div>
    </div>

    <div v-if="securityOpen" class="modal-overlay" role="dialog" aria-modal="true" @click.self="closeSecurity">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">账号安全</h3>
          <button type="button" class="modal-close" @click="closeSecurity">×</button>
        </div>
        <div class="modal-body">
          <label class="field">
            <span>当前密码</span>
            <input v-model="pwdForm.oldPwd" type="password" />
          </label>
          <label class="field">
            <span>新密码</span>
            <input v-model="pwdForm.newPwd" type="password" />
          </label>
          <label class="field">
            <span>确认新密码</span>
            <input v-model="pwdForm.confirmPwd" type="password" />
          </label>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn secondary" @click="closeSecurity">取消</button>
          <button type="button" class="btn primary" @click="saveSecurity">更新密码</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-profile-page {
  flex: 1;
  min-height: 100%;
  padding: 24px 28px 28px;
  background: #f4f7fb;
}

.main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 22px 24px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
}

.profile-main {
  display: flex;
  gap: 16px;
  align-items: center;
}

.avatar-wrap {
  display: flex;
  align-items: center;
}

.avatar-circle {
  width: 70px;
  height: 70px;
  border-radius: 999px;
  background: #bfdbfe;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #1d4ed8;
}

.profile-text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.profile-name {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.profile-role {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.profile-actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.btn {
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 14px;
  cursor: pointer;
}

.btn.primary {
  border: none;
  background: #2563eb;
  color: #ffffff;
}

.btn.secondary {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #0f172a;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
}

.stat-label {
  margin: 0 0 4px;
  font-size: 15px;
  color: #64748b;
}

.stat-value {
  margin: 0 0 4px;
  font-size: 25px;
  font-weight: 700;
  color: #0f172a;
}

.stat-trend {
  margin: 0;
  font-size: 15px;
}

.stat-trend.positive {
  color: #16a34a;
}

.stat-tag {
  margin: 0;
  font-size: 15px;
  color: #0f766e;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(260px, 1.1fr);
  gap: 16px;
}

.module-card,
.settings-card {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 18px 18px 20px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.link-btn {
  border: none;
  background: transparent;
  font-size: 14px;
  color: #2563eb;
  cursor: pointer;
}

.activity-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin-top: 6px;
}

.dot-blue {
  background: #3b82f6;
}

.dot-orange {
  background: #f97316;
}

.dot-green {
  background: #16a34a;
}

.dot-gray {
  background: #9ca3af;
}

.activity-text {
  flex: 1;
}

.activity-title {
  margin: 0 0 2px;
  font-size: 15px;
  color: #0f172a;
}

.activity-sub {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

.settings-list {
  list-style: none;
  padding: 0;
  margin: 0 0 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.settings-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 6px;
  border-radius: 10px;
  background: #f8fafc;
}

.settings-label {
  margin: 0 0 2px;
  font-size: 16px;
  color: #0f172a;
}

.settings-sub {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
}

.settings-arrow {
  font-size: 16px;
  color: #9ca3af;
}

.settings-switch {
  font-size: 14px;
  padding: 2px 8px;
  border-radius: 999px;
}

.settings-switch.on {
  background: #dcfce7;
  color: #15803d;
}

.settings-switch.off {
  background: #fee2e2;
  color: #b91c1c;
}

.logout-btn {
  width: 100%;
  border-radius: 10px;
  border: none;
  padding: 10px 0;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  padding: 12px;
}

.modal {
  width: min(520px, 96vw);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.2);
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
  font-size: 17px;
  color: #0f172a;
}

.modal-close {
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: #64748b;
}

.modal-body {
  padding: 14px;
  display: grid;
  gap: 10px;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 14px;
  color: #334155;
}

.field input {
  border: 1px solid #dbe2ea;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 14px;
}

.field input.input-readonly {
  background: #f8fafc;
  color: #475569;
  cursor: default;
}

.modal-footer {
  padding: 12px 14px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 1100px) {
  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
