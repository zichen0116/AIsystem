// teacher-platform/src/stores/rehearsal.js
import { defineStore } from 'pinia'
import {
  generateRehearsalStream,
  fetchSessions,
  fetchSession,
  fetchScene,
  retryScene,
  updatePlaybackSnapshot,
  deleteSession,
} from '../api/rehearsal.js'

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
      return state.sceneStatuses.filter(s => s.status === 'ready').length
    },
    failedSceneCount(state) {
      return state.sceneStatuses.filter(s => s.status === 'failed').length
    },
  },

  actions: {
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
              } catch { /* ignore */ }
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
          // 更新页级状态
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

          // 如果页面 ready，从 DB 获取完整数据
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
        // 按 scene_order 插入到正确位置
        const existing = this.scenes.findIndex(s => s.sceneOrder === sceneOrder)
        const mapped = {
          sceneOrder: scene.scene_order,
          title: scene.title,
          slideContent: scene.slide_content,
          actions: scene.actions,
          keyPoints: scene.key_points,
          sceneStatus: scene.scene_status,
          audioStatus: scene.audio_status,
        }
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
    clearEffects() {
      this.spotlightTarget = null
      this.laserTarget = null
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
        // 更新 sceneStatuses
        const idx = this.sceneStatuses.findIndex(s => s.sceneIndex === sceneOrder)
        if (idx >= 0) this.sceneStatuses[idx].status = 'ready'
      }
      return result.scene_status
    },

    // --- 会话 CRUD ---
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
      this.scenes = (data.scenes || [])
        .filter(s => s.scene_status === 'ready')
        .map(s => ({
          sceneOrder: s.scene_order,
          title: s.title,
          slideContent: s.slide_content,
          actions: s.actions,
          keyPoints: s.key_points,
          sceneStatus: s.scene_status,
          audioStatus: s.audio_status,
        }))
      if (data.playback_snapshot) {
        this.currentSceneIndex = data.playback_snapshot.sceneIndex || 0
        this.currentActionIndex = data.playback_snapshot.actionIndex || 0
      } else {
        this.currentSceneIndex = 0
        this.currentActionIndex = 0
      }
      this.playbackState = 'idle'
      this.clearEffects()
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
