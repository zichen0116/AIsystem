<template>
  <div class="chat-input">
    <input
      class="chat-input__field"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled || loading"
      @input="$emit('update:modelValue', $event.target.value)"
      @keydown.enter.exact.prevent="handleSend"
    />
    <button
      class="chat-input__btn"
      :disabled="disabled || loading || !modelValue?.trim()"
      @click="handleSend"
    >
      <span v-if="loading" class="chat-input__spinner" />
      <span v-else>发送</span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '输入消息...' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'send'])

function handleSend() {
  if (props.disabled || props.loading || !props.modelValue?.trim()) return
  emit('send')
}
</script>

<style scoped>
.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
  background: #fff;
}

.chat-input__field {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input__field:focus {
  border-color: #409eff;
}

.chat-input__field:disabled {
  background: #f5f7fa;
  cursor: not-allowed;
}

.chat-input__btn {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: #409eff;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
}

.chat-input__btn:hover:not(:disabled) {
  background: #337ecc;
}

.chat-input__btn:disabled {
  background: #a0cfff;
  cursor: not-allowed;
}

.chat-input__spinner {
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
