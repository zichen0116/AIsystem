<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { apiRequest } from '../api/http'
import { useLoginCharactersAnim } from '../composables/useLoginCharactersAnim.js'

const userStore = useUserStore()
const showPassword = ref(false)
const rememberMe = ref(false)
const router = useRouter()
const route = useRoute()

const isLogin = ref(true)
const loading = ref(false)
const errorMsg = ref('')
const codeCooldown = ref(0)
let cooldownTimer = null

const form = ref({
  phone: '',
  password: '',
  confirmPassword: '',
  code: '',
  fullName: '',
})

const {
  purpleEl,
  blackEl,
  orangeEl,
  yellowEl,
  purpleEyes,
  blackEyes,
  orangeEyes,
  yellowEyes,
  yellowMouth,
  onPhoneFocus,
  onPhoneBlur,
  onPasswordFocus,
  onPasswordBlur,
} = useLoginCharactersAnim({ showPassword, form })

onMounted(() => {
  try {
    rememberMe.value = localStorage.getItem('eduprep_remember_login') === '1'
  } catch {
    /* ignore */
  }
})

function setMode(nextIsLogin) {
  if (isLogin.value === nextIsLogin) return
  isLogin.value = nextIsLogin
  form.value = { phone: '', password: '', confirmPassword: '', code: '', fullName: '' }
  errorMsg.value = ''
  showPassword.value = false
}

async function sendCode() {
  if (codeCooldown.value > 0) return
  if (!form.value.phone || form.value.phone.length < 11) {
    errorMsg.value = '请输入正确的手机号'
    return
  }
  try {
    await apiRequest('/api/v1/auth/send-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: form.value.phone }),
    })
    // 开始冷却倒计时
    codeCooldown.value = 60
    cooldownTimer = setInterval(() => {
      codeCooldown.value--
      if (codeCooldown.value <= 0) clearInterval(cooldownTimer)
    }, 1000)
    errorMsg.value = ''
  } catch (e) {
    errorMsg.value = e.message || '验证码发送失败'
  }
}

async function handleSubmit() {
  errorMsg.value = ''

  if (!form.value.phone || !form.value.password) {
    errorMsg.value = '请填写手机号和密码'
    return
  }

  if (!isLogin.value) {
    if (form.value.password !== form.value.confirmPassword) {
      errorMsg.value = '两次密码不一致'
      return
    }
    if (!form.value.code) {
      errorMsg.value = '请输入验证码'
      return
    }
  }

  loading.value = true
  try {
    let user
    if (isLogin.value) {
      user = await userStore.login(form.value.phone, form.value.password)
      if (rememberMe.value) {
        try {
          localStorage.setItem('eduprep_remember_login', '1')
        } catch {
          /* ignore */
        }
      } else {
        try {
          localStorage.removeItem('eduprep_remember_login')
        } catch {
          /* ignore */
        }
      }
    } else {
      user = await userStore.register(
        form.value.phone,
        form.value.password,
        form.value.code,
        form.value.fullName || undefined,
      )
    }

    // 跳转
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    if (redirect) {
      router.replace(redirect)
    } else if (user.is_admin) {
      router.replace('/admin')
    } else {
      router.replace('/lesson-prep')
    }
  } catch (e) {
    errorMsg.value = e.message || '操作失败'
  } finally {
    loading.value = false
  }
}

