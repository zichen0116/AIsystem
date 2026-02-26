import { ref, onUnmounted } from 'vue'

export function useVoiceInput(textRefOrGetter, setter) {
  const isRecording = ref(false)
  const isSupported = ref(false)
  let recognition = null
  /** 已确认的文本（来自 final 结果），在每次 start 时从输入框同步 */
  let committedText = ''

  const getText = typeof textRefOrGetter === 'function'
    ? textRefOrGetter
    : () => textRefOrGetter.value
  const setText = setter || (typeof textRefOrGetter !== 'function' ? (v) => { textRefOrGetter.value = v } : null)
  if (!setText) return { isRecording, isSupported, toggleRecording: () => {} }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (SpeechRecognition) {
    isSupported.value = true
    recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'zh-CN'

    recognition.onresult = (event) => {
      if (!event.results || event.results.length === 0) return
      const results = event.results
      const startIdx = event.resultIndex

      for (let i = startIdx; i < results.length; i++) {
        const result = results[i]
        const transcript = (result[0] && result[0].transcript) ? result[0].transcript.trim() : ''
        if (!transcript) continue
        if (result.isFinal) {
          committedText += transcript
        }
      }

      const last = results[results.length - 1]
      const lastTranscript = (last[0] && last[0].transcript) ? last[0].transcript.trim() : ''
      const displayText = last.isFinal
        ? committedText
        : committedText + lastTranscript

      setText(displayText)
    }

    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        isRecording.value = false
      }
    }

    recognition.onend = () => {
      isRecording.value = false
    }
  }

  const toggleRecording = () => {
    if (!isSupported.value || !recognition) return
    if (isRecording.value) {
      recognition.stop()
    } else {
      committedText = String(getText() || '')
      recognition.start()
      isRecording.value = true
    }
  }

  onUnmounted(() => {
    if (recognition && isRecording.value) {
      recognition.stop()
    }
  })

  return { isRecording, isSupported, toggleRecording }
}
