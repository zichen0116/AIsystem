<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import LoginRegisterModal from './LoginRegisterModal.vue'

defineProps({
  title: { type: String, default: '' }
})

const router = useRouter()
const userStore = useUserStore()
const showLoginModal = ref(false)

function goHome() {
  router.push('/')
}

function handleAvatarClick() {
  if (userStore.isLoggedIn) {
    router.push('/personal-center')
  } else {
    showLoginModal.value = true
  }
}
</script>

<template>
  <header class="page-header">
    <button class="back-btn" @click="goHome">← 返回首页</button>
    <h1 v-if="title" class="page-title">{{ title }}</h1>
    <div class="spacer" />
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
  </header>
  <LoginRegisterModal v-model="showLoginModal" />
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.back-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  color: #475569;
  font-size: 14px;
  cursor: pointer;
}

.back-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.page-title {
  font-size: 1.25rem;
  color: #1e293b;
}

.spacer {
  flex: 1;
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
