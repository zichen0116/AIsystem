// teacher-platform/src/composables/usePlaybackEngine.js
import { ref } from 'vue'
import { useRehearsalStore } from '../stores/rehearsal.js'

/**
 * PlaybackEngine state machine: idle -> playing -> paused
 * Audio priority: persistent_audio_url > temp_audio_url > timer fallback
 */
export function usePlaybackEngine() {
  const store = useRehearsalStore()
  const audioRef = ref(null)
  let readingTimer = null

  function _clearTimers() {
    if (readingTimer) {
      clearTimeout(readingTimer)
      readingTimer = null
    }
    if (audioRef.value) {
      audioRef.value.pause()
      audioRef.value.onended = null
      audioRef.value.onerror = null
    }
  }

  function _getAudioCandidates(action) {
    const candidates = [action.persistent_audio_url, action.temp_audio_url, action.audioUrl].filter(Boolean)
    return [...new Set(candidates)]
  }

  async function _playAudioUrl(url) {
    return await new Promise((resolve) => {
      const audio = new Audio(url)
      let settled = false

      audio.onended = () => {
        audio.onended = null
        audio.onerror = null
        processNext()
      }

      audio.onerror = () => {
        audio.onended = null
        audio.onerror = null
        if (settled) {
          processNext()
          return
        }
        settled = true
        resolve(false)
      }

      audioRef.value = audio
      audio.play()
        .then(() => {
          if (!settled) {
            settled = true
            resolve(true)
          }
        })
        .catch(() => {
          audio.onended = null
          audio.onerror = null
          if (!settled) {
            settled = true
            resolve(false)
          }
        })
    })
  }

  async function _playSpeechAction(action, scene) {
    const candidates = _getAudioCandidates(action)
    for (const url of candidates) {
      const started = await _playAudioUrl(url)
      if (started) return true
    }

    // TTS may still be filling asynchronously; refresh scene once and retry.
    if (
      candidates.length === 0
      && action.audio_status === 'pending'
      && store.currentSession?.id
      && typeof scene?.sceneOrder === 'number'
    ) {
      await store._fetchScene(store.currentSession.id, scene.sceneOrder)
      const refreshedScene = store.scenes[store.currentSceneIndex]
      const refreshedAction = refreshedScene?.actions?.[store.currentActionIndex - 1]
      if (refreshedAction?.type === 'speech') {
        const refreshedCandidates = _getAudioCandidates(refreshedAction)
        for (const url of refreshedCandidates) {
          const started = await _playAudioUrl(url)
          if (started) return true
        }
      }
    }

    return false
  }

  async function processNext() {
    if (store.playbackState !== 'playing') return

    const scene = store.scenes[store.currentSceneIndex]
    if (!scene) {
      store.playbackState = 'idle'
      store.clearEffects()
      store.savePlaybackProgress()
      return
    }

    const actions = scene.actions || []
    const actionIndex = store.currentActionIndex

    if (actionIndex >= actions.length) {
      const nextIndex = store.currentSceneIndex + 1
      if (nextIndex >= store.scenes.length) {
        store.playbackState = 'idle'
        store.clearEffects()
        store.savePlaybackProgress()
        return
      }
      store.setSceneIndex(nextIndex)
      store.savePlaybackProgress()
      processNext()
      return
    }

    const action = actions[actionIndex]
    store.currentActionIndex = actionIndex + 1

    switch (action.type) {
      case 'speech':
        store.clearEffects()
        store.currentSubtitle = action.text || ''
        if (!(await _playSpeechAction(action, scene))) {
          _playWithTimer(action.duration || 3000)
        }
        break

      case 'spotlight':
        store.spotlightTarget = {
          elementId: action.elementId,
          dimOpacity: action.dimOpacity ?? 0.4,
        }
        store.laserTarget = null
        processNext()
        break

      case 'laser':
        store.laserTarget = {
          elementId: action.elementId,
          color: action.color || '#ff0000',
        }
        store.spotlightTarget = null
        processNext()
        break

      case 'navigate':
        store.setSceneIndex(action.targetSceneIndex)
        processNext()
        break

      default:
        processNext()
    }
  }

  function _playWithTimer(durationMs) {
    readingTimer = setTimeout(() => {
      readingTimer = null
      processNext()
    }, durationMs)
  }

  function start() {
    if (store.scenes.length === 0) return
    store.playbackState = 'playing'
    store.clearEffects()
    processNext()
  }

  function pause() {
    store.playbackState = 'paused'
    _clearTimers()
    if (audioRef.value && !audioRef.value.paused) audioRef.value.pause()
  }

  function resume() {
    if (store.playbackState !== 'paused') return
    store.playbackState = 'playing'
    if (audioRef.value && audioRef.value.paused && audioRef.value.src) {
      audioRef.value.play().catch(() => processNext())
    } else {
      processNext()
    }
  }

  function stop() {
    store.playbackState = 'idle'
    _clearTimers()
    store.clearEffects()
    store.savePlaybackProgress()
  }

  function jumpToScene(index) {
    _clearTimers()
    store.setSceneIndex(index)
    if (store.playbackState === 'playing') processNext()
  }

  function prevScene() { jumpToScene(Math.max(0, store.currentSceneIndex - 1)) }
  function nextScene() { jumpToScene(Math.min(store.scenes.length - 1, store.currentSceneIndex + 1)) }

  function cleanup() {
    _clearTimers()
    if (audioRef.value) { audioRef.value.pause(); audioRef.value = null }
  }

  return { start, pause, resume, stop, jumpToScene, prevScene, nextScene, cleanup }
}
