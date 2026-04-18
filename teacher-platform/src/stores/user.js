import { defineStore } from 'pinia'
import { apiRequest, setToken, removeToken, getToken, resolveApiUrl } from '../api/http'

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    userInfo: null,
  }),

  actions: {
    /**
     * 用户登录
     * 返回 { requires_2fa, temp_token, masked_email } 或直接完成登录
     */
    async login(phone, password) {
      const res = await fetch(resolveApiUrl('/api/v1/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, password }),
      })
      const data = await res.json()
      if (!res.ok) throw { status: res.status, detail: data.detail || '登录失败' }

      if (res.status === 202 && data.requires_2fa) {
        return data  // { requires_2fa: true, temp_token, masked_email }
      }

      setToken(data.access_token)
      this.isLoggedIn = true
      this.userInfo = data.user
      return data.user
    },

    /**
     * 2FA 二次验证
     */
    async verify2FALogin(temp_token, code) {
      const data = await apiRequest('/api/v1/auth/login/2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_token, code }),
      })
      setToken(data.access_token)
      this.isLoggedIn = true
      this.userInfo = data.user
      return data.user
    },

    /**
     * 用户注册
     */
    async register(phone, password, code, fullName) {
      const body = { phone, password, code }
      if (fullName) body.full_name = fullName
      const data = await apiRequest('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      setToken(data.access_token)
      this.isLoggedIn = true
      this.userInfo = data.user
      return data.user
    },

    /**
     * 退出登录
     */
    async logout() {
      const token = getToken()
      this.isLoggedIn = false
      this.userInfo = null
      if (token) {
        try {
          await fetch(resolveApiUrl('/api/v1/auth/logout'), {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          })
        } catch {
          // 忽略网络错误
        }
      }
      removeToken()
    },

    /**
     * 恢复登录态
     */
    async fetchUser() {
      const token = getToken()
      if (!token) return false
      try {
        const user = await apiRequest('/api/v1/auth/me')
        this.isLoggedIn = true
        this.userInfo = user
        return true
      } catch {
        removeToken()
        this.isLoggedIn = false
        this.userInfo = null
        return false
      }
    },

    /**
     * 更新个人资料
     */
    async updateProfile(profileData) {
      const user = await apiRequest('/api/v1/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData),
      })
      this.userInfo = user
      return user
    },

    /**
     * 修改手机号
     */
    async changePhone(new_phone, code) {
      const result = await apiRequest('/api/v1/auth/change-phone', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_phone, code }),
      })
      if (this.userInfo) this.userInfo.phone = new_phone
      return result
    },

    /**
     * 修改邮箱
     */
    async changeEmail(new_email) {
      const result = await apiRequest('/api/v1/auth/change-email', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_email }),
      })
      if (this.userInfo) this.userInfo.email = new_email
      return result
    },

    /**
     * 发送邮箱验证码（当前登录用户绑定邮箱）
     */
    async sendEmailCode() {
      return await apiRequest('/api/v1/auth/send-email-code', {
        method: 'POST',
      })
    },

    /**
     * 开启/关闭 2FA
     */
    async toggle2FA(enable, code) {
      const result = await apiRequest('/api/v1/auth/toggle-2fa', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable, code: code || null }),
      })
      if (this.userInfo) this.userInfo.two_fa_enabled = enable
      return result
    },

    /**
     * 忘记密码 - 发送短信验证码
     */
    async forgotPasswordSendCode(phone) {
      return await apiRequest('/api/v1/auth/forgot-password/send-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone }),
      })
    },

    /**
     * 忘记密码 - 重置密码
     */
    async resetPassword(phone, code, new_password) {
      return await apiRequest('/api/v1/auth/forgot-password/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code, new_password }),
      })
    },
  },
})
