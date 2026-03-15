<template>
  <div class="chat-msg assistant">
    <div class="document-card" @click="$emit('open')">
      <div class="doc-icon">📄</div>
      <div class="doc-info">
        <div class="doc-title">{{ title || '教案文档' }}</div>
        <div class="doc-hint">点击查看完整教案</div>
      </div>
      <div class="doc-arrow">›</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '教案文档' },
})
defineEmits(['open'])
</script>

<style scoped>
.chat-msg.assistant {
  justify-content: flex-start;
  margin-bottom: 20px;
  display: flex;
}
.document-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid #e8ecf0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  max-width: 360px;
}
.document-card:hover {
  border-color: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
}
.doc-icon {
  font-size: 28px;
}
.doc-info {
  flex: 1;
}
.doc-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
}
.doc-hint {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.doc-arrow {
  font-size: 20px;
  color: #ccc;
  transition: color 0.2s;
}
.document-card:hover .doc-arrow {
  color: #2563eb;
}
</style>
