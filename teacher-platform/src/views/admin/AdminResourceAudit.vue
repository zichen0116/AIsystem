<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">资源审计 · 待审核列表</h1>
        <p class="page-subtitle">目前共有 12 份教学资源等待你处理。</p>
      </div>
      <div class="header-actions">
        <button type="button" class="outline-btn">导出审核记录</button>
        <button type="button" class="primary-btn">全部通过</button>
      </div>
    </header>

    <section class="tabs-row">
      <button type="button" class="tab active">全部待审（12）</button>
      <button type="button" class="tab">文档资源（5）</button>
      <button type="button" class="tab">视频资源（4）</button>
      <button type="button" class="tab">课件 PPT（3）</button>
    </section>

    <section class="table-card">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" placeholder="搜索资源名称、上传教师或标签" />
        </div>
        <div class="toolbar-actions">
          <select class="filter-select">
            <option>按提交时间</option>
            <option>按资源类型</option>
            <option>按上传教师</option>
          </select>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>资源名称 &amp; 说明</th>
            <th>类型</th>
            <th>上传教师</th>
            <th>提交时间</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div class="res-cell">
                <span class="res-icon blue">PPT</span>
                <div>
                  <p class="res-title">2024 高中数学学习-函数专题课件</p>
                  <p class="res-sub">12.5 MB · PowerPoint 文件</p>
                </div>
              </div>
            </td>
            <td><span class="type-tag">课件</span></td>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">李</span>
                <span class="user-name">李泽洋（数学组）</span>
              </div>
            </td>
            <td>2023-11-25 14:30</td>
            <td class="col-actions">
              <button type="button" class="btn-pass">通过</button>
              <button type="button" class="btn-reject">驳回</button>
            </td>
          </tr>

          <tr class="row-highlight">
            <td>
              <div class="res-cell">
                <span class="res-icon green">MP4</span>
                <div>
                  <p class="res-title">英语口语课堂-情景对话示范视频</p>
                  <p class="res-sub">156 MB · MP4 视频 · 4K</p>
                </div>
              </div>
            </td>
            <td><span class="type-tag green">视频</span></td>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-green">王</span>
                <span class="user-name">王志琪（英语组）</span>
              </div>
            </td>
            <td>2023-11-25 10:15</td>
            <td class="col-actions">
              <button type="button" class="btn-pass">通过</button>
              <button type="button" class="btn-reject">驳回并说明</button>
            </td>
          </tr>

          <tr>
            <td>
              <div class="res-cell">
                <span class="res-icon orange">PDF</span>
                <div>
                  <p class="res-title">初中物理实验-电路串并联教案</p>
                  <p class="res-sub">2.1 MB · PDF 文档</p>
                </div>
              </div>
            </td>
            <td><span class="type-tag orange">文档</span></td>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-orange">陈</span>
                <span class="user-name">陈佳欣（物理组）</span>
              </div>
            </td>
            <td>2023-11-24 16:50</td>
            <td class="col-actions">
              <button type="button" class="btn-pass">通过</button>
              <button type="button" class="btn-reject">驳回</button>
            </td>
          </tr>

          <tr>
            <td>
              <div class="res-cell">
                <span class="res-icon blue">PPT</span>
                <div>
                  <p class="res-title">高一生物-大气环境变化课件</p>
                  <p class="res-sub">4.8 MB · PowerPoint 文件</p>
                </div>
              </div>
            </td>
            <td><span class="type-tag">课件</span></td>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">赵</span>
                <span class="user-name">赵立新（地理组）</span>
              </div>
            </td>
            <td>2023-11-24 09:20</td>
            <td class="col-actions">
              <button type="button" class="btn-pass">通过</button>
              <button type="button" class="btn-reject">驳回</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="res-cell">
                <span class="res-icon orange">PDF</span>
                <div>
                  <p class="res-title">语文阅读理解-课外文章精选</p>
                  <p class="res-sub">3.2 MB · PDF 文档</p>
                </div>
              </div>
            </td>
            <td><span class="type-tag orange">文档</span></td>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-green">孙</span>
                <span class="user-name">孙雅宁（语文组）</span>
              </div>
            </td>
            <td>2023-11-24 08:10</td>
            <td class="col-actions">
              <button type="button" class="btn-pass">通过</button>
              <button type="button" class="btn-reject">驳回</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <span class="footer-text">显示 1-4 条，共 12 份待审资源</span>
        <div class="pagination">
          <button type="button" class="page-btn">‹</button>
          <button type="button" class="page-btn active">1</button>
          <button type="button" class="page-btn">2</button>
          <button type="button" class="page-btn">3</button>
          <button type="button" class="page-btn">›</button>
        </div>
      </div>
    </section>

    <section class="bottom-stats">
      <div class="bottom-card">
        <p class="bottom-label">今日通过</p>
        <p class="bottom-value">12 份</p>
      </div>
      <div class="bottom-card">
        <p class="bottom-label">今日驳回</p>
        <p class="bottom-value">4 份</p>
      </div>
      <div class="bottom-card">
        <p class="bottom-label">平均处理时长</p>
        <p class="bottom-value">1.2 h</p>
      </div>
      <div class="bottom-card">
        <p class="bottom-label">资源合规率</p>
        <p class="bottom-value">92.5%</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-page {
  flex: 1;
  min-height: 100%;
  padding: 28px 32px 32px;
  background: #f4f7fb;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  font-size: 15px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.primary-btn {
  border: none;
  border-radius: 999px;
  padding: 9px 16px;
  background: #2563eb;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.outline-btn {
  border-radius: 999px;
  padding: 9px 16px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #0f172a;
  font-size: 15px;
  cursor: pointer;
}

