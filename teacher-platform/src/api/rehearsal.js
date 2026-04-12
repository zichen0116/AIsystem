// teacher-platform/src/api/rehearsal.js
import { apiRequest, authFetch } from './http.js'

const API = '/api/v1/rehearsal'

/** SSE 流式生成（返回 Response，调用方读 SSE） */
export async function generateRehearsalStream(params) {
  return await authFetch(`${API}/generate-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

/** 上传预演文件 */
export async function uploadRehearsalFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return await apiRequest(`${API}/upload`, {
    method: 'POST',
    body: formData,
  })
}

/** 会话列表 */
export async function fetchSessions() {
  return await apiRequest(`${API}/sessions`)
}

/** 会话详情（含全部场景） */
export async function fetchSession(sessionId) {
  return await apiRequest(`${API}/sessions/${sessionId}`)
}

/** 获取单个场景 */
export async function fetchScene(sessionId, sceneOrder) {
  return await apiRequest(`${API}/sessions/${sessionId}/scenes/${sceneOrder}`)
}

/** 重试失败场景 */
export async function retryScene(sessionId, sceneOrder) {
  return await apiRequest(`${API}/sessions/${sessionId}/scenes/${sceneOrder}/retry`, {
    method: 'POST',
  })
}

/** 更新播放进度 */
export async function updatePlaybackSnapshot(sessionId, snapshot) {
  return await apiRequest(`${API}/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ playback_snapshot: snapshot }),
  })
}

/** 删除预演 */
export async function deleteSession(sessionId) {
  return await apiRequest(`${API}/sessions/${sessionId}`, { method: 'DELETE' })
}
