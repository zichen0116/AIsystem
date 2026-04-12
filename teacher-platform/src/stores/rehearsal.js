// teacher-platform/src/stores/rehearsal.js
import { defineStore } from 'pinia'
import {
  generateRehearsalStream,
  uploadRehearsalFile,
  fetchSessions,
  fetchSession,
  fetchScene,
  retryScene,
  updatePlaybackSnapshot,
  deleteSession,
} from '../api/rehearsal.js'


const PLAYABLE_SCENE_STATUSES = new Set(['ready', 'fallback'])

function estimateSpeechDuration(text) {
  const normalized = String(text || '').trim()
  if (!normalized) return 3000
  const cjkChars = Array.from(normalized).filter(char => /[一-鿿]/.test(char)).length
  const latinWords = normalized.replace(/[一-鿿]/g, ' ').trim().split(/\s+/).filter(Boolean).length
  return Math.max(cjkChars * 150 + latinWords * 240, 2000)
}

export const useRehearsalStore = defineStore('rehearsal', {
  state: () => ({
    // 当前会话
    currentSession: null,
    scenes: [],

    // 播放状态
    currentSceneIndex: 0,
    currentActionIndex: 0,
    playbackState: 'idle', // idle | playing | paused

    // 视觉效果
    spotlightTarget: null,
    highlightTarget: null,
    laserTarget: null,
    currentSubtitle: '',

    // 生成状态
    generatingStatus: null, // null | generating | complete | error
    generatingProgress: '',
    totalScenes: 0,
    sceneStatuses: [], // [{sceneIndex, status, title}]

    // 历史列表
    sessions: [],
    sessionsLoading: false,
  }),

  getters: {
    currentScene(state) {
      return state.scenes[state.currentSceneIndex] || null
    },
    totalScenesCount(state) {
      return state.scenes.length
    },
    isPlaying(state) {
      return state.playbackState === 'playing'
    },
    isPaused(state) {
      return state.playbackState === 'paused'
    },
    readySceneCount(state) {
      return state.sceneStatuses.filter(s => PLAYABLE_SCENE_STATUSES.has(s.status)).length
    },
    failedSceneCount(state) {
      return state.sceneStatuses.filter(s => s.status === 'failed').length
    },
  },

  actions: {
    _mapScene(rawScene) {
      const source = this.currentSession?.source || 'topic'
      const slideContent = rawScene.slide_content || this._buildUploadSlide(rawScene)
      const actions = Array.isArray(rawScene.actions) && rawScene.actions.length > 0
        ? rawScene.actions
        : this._buildUploadActions(rawScene)

      return {
        sceneOrder: rawScene.scene_order,
        title: rawScene.title,
        slideContent,
        actions,
        keyPoints: rawScene.key_points,
        sceneStatus: rawScene.scene_status,
        audioStatus: rawScene.audio_status,
        source,
        pageImageUrl: rawScene.page_image_url,
        scriptText: rawScene.script_text,
      }
    },

    _buildUploadSlide(rawScene) {
      if (rawScene.page_image_url) {
        return {
          id: `upload-slide-${rawScene.id || rawScene.scene_order}`,
          viewportSize: 1000,
          viewportRatio: 0.5625,
          background: { type: 'solid', color: '#0f172a' },
          elements: [
            {
              id: `upload-page-image-${rawScene.id || rawScene.scene_order}`,
              type: 'image',
              src: rawScene.page_image_url,
              left: 0,
              top: 0,
              width: 1000,
              height: 562,
            },
          ],
        }
      }

      return {
        id: `upload-fallback-${rawScene.id || rawScene.scene_order}`,
        viewportSize: 1000,
        viewportRatio: 0.5625,
        background: { type: 'solid', color: '#ffffff' },
        elements: [
          {
            id: `upload-title-${rawScene.id || rawScene.scene_order}`,
            type: 'text',
            content: `<p style="font-size:32px;font-weight:700;margin:0;">${rawScene.title || 'Uploaded page'}</p>`,
            left: 60,
            top: 56,
            width: 880,
            height: 56,
          },
          {
            id: `upload-text-${rawScene.id || rawScene.scene_order}`,
            type: 'text',
            content: `<p style="font-size:18px;line-height:1.8;margin:0;">${rawScene.page_text || rawScene.script_text || 'This page will be explained in narration mode.'}</p>`,
            left: 60,
            top: 144,
            width: 880,
            height: 320,
          },
        ],
      }
    },

    _buildUploadActions(rawScene) {
      const text = rawScene.script_text || rawScene.page_text || rawScene.title
      if (!text) return []

      return [{
        type: 'speech',
        text,
        duration: estimateSpeechDuration(text),
        audio_status: rawScene.audio_status || 'failed',
        ...(rawScene.audio_url ? { persistent_audio_url: rawScene.audio_url } : {}),
      }]
    },

    _mapSceneStatus(rawScene) {
      return {
        sceneIndex: rawScene.scene_order,
        status: rawScene.scene_status,
        title: rawScene.title,
        sceneId: rawScene.id,
      }
    },

    _replaceReadyScenes(rawScenes, preserveSceneOrder = null) {
      this.scenes = (rawScenes || [])
        .filter(scene => PLAYABLE_SCENE_STATUSES.has(scene.scene_status))
        .map(scene => this._mapScene(scene))
        .sort((a, b) => a.sceneOrder - b.sceneOrder)

      if (preserveSceneOrder === null) return

      const matchedIndex = this.scenes.findIndex(scene => scene.sceneOrder === preserveSceneOrder)
      if (matchedIndex >= 0) {
        this.currentSceneIndex = matchedIndex
        return
      }

      this.currentSceneIndex = this.scenes.length > 0
        ? Math.min(this.currentSceneIndex, this.scenes.length - 1)
        : 0
    },

    // --- SSE 生成（通知模式） ---
    async startGenerate(params) {
      this.generatingStatus = 'generating'
      this.generatingProgress = '正在生成大纲...'
      this.scenes = []
      this.sceneStatuses = []
      this.currentSession = null
      this.totalScenes = 0

      try {
        const resp = await generateRehearsalStream(params)
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${resp.status}`)
        }
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop()

          let eventType = null
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                this._handleSSEEvent(eventType, data)
              } catch {
                // ignore malformed SSE payloads
              }
              eventType = null
            }
          }
        }

        if (this.generatingStatus === 'generating') {
          this.generatingStatus = 'complete'
        }
      } catch (e) {
        this.generatingStatus = 'error'
        this.generatingProgress = `生成失败: ${e.message}`
      }
    },

    _handleSSEEvent(eventType, data) {
      switch (eventType) {
        case 'session_created':
          this.currentSession = { id: data.sessionId, title: data.title }
          break

        case 'outline_ready':
          this.totalScenes = data.totalScenes
          this.generatingProgress = `大纲就绪，共 ${data.totalScenes} 页，正在生成第 1 页...`
          break

        case 'scene_status': {
          this.sceneStatuses.push({
            sceneIndex: data.sceneIndex,
            status: data.status,
            title: data.title,
            sceneId: data.sceneId,
          })
          const readyCount = this.sceneStatuses.filter(s => s.status === 'ready').length
          const failedCount = this.sceneStatuses.filter(s => s.status === 'failed').length
          this.generatingProgress = `已完成 ${readyCount + failedCount}/${this.totalScenes} 页`
            + (failedCount > 0 ? `（${failedCount} 页失败）` : '') + '...'

          if (data.status === 'ready' && this.currentSession?.id) {
            this._fetchScene(this.currentSession.id, data.sceneIndex)
          }
          break
        }

        case 'complete':
          this.generatingStatus = 'complete'
          this.generatingProgress = '生成完成'
          if (this.currentSession) {
            this.currentSession.status = data.status
          }
          break

        case 'error':
          this.generatingStatus = 'error'
          this.generatingProgress = `生成失败: ${data.message}`
          break
      }
    },

    async _fetchScene(sessionId, sceneOrder) {
      try {
        const scene = await fetchScene(sessionId, sceneOrder)
        const existing = this.scenes.findIndex(s => s.sceneOrder === sceneOrder)
        const mapped = this._mapScene(scene)
        if (existing >= 0) {
          this.scenes[existing] = mapped
        } else {
          this.scenes.push(mapped)
          this.scenes.sort((a, b) => a.sceneOrder - b.sceneOrder)
        }
      } catch (e) {
        console.error(`Failed to fetch scene ${sceneOrder}:`, e)
      }
    },

    // --- 播放控制 ---
    clearVisualEffects() {
      this.spotlightTarget = null
      this.highlightTarget = null
      this.laserTarget = null
    },

    clearSpeechBoundEffects() {
      this.spotlightTarget = null
      this.highlightTarget = null
    },

    clearEffects() {
      this.clearVisualEffects()
      this.currentSubtitle = ''
    },

    setSceneIndex(index) {
      this.currentSceneIndex = index
      this.currentActionIndex = 0
      this.clearEffects()
    },

    // --- 页面重试 ---
    async retryFailedScene(sessionId, sceneOrder) {
      const result = await retryScene(sessionId, sceneOrder)
      if (result.scene_status === 'ready') {
        await this._fetchScene(sessionId, sceneOrder)
        const idx = this.sceneStatuses.findIndex(s => s.sceneIndex === sceneOrder)
        if (idx >= 0) this.sceneStatuses[idx].status = 'ready'
      }
      return result.scene_status
    },

    // --- 会话 CRUD ---
    async uploadSessionFile(file) {
      this.generatingStatus = 'generating'
      this.generatingProgress = '正在上传文件...'
      this.currentSession = null
      this.scenes = []
      this.sceneStatuses = []
      this.totalScenes = 0

      try {
        const payload = await uploadRehearsalFile(file)
        this.currentSession = {
          id: payload.session_id,
          title: file.name.replace(/\.[^.]+$/, '') || '上传预演',
          status: 'processing',
          source: payload.source || 'upload',
        }
        this.generatingProgress = `上传成功，共 ${payload.total_pages || 0} 页，正在进入文件处理流程...`
        return payload
      } catch (error) {
        this.generatingStatus = null
        this.generatingProgress = ''
        this.currentSession = null
        this.scenes = []
        this.sceneStatuses = []
        this.totalScenes = 0
        throw error
      }
    },

    async loadSessions() {
      this.sessionsLoading = true
      try {
        const data = await fetchSessions()
        this.sessions = data.sessions || []
      } catch (e) {
        console.error('Failed to load sessions:', e)
      } finally {
        this.sessionsLoading = false
      }
    },

    async loadSession(sessionId) {
      const data = await fetchSession(sessionId)
      this.currentSession = data
      this.totalScenes = data.total_pages || data.total_scenes || 0
      this.sceneStatuses = (data.scenes || []).map(scene => this._mapSceneStatus(scene))
      this._replaceReadyScenes(data.scenes || [])
      if (data.playback_snapshot) {
        this.currentSceneIndex = Math.min(
          data.playback_snapshot.sceneIndex || 0,
          Math.max(this.scenes.length - 1, 0),
        )
        this.currentActionIndex = data.playback_snapshot.actionIndex || 0
      } else {
        this.currentSceneIndex = 0
        this.currentActionIndex = 0
      }
      this.playbackState = 'idle'
      this.clearEffects()
    },

    async refreshPlayableScenes(sessionId) {
      const preserveSceneOrder = this.currentScene?.sceneOrder ?? null
      const preserveActionIndex = this.currentActionIndex
      const data = await fetchSession(sessionId)
      this.currentSession = data
      this.totalScenes = data.total_pages || data.total_scenes || 0
      this.sceneStatuses = (data.scenes || []).map(scene => this._mapSceneStatus(scene))
      this._replaceReadyScenes(data.scenes || [], preserveSceneOrder)
      this.currentActionIndex = preserveSceneOrder !== null ? preserveActionIndex : 0
      return data
    },

    async savePlaybackProgress() {
      if (!this.currentSession?.id) return
      try {
        await updatePlaybackSnapshot(this.currentSession.id, {
          sceneIndex: this.currentSceneIndex,
          actionIndex: this.currentActionIndex,
        })
      } catch (e) {
        console.error('Failed to save progress:', e)
      }
    },

    async removeSession(sessionId) {
      await deleteSession(sessionId)
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
    },

    $reset() {
      this.currentSession = null
      this.scenes = []
      this.currentSceneIndex = 0
      this.currentActionIndex = 0
      this.playbackState = 'idle'
      this.spotlightTarget = null
      this.highlightTarget = null
      this.laserTarget = null
      this.currentSubtitle = ''
      this.generatingStatus = null
      this.generatingProgress = ''
      this.totalScenes = 0
      this.sceneStatuses = []
      this.sessions = []
      this.sessionsLoading = false
    },
  },
})
