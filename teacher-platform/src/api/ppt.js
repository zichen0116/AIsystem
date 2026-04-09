/**
 * PPT生成模块 - API接口封装
 */
import { apiRequest, authFetch } from '@/api/http'

const API = '/api/v1/ppt'

// ============ SSE 流式解析工具 ============

/**
 * SSE 流式事件解析器
 * 统一使用 event: message，通过 data.type 分流
 */
export async function* streamEvents(url, options = {}) {
  const response = await authFetch(url, options)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch (e) {
          // ignore parse errors
        }
      }
    }
  }
}

// ============ 项目接口 ============

export async function createProject(data) {
  return await apiRequest(`${API}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
}

export async function getProject(id) {
  return await apiRequest(`${API}/projects/${id}`)
}

export async function updateProject(id, data) {
  return await apiRequest(`${API}/projects/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
}

export async function deleteProject(id) {
  return await apiRequest(`${API}/projects/${id}`, {
    method: 'DELETE'
  })
}

export async function listProjects() {
  return await apiRequest(`${API}/projects`)
}

export async function batchDeleteProjects(ids) {
  return await apiRequest(`${API}/projects/batch-delete`, {
    method: 'POST',
    body: JSON.stringify(ids)
  })
}

// ============ 项目设置 ============

export async function updateProjectSettings(id, data) {
  return await apiRequest(`${API}/projects/${id}/settings`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

// ============ 页面接口 ============

export async function createPage(projectId, data) {
  return await apiRequest(`${API}/projects/${projectId}/pages`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function getPages(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/pages`)
}

export async function updatePage(projectId, pageId, data) {
  return await apiRequest(`${API}/projects/${projectId}/pages/${pageId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export async function deletePage(projectId, pageId) {
  return await apiRequest(`${API}/projects/${projectId}/pages/${pageId}`, {
    method: 'DELETE'
  })
}

export async function reorderPages(projectId, pageIds) {
  return await apiRequest(`${API}/projects/${projectId}/pages/reorder`, {
    method: 'POST',
    body: JSON.stringify({ page_ids: pageIds })
  })
}

// ============ 大纲生成 ============

export async function generateOutline(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/outline/generate`, {
    method: 'POST'
  })
}

export async function generateOutlineStream(projectId, payload = {}, language = 'zh') {
  const body = typeof payload === 'string'
    ? { idea_prompt: payload, language }
    : {
        idea_prompt: payload.idea_prompt ?? payload.ideaPrompt ?? null,
        planning_context_text: payload.planning_context_text ?? payload.planningContextText ?? null,
        language: payload.language ?? language
      }
  const url = `${API}/projects/${projectId}/outline/generate/stream`
  return streamEvents(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
}

// ============ 描述生成 ============

export async function generateDescriptions(projectId, language = 'zh', detailLevel = 'default') {
  return await apiRequest(`${API}/projects/${projectId}/descriptions/generate`, {
    method: 'POST',
    body: JSON.stringify({ language, detail_level: detailLevel })
  })
}

export async function generateDescriptionsStream(projectId, language = 'zh', detailLevel = 'default') {
  const url = `${API}/projects/${projectId}/descriptions/generate/stream`
  return streamEvents(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language, detail_level: detailLevel })
  })
}

// ============ 图片生成 ============

export async function generateImages(projectId, pageIds = null) {
  const params = pageIds ? `?page_ids=${pageIds.join(',')}` : ''
  return await apiRequest(`${API}/projects/${projectId}/images/generate${params}`, {
    method: 'POST'
  })
}

// ============ 自然语言修改 ============

export async function refineOutline(projectId, userRequirement, language = 'zh') {
  return await apiRequest(`${API}/projects/${projectId}/refine/outline`, {
    method: 'POST',
    body: JSON.stringify({ user_requirement: userRequirement, language })
  })
}

export async function refineDescriptions(projectId, userRequirement, language = 'zh') {
  return await apiRequest(`${API}/projects/${projectId}/refine/descriptions`, {
    method: 'POST',
    body: JSON.stringify({ user_requirement: userRequirement, language })
  })
}

export async function editPageImage(projectId, pageId, editInstruction, contextImages = null) {
  const uploadedFiles = Array.isArray(contextImages?.uploaded_files) ? contextImages.uploaded_files : []
  if (uploadedFiles.length > 0) {
    const formData = new FormData()
    formData.append('edit_instruction', editInstruction)
    formData.append('use_template', String(!!contextImages?.use_template))
    if (contextImages?.selection_bbox) {
      formData.append('selection_bbox', JSON.stringify(contextImages.selection_bbox))
    }
    if (Array.isArray(contextImages?.desc_image_urls) && contextImages.desc_image_urls.length > 0) {
      formData.append('desc_image_urls', JSON.stringify(contextImages.desc_image_urls))
    }
    if (Array.isArray(contextImages?.uploaded_image_ids) && contextImages.uploaded_image_ids.length > 0) {
      formData.append('uploaded_image_ids', JSON.stringify(contextImages.uploaded_image_ids))
    }
    uploadedFiles.forEach(file => {
      formData.append('context_images', file)
    })

    const res = await authFetch(`${API}/projects/${projectId}/pages/${pageId}/edit/image`, {
      method: 'POST',
      body: formData
    })
    if (!res.ok) {
      const detail = await res.text().catch(() => '')
      throw new Error(detail || '发起编辑失败')
    }
    return res.json()
  }

  return await apiRequest(`${API}/projects/${projectId}/pages/${pageId}/edit/image`, {
    method: 'POST',
    body: JSON.stringify({
      edit_instruction: editInstruction,
      context_images: contextImages
    })
  })
}

// ============ 导出 ============

export function getExportUrl(projectId, format, pageIds = null) {
  const base = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
  let url = `${base}${API}/projects/${projectId}/export/${format}`
  if (pageIds) {
    url += `?page_ids=${pageIds.join(',')}`
  }
  return url
}

export async function exportEditablePptx(projectId, pageIds = null) {
  const params = pageIds ? `?page_ids=${pageIds.join(',')}` : ''
  return await apiRequest(`${API}/projects/${projectId}/export/editable-pptx${params}`, {
    method: 'POST'
  })
}

// ============ 导出任务 ============

export async function getExportTasks(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/export-tasks`)
}

export async function getExportTaskStatus(taskId) {
  return await apiRequest(`${API}/export-tasks/${taskId}`)
}

// ============ 素材 ============

export async function getMaterials(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/materials`)
}

export async function uploadMaterial(projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await authFetch(`${API}/projects/${projectId}/materials/upload`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    throw new Error('上传失败')
  }
  return res.json()
}

export async function generateMaterial(projectId, prompt, aspectRatio = '1:1') {
  return await apiRequest(`${API}/projects/${projectId}/materials/generate`, {
    method: 'POST',
    body: JSON.stringify({ prompt, aspect_ratio: aspectRatio })
  })
}

export async function deleteMaterial(projectId, materialId) {
  return await apiRequest(`${API}/projects/${projectId}/materials/${materialId}`, {
    method: 'DELETE'
  })
}

export async function getAllMaterials() {
  return await apiRequest(`${API}/materials`)
}

// ============ 参考文件 ============

export async function uploadReferenceFile(projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await authFetch(`${API}/projects/${projectId}/reference-files`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    throw new Error('上传失败')
  }
  return res.json()
}

export async function parseReferenceFile(projectId, fileId) {
  return await apiRequest(`${API}/projects/${projectId}/reference-files/${fileId}/parse`, {
    method: 'POST'
  })
}

export async function getReferenceFiles(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/reference-files`)
}

export async function getReferenceFile(projectId, fileId) {
  return await apiRequest(`${API}/projects/${projectId}/reference-files/${fileId}`)
}

export async function confirmReferenceFile(projectId, fileId) {
  return await apiRequest(`${API}/projects/${projectId}/reference-files/${fileId}/confirm`, {
    method: 'POST'
  })
}

export async function getReferenceFilePreview(fileId) {
  return await apiRequest(`${API}/reference-files/${fileId}`)
}

export async function refreshPlanningContext(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/planning-context/refresh`, {
    method: 'POST'
  })
}

// ============ 对话 ============

export async function getSessions(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/sessions`)
}

export async function createSession(projectId, content, metadata = null) {
  return await apiRequest(`${API}/projects/${projectId}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ content, metadata })
  })
}

export async function chat(projectId, message) {
  return await apiRequest(`${API}/projects/${projectId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ content: message })
  })
}

export async function generateOutlineFromDialog(projectId, content = null) {
  return await apiRequest(`${API}/projects/${projectId}/dialog/generate-outline`, {
    method: 'POST',
    body: JSON.stringify({ content })
  })
}

export async function confirmIntent(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/intent/confirm`, {
    method: 'POST'
  })
}

export async function fetchIntent(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/intent`)
}

// ============ 模板 ============

export async function getPresetTemplates() {
  return await apiRequest(`${API}/templates/presets`)
}

export async function getUserTemplates() {
  return await apiRequest(`${API}/templates/user`)
}

export async function createUserTemplate(data) {
  return await apiRequest(`${API}/user-templates`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function deleteUserTemplate(templateId) {
  return await apiRequest(`${API}/user-templates/${templateId}`, {
    method: 'DELETE'
  })
}

// 从图片提取风格描述
export async function extractStyleFromImage(file) {
  const formData = new FormData()
  formData.append('image', file)

  const res = await authFetch(`${API}/extract-style`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    throw new Error('风格提取失败')
  }
  return res.json()
}

// 上传用户模板图片
export async function uploadUserTemplate(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await authFetch(`${API}/user-templates/upload`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    throw new Error('上传模板失败')
  }
  return res.json()
}

export async function uploadProjectTemplate(projectId, file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await authFetch(`${API}/projects/${projectId}/template`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    throw new Error('上传失败')
  }
  return res.json()
}

// ============ 图片版本 ============

export async function getImageVersions(projectId, pageId) {
  return await apiRequest(`${API}/projects/${projectId}/pages/${pageId}/versions`)
}

export async function createImageVersion(projectId, pageId) {
  return await apiRequest(`${API}/projects/${projectId}/pages/${pageId}/versions`, {
    method: 'POST'
  })
}

export async function setCurrentVersion(projectId, pageId, versionId) {
  return await apiRequest(
    `${API}/projects/${projectId}/pages/${pageId}/versions/${versionId}/set-current`,
    { method: 'POST' }
  )
}

// ============ 任务 ============

export async function getTasks(projectId) {
  return await apiRequest(`${API}/projects/${projectId}/tasks`)
}

export async function getTask(projectId, taskId) {
  return await apiRequest(`${API}/projects/${projectId}/tasks/${taskId}`)
}

// ============ 文件生成 ============

export async function createFileGenerationProject({ file, sourceText, title, theme, templateStyle, settings }) {
  const formData = new FormData()
  if (file) formData.append('file', file)
  if (sourceText) formData.append('source_text', sourceText)
  if (title) formData.append('title', title)
  if (theme) formData.append('theme', theme)
  if (templateStyle) formData.append('template_style', templateStyle)
  if (settings) formData.append('settings', JSON.stringify(settings))

  const res = await authFetch(`${API}/projects/file-generation`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(detail || '创建文件生成项目失败')
  }
  return res.json()
}

// ============ 翻新 ============

export async function createRenovationProject({ file, keepLayout, templateStyle, language }) {
  const formData = new FormData()
  formData.append('file', file)
  if (keepLayout != null) formData.append('keep_layout', String(keepLayout))
  if (templateStyle) formData.append('template_style', templateStyle)
  if (language) formData.append('language', language)

  const res = await authFetch(`${API}/projects/renovation`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(detail || '创建翻新项目失败')
  }
  return res.json()
}

export async function regeneratePageRenovation(projectId, pageId) {
  return await apiRequest(
    `${API}/projects/${projectId}/pages/${pageId}/regenerate-renovation`,
    { method: 'POST' }
  )
}
