<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import smartImg from '../assets/智能.png'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const isLogin = ref(true)

const form = ref({
  phone: '',
  password: '',
  confirmPassword: '',
  code: ''
})

function setMode(nextIsLogin) {
  if (isLogin.value === nextIsLogin) return
  isLogin.value = nextIsLogin
  form.value = { phone: '', password: '', confirmPassword: '', code: '' }
}

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
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  router.replace(redirect || '/lesson-prep')
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <section class="auth-left" aria-hidden="true">
        <div class="auth-left-inner">
          <div class="illus-bg">
            <div class="blob blob-1"></div>
            <div class="blob blob-2"></div>
            <div class="spark spark-1"></div>
            <div class="spark spark-2"></div>
          </div>

          <div class="illus-hero">
            <img class="auth-illus-img" :src="smartImg" alt="" />
          </div>
        </div>
      </section>

      <section class="auth-right">
        <h1 class="welcome-title">欢迎使用 EduPrep 教师备课平台</h1>
        <div class="mode-tabs" role="tablist" aria-label="登录注册切换">
          <button type="button" class="tab" :class="{ active: !isLogin }" @click="setMode(false)">注册账号</button>
          <button type="button" class="tab" :class="{ active: isLogin }" @click="setMode(true)">登录账号</button>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <label class="field">
            <span class="label">Phone</span>
            <input v-model="form.phone" type="tel" placeholder="手机号" class="input" required />
          </label>

          <label class="field">
            <span class="label">Password</span>
            <input v-model="form.password" type="password" placeholder="密码" class="input" required />
          </label>

          <template v-if="!isLogin">
            <label class="field">
              <span class="label">Confirm password</span>
              <input v-model="form.confirmPassword" type="password" placeholder="确认密码" class="input" required />
            </label>

            <div class="code-row">
              <label class="field field-code">
                <span class="label">Code</span>
                <input v-model="form.code" type="text" placeholder="验证码" class="input" required />
              </label>
              <button type="button" class="code-btn">获取验证码</button>
            </div>
          </template>

          <button type="submit" class="submit-btn">{{ isLogin ? '登录' : '注册' }}</button>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 60%, #ffffff 100%);
  padding: 24px;
}

.auth-card {
  display: flex;
  width: 1150px;
  max-width: 100%;
  height: 665px;
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.auth-left {
  flex: 1.1;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 45%, #dbeafe 100%);
  position: relative;
}

.auth-left-inner {
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
}

.illus-hero {
  position: relative;
  width: 100%;
  width: 560px;
  height: 400px;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-illus-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.illus-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.blob {
  position: absolute;
  border-radius: 999px;
  filter: blur(0px);
}

.blob-1 {
  width: 320px;
  height: 320px;
  left: -80px;
  top: -60px;
  background: radial-gradient(circle at 30% 30%, rgba(59,130,246,0.18), rgba(59,130,246,0));
}

.blob-2 {
  width: 360px;
  height: 360px;
  right: -120px;
  bottom: -120px;
  background: radial-gradient(circle at 60% 40%, rgba(99,102,241,0.18), rgba(99,102,241,0));
}

.spark {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.5);
}

.spark-1 { left: 22%; top: 38%; opacity: 0.6; }
.spark-2 { right: 26%; top: 28%; opacity: 0.35; background: rgba(99,102,241,0.5); }

.illus-hero {
  position: relative;
  width: 100%;
  max-width: 520px;
  height: 360px;
}


.auth-right {
  flex: 0.9;
  padding: 64px 72px;
}

.welcome-title {
  margin: 0 0 18px;
  font-size: 30px;
  font-weight: 700;
  color: #334155;
}

.mode-tabs {
  display: flex;
  gap: 18px;
  margin-bottom: 30px;
}

.tab {
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  position: relative;
}

.tab::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -8px;
  height: 2px;
  border-radius: 999px;
  background: transparent;
  transition: background 0.2s;
}

.tab.active {
  color: #3b82f6;
  font-weight: 600;
}

.tab.active::after {
  background: #3b82f6;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label {
  font-size: 14px;
  color: #64748b;
}

.input {
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fff;
}

.input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(59,130,246,0.12);
}

.code-btn {
  height: 46px;
  padding: 0 22px;
  background: #3b82f6;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
  align-self: end;
  transition: filter 0.2s;
}

.submit-btn {
  margin-top: 8px;
  height: 50px;
  background: #3b82f6;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.2s;
}

.submit-btn:hover,
.code-btn:hover {
  filter: brightness(0.95);
}

.code-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.field-code {
  flex: 1;
}

@media (max-width: 900px) {
  .auth-card {
    width: 100%;
    min-height: auto;
    flex-direction: column;
  }

  .auth-left {
    min-height: 260px;
  }

  .auth-right {
    padding: 28px 22px 30px;
  }

  .illus-hero { height: 260px; }
}
</style>
