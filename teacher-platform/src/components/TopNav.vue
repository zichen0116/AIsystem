<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import LoginRegisterModal from './LoginRegisterModal.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const showLoginModal = ref(false)

const navItems = [
  { path: '/lesson-prep', label: '进入备课' },
  { path: '/courseware', label: '课件管理' },
  { path: '/knowledge-base', label: '知识库' }
]

function handleAvatarClick() {
  if (userStore.isLoggedIn) {
    router.push('/personal-center')
  } else {
    showLoginModal.value = true
  }
}

function goTo(path) {
  router.push(path)
}
</script>

<template>
  <header class="top-nav">
    <div class="nav-left" @click="router.push('/')" style="cursor: pointer">
      <h1 class="logo">教师备课平台</h1>
    </div>
    <nav class="nav-right">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="nav-btn"
        :class="{ active: route.path === item.path }"
        @click="goTo(item.path)"
      >
        {{ item.label }}
      </button>
      <div
        class="avatar"
        :class="{ 'avatar-logged-in': userStore.isLoggedIn }"
        @click="handleAvatarClick"
      >
        <span v-if="userStore.isLoggedIn" class="avatar-initial">
          {{ userStore.userInfo?.name?.[0] || '用' }}
        </span>
        <span v-else class="avatar-icon">👤</span>
      </div>
    </nav>
  </header>

  <LoginRegisterModal v-model="showLoginModal" />
</template>

<style scoped>
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 48px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.logo {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-btn {
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: #475569;
  font-size: 15px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.nav-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.nav-btn.active {
  color: #3b82f6;
  background: #eff6ff;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.avatar-logged-in {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
}

.avatar-initial {
  color: #fff;
  font-weight: 600;
  font-size: 1rem;
}

.avatar-icon {
  font-size: 1.2rem;
  opacity: 0.7;
}

.avatar:hover {
  transform: scale(1.05);
}
</style>
