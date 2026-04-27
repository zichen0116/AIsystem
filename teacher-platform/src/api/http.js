const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '')

// 不做 401 自动跳转的路径（登录/注册等接口本身会返回 401）
const AUTH_PATHS = ['/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/send-code', '/api/v1/auth/me', '/api/v1/auth/forgot-password']

function isAuthPath(path) {
  return AUTH_PATHS.some(p => path.includes(p))
}

export function buildApiUrl(base, path) {
  if (!path) return base || ''
  if (/^https?:\/\//i.test(path)) return path

  const normalizedBase = (base || '').replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  if (!normalizedBase) return normalizedPath
  if (normalizedBase === '/api' && normalizedPath.startsWith('/api/')) return normalizedPath

  return `${normalizedBase}${normalizedPath}`
}

export function resolveApiUrl(path) {
  return buildApiUrl(API_BASE, path)
}

export function getToken() {
  return localStorage.getItem('access_token') || ''
}

export function setToken(token) {
  localStorage.setItem('access_token', token)
}

export function removeToken() {
  localStorage.removeItem('access_token')
}

function getAuthHeaders(extra = {}) {
  const token = getToken()
  const headers = { ...extra }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

/**
 * 带认证的 fetch 封装（支持流式等场景）
 * 自动附加 Authorization header，非 auth 路径 401 时清 token 跳登录页
 */
export async function authFetch(path, options = {}) {
  const url = buildApiUrl(API_BASE, path)
  const headers = getAuthHeaders(options.headers || {})

  const res = await fetch(url, { ...options, headers })

  if (res.status === 401 && !isAuthPath(path)) {
    removeToken()
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }

  return res
}

/**
 * JSON API 请求封装
 */
export async function apiRequest(path, { method = 'GET', headers = {}, body } = {}) {
  const url = buildApiUrl(API_BASE, path)
  const finalHeaders = getAuthHeaders(headers)
  // 自动为字符串body添加Content-Type（避免FormData需要手动设置）
  if (typeof body === 'string' && body && !finalHeaders['Content-Type']) {
    finalHeaders['Content-Type'] = 'application/json'
  }

  const res = await fetch(url, { method, headers: finalHeaders, body })

  // 非 auth 路径的 401 视为登录过期
  if (res.status === 401 && !isAuthPath(path)) {
    removeToken()
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }

  const contentType = res.headers.get('content-type') || ''

  if (!res.ok) {
    let detail = ''
    try {
      if (contentType.includes('application/json')) {
        const payload = await res.json()
        const parsedDetail = payload?.detail ?? payload?.message ?? payload
        detail = typeof parsedDetail === 'string' ? parsedDetail : JSON.stringify(parsedDetail)
      } else {
        detail = await res.text()
      }
    } catch {
      detail = ''
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }

  // 204/205 has no response body.
  if (res.status === 204 || res.status === 205) return null

  if (contentType.includes('application/json')) {
    const text = await res.text()
    return text ? JSON.parse(text) : null
  }

  const text = await res.text()
  return text || null
}
