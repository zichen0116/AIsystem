/**
 * 课件管理模块 - API接口封装
 */
import { apiRequest, authFetch, resolveApiUrl } from './http.js'

const API = '/api/v1/courseware'

/**
 * 聚合获取所有课件（PPT + 教案 + 上传文件）
 * @param {Object} filters - { source_type, file_type, date_range }
 */
export async function fetchAllCourseware(filters = {}) {
  const params = new URLSearchParams()
  if (filters.source_type) params.append('source_type', filters.source_type)
  if (filters.file_type) params.append('file_type', filters.file_type)
  if (filters.date_range) params.append('date_range', filters.date_range)
  const query = params.toString()
  const url = `${API}/all${query ? '?' + query : ''}`
  return await apiRequest(url)
}

/**
 * 上传课件文件
 * @param {File} file
 * @param {Object} meta - { title, tags, remark }
 */
export async function uploadCourseware(file, meta = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (meta.title) formData.append('title', meta.title)
  if (meta.tags) formData.append('tags', meta.tags)
  if (meta.remark) formData.append('remark', meta.remark)

  const resp = await authFetch(`${API}/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || '上传失败')
  }
  return await resp.json()
}

/**
 * 更新上传课件信息
 */
export async function updateCourseware(id, data) {
  return await apiRequest(`${API}/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/**
 * 删除上传课件
 */
export async function deleteCoursewareItem(id) {
  return await apiRequest(`${API}/${id}`, { method: 'DELETE' })
}

/**
 * 下载课件
 * @param {string} sourceType - ppt / lesson_plan
 * @param {number} sourceId
 */
export function getDownloadUrl(sourceType, sourceId) {
  return resolveApiUrl(`${API}/download?source_type=${sourceType}&source_id=${sourceId}`)
}

/**
 * 下载受保护课件（PPT / 教案）
 * 通过带 token 的请求获取 blob，再触发浏览器下载。
 * @param {string} sourceType - ppt / lesson_plan
 * @param {number} sourceId
 * @param {string} fileName
 */
export async function downloadProtectedCourseware(sourceType, sourceId, fileName) {
  const resp = await authFetch(`${API}/download?source_type=${sourceType}&source_id=${sourceId}`)
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || '下载失败')
  }

  const blob = await resp.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = fileName || '课件'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(blobUrl), 3000)
}
