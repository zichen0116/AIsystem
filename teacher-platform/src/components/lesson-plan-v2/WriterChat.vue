<template>
  <div class="writer-chat">
    <ChatFlow
      ref="chatFlowRef"
      :messages="messages"
      :is-streaming="isStreaming"
      :streaming-text="streamingText"
      @open-document="$emit('open-document')"
    />
    <ChatInput
      placeholder="输入修改意见..."
      :disabled="isStreaming"
      :lesson-plan-id="lessonPlanId"
      @send="$emit('send-modify', $event)"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChatFlow from './ChatFlow.vue'
import ChatInput from './ChatInput.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  lessonPlanId: { type: [Number, String], default: null },
})

defineEmits(['send-modify', 'open-document'])

const chatFlowRef = ref(null)

function scrollToBottom() {
  chatFlowRef.value?.scrollToBottom()
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.writer-chat {
  width: 40%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #eaedf0;
  background: #f7f8fa;
}
.writer-chat :deep(.chat-flow) {
  padding: 20px 24px;
}
</style>
