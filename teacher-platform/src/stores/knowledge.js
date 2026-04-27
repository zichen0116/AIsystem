import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiRequest, authFetch } from '../api/http'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const libraries = ref([])
  const total = ref(0)
  const userTags = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchLibraries({ scope = 'all', search = '', tag = '', page = 1, pageSize = 50 } = {}) {
    loading.value = true
    error.value = null
    try {
      const params = new URLSearchParams()
      params.set('scope', scope)
      params.set('page', String(page))
      params.set('page_size', String(pageSize))
      if (search) params.set('search', search)
      if (tag) params.set('tag', tag)

      const data = await apiRequest(`/api/v1/libraries?${params}`)
      libraries.value = data.items
      total.value = data.total
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createLibrary({ name, description, tags, isPublic }) {
    const payload = { name, description, tags: tags || [] }
    if (isPublic !== undefined) payload.is_public = isPublic
    const body = JSON.stringify(payload)
    const data = await apiRequest('/api/v1/libraries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    return data
  }

  async function updateLibrary(id, { name, description, tags, isPublic }) {
    const payload = {}
    if (name !== undefined) payload.name = name
    if (description !== undefined) payload.description = description
    if (tags !== undefined) payload.tags = tags
    if (isPublic !== undefined) payload.is_public = isPublic
    const body = JSON.stringify(payload)
    const data = await apiRequest(`/api/v1/libraries/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    return data
  }

  async function deleteLibrary(id) {
    await apiRequest(`/api/v1/libraries/${id}`, { method: 'DELETE' })
  }

  async function fetchUserTags() {
    try {
      const data = await apiRequest('/api/v1/libraries/tags')
      userTags.value = data
    } catch {
      userTags.value = []
    }
  }

  async function renameTag(oldName, newName) {
    const body = JSON.stringify({ old_name: oldName, new_name: newName })
    const data = await apiRequest('/api/v1/libraries/tags/rename', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    return data
  }

  async function uploadFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await authFetch('/api/v1/upload', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}))
      throw new Error(detail.detail || `上传失败 (${res.status})`)
    }
    return await res.json()
  }

  async function createAsset({ fileName, fileType, filePath, libraryId }) {
    const body = JSON.stringify({
      file_name: fileName,
      file_type: fileType,
      file_path: filePath,
      library_id: libraryId,
    })
    return await apiRequest('/api/v1/knowledge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
  }

  async function fetchAssets(libraryId, { page = 1, pageSize = 50 } = {}) {
    const params = new URLSearchParams()
    params.set('library_id', String(libraryId))
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    return await apiRequest(`/api/v1/knowledge?${params}`)
  }

  async function deleteAsset(assetId) {
    await apiRequest(`/api/v1/knowledge/${assetId}`, { method: 'DELETE' })
  }

  async function getAssetStatus(assetId) {
    return await apiRequest(`/api/v1/knowledge/${assetId}/status`)
  }

  return {
    libraries,
    total,
    userTags,
    loading,
    error,
    fetchLibraries,
    createLibrary,
    updateLibrary,
    deleteLibrary,
    fetchUserTags,
    renameTag,
    uploadFile,
    createAsset,
    fetchAssets,
    deleteAsset,
    getAssetStatus,
  }
})
