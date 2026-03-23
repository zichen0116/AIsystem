<script setup>
import { ref } from 'vue'

const inputText = ref('')
const messages = ref([
  {
    id: 1,
    role: 'user',
    text: '帮我根据“量子力学”生成一张适合高中课堂讲解的知识图谱。'
  },
  {
    id: 2,
    role: 'assistant',
    text:
      '好的，我会围绕核心概念、先修知识和典型应用三个维度，生成层级清晰的知识节点，并在右侧画布中展示。'
  }
])

function sendMessage() {
  const v = inputText.value.trim()
  if (!v) return
  messages.value.push({
    id: Date.now(),
    role: 'user',
    text: v
  })
  inputText.value = ''
}
</script>

<template>
  <div class="knowledge-page">
    <div class="knowledge-layout">
      <!-- 左侧聊天栏 -->
      <aside class="panel-left">

        <section class="chat-panel">
          <div class="chat-messages">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="chat-row"
              :class="msg.role === 'user' ? 'from-user' : 'from-assistant'"
            >
              <div class="avatar" aria-hidden="true">
                <span v-if="msg.role === 'user'">👩‍🏫</span>
                <span v-else>🤖</span>
              </div>
              <div class="bubble">
                <p class="bubble-text">
                  {{ msg.text }}
                </p>
              </div>
            </div>
          </div>

          <form class="chat-composer" @submit.prevent="sendMessage">
            <textarea
              v-model="inputText"
              class="composer-input"
              rows="3"
              placeholder="输入你想生成的知识图谱主题，如：量子力学在高中物理中的知识结构…"
            />
            <button type="submit" class="composer-btn">生成知识图谱</button>
          </form>
        </section>
      </aside>

      <!-- 右侧知识图谱画布 -->
      <section class="panel-right">

        <div class="canvas">
          <!-- 中心节点 -->
          <div class="node node-main">
            <span class="node-label">量子力学</span>
          </div>

          <!-- 子节点 -->
          <div class="node node-a">
            <span class="node-label">波粒二象性</span>
          </div>
          <div class="node node-b">
            <span class="node-label">薛定谔方程</span>
          </div>
          <div class="node node-c">
            <span class="node-label">量子纠缠</span>
          </div>
          <div class="node node-d">
            <span class="node-label muted">经典物理</span>
          </div>

          <!-- 连线（简化为背景线段） -->
          <svg class="canvas-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
            <line x1="30" y1="50" x2="55" y2="35" />
            <line x1="30" y1="50" x2="70" y2="50" />
            <line x1="30" y1="50" x2="48" y2="70" />
            <line x1="30" y1="50" x2="18" y2="70" />
          </svg>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.knowledge-page {
  flex: 1;
  min-height: 0;
  padding: 1.6% 2.2% 1.8%;
  background: #f5f7fb;
  display: flex;
}

.knowledge-layout {
  display: grid;
  grid-template-columns: minmax(280px, 30%) minmax(0, 1fr);
  gap: 1.4%;
  width: 100%;
  margin: 0 auto;
}

.panel-left {
  background: #ffffff;
  border-radius: 18px;
  padding: 20px 18px 18px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-header {
  margin-bottom: 4px;
}

.pill-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.pill-blue {
  background: #e0edff;
  color: #2563eb;
}

.pill-gray {
  background: #e5e7eb;
  color: #4b5563;
}

.topic-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.topic-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.chat-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-messages {
  flex: 1;
  min-height: 0;
  padding: 10px 8px 6px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  overflow-y: auto;
}

.chat-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.chat-row.from-user {
  flex-direction: row-reverse;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #e5edff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.chat-row.from-user .avatar {
  background: #dbeafe;
}

.bubble {
  max-width: min(88%, 340px);
  padding: 8px 10px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
}

.chat-row.from-user .bubble {
  background: #2563eb;
  color: #ffffff;
}

.chat-row.from-assistant .bubble {
  background: #ffffff;
  color: #111827;
  border: 1px solid #e5e7eb;
}

.bubble-text {
  margin: 0;
}

.chat-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.hint-title {
  font-weight: 500;
}

.hint-pill {
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4b5563;
}

.chat-composer {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.composer-input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 13px;
  resize: vertical;
  min-height: 70px;
  outline: none;
}

.composer-btn {
  align-self: flex-end;
  border: none;
  border-radius: 999px;
  background: #2563eb;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  cursor: pointer;
}

.panel-right {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 18px 18px 20px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 68vh;
}

.breadcrumb-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 8px;
}

.crumb.current {
  color: #4b5563;
  font-weight: 500;
}

.canvas {
  position: relative;
  flex: 1;
  min-height: 62vh;
  background: radial-gradient(circle at top, #f4f7ff 0, #ffffff 55%);
  border-radius: 14px;
  overflow: hidden;
  padding: 24px 24px 18px;
}

.canvas-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  stroke: #e0e7ff;
  stroke-width: 0.6;
  fill: none;
  pointer-events: none;
}

.node {
  position: absolute;
  padding: 8px 14px;
  border-radius: 999px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
  border: 1px solid #e5e7f5;
}

.node-label {
  font-size: 13px;
  color: #111827;
}

.node-main {
  left: 32%;
  top: 44%;
  padding: 10px 22px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  border: none;
}

.node-main .node-label {
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
}

.node-a {
  left: 52%;
  top: 30%;
}

.node-b {
  left: 75%;
  top: 45%;
}

.node-c {
  left: 45%;
  top: 70%;
}

.node-d {
  left: 20%;
  top: 70%;
}

.node-label.muted {
  color: #cbd5e1;
}

@media (max-width: 960px) {
  .knowledge-layout {
    grid-template-columns: minmax(0, 1fr);
    width: 100%;
    gap: 12px;
  }

  .panel-right {
    min-height: 52vh;
  }

  .canvas {
    min-height: 50vh;
  }
}

@media (max-width: 720px) {
  .knowledge-page {
    padding: 12px;
  }

  .panel-left {
    padding: 16px 14px 14px;
  }

  .canvas {
    padding: 20px 16px 16px;
    min-height: 46vh;
  }
}
</style>

