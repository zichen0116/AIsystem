<template>
  <div class="chat-panel">
    <div ref="listRef" class="chat-panel__list">
      <ChatMessage
        v-for="(msg, idx) in messages"
        :key="idx"
        :message="msg"
        :outline-interactive="isInteractiveOutline(msg)"
        :show-outline-approve="showOutlineApprove(msg)"
        @preview="$emit('preview')"
        @outline-approve="$emit('outline-approve', $event)"
        @outline-edit="$emit('outline-edit', msg, $event)"
        @outline-regenerate="$emit('outline-regenerate', msg)"
      />
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
  activeOutlineId: { type: Number, default: null },
  canApproveOutline: { type: Boolean, default: false },
})

defineEmits(['preview', 'outline-approve', 'outline-edit', 'outline-regenerate'])

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

function getOutlineId(message) {
  return message?.metadata_?.outline_id || message?.outline_id || null
}

function isInteractiveOutline(message) {
  return message?.message_type === 'outline' && getOutlineId(message) === props.activeOutlineId
}

function showOutlineApprove(message) {
  return isInteractiveOutline(message) && props.canApproveOutline
}
</script>

<style scoped>
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #f5f7fa;
  overflow: hidden;
}

.chat-panel__list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 40px 24px 16px;
}

.chat-panel__streaming {
  opacity: 0.8;
}
</style>
