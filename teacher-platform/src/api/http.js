const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '')

export function resolveApiUrl(path) {
  if (!path) return ''
  // already absolute
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
}

export function getToken() {
  return localStorage.getItem('access_token') || ''
}

export async function apiRequest(path, { method = 'GET', headers = {}, body } = {}) {
  const url = `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
  const token = getToken()

  const finalHeaders = { ...headers }
  if (token) finalHeaders.Authorization = `Bearer ${token}`

  const res = await fetch(url, { method, headers: finalHeaders, body })
  const contentType = res.headers.get('content-type') || ''

  if (!res.ok) {
    let detail = ''
    try {
      detail = contentType.includes('application/json') ? (await res.json())?.detail : await res.text()
    } catch {
      detail = ''
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }

  if (contentType.includes('application/json')) return await res.json()
  return await res.text()
}

