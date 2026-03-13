<template>
  <div class="chat-panel">
    <!-- Messages -->
    <div class="messages-area" ref="messagesRef">
      <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', msg.role]">
        <div class="msg-label">{{ msg.role === 'user' ? '我' : 'AI 助手' }}</div>
        <div class="msg-bubble" v-html="renderMsg(msg.content)"></div>
      </div>
      <!-- Loading bubble during streaming -->
      <div v-if="isSending" class="msg assistant">
        <div class="msg-label">AI 助手</div>
        <div class="msg-bubble loading-bubble">
          <span class="dot-anim">{{ hasContent ? '正在修改教案' : '正在生成教案' }}</span>
        </div>
      </div>
    </div>

    <!-- Tags: uploaded files + selected knowledge bases -->
    <div class="tags-area" v-if="uploadedFiles.length > 0 || selectedLibraries.length > 0">
      <span v-for="f in uploadedFiles" :key="'f' + f.file_id" class="tag file-tag">
        {{ f.filename }}
        <button class="tag-remove" @click="removeFile(f.file_id)">&times;</button>
      </span>
      <span v-for="lib in selectedLibraries" :key="'l' + lib.id" :class="['tag', lib.type === 'system' ? 'system-tag' : 'user-tag']">
        {{ lib.name }}
        <button class="tag-remove" @click="removeLibrary(lib.id)">&times;</button>
      </span>
    </div>

    <!-- Input area -->
    <div class="input-area">
      <textarea
        ref="inputRef"
        v-model="inputText"
        :placeholder="hasContent ? '输入修改要求...' : '描述您的教学需求，例如：帮我生成一份高一数学函数与方程的教案'"
        rows="3"
        @keydown.enter.exact.prevent="handleSend"
        :disabled="isSending"
      ></textarea>
      <div class="input-actions">
        <button class="action-btn" @click="triggerFileUpload" :disabled="isSending" title="上传参考资料">
          &#128206;
        </button>
        <button class="action-btn" @click="showLibPicker = !showLibPicker" :disabled="isSending" title="选择知识库">
          &#128218;
        </button>
        <button :class="['action-btn', { recording: isRecording }]" @click="toggleRecording" :disabled="isSending" title="语音输入">
          &#127908;
        </button>
        <button class="send-btn" @click="handleSend" :disabled="isSending || !inputText.trim()">发送</button>
      </div>
    </div>

    <!-- Knowledge base picker dropdown -->
    <div class="lib-picker" v-if="showLibPicker" @click.stop>
      <div class="lib-group" v-if="userLibs.length > 0">
        <div class="lib-group-title">&#128193; 我的知识库</div>
        <label v-for="lib in userLibs" :key="lib.id" class="lib-item">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          <span>{{ lib.name }}</span>
        </label>
      </div>
      <div class="lib-divider" v-if="userLibs.length > 0 && sysLibs.length > 0"></div>
      <div class="lib-group" v-if="sysLibs.length > 0">
        <div class="lib-group-title">&#127760; 公开知识库</div>
        <label v-for="lib in sysLibs" :key="lib.id" class="lib-item">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          <span>{{ lib.name }}</span>
        </label>
      </div>
      <p class="lib-empty" v-if="userLibs.length === 0 && sysLibs.length === 0">暂无知识库</p>
    </div>

    <!-- Hidden file input (no .pptx - parser unsupported) -->
    <input ref="fileInputRef" type="file" hidden accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" @change="handleFileUpload" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { resolveApiUrl, getToken } from '@/api/http.js'
import { useVoiceInput } from '@/composables/useVoiceInput.js'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isSending: { type: Boolean, default: false },
  hasContent: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'send-modify'])

const inputText = ref('')
const messagesRef = ref(null)
const inputRef = ref(null)
const fileInputRef = ref(null)
const showLibPicker = ref(false)
const uploadedFiles = ref([])
const selectedLibIds = ref([])
const userLibs = ref([])
const sysLibs = ref([])

const { isRecording, toggleRecording } = useVoiceInput(inputText)

const selectedLibraries = computed(() => {
  const all = [...userLibs.value, ...sysLibs.value]
  return all.filter((lib) => selectedLibIds.value.includes(lib.id))
})

// Auto-scroll messages on new entries
watch(() => props.messages.length, () => {
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
})

