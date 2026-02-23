<script setup>
import { ref } from 'vue'

const docs = ref([
  { name: 'Lecture_04_Quantum_Intro.pdf', type: 'PDF', size: '4.2 MB', status: '处理中', updateTime: '2分钟前' },
  { name: 'Thermodynamics_Summary.docx', type: 'Word', size: '1.8 MB', status: '已向量化', updateTime: '昨天' },
  { name: 'Lab_Safety_Protocol_v2.pptx', type: 'PPT', size: '12.5 MB', status: '已向量化', updateTime: '3天前' },
  { name: 'Newtonian_Mechanics_Quiz.pdf', type: 'PDF', size: '850 KB', status: '已向量化', updateTime: '5天前' },
  { name: 'Unreadable_Scan_004.txt', type: 'TXT', size: '12 KB', status: '失败', updateTime: '1周前' }
])

function getStatusClass(status) {
  if (status === '已向量化') return 'status-success'
  if (status === '处理中') return 'status-processing'
  return 'status-failed'
}
</script>

<template>
  <div class="knowledge-page">
    <div class="knowledge-content">
    <div class="header-actions-bar">
      <button class="action-btn">🔄 全部重新同步</button>
      <button class="action-btn primary">☁️ 上传资料</button>
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-icon success">✓</span>
        <span class="stat-value">142</span>
        <span class="stat-label">已索引总量</span>
      </div>
      <div class="stat-card">
        <span class="stat-icon processing">⏳</span>
        <span class="stat-value">4</span>
        <span class="stat-label">处理中</span>
      </div>
      <div class="stat-card">
        <span class="stat-icon vector">⚛</span>
        <span class="stat-value">2.4M</span>
        <span class="stat-label">向量数</span>
      </div>
      <div class="stat-card">
        <span class="stat-icon storage">☁</span>
        <span class="stat-value">450 / 1GB</span>
        <span class="stat-label">存储空间</span>
      </div>
    </div>

    <div class="content-layout">
      <div class="doc-repo">
        <div class="section-header">
          <h3>文档仓库</h3>
          <span class="sort-icon">⋮⋮</span>
        </div>
        <table class="doc-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>类型</th>
              <th>大小</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(doc, i) in docs" :key="i">
              <td>
                <span class="doc-name">{{ doc.name }}</span>
                <span class="doc-time">{{ doc.updateTime }}</span>
              </td>
              <td>{{ doc.type }}</td>
              <td>{{ doc.size }}</td>
              <td>
                <span :class="['status-tag', getStatusClass(doc.status)]">
                  {{ doc.status === '失败' ? '✗ ' : '' }}{{ doc.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <span>显示146个文档中的1-5个</span>
          <div class="page-btns">
            <button class="page-btn">上一页</button>
            <button class="page-btn">下一页</button>
          </div>
        </div>
      </div>

      <div class="right-panels">
        <div class="panel source-mapping">
          <h3>🔗 来源映射</h3>
          <p class="panel-desc">可视化文件与模块之间的链接。</p>
          <div class="mapping-diagram">
            <div class="core-module">Physics 101 Module A</div>
            <div class="aux-docs">
              <span class="aux-doc">Quantum_Int...</span>
              <span class="aux-doc">Thermo.docx</span>
              <span class="aux-doc badge">Lab_Safety_Pr... <small>1</small></span>
            </div>
          </div>
          <div class="legend">
            <span>● 核心模块</span>
            <span>○ 辅助文档</span>
          </div>
        </div>
        <div class="panel capacity">
          <h3>知识库容量</h3>
          <div class="progress-bar">
            <div class="progress-fill" style="width: 45%"></div>
          </div>
          <p class="capacity-text">450 MB 已用 / 1 GB 总量</p>
          <button class="upgrade-btn">升级方案</button>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-page {
  min-height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
}

.knowledge-content {
  flex: 1;
  padding: 24px;
}

.header-actions-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.action-btn {
  padding: 10px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.action-btn.primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-icon {
  font-size: 1.5rem;
}

.stat-icon.success { color: #22c55e; }
.stat-icon.processing { color: #eab308; }
.stat-icon.vector { color: #38bdf8; }
.stat-icon.storage { color: #a78bfa; }

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
}

.stat-label {
  font-size: 0.875rem;
  color: #64748b;
}

.content-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 24px;
}

.doc-repo {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 1.125rem;
  color: #1e293b;
}

.sort-icon {
  color: #94a3b8;
  cursor: pointer;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
}

.doc-table th {
  text-align: left;
  padding: 12px;
  font-size: 0.875rem;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
}

.doc-table td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem;
}

.doc-name {
  display: block;
  color: #1e293b;
}

.doc-time {
  font-size: 0.75rem;
  color: #94a3b8;
}

.status-tag {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8125rem;
}

.status-success { background: #dcfce7; color: #166534; }
.status-processing { background: #fef9c3; color: #854d0e; }
.status-failed { background: #fee2e2; color: #991b1b; }

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
  font-size: 0.875rem;
  color: #64748b;
}

.page-btns {
  display: flex;
  gap: 8px;
}

.page-btn {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
}

.right-panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.panel h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 8px;
}

.panel-desc {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 16px;
}

.mapping-diagram {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 12px;
}

.core-module {
  width: 140px;
  padding: 12px;
  background: #3b82f6;
  color: #fff;
  text-align: center;
  border-radius: 20px;
  font-size: 0.875rem;
}

.aux-docs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.aux-doc {
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.75rem;
  color: #64748b;
}

.aux-doc.badge {
  border-color: #3b82f6;
  color: #3b82f6;
}

.legend {
  font-size: 0.75rem;
  color: #94a3b8;
  display: flex;
  gap: 16px;
}

.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 4px;
}

.capacity-text {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 12px;
}

.upgrade-btn {
  padding: 8px 16px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
}
</style>
