/**
 * PPT API 封装
 *
 * 复用 http.js 的 resolveApiUrl / authFetch / apiRequest 模式
 */
import { resolveApiUrl, getToken, apiRequest, authFetch } from './http.js'

// ========== 模板 ==========

export function getTemplates(page = 1, size = 20) {
  return apiRequest(`/api/v1/ppt/templates?page=${page}&size=${size}`)
}

// ========== 会话 ==========

export function createSession(title = '新建PPT') {
  return apiRequest('/api/v1/ppt/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export function listSessions() {
  return apiRequest('/api/v1/ppt/sessions')
}

export function getSessionDetail(sessionId) {
  return apiRequest(`/api/v1/ppt/sessions/${sessionId}`)
}

export function deleteSession(sessionId) {
  return apiRequest(`/api/v1/ppt/sessions/${sessionId}`, { method: 'DELETE' })
}

// ========== 大纲 ==========

function normalizeImageUrlsPayload(imageUrls) {
  if (imageUrls == null) return null
  if (Array.isArray(imageUrls)) {
    return Object.fromEntries(
      imageUrls
        .filter(Boolean)
        .map((url, index) => [String(index), url])
    )
  }
  if (typeof imageUrls === 'object') return imageUrls
  return null
}

export function approveOutline(outlineId, content = null, imageUrls = null, outlinePayload = null) {
  const body = {}
  if (content !== null) body.content = content
  const normalizedImageUrls = normalizeImageUrlsPayload(imageUrls)
  if (normalizedImageUrls !== null) body.image_urls = normalizedImageUrls
  if (outlinePayload !== null) body.outline_payload = outlinePayload
  return apiRequest(`/api/v1/ppt/outlines/${outlineId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// ========== PPT结果 ==========

export function getResultDetail(resultId) {
  return apiRequest(`/api/v1/ppt/results/${resultId}`)
}

export function saveEditSnapshot(resultId, editedPptxProperty) {
  return apiRequest(`/api/v1/ppt/results/${resultId}/edit-snapshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edited_pptx_property: editedPptxProperty }),
  })
}

export function modifyPptResult(resultId, instruction, slideIndex, currentPptxProperty) {
  return apiRequest(`/api/v1/ppt/results/${resultId}/modify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      instruction,
      slide_index: slideIndex,
      current_pptx_property: currentPptxProperty,
    }),
  })
}

export function downloadResult(resultId) {
  return apiRequest(`/api/v1/ppt/results/${resultId}/download`, { method: 'POST' })
}

// ========== 版本 ==========

export function getVersions(sessionId) {
  return apiRequest(`/api/v1/ppt/sessions/${sessionId}/versions`)
}

// ========== 文件上传 ==========

export async function uploadFile(sessionId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return authFetch(`/api/v1/ppt/sessions/${sessionId}/upload`, {
    method: 'POST',
    body: formData,
  }).then(r => r.json())
}

// ========== 流式请求 (fetch + reader) ==========

/**
 * 通用SSE流式请求
 * 复用教案页的 fetch + reader 模式
 */
export async function streamPptSSE(url, body, callbacks, abortSignal) {
  const { onMeta, onChunk, onOutlineReady, onProgress, onPageReady, onResultReady, onDone, onError } = callbacks

  const res = await fetch(resolveApiUrl(url), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    signal: abortSignal,
  })

  if (!res.ok) throw new Error(`HTTP ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.replace(/^data:\s*/, '').trim()
      if (!trimmed || trimmed === '[DONE]') continue
      try {
        const data = JSON.parse(trimmed)
        switch (data.type) {
          case 'meta': onMeta?.(data); break
          case 'assistant_chunk':
          case 'outline_chunk': onChunk?.(data.content); break
          case 'outline_ready': onOutlineReady?.(data); break
          case 'progress': onProgress?.(data); break
          case 'page_ready': onPageReady?.(data); break
          case 'result_ready': onResultReady?.(data); break
          case 'done': onDone?.(); break
          case 'error': onError?.(data.message); break
        }
      } catch { /* skip non-JSON */ }
    }
  }
}
