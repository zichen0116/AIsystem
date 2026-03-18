<template>
  <div class="chat-panel">
    <div ref="listRef" class="chat-panel__list">
      <ChatMessage v-for="(msg, idx) in messages" :key="idx" :message="msg" />
      <div v-if="isStreaming && streamingText" class="chat-panel__streaming">
        <ChatMessage
          :message="{ role: 'assistant', message_type: 'text', content: streamingText }"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  streamingText: { type: String, default: '' },
  isStreaming: { type: Boolean, default: false },
})

const listRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.streamingText, scrollToBottom)
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
}

.chat-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

.chat-panel__streaming {
  opacity: 0.8;
}
</style>
