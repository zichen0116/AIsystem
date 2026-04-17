/**
 * PPT生成模块 - Pinia状态管理
 */
import { defineStore } from 'pinia'
import { apiRequest, authFetch } from '@/api/http'
import { createDefaultIntentState, normalizeIntentState, resolveIntentPhase } from '@/utils/pptIntent'
import {
  createFileGenerationProject as apiCreateFileGeneration,
  createRenovationProject as apiCreateRenovation,
  getTask as apiGetTask
} from '@/api/ppt'

const API = '/api/v1/ppt'

/** 将 points 数组中的每个元素强制转为字符串，防止 [object Object] */
function _sanitizePoints(points) {
  if (!Array.isArray(points)) return []
  return points.map(p => {
    if (typeof p === 'string') return p
    if (p && typeof p === 'object') return p.content || p.text || p.title || JSON.stringify(p)
    return String(p)
  }).filter(Boolean)
}

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
    intentState: createDefaultIntentState(),

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
    },

    // 文件生成任务
    fileGenerationTaskId: null,
    fileGenerationTaskStatus: null, // null | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
    fileGenerationTaskResult: null,
    _fileGenerationPollTimer: null,

    // 翻新任务
    renovationTaskId: null,
    renovationTaskStatus: null,
    renovationTaskResult: null,
    renovationFailedPages: [],
    _renovationPollTimer: null
  }),

  getters: {
    isLoggedIn: (state) => !!state.projectId,
    intentSummary: (state) => state.intentState?.intent_summary || {},
    confirmedIntent: (state) => state.intentState?.status === 'CONFIRMED' ? (state.intentState.intent_summary || {}) : null,
    isIntentReady: (state) => Boolean(state.intentState?.ready_for_confirmation),
    isIntentConfirmed: (state) => state.intentState?.status === 'CONFIRMED',

    completedPagesCount: (state) => {
      return Object.values(state.descriptions).filter(d => d && d.status === 'completed').length
    },

    totalPagesCount: (state) => state.outlinePages.length
  },

  actions: {
    resetIntentState(initialTopic = '') {
      this.intentState = createDefaultIntentState(initialTopic)
    },

    applyIntentPayload(payload, fallbackTopic = '') {
      this.intentState = normalizeIntentState(payload, fallbackTopic)
      return this.intentState
    },

    resetProjectWorkspace() {
      this.stopFileGenerationPolling()
      this.stopRenovationPolling()
      this.projectId = null
      this.projectStatus = null
      this.projectData = null
      this.creationType = null
      this.referenceFiles = []
      this.outlineText = ''
      this.outlinePages = []
      this.descriptions = {}
      this.sessions = []
      this.sessionMetrics = { round: 0, confidence: 0, phase: 'clarifying' }
      this.generationProgress = { total: 0, completed: 0, failed: 0 }
      this.materials = []
      this.exportTasks = []
      this.fileGenerationTaskId = null
      this.fileGenerationTaskStatus = null
      this.fileGenerationTaskResult = null
      this.renovationTaskId = null
      this.renovationTaskStatus = null
      this.renovationTaskResult = null
      this.renovationFailedPages = []
      this.resetIntentState()
    },
    // ============ 项目管理 ============

    async createProject(data) {
      try {
        this.resetProjectWorkspace()
        const response = await apiRequest(`${API}/projects`, {
          method: 'POST',
          body: JSON.stringify(data)
        })
        this.projectId = response.id
        this.projectData = response
        this.projectStatus = response.status
        this.creationType = data.creation_type
        this.outlineText = response.outline_text || data.outline_text || ''
        this.selectedPresetTemplateId = response.settings?.template_id || data?.settings?.template_id || null
        this.templateStyle = response.template_style || data.template_style || data?.settings?.template_style || ""
        this.aspectRatio = response.settings?.aspect_ratio || data?.settings?.aspect_ratio || this.aspectRatio
        this.resetIntentState(response.theme || this.outlineText)
        return response
      } catch (error) {
        this.setError('create', error.message)
        throw error
      }
    },

    async fetchProject(projectId) {
      try {
        if (this.projectId !== projectId) {
          this.resetProjectWorkspace()
        }
        const response = await apiRequest(`${API}/projects/${projectId}`)
        this.projectId = response.id
        this.projectData = response
        this.projectStatus = response.status
        this.creationType = response.creation_type
        this.outlineText = response.outline_text || ''
        this.selectedPresetTemplateId = response.settings?.template_id || null
        this.aspectRatio = response.settings?.aspect_ratio || this.aspectRatio
        if (response.settings && typeof response.settings === 'object') {
          this.projectSettings = { ...this.projectSettings, ...response.settings }
        }
        this.templateStyle = response.template_style || response.settings?.template_style || this.templateStyle
        this.resetIntentState(response.theme || this.outlineText)
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
        const mergedSettings = response?.settings && typeof response.settings === 'object'
          ? { ...this.projectSettings, ...response.settings }
          : { ...this.projectSettings, ...settingsData }
        this.projectSettings = mergedSettings
        this.templateStyle = response?.template_style || mergedSettings.template_style || this.templateStyle
        if (this.projectData) {
          this.projectData = { ...this.projectData, ...response, settings: mergedSettings }
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
          const config = p.config && typeof p.config === 'object' ? p.config : {}
          let points = _sanitizePoints(config.points)
          if (!points.length && p.description) {
            try {
              const parsed = JSON.parse(p.description)
              if (Array.isArray(parsed)) points = _sanitizePoints(parsed)
            } catch (e) {
              // description is plain text, not points array
            }
          }
          const part = config.part || ''
          const extraFields = config.extra_fields && typeof config.extra_fields === 'object'
            ? config.extra_fields
            : {}
          const renovationStatus = p.renovation_status || config.renovation_status || null
          const renovationError = p.renovation_error || config.renovation_error || null
          const pageStatus = renovationStatus === 'failed'
            ? 'failed'
            : (p.is_description_generating ? 'generating' : (p.description ? 'completed' : 'pending'))
          return {
            id: p.id,
            pageNumber: p.page_number,
            title: p.title,
            description: p.description,
            imagePrompt: p.image_prompt,
            notes: p.notes,
            imageUrl: p.image_url,
            isDescriptionGenerating: !!p.is_description_generating,
            isImageGenerating: !!p.is_image_generating,
            points,
            part,
            config,
            extraFields: {
              visual_element: extraFields.visual_element || '',
              visual_focus: extraFields.visual_focus || '',
              layout: extraFields.layout || '',
              ...extraFields,
              notes: p.notes || ''
            },
            status: pageStatus,
            renovationStatus,
            renovationError
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
          const config = page.config && typeof page.config === 'object' ? page.config : {}
          const extraFields = config.extra_fields && typeof config.extra_fields === 'object'
            ? config.extra_fields
            : {}
          this.outlinePages[idx] = {
            ...this.outlinePages[idx],
            pageNumber: page.page_number ?? this.outlinePages[idx].pageNumber,
            title: page.title,
            description: page.description,
            imagePrompt: page.image_prompt,
            notes: page.notes,
            imageUrl: page.image_url,
            isDescriptionGenerating: !!page.is_description_generating,
            isImageGenerating: !!page.is_image_generating,
            config,
            extraFields: {
              visual_element: extraFields.visual_element || '',
              visual_focus: extraFields.visual_focus || '',
              layout: extraFields.layout || '',
              ...extraFields,
              notes: page.notes || ''
            },
            status: (page.renovation_status || config.renovation_status) === 'failed'
              ? 'failed'
              : (page.is_description_generating ? 'generating' : (page.description ? 'completed' : 'pending')),
            renovationStatus: page.renovation_status || config.renovation_status || null,
            renovationError: page.renovation_error || config.renovation_error || null
          }
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
      this.outlineText = ''
      this.generationProgress = { total: 0, completed: 0, failed: 0 }

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
              } else if (event.type === 'reset_pages') {
                this.outlinePages = []
              } else if (event.type === 'page' && event.page) {
                const page = event.page
                const pageId = Number(page.id)
                const normalizedPage = {
                  id: pageId,
                  pageNumber: Number(page.page_number) || (this.outlinePages.length + 1),
                  title: page.title || '未命名',
                  description: page.description || '',
                  imagePrompt: page.image_prompt || '',
                  notes: page.notes || '',
                  imageUrl: page.image_url || '',
                  isDescriptionGenerating: false,
                  isImageGenerating: false,
                  points: _sanitizePoints(page.points),
                  part: page.part || '',
                  config: {
                    points: _sanitizePoints(page.points),
                    part: page.part || ''
                  },
                  extraFields: {
                    visual_element: '',
                    visual_focus: '',
                    layout: '',
                    notes: ''
                  },
                  status: 'pending'
                }

                const idx = this.outlinePages.findIndex(p => Number(p.id) === pageId)
                if (idx !== -1) {
                  this.outlinePages[idx] = { ...this.outlinePages[idx], ...normalizedPage }
                } else {
                  this.outlinePages.push(normalizedPage)
                }
              } else if (event.type === 'progress') {
                this.generationProgress = {
                  total: Number(event.total) || this.generationProgress.total,
                  completed: Number(event.current) || this.generationProgress.completed,
                  failed: 0
                }
              } else if (event.type === 'done') {
                if (this.generationProgress.total > 0) {
                  this.generationProgress = {
                    ...this.generationProgress,
                    completed: this.generationProgress.total
                  }
                }
                return
              } else if (event.type === 'error') {
                throw new Error(event.message || '大纲生成失败')
              }
            } catch (e) {
              if (!(e instanceof SyntaxError)) throw e
              // ignore JSON parse errors from malformed SSE lines
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
      const { language = 'zh', detail_level = 'default', page_ids } = options

      const response = await authFetch(
        `${API}/projects/${projectId}/descriptions/generate/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language, detail_level, page_ids })
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
          {
            const idx = this.outlinePages.findIndex(page => page.id === event.page_id)
            if (idx !== -1) {
              this.outlinePages[idx] = {
                ...this.outlinePages[idx],
                description: event.content,
                status: 'completed'
              }
            }
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
        const fallbackTopic = this.projectData?.theme || this.outlineText || ''
        this.applyIntentPayload(response.intent_state || response.intent, fallbackTopic)
        this.sessionMetrics = {
          round: this.intentState.round || response.round || this.sessionMetrics.round,
          confidence: this.intentState.confidence,
          phase: this.intentState.status === 'CONFIRMED' ? 'confirmed' : (this.intentState.ready_for_confirmation ? 'ready' : 'clarifying')
        }

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
        const fallbackTopic = this.projectData?.theme || this.outlineText || ''
        this.applyIntentPayload(response.intent, fallbackTopic)
        this.projectStatus = 'INTENT_CONFIRMED'
        if (this.projectData) {
          this.projectData = { ...this.projectData, status: 'INTENT_CONFIRMED' }
        }
        return response
      } catch (error) {
        this.setError('confirmIntent', error.message)
        throw error
      }
    },

    async fetchIntent(projectId) {
      try {
        const response = await apiRequest(`${API}/projects/${projectId}/intent`)
        const fallbackTopic = this.projectData?.theme || this.outlineText || ''
        this.applyIntentPayload(response.intent, fallbackTopic)
        return response
      } catch (error) {
        this.setError('fetchIntent', error.message)
        throw error
      }
    },

    // ============ 参考文件 ============

    async loadProjectWorkspace(projectId) {
      await this.fetchProject(projectId)
      await this.fetchPages(projectId)
      if (this.creationType === 'dialog') {
        try {
          await this.fetchIntent(projectId)
        } catch (_) {
          this.resetIntentState(this.projectData?.theme || this.outlineText || '')
        }
      } else {
        this.resetIntentState(this.projectData?.theme || this.outlineText || '')
      }

      // 翻新项目：同步失败页信息，并检查是否需要恢复轮询
      if (this.creationType === 'renovation') {
        this.syncRenovationFailedPages()
        if (this.projectStatus === 'PARSE' || this.projectStatus === 'GENERATING') {
          try {
            const { getTasks } = await import('@/api/ppt')
            const tasks = await getTasks(projectId)
            const activeTask = tasks.find(t =>
              t.task_type === 'renovation_parse' && (t.status === 'PENDING' || t.status === 'PROCESSING')
            )
            if (activeTask) {
              this.renovationTaskId = activeTask.task_id
              this.renovationTaskStatus = activeTask.status
              this.pollRenovationTask(projectId, activeTask.task_id)
            }
          } catch (_) { /* ignore */ }
        }
      }

      // 文件生成项目：检查是否需要恢复轮询
      if (this.creationType === 'file' && (this.projectStatus === 'GENERATING')) {
        try {
          const { getTasks } = await import('@/api/ppt')
          const tasks = await getTasks(projectId)
          const activeTask = tasks.find(t =>
            t.task_type === 'file_generation' && (t.status === 'PENDING' || t.status === 'PROCESSING')
          )
          if (activeTask) {
            this.fileGenerationTaskId = activeTask.task_id
            this.fileGenerationTaskStatus = activeTask.status
            this.pollFileGenerationTask(projectId, activeTask.task_id)
          }
        } catch (_) { /* ignore */ }
      }

      this.setPhase(resolveIntentPhase(this.projectData, this.outlinePages.length, this.intentState))
    },

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

    // ============ 文件生成 ============

    async createFileGenerationProject(payload) {
      try {
        this.resetProjectWorkspace()
        const res = await apiCreateFileGeneration(payload)
        this.projectId = res.project_id
        this.creationType = 'file'
        this.projectStatus = 'GENERATING'
        this.fileGenerationTaskId = res.task_id
        this.fileGenerationTaskStatus = 'PROCESSING'
        return res
      } catch (error) {
        this.setError('createFileGeneration', error.message)
        throw error
      }
    },

    pollFileGenerationTask(projectId, taskId) {
      this.stopFileGenerationPolling()
      this._fileGenerationPollTimer = setInterval(async () => {
        try {
          const task = await apiGetTask(projectId, taskId)
          this.fileGenerationTaskStatus = task.status
          this.fileGenerationTaskResult = task.result
          if (task.status === 'COMPLETED') {
            this.stopFileGenerationPolling()
            await this.fetchProject(projectId)
            await this.fetchPages(projectId)
          } else if (task.status === 'FAILED') {
            this.stopFileGenerationPolling()
            await this.fetchProject(projectId)
            await this.fetchPages(projectId)
          }
        } catch (e) {
          console.error('[PPT Store] 文件生成轮询失败:', e)
          this.stopFileGenerationPolling()
          this.fileGenerationTaskStatus = 'FAILED'
        }
      }, 3000)
    },

    stopFileGenerationPolling() {
      if (this._fileGenerationPollTimer) {
        clearInterval(this._fileGenerationPollTimer)
        this._fileGenerationPollTimer = null
      }
    },

    // ============ 翻新 ============

    async createRenovationProjectAction(payload) {
      try {
        this.resetProjectWorkspace()
        const res = await apiCreateRenovation(payload)
        this.projectId = res.project_id
        this.creationType = 'renovation'
        this.projectStatus = 'PARSE'
        this.renovationTaskId = res.task_id
        this.renovationTaskStatus = 'PROCESSING'
        return res
      } catch (error) {
        this.setError('createRenovation', error.message)
        throw error
      }
    },

    pollRenovationTask(projectId, taskId) {
      this.stopRenovationPolling()
      this._renovationPollTimer = setInterval(async () => {
        try {
          const task = await apiGetTask(projectId, taskId)
          this.renovationTaskStatus = task.status
          this.renovationTaskResult = task.result
          if (task.status === 'COMPLETED' || task.status === 'FAILED') {
            this.stopRenovationPolling()
            await this.fetchProject(projectId)
            await this.fetchPages(projectId)
            this.syncRenovationFailedPages()
          }
        } catch (e) {
          console.error('[PPT Store] 翻新轮询失败:', e)
          this.stopRenovationPolling()
          this.renovationTaskStatus = 'FAILED'
        }
      }, 3000)
    },

    stopRenovationPolling() {
      if (this._renovationPollTimer) {
        clearInterval(this._renovationPollTimer)
        this._renovationPollTimer = null
      }
    },

    syncRenovationFailedPages() {
      this.renovationFailedPages = this.outlinePages
        .filter(p => p.renovationStatus === 'failed')
        .map(p => ({ id: p.id, title: p.title, error: p.renovationError || '' }))
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
      this.resetProjectWorkspace()
      this.currentPhase = 'home'
      this.selectedTemplate = null
      this.selectedPresetTemplateId = null
      this.templateStyle = ''
      this.aspectRatio = '16:9'
      this.error = null
      this.errorMessage = null
    }
  }
})
