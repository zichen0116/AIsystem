// teacher-platform/src/composables/usePlaybackEngine.js
import { ref } from 'vue'
import { useRehearsalStore } from '../stores/rehearsal.js'
import { applySpotlightAction } from './rehearsalPlaybackEffects.js'

/**
 * PlaybackEngine state machine: idle -> playing -> paused
 * Audio priority: persistent_audio_url > temp_audio_url > timer fallback
 */
export function usePlaybackEngine() {
  const store = useRehearsalStore()
  const audioRef = ref(null)
  let readingTimer = null
  let spotlightTimer = null
  let laserTimer = null
  let highlightTimer = null
  let sceneAdvanceTimer = null

  function _clearEffectTimers() {
    if (spotlightTimer) {
      clearTimeout(spotlightTimer)
      spotlightTimer = null
    }
    if (laserTimer) {
      clearTimeout(laserTimer)
      laserTimer = null
    }
    if (highlightTimer) {
      clearTimeout(highlightTimer)
      highlightTimer = null
    }
  }

  function _clearTimers() {
    if (readingTimer) {
      clearTimeout(readingTimer)
      readingTimer = null
    }
    if (sceneAdvanceTimer) {
      clearTimeout(sceneAdvanceTimer)
      sceneAdvanceTimer = null
    }
    _clearEffectTimers()
    if (audioRef.value) {
      audioRef.value.pause()
      audioRef.value.onended = null
      audioRef.value.onerror = null
    }
  }

  function _scheduleEffectClear(timerName, durationMs, clearFn) {
    if (!durationMs || durationMs <= 0) return

    if (timerName === 'spotlight' && spotlightTimer) {
      clearTimeout(spotlightTimer)
      spotlightTimer = null
    }
    if (timerName === 'laser' && laserTimer) {
      clearTimeout(laserTimer)
      laserTimer = null
    }
    if (timerName === 'highlight' && highlightTimer) {
      clearTimeout(highlightTimer)
      highlightTimer = null
    }

    const timeoutId = setTimeout(() => {
      if (timerName === 'spotlight') spotlightTimer = null
      if (timerName === 'laser') laserTimer = null
      if (timerName === 'highlight') highlightTimer = null
      clearFn()
    }, durationMs)

    if (timerName === 'spotlight') spotlightTimer = timeoutId
    if (timerName === 'laser') laserTimer = timeoutId
    if (timerName === 'highlight') highlightTimer = timeoutId
  }

  function _getAudioCandidates(action) {
    const candidates = [action.persistent_audio_url, action.temp_audio_url, action.audioUrl].filter(Boolean)
    return [...new Set(candidates)]
  }

  function _handleSpeechFinished() {
    if (store.playbackState !== 'playing') return
    processNext()
  }

  function _findNextSceneIndex(currentSceneOrder) {
    return store.scenes.findIndex(scene => scene.sceneOrder > currentSceneOrder)
  }

  function _scheduleSceneAdvanceRetry(delayMs = 1200) {
    if (sceneAdvanceTimer) {
      clearTimeout(sceneAdvanceTimer)
    }
    sceneAdvanceTimer = setTimeout(() => {
      sceneAdvanceTimer = null
      processNext()
    }, delayMs)
  }

  async function _advanceToNextScene(currentSceneOrder) {
    let nextIndex = _findNextSceneIndex(currentSceneOrder)
    if (nextIndex >= 0) {
      _clearEffectTimers()
      store.setSceneIndex(nextIndex)
      store.savePlaybackProgress()
      processNext()
      return
    }

    if (store.currentSession?.id) {
      try {
        await store.refreshPlayableScenes(store.currentSession.id)
      } catch (error) {
        console.error('Failed to refresh rehearsal session before advancing:', error)
      }
      nextIndex = _findNextSceneIndex(currentSceneOrder)
      if (nextIndex >= 0) {
        _clearEffectTimers()
        store.setSceneIndex(nextIndex)
        store.savePlaybackProgress()
        processNext()
        return
      }
    }

    const hasPendingScenes = store.sceneStatuses.some(sceneStatus =>
      sceneStatus.status === 'pending' || sceneStatus.status === 'generating')

    if (hasPendingScenes) {
      _scheduleSceneAdvanceRetry()
      return
    }

    store.playbackState = 'idle'
    store.clearEffects()
    store.savePlaybackProgress()
  }

  async function _playAudioUrl(url, onDone) {
    return await new Promise((resolve) => {
      const audio = new Audio(url)
      let settled = false

      audio.onended = () => {
        audio.onended = null
        audio.onerror = null
        audioRef.value = null
        onDone?.()
      }

      audio.onerror = () => {
        audio.onended = null
        audio.onerror = null
        audioRef.value = null
        if (settled) {
          onDone?.()
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

  async function _playSpeechAction(action, scene, onDone) {
    const candidates = _getAudioCandidates(action)
    for (const url of candidates) {
      const started = await _playAudioUrl(url, onDone)
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
          const started = await _playAudioUrl(url, onDone)
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
      await _advanceToNextScene(scene.sceneOrder)
      return
    }

    const action = actions[actionIndex]
    store.currentActionIndex = actionIndex + 1

    switch (action.type) {
      case 'speech':
        store.currentSubtitle = action.text || ''
        if (!(await _playSpeechAction(action, scene, _handleSpeechFinished))) {
          _playWithTimer(action.duration || 3000, _handleSpeechFinished)
        }
        break

      case 'spotlight':
        applySpotlightAction(store, action, _scheduleEffectClear)
        processNext()
        break

      case 'highlight': {
        const elementIds = Array.isArray(action.elementIds)
          ? action.elementIds.filter(Boolean)
          : [action.elementId].filter(Boolean)
        if (elementIds.length > 0) {
          store.highlightTarget = {
            elementIds,
            color: action.color || '#ff6b6b',
            opacity: action.opacity ?? 0.22,
            borderWidth: action.borderWidth ?? 3,
          }
          _scheduleEffectClear('highlight', action.duration || 2400, () => {
            store.highlightTarget = null
          })
        }
        processNext()
        break
      }

      case 'laser':
        store.laserTarget = {
          elementId: action.elementId,
          color: action.color || '#ff0000',
        }
        _scheduleEffectClear('laser', action.duration || 1600, () => {
          store.laserTarget = null
        })
        processNext()
        break

      case 'navigate':
        _clearEffectTimers()
        store.setSceneIndex(action.targetSceneIndex)
        processNext()
        break

      default:
        processNext()
    }
  }

  function _playWithTimer(durationMs, onDone) {
    readingTimer = setTimeout(() => {
      readingTimer = null
      onDone?.()
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
