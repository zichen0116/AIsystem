<script setup>
import { ref } from 'vue'

const activeTab = ref('ppt') // ppt | animation | data | knowledge

const tabs = [
  { id: 'ppt', label: '生成ppt和教案', icon: '📄' },
  { id: 'animation', label: '做动画和小游戏', icon: '🎮' },
  { id: 'data', label: '数据分析', icon: '📊' },
  { id: 'knowledge', label: '知识图谱', icon: '🕸' }
]

</script>

<template>
  <div class="lesson-prep-page">
    <div class="lesson-prep-body">
    <aside class="sidebar">
      <nav class="sidebar-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="nav-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="nav-icon">{{ tab.icon }}</span>
          <span class="nav-label">{{ tab.label }}</span>
        </button>
      </nav>
    </aside>

    <main class="main-content">
      <!-- 生成ppt和教案 -->
      <div v-show="activeTab === 'ppt'" class="content-panel">
        <div class="chat-header">
          <h3>生成PPT和教案</h3>
          <span class="model-badge">GLM-5</span>
        </div>
        <div class="chat-area">
          <div class="greeting">
            <p class="greeting-text">过年好，有什么我能帮你分担的吗？👋</p>
            <div class="glm-card">
              <span>GLM-5，进化开启</span>
            </div>
          </div>
          <div class="input-section">
            <textarea class="chat-input" placeholder="和我聊聊天吧" rows="3"></textarea>
            <div class="input-toolbar">
              <span class="tool-btn">📎</span>
              <span class="tool-btn">⊕</span>
              <span class="tool-btn">💭 思考</span>
              <span class="tool-btn active">🌐 联网</span>
              <span class="tool-btn">⚙ Agent</span>
              <button class="send-btn">➤</button>
            </div>
            <div class="mode-btns">
              <button class="mode-btn">🔬 研究模式</button>
              <button class="mode-btn">🖥 PPT模式</button>
              <button class="mode-btn">📈 数据分析 <span class="new-badge">New</span></button>
              <button class="mode-btn">更多 ▼</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 做动画和小游戏 -->
      <div v-show="activeTab === 'animation'" class="content-panel">
        <div class="panel-placeholder">
          <h3>做动画和小游戏</h3>
          <p>在此创建互动式动画与教育小游戏</p>
        </div>
      </div>

      <!-- 数据分析 -->
      <div v-show="activeTab === 'data'" class="content-panel">
        <div class="panel-placeholder">
          <h3>数据分析</h3>
          <p>导入学生数据，进行学情分析与可视化</p>
        </div>
      </div>

      <!-- 知识图谱 -->
      <div v-show="activeTab === 'knowledge'" class="content-panel">
        <div class="panel-placeholder">
          <h3>知识图谱</h3>
          <p>构建与可视化学科知识关联网络</p>
        </div>
      </div>
    </main>
    </div>
  </div>
</template>

<style scoped>
.lesson-prep-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.lesson-prep-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.sidebar-nav {
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  border-radius: 10px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.nav-item.active {
  background: #eff6ff;
  color: #3b82f6;
  font-weight: 500;
}

.nav-icon {
  font-size: 1.25rem;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  margin: 24px;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-header h3 {
  font-size: 1.125rem;
  color: #1e293b;
}

.model-badge {
  font-size: 0.75rem;
  padding: 4px 10px;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 6px;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.greeting {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
}

.greeting-text {
  font-size: 1.5rem;
  color: #1e293b;
  margin-bottom: 20px;
}

.glm-card {
  padding: 12px 20px;
  background: #f8fafc;
  border-radius: 12px;
  font-size: 0.875rem;
  color: #64748b;
}

.input-section {
  margin-top: auto;
}

.chat-input {
  width: 100%;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-size: 15px;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #3b82f6;
}

.input-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 0;
}

.tool-btn {
  padding: 6px 12px;
  font-size: 0.875rem;
  color: #64748b;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.tool-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.tool-btn.active {
  color: #3b82f6;
  background: #eff6ff;
}

.send-btn {
  margin-left: auto;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #3b82f6;
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 1rem;
}

.mode-btns {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.mode-btn {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #475569;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.new-badge {
  font-size: 0.65rem;
  padding: 2px 6px;
  background: #22c55e;
  color: #fff;
  border-radius: 4px;
}

.panel-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: #64748b;
}

.panel-placeholder h3 {
  font-size: 1.25rem;
  color: #1e293b;
  margin-bottom: 8px;
}
</style>
