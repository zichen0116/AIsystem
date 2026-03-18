<template>
  <div class="welcome-panel">
    <div class="welcome-header">
      <div class="welcome-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect x="4" y="8" width="40" height="32" rx="4" fill="#3a61ea" opacity="0.12" />
          <rect x="8" y="12" width="32" height="24" rx="2" stroke="#3a61ea" stroke-width="2" fill="none" />
          <path d="M20 20l6 4-6 4V20z" fill="#3a61ea" />
        </svg>
      </div>
      <h1 class="welcome-title">智能 PPT 生成</h1>
      <p class="welcome-desc">输入主题或选择预设场景，AI 帮你快速生成专业演示文稿</p>
    </div>

    <div class="preset-grid">
      <div
        v-for="(card, i) in presetCards"
        :key="i"
        class="preset-card"
        @click="$emit('select-preset', card.prompt)"
      >
        <span class="preset-icon">{{ card.icon }}</span>
        <div class="preset-info">
          <span class="preset-title">{{ card.title }}</span>
          <span class="preset-desc">{{ card.desc }}</span>
        </div>
      </div>
    </div>

    <div class="action-bar">
      <button class="action-btn" @click="$emit('open-templates')">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <rect x="1" y="1" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.4" />
          <rect x="10" y="1" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.4" />
          <rect x="1" y="10" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.4" />
          <rect x="10" y="10" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.4" />
        </svg>
        选择模板
      </button>
      <button class="action-btn" @click="$emit('open-knowledge')">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M3 3h4.5v12H3a1 1 0 01-1-1V4a1 1 0 011-1z" stroke="currentColor" stroke-width="1.4" />
          <path d="M7.5 3H15a1 1 0 011 1v10a1 1 0 01-1 1H7.5V3z" stroke="currentColor" stroke-width="1.4" />
          <path d="M5 7h1M5 9.5h1M10 7h3M10 9.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
        </svg>
        知识库
      </button>
    </div>

    <div class="input-area">
      <input
        class="topic-input"
        :value="modelValue"
        placeholder="输入你想生成的 PPT 主题，例如：人工智能发展趋势"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.enter.exact.prevent="handleSend"
      />
      <button
        class="send-btn"
        :disabled="!modelValue?.trim()"
        @click="handleSend"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M3 10h14M12 5l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
})

const emit = defineEmits([
  'update:modelValue',
  'send',
  'select-preset',
  'open-templates',
  'open-knowledge',
])

const presetCards = [
  {
    icon: '📚',
    title: '教学课件',
    desc: '课堂教学演示文稿',
    prompt: '帮我生成一份教学课件PPT',
  },
  {
    icon: '🎓',
    title: '学术汇报',
    desc: '论文答辩与学术分享',
    prompt: '帮我生成一份学术汇报PPT',
  },
  {
    icon: '📊',
    title: '工作总结',
    desc: '阶段性工作成果汇报',
    prompt: '帮我生成一份工作总结PPT',
  },
  {
    icon: '🎨',
    title: '创意展示',
    desc: '创意方案与项目展示',
    prompt: '帮我生成一份创意展示PPT',
  },
]

function handleSend() {
  if (!props.modelValue?.trim()) return
  emit('send')
}
</script>

<style scoped>
.welcome-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 48px 24px 32px;
  min-height: 0;
}

.welcome-header {
  text-align: center;
  margin-bottom: 36px;
}

.welcome-icon {
  margin-bottom: 12px;
}

.welcome-title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #1e3a8a 0%, #3a61ea 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 8px;
}

.welcome-desc {
  font-size: 15px;
  color: #64748b;
  margin: 0;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  width: 100%;
  max-width: 520px;
  margin-bottom: 24px;
}

.preset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-card:hover {
  border-color: #3a61ea;
  box-shadow: 0 4px 12px rgba(58, 97, 234, 0.1);
  transform: translateY(-1px);
}

.preset-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.preset-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.preset-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.preset-desc {
  font-size: 12px;
  color: #94a3b8;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  border-color: #3a61ea;
  color: #3a61ea;
  background: #f0f4ff;
}

.input-area {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  max-width: 520px;
}

.topic-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  color: #1e293b;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fff;
}

.topic-input::placeholder {
  color: #94a3b8;
}

.topic-input:focus {
  border-color: #3a61ea;
  box-shadow: 0 0 0 3px rgba(58, 97, 234, 0.12);
}

.send-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 12px;
  background: #3a61ea;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #2d4fd4;
}

.send-btn:disabled {
  background: #c7d2fe;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .preset-grid {
    grid-template-columns: 1fr;
  }
  .input-area {
    max-width: 100%;
  }
}
</style>
