<template>
  <div class="welcome-area">
    <div class="welcome-icon">📝</div>
    <div class="welcome-title">AI 智能教案生成</div>
    <div class="welcome-desc">告诉我你的教学需求，我来帮你生成专业教案</div>
    <div class="prompt-grid">
      <div
        v-for="(card, i) in promptCards"
        :key="i"
        class="prompt-card"
        @click="$emit('select-prompt', card.prompt)"
      >
        <div class="card-icon">{{ card.icon }}</div>
        <div class="card-title">{{ card.title }}</div>
        <div class="card-desc">{{ card.desc }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['select-prompt'])

const promptCards = [
  { icon: '📐', title: '小学数学教案', desc: '帮我生成一份三年级「分数的初步认识」教案', prompt: '帮我生成一份三年级「分数的初步认识」教案' },
  { icon: '🔬', title: '实验课教案', desc: '设计一节高中化学实验课教案', prompt: '设计一节高中化学实验课教案' },
  { icon: '📖', title: '语文阅读课', desc: '初中语文《背影》精读课教案', prompt: '初中语文《背影》精读课教案' },
  { icon: '🌍', title: '地理探究课', desc: '「地球的运动」探究式教学设计', prompt: '帮我设计「地球的运动」探究式教学' },
  { icon: '🎨', title: '美术鉴赏课', desc: '小学美术色彩基础课教案', prompt: '帮我生成小学美术色彩基础课教案' },
  { icon: '🏃', title: '体育课教案', desc: '初中篮球基础技能训练课', prompt: '帮我设计初中篮球基础技能训练课教案' },
  { icon: '🎵', title: '音乐欣赏课', desc: '小学音乐节奏感培养教案', prompt: '帮我生成小学音乐节奏感培养教案' },
  { icon: '💻', title: '信息技术课', desc: '初中 Python 编程入门教案', prompt: '帮我生成初中 Python 编程入门教案' },
  { icon: '🧪', title: '跨学科融合', desc: 'STEM 项目式学习教案设计', prompt: '帮我设计一份 STEM 项目式学习教案' },
]
</script>

<style scoped>
.welcome-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.welcome-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.welcome-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}
.welcome-desc {
  font-size: 14px;
  color: #888;
  margin-bottom: 36px;
}
.prompt-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
  max-width: 680px;
}
.prompt-card {
  background: #fff;
  border: 1px solid #e8ecf0;
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 13px;
  color: #444;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.5;
}
.prompt-card:hover {
  border-color: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
  transform: translateY(-1px);
}
.card-icon {
  font-size: 18px;
  margin-bottom: 6px;
}
.card-title {
  font-weight: 500;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.card-desc {
  font-size: 12px;
  color: #888;
}
</style>
