<template>
  <div class="writer-layout">
    <WriterChat
      ref="writerChatRef"
      :messages="messages"
      :is-streaming="isStreaming"
      :streaming-text="streamingText"
      :lesson-plan-id="lessonPlanId"
      @send-modify="$emit('send-modify', $event)"
    />
    <WriterEditor
      ref="writerEditorRef"
      :is-streaming="isStreaming"
      :streaming-markdown="streamingMarkdown"
      @back="$emit('back')"
      @update:markdown="$emit('update:markdown', $event)"
      @blur="$emit('editor-blur')"
      @toast="$emit('toast', $event)"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import WriterChat from './WriterChat.vue'
import WriterEditor from './WriterEditor.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  streamingText: { type: String, default: '' },
  streamingMarkdown: { type: String, default: '' },
  lessonPlanId: { type: [Number, String], default: null },
})

defineEmits(['send-modify', 'back', 'update:markdown', 'editor-blur', 'toast'])

const writerChatRef = ref(null)
const writerEditorRef = ref(null)

defineExpose({
  getMarkdown: () => writerEditorRef.value?.getMarkdown(),
  loadContent: (md) => writerEditorRef.value?.loadContent(md),
  destroyEditor: () => writerEditorRef.value?.destroy(),
  createEditor: (content) => writerEditorRef.value?.createEditor(content),
  scrollChatToBottom: () => writerChatRef.value?.scrollToBottom(),
})
</script>

<style scoped>
.writer-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
