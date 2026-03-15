<template>
  <div class="dialog-container">
    <!-- Phase 1: Welcome (no messages yet) -->
    <WelcomePanel
      v-if="!hasMessages"
      @select-prompt="$emit('send-prompt', $event)"
    />

    <!-- Phase 2: Chat flow (has messages) -->
    <ChatFlow
      v-else
      ref="chatFlowRef"
      :messages="messages"
      :is-streaming="isStreaming"
      :streaming-text="streamingText"
      @open-document="$emit('open-document')"
      @regenerate="$emit('regenerate', $event)"
    />

    <!-- Input always at bottom -->
    <ChatInput
      :placeholder="placeholder"
      :disabled="isStreaming"
      :lesson-plan-id="lessonPlanId"
      @send="$emit('send', $event)"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import WelcomePanel from './WelcomePanel.vue'
import ChatFlow from './ChatFlow.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  lessonPlanId: { type: [Number, String], default: null },
})

defineEmits(['send', 'send-prompt', 'open-document', 'regenerate'])

const chatFlowRef = ref(null)

const hasMessages = computed(() => props.messages.length > 0)

const placeholder = computed(() =>
  hasMessages.value ? '继续对话...' : '发消息以生成教案...'
)

function scrollToBottom() {
  chatFlowRef.value?.scrollToBottom()
}

defineExpose({ scrollToBottom })
</script>

<style scoped>
.dialog-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}
</style>
