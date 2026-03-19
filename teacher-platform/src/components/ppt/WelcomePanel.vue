<template>
  <div class="welcome-stage">
    <h1 class="welcome-title">创建你的教学PPT</h1>
    <p class="welcome-subtitle">选择模板，输入主题，AI帮你生成专业课件</p>

    <div class="input-section">
      <ChatInput
        :model-value="modelValue"
        :placeholder="'输入你想创建的 PPT 主题，例如：中国传统文化'"
        @update:model-value="$emit('update:modelValue', $event)"
        @send="$emit('send')"
        @open-file-upload="$emit('open-file-upload')"
        @open-image-upload="$emit('open-image-upload')"
        @open-voice="$emit('open-voice')"
        @open-knowledge="$emit('open-knowledge')"
      />
    </div>

    <TemplateSelector
      :inline="true"
      :model-value="selectedTemplateId"
      @update:model-value="$emit('update:templateId', $event)"
      @select="$emit('select-template', $event)"
    />
  </div>
</template>

<script setup>
import ChatInput from './ChatInput.vue'
import TemplateSelector from './TemplateSelector.vue'

defineProps({
  modelValue: { type: String, default: '' },
  selectedTemplateId: { type: String, default: null },
})

defineEmits([
  'update:modelValue',
  'send',
  'update:templateId',
  'select-template',
  'open-file-upload',
  'open-image-upload',
  'open-voice',
  'open-knowledge',
])
</script>

<style scoped>
.welcome-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  height: 100%;
  padding: 72px 40px 40px;
  overflow-y: auto;
}
.welcome-title {
  font-size: 48px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 16px;
}
.welcome-subtitle {
  font-size: 16px;
  color: #666;
  margin: 0 0 40px;
}
.input-section {
  width: 100%;
  max-width: 800px;
  margin-bottom: 40px;
}
.input-section :deep(.chat-input-wrap) {
  padding: 0;
  background: transparent;
  border-top: none;
}
</style>
