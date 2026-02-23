<script setup>
import { inject } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const openLoginModal = inject('openLoginModal', null)

function logout() {
  userStore.logout()
}
</script>

<template>
  <div class="personal-page">
    <div v-if="userStore.isLoggedIn" class="center-content">
      <div class="profile-card">
        <div class="avatar-large">
          {{ userStore.userInfo?.name?.[0] || '用' }}
        </div>
        <h2>{{ userStore.userInfo?.name || userStore.userInfo?.phone || '用户' }}</h2>
        <p class="phone">{{ userStore.userInfo?.phone || '未绑定手机' }}</p>
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>
      <div class="menu-list">
        <div class="menu-item">账号设置</div>
        <div class="menu-item">我的课件</div>
        <div class="menu-item">使用记录</div>
      </div>
    </div>

    <div v-else class="login-prompt">
      <p>请先登录</p>
      <button class="login-redirect" @click="openLoginModal?.()">前往登录</button>
    </div>
  </div>
</template>

<style scoped>
.personal-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.center-content {
  max-width: 480px;
  margin: 0 auto;
  padding: 24px;
}

.profile-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.avatar-large {
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
  margin: 0 auto 16px;
}

.profile-card h2 {
  font-size: 1.25rem;
  color: #1e293b;
  margin-bottom: 4px;
}

.phone {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 24px;
}

.logout-btn {
  padding: 10px 32px;
  background: #f1f5f9;
  border: none;
  border-radius: 8px;
  color: #475569;
  font-size: 14px;
  cursor: pointer;
}

.logout-btn:hover {
  background: #e2e8f0;
}

.menu-list {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.menu-item {
  padding: 16px 24px;
  border-bottom: 1px solid #f1f5f9;
  color: #475569;
  cursor: pointer;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item:hover {
  background: #f8fafc;
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
</style>
