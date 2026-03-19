<template>
  <div
    class="chat-message"
    :class="[
      `chat-message--${message.role}`,
      {
        'ppt-result-message': message.message_type === 'ppt_result',
        'outline-message': message.message_type === 'outline',
      },
    ]"
  >
    <div class="chat-message__bubble">
      <span v-if="message.message_type === 'error'" class="chat-message__error">{{ message.content }}</span>

      <template v-else-if="message.message_type === 'outline'">
        <OutlineCard
          :outline="outlineMessage"
          :editable="outlineInteractive"
          :show-approve="showOutlineApprove"
          @approve="$emit('outline-approve', $event)"
          @edit="$emit('outline-edit', $event)"
          @regenerate="$emit('outline-regenerate')"
        />
      </template>

      <template v-else-if="message.message_type === 'ppt_result'">
        <div class="ppt-result-head">{{ message.content }}</div>
        <div class="ppt-result-card" @click="$emit('preview')">
          <div class="ppt-result-left">
            <span class="ppt-file-icon">P</span>
            <div>
              <div class="ppt-result-title">{{ message.pptTitle || 'PPT文件' }}</div>
              <div class="ppt-result-time">创建时间：{{ formatTime(message.created_at) }}</div>
            </div>
          </div>
          <div class="ppt-result-right">
            <div class="ppt-result-thumb">预览缩略图</div>
            <button class="ppt-preview-btn" type="button" @click.stop="$emit('preview')">预览</button>
          </div>
        </div>
      </template>

      <span v-else>{{ message.content }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import OutlineCard from './OutlineCard.vue'

const props = defineProps({
  message: { type: Object, required: true },
  outlineInteractive: { type: Boolean, default: false },
  showOutlineApprove: { type: Boolean, default: false },
})

defineEmits(['preview', 'outline-approve', 'outline-edit', 'outline-regenerate'])

const outlineMessage = computed(() => {
  const meta = props.message.metadata_ || {}
  return {
    id: meta.outline_id || props.message.outline_id || null,
    content: props.message.content || '',
    image_urls: meta.image_urls || props.message.image_urls || {},
    outline_payload: meta.outline_payload || props.message.outline_payload || null,
  }
})

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.chat-message {
  display: flex;
  margin-bottom: 24px;
  padding: 0;
}

.chat-message--user {
  justify-content: flex-end;
}

.chat-message--assistant {
  justify-content: flex-start;
}

.chat-message__bubble {
  max-width: 82%;
  padding: 16px 20px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.chat-message--user .chat-message__bubble {
  background: #3a61ea;
  color: #fff;
}

.chat-message--assistant .chat-message__bubble {
  background: #fff;
  color: #333;
  border: 1px solid #e5e5e5;
}

.chat-message__error {
  color: #e53935;
}

.outline-message .chat-message__bubble,
.ppt-result-message .chat-message__bubble {
  max-width: min(1180px, 100%);
}

.outline-message .chat-message__bubble {
  padding: 0;
  background: transparent;
  border: none;
}

.ppt-result-head {
  font-size: 14px;
  color: #7d8697;
  margin-bottom: 12px;
}

.ppt-result-card {
  border: 1px solid #e6e9f2;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.2s;
  background: #fbfcff;
  cursor: pointer;
}

.ppt-result-card:hover {
  border-color: #3a61ea;
  box-shadow: 0 4px 12px rgba(58, 97, 234, 0.14);
  transform: translateY(-1px);
}

.ppt-result-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.ppt-file-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #ffecee;
  color: #ef4444;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 13px;
}

.ppt-result-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.ppt-result-time {
  font-size: 12px;
  color: #8a94a6;
  margin-top: 3px;
}

.ppt-result-right {
  width: 128px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  flex-shrink: 0;
}

.ppt-result-thumb {
  width: 100%;
  height: 56px;
  border-radius: 8px;
  border: 1px solid #d6ddee;
  background: linear-gradient(135deg, #eff4ff 0%, #f9fbff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7e89a1;
  font-size: 12px;
}

.ppt-preview-btn {
  width: 100%;
  border: none;
  border-radius: 8px;
  background: #3a61ea;
  color: #fff;
  padding: 8px 10px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.ppt-preview-btn:hover {
  background: #2a4bc8;
}
</style>
