<template>
  <div class="chat-msg" :class="msg.role">
    <div class="msg-bubble">
      <div v-if="msg.role === 'assistant'" v-html="renderedContent" />
      <template v-else>{{ msg.content }}</template>
    </div>
    <div v-if="msg.role === 'assistant'" class="ai-actions">
      <button @click="copyContent">📋 复制</button>
      <button @click="$emit('regenerate')">🔄 重新生成</button>
      <button @click="$emit('like')">👍</button>
      <button @click="$emit('dislike')">👎</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const props = defineProps({
  msg: { type: Object, required: true },
})

defineEmits(['regenerate', 'like', 'dislike'])

const renderedContent = computed(() => {
  return md.render(props.msg.content || '')
})

function copyContent() {
  navigator.clipboard.writeText(props.msg.content)
}
</script>

<style scoped>
.chat-msg {
  margin-bottom: 20px;
  display: flex;
}
.chat-msg.user {
  justify-content: flex-end;
}
.chat-msg.assistant {
  justify-content: flex-start;
}
.msg-bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
}
.chat-msg.user .msg-bubble {
  background: #2563eb;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg.assistant .msg-bubble {
  background: #fff;
  color: #333;
  border: 1px solid #e8ecf0;
  border-bottom-left-radius: 4px;
}
.msg-bubble :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 8px 0 4px;
}
.msg-bubble :deep(ul) {
  padding-left: 18px;
  margin: 4px 0;
}
.msg-bubble :deep(li) {
  margin: 2px 0;
}
.msg-bubble :deep(p) {
  margin: 4px 0;
}
.ai-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-self: flex-start;
}
.ai-actions button {
  background: none;
  border: 1px solid #e0e3e8;
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 11px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}
.ai-actions button:hover {
  color: #2563eb;
  border-color: #2563eb;
}
</style>
