<template>
  <div class="chat-msg" :class="msg.role">
    <div class="msg-content">
      <div v-if="msg.role === 'assistant'" v-html="renderedContent" />
      <template v-else>{{ msg.content }}</template>
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

defineEmits(['regenerate'])

const renderedContent = computed(() => {
  return md.render(props.msg.content || '')
})
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
.msg-content {
  font-size: 14px;
  line-height: 1.7;
}
/* User: keep bubble style */
.chat-msg.user .msg-content {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
  border-bottom-right-radius: 4px;
  background: #2563eb;
  color: #fff;
}
/* AI: no bubble, plain text */
.chat-msg.assistant .msg-content {
  color: #333;
}
.msg-content :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 8px 0 4px;
}
.msg-content :deep(ul) {
  padding-left: 18px;
  margin: 4px 0;
}
.msg-content :deep(li) {
  margin: 2px 0;
}
.msg-content :deep(p) {
  margin: 4px 0;
}
</style>
