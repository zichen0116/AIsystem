<template>
  <div class="chat-input-wrap">
    <div class="input-wrapper" :class="{ focused }">
      <textarea
        ref="textareaRef"
        class="main-input"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled || loading"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.enter.exact.prevent="handleSend"
        @focus="focused = true"
        @blur="focused = false"
      />
      <div class="input-actions">
        <div class="input-tools">
          <div class="input-tool" @click="$emit('open-file-upload')">
            <span>📎</span> 上传文件
          </div>
          <div class="input-tool" @click="$emit('open-image-upload')">
            <span>🖼️</span> 上传图片
          </div>
          <div class="input-tool" @click="$emit('open-voice')">
            <span>🎤</span> 语音输入
          </div>
          <div class="input-tool" @click="$emit('open-knowledge')">
            <span>📚</span> 选择知识库
          </div>
        </div>
        <button
          class="send-btn"
          :disabled="disabled || loading || !modelValue?.trim()"
          @click="handleSend"
        >
          <span v-if="loading" class="send-spinner" />
          <span v-else>发送</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入消息...' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:modelValue', 'send',
  'open-file-upload', 'open-image-upload', 'open-voice', 'open-knowledge',
])

const focused = ref(false)
const textareaRef = ref(null)

function handleSend() {
  if (props.disabled || props.loading || !props.modelValue?.trim()) return
  emit('send')
}
</script>

<style scoped>
.chat-input-wrap {
  padding: 20px;
  background: #fff;
  border-top: 1px solid #e5e5e5;
  flex-shrink: 0;
}
.input-wrapper {
  background: #fff;
  border: 2px solid #e5e5e5;
  border-radius: 12px;
  padding: 16px;
  transition: border-color 0.2s;
}
.input-wrapper.focused {
  border-color: #3a61ea;
}
.main-input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 15px;
  resize: none;
  min-height: 60px;
  font-family: inherit;
  color: #1a1a1a;
  line-height: 1.5;
}
.main-input::placeholder {
  color: #999;
}
.main-input:disabled {
  background: transparent;
  cursor: not-allowed;
}
.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.input-tools {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.input-tool {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  transition: color 0.2s;
  user-select: none;
}
.input-tool:hover {
  color: #3a61ea;
}
.send-btn {
  padding: 8px 24px;
  background: #3a61ea;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
  min-width: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.send-btn:hover:not(:disabled) {
  background: #2a4bc8;
}
.send-btn:disabled {
  background: #a0b4f0;
  cursor: not-allowed;
}
.send-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
