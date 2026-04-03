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

// 2FA modal state
const show2FAVerifyModal = ref(false)
const twoFATempToken = ref('')
const twoFAMaskedEmail = ref('')
const twoFACode = ref(['', '', '', '', '', ''])
const twoFALoading = ref(false)
const twoFAError = ref('')
const pendingRememberMe = ref(false)
const pendingRedirect = ref('')

// 忘记密码 modal state
const showForgotModal = ref(false)
const forgotPhone = ref('')
const forgotCode = ref('')
const forgotNewPassword = ref('')
const forgotConfirmPassword = ref('')
const forgotLoading = ref(false)
const forgotError = ref('')
const forgotSuccess = ref('')
const forgotCooldown = ref(0)
let forgotCooldownTimer = null

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
      const result = await userStore.login(form.value.phone, form.value.password)
      // 2FA required
      if (result && result.requires_2fa) {
        twoFATempToken.value = result.temp_token
        twoFAMaskedEmail.value = result.masked_email
        twoFACode.value = ['', '', '', '', '', '']
        twoFAError.value = ''
        pendingRememberMe.value = rememberMe.value
        pendingRedirect.value = typeof route.query.redirect === 'string' ? route.query.redirect : ''
        show2FAVerifyModal.value = true
        loading.value = false
        return
      }
      user = result
      if (rememberMe.value) {
        try { localStorage.setItem('eduprep_remember_login', '1') } catch { /* ignore */ }
      } else {
        try { localStorage.removeItem('eduprep_remember_login') } catch { /* ignore */ }
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
    errorMsg.value = e.detail || e.message || '操作失败'
  } finally {
    loading.value = false
  }
}