.tabs-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tab {
  border-radius: 999px;
  border: none;
  padding: 7px 14px;
  background: #e5e7eb;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
}

.tab.active {
  background: #2563eb;
  color: #ffffff;
}

.table-card {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 20px 20px 22px;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.search-icon {
  font-size: 14px;
}

.search-box input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 14px;
  color: #4b5563;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table thead {
  background: #f8fafc;
}

.data-table th,
.data-table td {
  padding: 9px 10px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.data-table th {
  font-weight: 600;
  color: #64748b;
}

.res-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.res-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #ffffff;
}

.res-icon.blue {
  background: #2563eb;
}

.res-icon.green {
  background: #16a34a;
}

.res-icon.orange {
  background: #f97316;
}

.res-title {
  margin: 0 0 2px;
  color: #0f172a;
}

.res-sub {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}

.type-tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e5e7eb;
  font-size: 12px;
  color: #4b5563;
}

.type-tag.green {
  background: #dcfce7;
  color: #15803d;
}

.type-tag.orange {
  background: #fee2e2;
  color: #b91c1c;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #ffffff;
}

.avatar-blue {
  background: #3b82f6;
}

.avatar-green {
  background: #10b981;
}

.avatar-orange {
  background: #f97316;
}

.user-name {
  color: #0f172a;
}

.btn-pass,
.btn-reject {
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  border: none;
  cursor: pointer;
  margin-left: 4px;
}

.btn-pass {
  background: #dcfce7;
  color: #15803d;
}

.btn-reject {
  background: #fee2e2;
  color: #b91c1c;
}

.row-highlight {
  background: #fefce8;
}

.col-actions {
  text-align: center;
  white-space: nowrap;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  font-size: 13px;
  color: #9ca3af;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-btn {
  min-width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

.page-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.bottom-stats {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.bottom-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
}

.bottom-label {
  margin: 0 0 4px;
  font-size: 13px;
  color: #64748b;
}

.bottom-value {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
}

@media (max-width: 1100px) {
  .admin-page { padding: 20px 20px 24px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .tabs-row { flex-wrap: wrap; gap: 6px; }
  .bottom-stats { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 720px) {
  .admin-page { padding: 16px 12px 20px; }
  .page-title { font-size: 20px; }
  .header-actions { flex-wrap: wrap; }
  .table-card { padding: 12px; overflow-x: auto; }
  .data-table { min-width: 620px; font-size: 13px; }
  .table-toolbar { flex-direction: column; align-items: stretch; }
  .bottom-stats { grid-template-columns: 1fr; }
  .table-footer { flex-direction: column; gap: 8px; align-items: flex-start; }
}

@media (max-width: 480px) {
  .admin-page { padding: 12px 10px 16px; }
  .page-title { font-size: 18px; }
}
</style>

