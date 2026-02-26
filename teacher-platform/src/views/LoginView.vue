<script setup>
import { ref } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

const isLogin = ref(true)

const form = ref({
  phone: '',
  password: '',
  confirmPassword: '',
  code: ''
})

function switchMode() {
  isLogin.value = !isLogin.value
  form.value = { phone: '', password: '', confirmPassword: '', code: '' }
}

function handleSubmit() {
  if (isLogin.value) {
    userStore.login({ name: form.value.phone, phone: form.value.phone })
  } else {
    userStore.login({ name: form.value.phone, phone: form.value.phone })
  }
  // 登录成功后由 App 自动切换至主页面
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-left" :class="{ 'mode-register': !isLogin }">
        <div class="illustration">
          <div class="illustration-figure">📄</div>
        </div>
        <div class="left-text">
          <h3 v-if="isLogin">还没有账号?</h3>
          <h3 v-else>已有账号?</h3>
          <p v-if="isLogin">请使用手机号注册账号</p>
          <p v-else>如果已有账号,请使用用户名和密码登录</p>
        </div>
        <button class="switch-btn" @click="switchMode">
          {{ isLogin ? '注册' : '登录' }}
        </button>
      </div>

      <div class="login-right">
        <div class="form-header">
          <p class="category">家校沟通</p>
          <h2>{{ isLogin ? '教师端登录' : '教师端注册' }}</h2>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <input v-model="form.phone" type="tel" placeholder="手机号" class="form-input" required />
          <input v-model="form.password" type="password" placeholder="密码" class="form-input" required />
          <template v-if="!isLogin">
            <input v-model="form.confirmPassword" type="password" placeholder="确认密码" class="form-input" required />
            <div class="code-row">
              <input v-model="form.code" type="text" placeholder="验证码" class="form-input" required />
              <button type="button" class="code-btn">获取验证码</button>
            </div>
          </template>
          <button type="submit" class="submit-btn">{{ isLogin ? '登录' : '注册' }}</button>
          <button v-if="!isLogin" type="button" class="back-btn" @click="switchMode">返回登录</button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
}

.login-container {
  display: flex;
  width: 720px;
  max-width: 95vw;
  min-height: 480px;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #a8b5e8 0%, #f0c4c4 100%);
  padding: 40px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
}

.login-left.mode-register {
  background: linear-gradient(135deg, #a8b5e8 0%, #e8c4d4 100%);
}

.illustration {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 6rem;
}

.left-text {
  text-align: center;
  margin-bottom: 24px;
}

.left-text h3 {
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.25rem;
  margin-bottom: 8px;
}

.left-text p {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.9rem;
}

.switch-btn {
  padding: 12px 40px;
  background: #93c5fd;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-btn:hover {
  background: #60a5fa;
}

.login-right {
  flex: 1;
  padding: 40px 48px;
}

.form-header {
  margin-bottom: 32px;
}

.category {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 4px;
}

.form-header h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-input {
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: #60a5fa;
}

.code-row {
  display: flex;
  gap: 12px;
}

.code-row .form-input {
  flex: 1;
}

.code-btn {
  padding: 12px 20px;
  background: #93c5fd;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
}

.submit-btn {
  padding: 14px;
  background: #93c5fd;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  margin-top: 8px;
}

.submit-btn:hover {
  background: #60a5fa;
}

.back-btn {
  padding: 12px;
  background: #fff;
  border: 1px solid #93c5fd;
  border-radius: 10px;
  color: #3b82f6;
  font-size: 14px;
  cursor: pointer;
}
</style>