async function fetchLibraries() {
  try {
    const headers = { Authorization: `Bearer ${getToken()}` }
    const [uRes, sRes] = await Promise.all([
      fetch(resolveApiUrl('/api/v1/libraries?scope=personal'), { headers }),
      fetch(resolveApiUrl('/api/v1/libraries?scope=system'), { headers }),
    ])
    if (uRes.ok) {
      const d = await uRes.json()
      userLibs.value = (d.items || d || []).map((lib) => ({ ...lib, type: 'user' }))
    }
    if (sRes.ok) {
      const d = await sRes.json()
      sysLibs.value = (d.items || d || []).map((lib) => ({ ...lib, type: 'system' }))
    }
  } catch (e) {
    console.warn('Failed to fetch libraries:', e)
  }
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.isSending) return
  const payload = {
    text,
    file_ids: uploadedFiles.value.map((f) => f.file_id),
    library_ids: selectedLibIds.value,
  }
  emit(props.hasContent ? 'send-modify' : 'send', payload)
  inputText.value = ''
}

function triggerFileUpload() { fileInputRef.value?.click() }

async function handleFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/upload'), {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    })
    if (!res.ok) throw new Error('Upload failed')
    const data = await res.json()
    uploadedFiles.value.push(data)
  } catch (e) {
    console.error('File upload failed:', e)
  }
  fileInputRef.value.value = ''
}

function removeFile(fid) { uploadedFiles.value = uploadedFiles.value.filter((f) => f.file_id !== fid) }
function removeLibrary(lid) { selectedLibIds.value = selectedLibIds.value.filter((id) => id !== lid) }
function renderMsg(content) { return content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') }

// Restore uploaded files from parent (after GET /latest)
function restoreFiles(files) { uploadedFiles.value = files }

function handleClickOutside(e) {
  if (showLibPicker.value && !e.target.closest('.lib-picker') && !e.target.closest('.action-btn')) {
    showLibPicker.value = false
  }
}

onMounted(() => {
  fetchLibraries()
  document.addEventListener('click', handleClickOutside)
})
onBeforeUnmount(() => { document.removeEventListener('click', handleClickOutside) })

defineExpose({ restoreFiles })
</script>

<style scoped>
.chat-panel { display: flex; flex-direction: column; height: 100%; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; }
.messages-area { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.msg { display: flex; flex-direction: column; gap: 4px; }
.msg.user { align-items: flex-end; }
.msg.assistant { align-items: flex-start; }
.msg-label { font-size: 0.75rem; color: #94a3b8; padding: 0 4px; }
.msg-bubble { max-width: 90%; padding: 10px 14px; border-radius: 12px; font-size: 0.9rem; line-height: 1.6; word-break: break-word; }
.msg.user .msg-bubble { background: #E0EDFE; color: #1e293b; border-bottom-right-radius: 4px; }
.msg.assistant .msg-bubble { background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
.loading-bubble .dot-anim::after { content: ''; animation: dots 1.5s steps(3) infinite; }
@keyframes dots { 0% { content: ''; } 33% { content: '.'; } 66% { content: '..'; } 100% { content: '...'; } }

.tags-area { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 16px; border-top: 1px solid #f1f5f9; }
.tag { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; }
.file-tag { background: #f1f5f9; color: #475569; }
.user-tag { background: #dbeafe; color: #2563eb; }
.system-tag { background: #d1fae5; color: #059669; }
.tag-remove { border: none; background: none; cursor: pointer; font-size: 0.85rem; color: inherit; opacity: 0.6; padding: 0 2px; }
.tag-remove:hover { opacity: 1; }

.input-area { padding: 12px 16px; border-top: 1px solid #e2e8f0; }
.input-area textarea { width: 100%; resize: none; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; font-size: 0.9rem; font-family: inherit; outline: none; }
.input-area textarea:focus { border-color: #93c5fd; }
.input-actions { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.action-btn { width: 32px; height: 32px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1rem; }
.action-btn:hover { background: #f1f5f9; }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-btn.recording { background: #fee2e2; border-color: #fca5a5; }
.send-btn { margin-left: auto; padding: 6px 20px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-size: 0.85rem; cursor: pointer; }
.send-btn:hover { background: #1d4ed8; }
.send-btn:disabled { background: #93c5fd; cursor: not-allowed; }

.lib-picker { position: absolute; bottom: 120px; left: 16px; right: 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); z-index: 20; max-height: 240px; overflow-y: auto; padding: 8px 0; }
.lib-group-title { padding: 8px 16px 4px; font-size: 0.78rem; font-weight: 600; color: #94a3b8; }
.lib-item { display: flex; align-items: center; gap: 8px; padding: 6px 16px; font-size: 0.85rem; color: #334155; cursor: pointer; }
.lib-item:hover { background: #f8fafc; }
.lib-item input[type="checkbox"] { accent-color: #2563eb; }
.lib-divider { height: 1px; background: #e2e8f0; margin: 4px 12px; }
.lib-empty { padding: 16px; text-align: center; font-size: 0.82rem; color: #94a3b8; }
</style>