function goHome() {
  router.push('/')
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <section class="auth-left" aria-hidden="true">
        <button type="button" class="home-btn" @click.stop="goHome">首页</button>
        <div class="characters-wrap">
          <div class="characters">
            <div ref="purpleEl" class="char char-purple">
              <div ref="purpleEyes" class="eyes-wrap">
                <div class="eyeball" style="width: 18px; height: 18px">
                  <div class="pupil" style="width: 7px; height: 7px" />
                </div>
                <div class="eyeball" style="width: 18px; height: 18px">
                  <div class="pupil" style="width: 7px; height: 7px" />
                </div>
              </div>
            </div>
            <div ref="blackEl" class="char char-black">
              <div ref="blackEyes" class="eyes-wrap">
                <div class="eyeball" style="width: 16px; height: 16px">
                  <div class="pupil" style="width: 6px; height: 6px" />
                </div>
                <div class="eyeball" style="width: 16px; height: 16px">
                  <div class="pupil" style="width: 6px; height: 6px" />
                </div>
              </div>
            </div>
            <div ref="orangeEl" class="char char-orange">
              <div ref="orangeEyes" class="eyes-wrap">
                <div class="pupil-only" style="width: 12px; height: 12px" />
                <div class="pupil-only" style="width: 12px; height: 12px" />
              </div>
            </div>
            <div ref="yellowEl" class="char char-yellow">
              <div ref="yellowEyes" class="eyes-wrap">
                <div class="pupil-only" style="width: 12px; height: 12px" />
                <div class="pupil-only" style="width: 12px; height: 12px" />
              </div>
              <div ref="yellowMouth" class="mouth" />
            </div>
          </div>
        </div>
        <div class="grid-overlay"></div>
        <div class="blob1"></div>
        <div class="blob2"></div>
      </section>

      <section class="auth-right">
        <div class="form-box">
          <header class="form-header">
            <h1 class="form-title">{{ isLogin ? '欢迎回来！' : '注册账号' }}</h1>
            <p class="form-subtitle">
              {{ isLogin ? '请输入你的登录信息' : '请填写手机号与验证码完成注册' }}
            </p>
          </header>

          <div class="mode-tabs" role="tablist" aria-label="登录注册切换">
            <button type="button" class="tab" :class="{ active: !isLogin }" @click="setMode(false)">注册账号</button>
            <button type="button" class="tab" :class="{ active: isLogin }" @click="setMode(true)">登录账号</button>
          </div>

          <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

          <form class="auth-form" @submit.prevent="handleSubmit">
          <label class="field">
            <span class="label">手机号</span>
            <input
              v-model="form.phone"
              type="tel"
              placeholder="请输入手机号"
              class="input"
              required
              @focus="onPhoneFocus"
              @blur="onPhoneBlur"
            />
          </label>

          <label class="field">
            <span class="label">密码</span>
            <div class="input-wrap">
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                class="input input-with-toggle input-password"
                required
                @focus="onPasswordFocus"
                @blur="onPasswordBlur"
              />
              <button type="button" class="toggle-pw" aria-label="显示或隐藏密码" @click="showPassword = !showPassword">
                <svg
                  v-show="!showPassword"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
                  />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                </svg>
                <svg
                  v-show="showPassword"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12c1.292 4.338 5.31 7.5 10.066 7.5.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88"
                  />
                </svg>
              </button>
            </div>
          </label>

          <template v-if="!isLogin">
            <label class="field">
              <span class="label">确认密码</span>
              <input
                v-model="form.confirmPassword"
                :type="showPassword ? 'text' : 'password'"
                placeholder="再次输入密码"
                class="input input-password"
                required
                @focus="onPasswordFocus"
                @blur="onPasswordBlur"
              />
            </label>

            <label class="field">
              <span class="label">姓名（选填）</span>
              <input v-model="form.fullName" type="text" placeholder="请输入姓名" class="input" />
            </label>

            <div class="code-row">
              <label class="field field-code">
                <span class="label">验证码</span>
                <input v-model="form.code" type="text" placeholder="请输入验证码" class="input" required />
              </label>
              <button
                type="button"
                class="code-btn"
                :disabled="codeCooldown > 0"
                @click="sendCode"
              >
                {{ codeCooldown > 0 ? `${codeCooldown}s 后重发` : '获取验证码' }}
              </button>
            </div>
          </template>

          <div v-if="isLogin" class="form-options-row">
            <label class="remember">
              <input v-model="rememberMe" type="checkbox" />
              30天内记住我
            </label>
            <a href="#" class="forgot-link" @click.prevent>忘记密码？</a>
          </div>

          <button type="submit" class="submit-btn hover-btn" :disabled="loading">
            <span class="btn-label">{{ loading ? '处理中...' : (isLogin ? '登录' : '注册') }}</span>
            <span class="btn-overlay" aria-hidden="true">
              <span>{{ isLogin ? '登录' : '注册' }}</span>
              <svg class="arrow-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </span>
          </button>
        </form>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 60%, #ffffff 100%);
  padding: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.auth-card {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: none;
  background: #fff;
  border-radius: 0;
  overflow: hidden;
  box-shadow: none;
  border: none;
}

.auth-left {
  flex: 1 1 0;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px;
  background: linear-gradient(135deg, #9ca3af, #6b7280, #4b5563);
  color: #fff;
  overflow: hidden;
  min-height: 0;
}

.auth-left .blob1,
.auth-left .blob2 {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
}

.auth-left .blob1 {
  top: 25%;
  right: 25%;
  width: 256px;
  height: 256px;
  background: rgba(156, 163, 175, 0.2);
}

.auth-left .blob2 {
  bottom: 25%;
  left: 25%;
  width: 384px;
  height: 384px;
  background: rgba(209, 213, 219, 0.2);
}

.auth-left .grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.05) 0 1px, transparent 1px 20px),
    repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.05) 0 1px, transparent 1px 20px);
  pointer-events: none;
}

.auth-left .characters-wrap {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  height: 500px;
}

.auth-left .characters {
  position: relative;
  width: 550px;
  height: 400px;
}

.auth-left .char {
  position: absolute;
  bottom: 0;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: bottom center;
}

.auth-left .char-purple {
  left: 70px;
  width: 180px;
  height: 400px;
  background: #6c3ff5;
  border-radius: 10px 10px 0 0;
  z-index: 1;
}

.auth-left .char-purple .eyes-wrap {
  position: absolute;
  display: flex;
  gap: 32px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}

.auth-left .char-black {
  left: 240px;
  width: 120px;
  height: 310px;
  background: #2d2d2d;
  border-radius: 8px 8px 0 0;
  z-index: 2;
}

.auth-left .char-black .eyes-wrap {
  position: absolute;
  display: flex;
  gap: 24px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}

