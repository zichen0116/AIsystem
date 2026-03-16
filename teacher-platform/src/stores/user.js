import { defineStore } from 'pinia'
import { apiRequest, setToken, removeToken, getToken } from '../api/http'

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    userInfo: null,
  }),

  actions: {
    /**
     * 用户登录
     */
    async login(phone, password) {
      const data = await apiRequest('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, password }),
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
     * 退出登录 — 先用 token 请求后端加黑名单，再清本地
     */
    async logout() {
      const token = getToken()
      // 先清 UI 状态（立即反映退出）
      this.isLoggedIn = false
      this.userInfo = null
      // 带着 token 请求后端加黑名单
      if (token) {
        try {
          const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '')
          await fetch(`${API_BASE}/api/v1/auth/logout`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          })
        } catch {
          // 忽略网络错误
        }
      }
      // 最后清 token
      removeToken()
    },

    /**
     * 恢复登录态：用本地 token 请求 /me
     * 返回 true 表示恢复成功
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
  },
})
