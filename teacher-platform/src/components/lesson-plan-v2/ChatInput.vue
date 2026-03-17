<template>
  <div class="chat-input-area">
    <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
    <div class="chat-input-box" :class="{ focused }">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        :placeholder="placeholder"
        rows="2"
        @focus="focused = true"
        @blur="focused = false"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="chat-input-bottom">
        <div class="chat-input-actions">
          <button class="action-btn" @click="triggerUpload">
            <span class="action-icon">📎</span> 上传文件
          </button>
          <button class="action-btn" @click="toggleRecording" :class="{ recording: isRecording }">
            <span class="action-icon">🎙</span> {{ isRecording ? '停止' : '语音输入' }}
          </button>
          <button class="action-btn" @click="showLibPicker = !showLibPicker">
            <span class="action-icon">📚</span> 知识库
          </button>
        </div>
        <button class="send-btn" @click="handleSend" :disabled="!canSend">▶</button>
      </div>

      <!-- Tags for uploaded files and selected libraries -->
      <div v-if="uploadedFiles.length || selectedLibraries.length" class="input-tags">
        <span v-for="f in uploadedFiles" :key="f.file_id" class="tag tag-file">
          {{ f.filename }} <span class="tag-close" @click="removeFile(f.file_id)">&times;</span>
        </span>
        <span v-for="lib in selectedLibraries" :key="lib.id" class="tag tag-lib">
          {{ lib.name }} <span class="tag-close" @click="removeLib(lib.id)">&times;</span>
        </span>
      </div>
    </div>

    <!-- Hidden file input -->
    <input ref="fileInput" type="file" hidden accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" @change="handleFileUpload" />

    <!-- Knowledge base picker dropdown -->
    <div v-if="showLibPicker" class="lib-picker">
      <div class="lib-section">
        <div class="lib-section-title">个人知识库</div>
        <label v-for="lib in personalLibs" :key="lib.id" class="lib-option">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          {{ lib.name }}
        </label>
        <div v-if="!personalLibs.length" class="lib-empty">暂无</div>
      </div>
      <div class="lib-section">
        <div class="lib-section-title">系统知识库</div>
        <label v-for="lib in systemLibs" :key="lib.id" class="lib-option">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          {{ lib.name }}
        </label>
        <div v-if="!systemLibs.length" class="lib-empty">暂无</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { resolveApiUrl, getToken } from '../../api/http.js'
import { useVoiceInput } from '../../composables/useVoiceInput.js'

const props = defineProps({
  placeholder: { type: String, default: '发消息以生成教案...' },
  disabled: { type: Boolean, default: false },
  lessonPlanId: { type: [Number, String], default: null },
})

const emit = defineEmits(['send'])

const inputText = ref('')
const focused = ref(false)
const textareaRef = ref(null)
const fileInput = ref(null)
const uploadedFiles = ref([])
const selectedLibIds = ref([])
const personalLibs = ref([])
const systemLibs = ref([])
const showLibPicker = ref(false)

const uploadError = ref('')

const { isRecording, toggleRecording } = useVoiceInput(inputText)

const selectedLibraries = computed(() => {
  const all = [...personalLibs.value, ...systemLibs.value]
  return all.filter(l => selectedLibIds.value.includes(l.id))
})

const canSend = computed(() => inputText.value.trim() && !props.disabled)

function handleSend() {
  if (!canSend.value) return
  emit('send', {
    text: inputText.value.trim(),
    file_ids: uploadedFiles.value.map(f => f.file_id),
    library_ids: selectedLibIds.value,
  })
  inputText.value = ''
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  if (props.lessonPlanId) formData.append('lesson_plan_id', props.lessonPlanId)
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/upload'), {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    })
    if (!res.ok) throw new Error('上传失败')
    const data = await res.json()
    uploadedFiles.value.push(data)
  } catch (err) {
    console.error('File upload error:', err)
    uploadError.value = '文件上传失败，请重试'
    setTimeout(() => { uploadError.value = '' }, 3000)
  }
  e.target.value = ''
}

function removeFile(fileId) {
  uploadedFiles.value = uploadedFiles.value.filter(f => f.file_id !== fileId)
}

function removeLib(libId) {
  selectedLibIds.value = selectedLibIds.value.filter(id => id !== libId)
}

// Cache libraries data to avoid repeated requests
let librariesCache = null
let cacheTimestamp = 0
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

async function fetchLibraries(forceRefresh = false) {
  const now = Date.now()

  // Use cache if available and not expired
  if (!forceRefresh && librariesCache && (now - cacheTimestamp < CACHE_DURATION)) {
    personalLibs.value = librariesCache.personal
    systemLibs.value = librariesCache.system
    return
  }

  try {
    const token = getToken()
    const headers = { Authorization: `Bearer ${token}` }
    const [pRes, sRes] = await Promise.all([
      fetch(resolveApiUrl('/api/v1/libraries?scope=personal'), { headers }),
      fetch(resolveApiUrl('/api/v1/libraries?scope=system'), { headers }),
    ])
    if (pRes.ok) personalLibs.value = (await pRes.json()).items || []
    if (sRes.ok) systemLibs.value = (await sRes.json()).items || []

    // Update cache
    librariesCache = {
      personal: personalLibs.value,
      system: systemLibs.value
    }
    cacheTimestamp = now
  } catch (err) {
    console.error('Failed to fetch libraries:', err)
  }
}

function restoreFiles(files) {
  uploadedFiles.value = files || []
}

defineExpose({ restoreFiles })

// Click-outside handler for knowledge base picker
function handleClickOutside(e) {
  if (showLibPicker.value && !e.target.closest('.lib-picker') && !e.target.closest('.action-btn')) {
    showLibPicker.value = false
  }
}

onMounted(() => {
  fetchLibraries()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #eaedf0;
  position: relative;
}
.upload-error {
  color: #e53e3e;
  font-size: 12px;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: #fff5f5;
  border-radius: 4px;
}
.chat-input-box {
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  border: 1px solid #e0e3e8;
  border-radius: 12px;
  padding: 12px 16px;
  transition: border-color 0.2s;
}
.chat-input-box.focused {
  border-color: #2563eb;
}
.chat-input-box textarea {
  width: 100%;
  border: none;
  background: none;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  color: #333;
  line-height: 1.5;
}
.chat-input-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.chat-input-actions {
  display: flex;
  gap: 8px;
}
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid #e0e3e8;
  border-radius: 6px;
  background: #fff;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}
.action-btn:hover {
  border-color: #2563eb;
  color: #2563eb;
}
.action-btn.recording {
  border-color: #e53e3e;
  color: #e53e3e;
}
.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}
.send-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
.input-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.tag-file {
  background: #e8f0fe;
  color: #2563eb;
}
.tag-lib {
  background: #f0fdf4;
  color: #16a34a;
}
.tag-close {
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}
.tag-close:hover {
  color: #e53e3e;
}
.lib-picker {
  position: absolute;
  bottom: 100%;
  left: 24px;
  right: 24px;
  background: #fff;
  border: 1px solid #e0e3e8;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.08);
  z-index: 20;
  max-height: 240px;
  overflow-y: auto;
}
.lib-section {
  margin-bottom: 8px;
}
.lib-section-title {
  font-size: 12px;
  color: #999;
  font-weight: 500;
  margin-bottom: 6px;
}
.lib-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: 13px;
  color: #444;
  cursor: pointer;
}
.lib-empty {
  font-size: 12px;
  color: #ccc;
  padding: 4px 0;
}
</style>