.auth-left .char-orange {
  left: 0;
  width: 240px;
  height: 200px;
  background: #ff9b6b;
  border-radius: 120px 120px 0 0;
  z-index: 3;
}

.auth-left .char-orange .eyes-wrap {
  position: absolute;
  display: flex;
  gap: 32px;
  transition: all 0.2s ease-out;
}

.auth-left .char-yellow {
  left: 310px;
  width: 140px;
  height: 230px;
  background: #e8d754;
  border-radius: 70px 70px 0 0;
  z-index: 4;
}

.auth-left .char-yellow .eyes-wrap {
  position: absolute;
  display: flex;
  gap: 24px;
  transition: all 0.2s ease-out;
}

.auth-left .char-yellow .mouth {
  position: absolute;
  width: 80px;
  height: 4px;
  background: #2d2d2d;
  border-radius: 4px;
  transition: all 0.2s ease-out;
}

.auth-left .eyeball {
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: height 0.15s;
  background: #fff;
}

.auth-left .eyeball .pupil {
  border-radius: 50%;
  background: #2d2d2d;
  transition: transform 0.1s ease-out;
}

.auth-left .pupil-only {
  border-radius: 50%;
  background: #2d2d2d;
  transition: transform 0.1s ease-out;
}

.home-btn {
  position: absolute;
  left: 18px;
  top: 18px;
  height: 46px;
  padding: 0 22px;
  border-radius: 999px;
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  z-index: 30;
  backdrop-filter: blur(6px);
}

.home-btn:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.65);
}

.home-btn:active {
  transform: translateY(1px);
}

.auth-right {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
  padding: 32px;
  box-sizing: border-box;
  background: #fff;
}

.form-box {
  width: 100%;
  max-width: 420px;
}

.form-header {
  text-align: center;
  margin-bottom: 28px;
}

.form-title {
  margin: 0 0 8px;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: #111827;
}

.form-subtitle {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
}

.mode-tabs {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 24px;
}

.tab {
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s;
}

.tab:hover {
  color: #111827;
}

.tab.active {
  color: #111827;
  font-weight: 600;
}

.error-msg {
  padding: 10px 14px;
  margin-bottom: 20px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
}

.auth-form {
  display: flex;
  flex-direction: column;
}

.field {
  display: block;
  margin-bottom: 20px;
}

.label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #111827;
}

.input {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
}

.input::placeholder {
  color: #9ca3af;
}

.input:focus {
  border-color: #111827;
  box-shadow: none;
}

.input-password {
  background: #e8f0fe;
}

.input-password:focus {
  background: #e8f0fe;
}

.input-wrap {
  position: relative;
}

.input-with-toggle {
  padding-right: 44px;
}

.toggle-pw {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  background: none;
  border: none;
  cursor: pointer;
  color: #9ca3af;
  transition: color 0.2s;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-pw:hover {
  color: #111827;
}

.toggle-pw svg {
  width: 20px;
  height: 20px;
  pointer-events: none;
}

.code-btn {
  height: 48px;
  padding: 0 18px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  align-self: flex-end;
  transition: background 0.2s, border-color 0.2s;
}

.code-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.code-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.form-options-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  margin-top: 4px;
}

.remember {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #111827;
  cursor: pointer;
  user-select: none;
}

.remember input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: #111827;
  cursor: pointer;
}

.forgot-link {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.submit-btn.hover-btn {
  position: relative;
  width: 100%;
  height: 48px;
  margin-top: 4px;
  border-radius: 9999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  cursor: pointer;
  overflow: hidden;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  padding: 0;
}

.submit-btn .btn-label {
  display: inline-block;
  transition: all 0.3s;
}

.submit-btn .btn-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #111827;
  color: #fff;
  border-radius: 9999px;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.submit-btn:hover:not(:disabled) .btn-label {
  transform: translateX(48px);
  opacity: 0;
}

.submit-btn:hover:not(:disabled) .btn-overlay {
  opacity: 1;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.submit-btn:disabled:hover .btn-label {
  transform: none;
  opacity: 1;
}

.submit-btn:disabled:hover .btn-overlay {
  opacity: 0;
}

.arrow-icon {
  width: 16px;
  height: 16px;
}

.code-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 20px;
}

.field-code {
  flex: 1;
  margin-bottom: 0;
}

.code-row .field {
  margin-bottom: 0;
}

@media (max-width: 900px) {
  .auth-page {
    height: auto;
    min-height: 100vh;
    max-height: none;
    overflow-y: auto;
  }

  .auth-card {
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
  }

  .auth-left {
    flex: 0 0 auto;
    min-height: 220px;
    padding: 24px 16px 0;
  }

  .auth-left .characters-wrap {
    height: 220px;
  }

  .auth-left .characters {
    transform: scale(0.45);
    transform-origin: bottom center;
  }

  .auth-right {
    flex: 1 1 auto;
    min-height: 0;
    padding: 24px 20px 40px;
    align-items: flex-start;
  }

  .form-header {
    margin-bottom: 24px;
  }
}
</style>
