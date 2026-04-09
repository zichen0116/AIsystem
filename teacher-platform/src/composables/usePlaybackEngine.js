// teacher-platform/src/composables/usePlaybackEngine.js
import { ref, watch } from 'vue'
import { useRehearsalStore } from '../stores/rehearsal.js'

/**
 * PlaybackEngine — 状态机: idle → playing → paused
 * 音频优先级: persistent_audio_url > temp_audio_url > 计时播放
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
    }
  }

  function _getAudioUrl(action) {
    // 优先级: persistent > temp > null
    return action.persistent_audio_url || action.temp_audio_url || action.audioUrl || null
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
        const audioUrl = _getAudioUrl(action)
        if (audioUrl) {
          audioRef.value = new Audio(audioUrl)
          audioRef.value.onended = () => processNext()
          audioRef.value.onerror = () => _playWithTimer(action.duration || 3000)
          try {
            await audioRef.value.play()
          } catch {
            _playWithTimer(action.duration || 3000)
          }
        } else {
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
