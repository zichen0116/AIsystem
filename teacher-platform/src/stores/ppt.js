/**
 * PPT生成模块 - Pinia状态管理
 */
import { defineStore } from 'pinia'
import { apiRequest, authFetch } from '@/api/http'

const API = '/api/v1/ppt'

export const usePptStore = defineStore('ppt', {
  state: () => ({
    // 项目信息
    projectId: null,
    projectStatus: null,
    projectData: null,

    // 流程控制
    creationType: null, // 'dialog' | 'file' | 'renovation'
    currentPhase: 'home', // 'home' | 'dialog' | 'outline' | 'description' | 'preview'

    // 模板与风格
    selectedTemplate: null,
    selectedPresetTemplateId: null,
    templateStyle: '',
    aspectRatio: '16:9',

    // 参考文件
    referenceFiles: [],

    // 大纲数据
    outlineText: '',
    outlinePages: [],

    // 描述数据
    descriptions: {},

    // 已确认的意图摘要
    confirmedIntent: null,

    // 对话历史（对话页用）
    sessions: [],
    sessionMetrics: {
      round: 0,
      confidence: 0,
      phase: 'clarifying'
    },

    // 生成进度
    generationProgress: { total: 0, completed: 0, failed: 0 },

    // 错误状态
    error: null,
    errorMessage: null,

    // 素材
    materials: [],

    // 导出任务
    exportTasks: [],

    // 项目设置
    projectSettings: {
      description_generation_mode: 'auto',
      description_extra_fields: ['visual_element', 'visual_focus', 'layout', 'notes'],
      detail_level: 'default'
    }
  }),

  getters: {
    isLoggedIn: (state) => !!state.projectId,

    completedPagesCount: (state) => {
      return Object.values(state.descriptions).filter(d => d && d.status === 'completed').length
    },

    totalPagesCount: (state) => state.outlinePages.length
  },

  actions: {
    // ============ 项目管理 ============

    async createProject(data) {
      try {
        const response = await apiRequest(`${API}/projects`, {
          method: 'POST',
          body: JSON.stringify(data)
        })
        this.projectId = response.id
        this.projectData = response
        this.creationType = data.creation_type
        return response
      } catch (error) {
        this.setError('create', error.message)
        throw error
      }
    },

    async fetchProject(projectId) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}`)
        this.projectId = response.id
        this.projectData = response
        this.projectStatus = response.status
        this.creationType = response.creation_type
        this.outlineText = response.outline_text || ''
        if (response.settings && typeof response.settings === 'object') {
          this.projectSettings = { ...this.projectSettings, ...response.settings }
        }
        return response
      } catch (error) {
        this.setError('fetch', error.message)
        throw error
      }
    },

    async updateSettings(projectId, settingsData) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}/settings`, {
          method: 'PUT',
          body: JSON.stringify(settingsData)
        })
        this.projectSettings = { ...this.projectSettings, ...settingsData }
        if (this.projectData) {
          this.projectData = { ...this.projectData, settings: this.projectSettings }
        }
        return response
      } catch (error) {
        this.setError('updateSettings', error.message)
        throw error
      }
    },

    async updateProject(projectId, data) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}`, {
          method: 'PUT',
          body: JSON.stringify(data)
        })
        if (this.projectData?.id === projectId) {
          this.projectData = { ...this.projectData, ...response }
        }
        return response
      } catch (error) {
        this.setError('update', error.message)
        throw error
      }
    },

    async deleteProject(projectId) {
      try {
        await apiRequest(`${API}/projects/${projectId}`, { method: 'DELETE' })
        if (this.projectId === projectId) {
          this.resetState()
        }
      } catch (error) {
        this.setError('delete', error.message)
        throw error
      }
    },

    async listProjects() {
      try {
        return await apiRequest(`${API}/projects`)
      } catch (error) {
        this.setError('list', error.message)
        throw error
      }
    },

    // ============ 页面管理 ============

    async fetchPages(projectId) {
      try {
        const pages = await apiRequest(`${API}/projects/${projectId}/pages`)
        this.outlinePages = pages.map(p => {
          // points are stored as JSON array in description field
          let points = []
          if (p.description) {
            try {
              const parsed = JSON.parse(p.description)
              if (Array.isArray(parsed)) points = parsed
            } catch (e) {
              // description is plain text, not points array
            }
          }
          // part is stored in config.part
          const part = (p.config && p.config.part) ? p.config.part : ''
          return {
            id: p.id,
            pageNumber: p.page_number,
            title: p.title,
            description: p.description,
            imagePrompt: p.image_prompt,
            notes: p.notes,
            imageUrl: p.image_url,
            points,
            part,
            status: p.is_description_generating ? 'generating' : (p.description ? 'completed' : 'pending')
          }
        })
        return pages
      } catch (error) {
        this.setError('fetchPages', error.message)
        throw error
      }
    },

    async createPage(projectId, data) {
      try {
        const page = await apiRequest(`${API}/projects/${projectId}/pages`, {
          method: 'POST',
          body: JSON.stringify(data)
        })
        this.outlinePages.push({
          id: page.id,
          pageNumber: page.page_number,
          title: page.title,
          description: page.description,
          status: 'pending'
        })
        return page
      } catch (error) {
        this.setError('createPage', error.message)
        throw error
      }
    },

    async updatePage(projectId, pageId, data) {
      try {
        const page = await apiRequest(`${API}/projects/${projectId}/pages/${pageId}`, {
          method: 'PUT',
          body: JSON.stringify(data)
        })
        const idx = this.outlinePages.findIndex(p => p.id === pageId)
        if (idx !== -1) {
          this.outlinePages[idx] = { ...this.outlinePages[idx], ...page }
        }
        return page
      } catch (error) {
        this.setError('updatePage', error.message)
        throw error
      }
    },

    async deletePage(projectId, pageId) {
      try {
        await apiRequest(`${API}/projects/${projectId}/pages/${pageId}`, { method: 'DELETE' })
        this.outlinePages = this.outlinePages.filter(p => p.id !== pageId)
      } catch (error) {
        this.setError('deletePage', error.message)
        throw error
      }
    },

    async reorderPages(projectId, pageIds) {
      try {
        await apiRequest(`${API}/projects/${projectId}/pages/reorder`, {
          method: 'POST',
          body: JSON.stringify({ page_ids: pageIds })
        })
        // 重新排序本地数据
        const sorted = pageIds.map((id, idx) => {
          const page = this.outlinePages.find(p => p.id === id)
          return page ? { ...page, pageNumber: idx + 1 } : null
        }).filter(Boolean)
        this.outlinePages = sorted
      } catch (error) {
        this.setError('reorderPages', error.message)
        throw error
      }
    },

    addPage(page) {
      this.outlinePages.push({
        id: page.id || Date.now(),
        pageNumber: this.outlinePages.length + 1,
        title: page.title || '新页面',
        points: page.points || [],
        part: page.part || '',
        status: 'pending'
      })
    },

    deletePageLocal(pageId) {
      this.outlinePages = this.outlinePages.filter(p => p.id !== pageId)
    },

    updatePageLocal(pageId, data) {
      const idx = this.outlinePages.findIndex(p => p.id === pageId)
      if (idx !== -1) {
        this.outlinePages[idx] = { ...this.outlinePages[idx], ...data }
      }
    },

    reorderPagesLocal(newOrder) {
      this.outlinePages = newOrder.map((id, idx) => {
        const page = this.outlinePages.find(p => p.id === id)
        return page ? { ...page, pageNumber: idx + 1 } : null
      }).filter(Boolean)
    },

    // ============ 大纲生成 ============

    async parseOutline(projectId) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}/outline/generate`, {
          method: 'POST'
        })
        return response
      } catch (error) {
        this.setError('parseOutline', error.message)
        throw error
      }
    },

    async generateOutlineStream(projectId, ideaPrompt) {
      const response = await authFetch(`${API}/projects/${projectId}/outline/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea_prompt: ideaPrompt })
      })

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
              const event = JSON.parse(line.slice(6))
              if (event.type === 'outline_chunk') {
                this.outlineText += event.content
              } else if (event.type === 'done') {
                return
              }
            } catch (e) {
              // ignore parse errors
            }
          }
        }
      }
    },

    // ============ 描述生成 ============

    async generateDescriptions(projectId, pageIds = null) {
      try {
        const url = pageIds
          ? `${API}/projects/${projectId}/descriptions/generate?page_ids=${pageIds.join(',')}`
          : `${API}/projects/${projectId}/descriptions/generate`
        return await apiRequest(url, { method: 'POST' })
      } catch (error) {
        this.setError('generateDescriptions', error.message)
        throw error
      }
    },

    async generateDescriptionsStream(projectId, options = {}) {
      const { language = 'zh', detail_level = 'default' } = options

      const response = await authFetch(
        `${API}/projects/${projectId}/descriptions/generate/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language, detail_level })
        }
      )

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
              const event = JSON.parse(line.slice(6))
              this.handleDescriptionEvent(event)
            } catch (e) {
              // ignore parse errors
            }
          }
        }
      }
    },

    handleDescriptionEvent(event) {
      switch (event.type) {
        case 'page':
          this.descriptions[event.page_id] = {
            content: event.content,
            status: 'completed'
          }
          break
        case 'progress':
          this.generationProgress = {
            total: event.total,
            completed: event.completed,
            failed: event.failed || 0
          }
          break
        case 'done':
          this.generationProgress = { ...this.generationProgress, completed: this.generationProgress.total }
          break
        case 'error':
          this.setError('generate', event.message)
          break
      }
    },

    // ============ 对话管理 ============

    async fetchSessions(projectId) {
      try {
        const sessions = await apiRequest(`${API}/projects/${projectId}/sessions`)
        this.sessions = sessions
        return sessions
      } catch (error) {
        this.setError('fetchSessions', error.message)
        throw error
      }
    },

    async saveSession(projectId, role, content, metadata = null) {
      try {
        const session = await apiRequest(`${API}/projects/${projectId}/sessions`, {
          method: 'POST',
          body: JSON.stringify({ content, metadata })
        })
        this.sessions.push(session)
        return session
      } catch (error) {
        this.setError('saveSession', error.message)
        throw error
      }
    },

    async sendChat(projectId, message) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}/chat`, {
          method: 'POST',
          body: JSON.stringify({ content: message })
        })

        // 保存用户消息和AI回复
        await this.saveSession(projectId, 'user', message)
        await this.saveSession(projectId, 'assistant', response.message)

        return response
      } catch (error) {
        this.setError('chat', error.message)
        throw error
      }
    },

    // ============ 意图确认 ============

    async confirmIntent(projectId) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}/intent/confirm`, {
          method: 'POST'
        })
        this.confirmedIntent = response.intent_summary || {}
        this.projectStatus = 'INTENT_CONFIRMED'
        return response
      } catch (error) {
        this.setError('confirmIntent', error.message)
        throw error
      }
    },

    async fetchIntent(projectId) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}/intent`)
        this.confirmedIntent = response.intent_summary || null
        return response
      } catch (error) {
        this.setError('fetchIntent', error.message)
        throw error
      }
    },

    // ============ 参考文件 ============

    async uploadReferenceFile(projectId, file) {
      try {
        const formData = new FormData()
        formData.append('file', file)

        const res = await authFetch(`${API}/projects/${projectId}/reference-files`, {
          method: 'POST',
          body: formData
        })

        if (res.ok) {
          const fileData = await res.json()
          this.referenceFiles.push(fileData)
          return fileData
        } else {
          throw new Error('上传失败')
        }
      } catch (error) {
        this.setError('uploadRef', error.message)
        throw error
      }
    },

    async parseReferenceFile(projectId, fileId) {
      try {
        await apiRequest(`${API}/projects/${projectId}/reference-files/${fileId}/parse`, {
          method: 'POST'
        })
        const idx = this.referenceFiles.findIndex(f => f.id === fileId)
        if (idx !== -1) {
          this.referenceFiles[idx].parse_status = 'processing'
        }
      } catch (error) {
        this.setError('parseRef', error.message)
        throw error
      }
    },

    // ============ 素材 ============

    async fetchMaterials(projectId) {
      try {
        const materials = await apiRequest(`${API}/projects/${projectId}/materials`)
        this.materials = materials
        return materials
      } catch (error) {
        this.setError('fetchMaterials', error.message)
        throw error
      }
    },

    // ============ 模板 ============

    async fetchPresetTemplates() {
      try {
        return await apiRequest(`${API}/templates/presets`)
      } catch (error) {
        this.setError('fetchTemplates', error.message)
        throw error
      }
    },

    async fetchUserTemplates() {
      try {
        return await apiRequest(`${API}/templates/user`)
      } catch (error) {
        this.setError('fetchTemplates', error.message)
        throw error
      }
    },

    // ============ 错误处理 ============

    setError(type, message) {
      this.error = type
      this.errorMessage = message
      console.error(`[PPT Store Error] ${type}:`, message)
    },

    clearError() {
      this.error = null
      this.errorMessage = null
    },

    // ============ 流程控制 ============

    setPhase(phase) {
      this.currentPhase = phase
    },

    // ============ 状态重置 ============

    resetState() {
      this.projectId = null
      this.projectStatus = null
      this.projectData = null
      this.creationType = null
      this.currentPhase = 'home'
      this.selectedTemplate = null
      this.selectedPresetTemplateId = null
      this.templateStyle = ''
      this.aspectRatio = '16:9'
      this.referenceFiles = []
      this.outlineText = ''
      this.outlinePages = []
      this.descriptions = {}
      this.confirmedIntent = null
      this.sessions = []
      this.sessionMetrics = { round: 0, confidence: 0, phase: 'clarifying' }
      this.generationProgress = { total: 0, completed: 0, failed: 0 }
      this.error = null
      this.errorMessage = null
      this.materials = []
      this.exportTasks = []
    }
  }
})
