<template>
  <div class="chat-message" :class="[`chat-message--${message.role}`]">
    <div class="chat-message__bubble">
      <span v-if="message.message_type === 'error'" class="chat-message__error">{{ message.content }}</span>
      <span v-else>{{ message.content }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
.chat-message {
  display: flex;
  margin-bottom: 12px;
  padding: 0 16px;
}

.chat-message--user {
  justify-content: flex-end;
}

.chat-message--assistant {
  justify-content: flex-start;
}

.chat-message__bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.chat-message--user .chat-message__bubble {
  background: #e0edfe;
  color: #1a1a1a;
  border-bottom-right-radius: 4px;
}

.chat-message--assistant .chat-message__bubble {
  background: #ffffff;
  color: #1a1a1a;
  border: 1px solid #e8e8e8;
  border-bottom-left-radius: 4px;
}

.chat-message__error {
  color: #e53935;
}
</style>