async function submit2FAVerify() {
  const code = twoFACode.value.join('')
  if (code.length !== 6) {
    twoFAError.value = '请输入完整的6位验证码'
    return
  }
  twoFALoading.value = true
  twoFAError.value = ''
  try {
    const user = await userStore.verify2FALogin(twoFATempToken.value, code)
    show2FAVerifyModal.value = false
    if (pendingRememberMe.value) {
      try { localStorage.setItem('eduprep_remember_login', '1') } catch { /* ignore */ }
    } else {
      try { localStorage.removeItem('eduprep_remember_login') } catch { /* ignore */ }
    }
    if (pendingRedirect.value) {
      router.replace(pendingRedirect.value)
    } else if (user.is_admin) {
      router.replace('/admin')
    } else {
      router.replace('/lesson-prep')
    }
  } catch (e) {
    twoFAError.value = e.detail || e.message || '验证失败'
  } finally {
    twoFALoading.value = false
  }
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

// ===== 忘记密码方法 =====
function openForgotModal() {
  forgotPhone.value = form.value.phone || ''
  forgotCode.value = ''
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
  forgotError.value = ''
  forgotSuccess.value = ''
  forgotLoading.value = false
  showForgotModal.value = true
}

function closeForgotModal() {
  showForgotModal.value = false
  if (forgotCooldownTimer) {
    clearInterval(forgotCooldownTimer)
    forgotCooldownTimer = null
  }
}

function startForgotCooldown() {
  forgotCooldown.value = 60
  if (forgotCooldownTimer) clearInterval(forgotCooldownTimer)
  forgotCooldownTimer = setInterval(() => {
    forgotCooldown.value--
    if (forgotCooldown.value <= 0) {
      clearInterval(forgotCooldownTimer)
      forgotCooldownTimer = null
    }
  }, 1000)
}

async function forgotSendCode() {
  forgotError.value = ''
  if (!forgotPhone.value || forgotPhone.value.length < 11) {
    forgotError.value = '请输入正确的手机号'
    return
  }
  forgotLoading.value = true
  try {
    await userStore.forgotPasswordSendCode(forgotPhone.value)
    startForgotCooldown()
  } catch (e) {
    forgotError.value = e.message || '发送验证码失败'
  } finally {
    forgotLoading.value = false
  }
}

async function forgotSubmitReset() {
  forgotError.value = ''
  if (!forgotPhone.value || forgotPhone.value.length < 11) {
    forgotError.value = '请输入正确的手机号'
    return
  }
  if (!forgotCode.value) {
    forgotError.value = '请输入验证码'
    return
  }
  if (!forgotNewPassword.value || forgotNewPassword.value.length < 6) {
    forgotError.value = '密码长度不能少于6位'
    return
  }
  if (forgotNewPassword.value !== forgotConfirmPassword.value) {
    forgotError.value = '两次密码不一致'
    return
  }
  forgotLoading.value = true
  try {
    await userStore.resetPassword(forgotPhone.value, forgotCode.value, forgotNewPassword.value)
    forgotSuccess.value = '密码重置成功，请使用新密码登录'
    setTimeout(() => {
      closeForgotModal()
    }, 2000)
  } catch (e) {
    forgotError.value = e.message || '密码重置失败'
  } finally {
    forgotLoading.value = false
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
            <a href="#" class="forgot-link" @click.prevent="openForgotModal">忘记密码？</a>
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

    <!-- 2FA 验证弹框 -->
    <Teleport to="body">
      <div v-if="show2FAVerifyModal" class="twofa-overlay" @click.self="show2FAVerifyModal = false">
        <div class="twofa-box">
          <div class="twofa-header">
            <h3>双重身份验证</h3>
            <button class="twofa-close" @click="show2FAVerifyModal = false">×</button>
          </div>
          <div class="twofa-body">
            <div class="twofa-icon">✉️</div>
            <p class="twofa-desc">验证码已发送至 <strong>{{ twoFAMaskedEmail }}</strong>，请在 5 分钟内输入。</p>
            <div class="twofa-inputs">
              <input
                v-for="(_, i) in 6"
                :key="i"
                :value="twoFACode[i]"
                type="text"
                inputmode="numeric"
                maxlength="1"
                class="twofa-digit"
                @input="on2FACodeInput(i, $event)"
                @keydown="on2FACodeKeydown(i, $event)"
              />
            </div>
            <p v-if="twoFAError" class="twofa-error">{{ twoFAError }}</p>
          </div>
          <div class="twofa-footer">
            <button class="twofa-cancel" @click="show2FAVerifyModal = false">取消</button>
            <button class="twofa-confirm" :disabled="twoFALoading" @click="submit2FAVerify">
              {{ twoFALoading ? '验证中...' : '确认验证' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 忘记密码弹框 -->
    <Teleport to="body">
      <div v-if="showForgotModal" class="twofa-overlay" @click.self="closeForgotModal">
        <div class="twofa-box forgot-box">
          <div class="twofa-header">
            <h3>重置密码</h3>
            <button class="twofa-close" @click="closeForgotModal">×</button>
          </div>
          <div class="twofa-body">
            <!-- 成功提示 -->
            <template v-if="forgotSuccess">
              <div class="forgot-success-icon">✅</div>
              <p class="forgot-success-msg">{{ forgotSuccess }}</p>
            </template>

            <template v-else>
              <!-- 手机号 -->
              <div class="forgot-row">
                <label class="forgot-label">手机号</label>
                <input
                  v-model="forgotPhone"
                  type="tel"
                  placeholder="请输入手机号"
                  class="forgot-input"
                  maxlength="11"
                />
              </div>
              <!-- 验证码 -->
              <div class="forgot-row">
                <label class="forgot-label">验证码</label>
                <input
                  v-model="forgotCode"
                  type="text"
                  placeholder="验证码"
                  class="forgot-input forgot-input-short"
                  maxlength="6"
                  inputmode="numeric"
                />
                <button
                  type="button"
                  class="forgot-send-btn"
                  :disabled="forgotCooldown > 0 || forgotLoading"
                  @click="forgotSendCode"
                >
                  {{ forgotCooldown > 0 ? `${forgotCooldown}s` : '发送验证码' }}
                </button>
              </div>
              <!-- 新密码 -->
              <div class="forgot-row">
                <label class="forgot-label">新密码</label>
                <input
                  v-model="forgotNewPassword"
                  type="password"
                  placeholder="请输入新密码（至少6位）"
                  class="forgot-input"
                />
              </div>
              <!-- 确认密码 -->
              <div class="forgot-row">
                <label class="forgot-label">确认密码</label>
                <input
                  v-model="forgotConfirmPassword"
                  type="password"
                  placeholder="再次确认新密码"
                  class="forgot-input"
                />
              </div>
              <p v-if="forgotError" class="twofa-error">{{ forgotError }}</p>
            </template>
          </div>
          <div v-if="!forgotSuccess" class="twofa-footer">
            <button class="twofa-cancel" @click="closeForgotModal">取消</button>
            <button
              class="twofa-confirm"
              :disabled="forgotLoading"
              @click="forgotSubmitReset"
            >
              {{ forgotLoading ? '重置中...' : '确认重置' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
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

.twofa-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.twofa-box {
  background: #fff;
  border-radius: 16px;
  width: 360px;
  max-width: 92vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}

.twofa-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.twofa-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.twofa-close {
  background: none;
  border: none;
  font-size: 1.4rem;
  color: #94a3b8;
  cursor: pointer;
  line-height: 1;
}

.twofa-body {
  padding: 20px 24px;
  text-align: center;
}

.twofa-icon {
  font-size: 2rem;
  margin-bottom: 12px;
}

.twofa-desc {
  font-size: 0.9rem;
  color: #475569;
  margin-bottom: 20px;
}

.twofa-inputs {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 12px;
}

.twofa-digit {
  width: 44px;
  height: 48px;
  text-align: center;
  font-size: 1.25rem;
  font-weight: 600;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  outline: none;
}

.twofa-digit:focus {
  border-color: #3b82f6;
}

.twofa-error {
  color: #ef4444;
  font-size: 0.85rem;
  margin-top: 8px;
}

.twofa-footer {
  display: flex;
  gap: 12px;
  padding: 0 24px 20px;
  justify-content: flex-end;
}

.twofa-cancel {
  padding: 8px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  font-size: 0.95rem;
}

.twofa-confirm {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: #fff;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
}

.twofa-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 忘记密码弹窗样式 */
.forgot-box {
  width: 440px;
}

.forgot-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.forgot-label {
  flex-shrink: 0;
  width: 64px;
  font-size: 0.9rem;
  font-weight: 500;
  color: #334155;
  text-align: right;
}

.forgot-input {
  flex: 1;
  height: 42px;
  padding: 0 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
  color: #1e293b;
  box-sizing: border-box;
  min-width: 0;
}

.forgot-input-short {
  flex: 0 1 120px;
}

.forgot-input:focus {
  border-color: #3b82f6;
}

.forgot-input::placeholder {
  color: #94a3b8;
}

.forgot-send-btn {
  flex-shrink: 0;
  height: 42px;
  padding: 0 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  font-size: 0.85rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s, border-color 0.2s;
}

.forgot-send-btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.forgot-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.forgot-success-icon {
  font-size: 2.5rem;
  margin-bottom: 12px;
}

.forgot-success-msg {
  font-size: 0.95rem;
  color: #16a34a;
  font-weight: 500;
}
</style>
