<template>
  <div ref="flowRef" class="chat-flow">
    <template v-for="(msg, i) in messages" :key="i">
      <DocumentCard
        v-if="msg.type === 'document-card'"
        :title="msg.title"
        @open="$emit('open-document')"
      />
      <ChatMessage v-else :msg="msg" @regenerate="$emit('regenerate', i)" />
    </template>

    <!-- Streaming indicator -->
    <div v-if="isStreaming" class="chat-msg assistant">
      <div class="msg-bubble">
        <div v-if="streamingText" v-html="renderStreaming(streamingText)" />
        <div v-else class="typing-indicator">
          <span /><span /><span />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import DocumentCard from './DocumentCard.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
})

defineEmits(['open-document', 'regenerate'])

const flowRef = ref(null)

function renderStreaming(text) {
  return text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (flowRef.value) {
      flowRef.value.scrollTop = flowRef.value.scrollHeight
    }
  })
}

// Auto-scroll when messages change or streaming updates
watch(() => props.messages.length, scrollToBottom)
watch(() => props.streamingText, scrollToBottom)

defineExpose({ scrollToBottom })
</script>

<style scoped>
.chat-flow {
  flex: 1;
  overflow-y: auto;
  padding: 24px 15%;
}
.chat-msg.assistant {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-start;
}
.chat-msg.assistant .msg-bubble {
  background: #fff;
  color: #333;
  border: 1px solid #e8ecf0;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.7;
  max-width: 75%;
}
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}
.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #aaa;
  border-radius: 50%;
  animation: blink 1.4s infinite both;
}
.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}
.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}
</style>
