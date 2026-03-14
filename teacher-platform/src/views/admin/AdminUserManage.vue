<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">教师用户管理</h1>
        <p class="page-subtitle">管理全体教师账号，角色分配及使用状态。</p>
      </div>
      <button type="button" class="primary-btn">+ 新增教师</button>
    </header>

    <section class="stats-row">
      <div class="stat-card">
        <p class="stat-label">总教师数</p>
        <p class="stat-value">1,280</p>
        <p class="stat-extra">较上月 +12%</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">当前在线</p>
        <p class="stat-value online">42</p>
        <p class="stat-extra">含移动端登录</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">待审核账号</p>
        <p class="stat-value pending">15</p>
        <p class="stat-extra">优先审核新加入学校</p>
      </div>
    </section>

    <section class="table-card">
      <div class="table-toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" placeholder="搜索教师姓名、工号或所属部门" />
        </div>
        <div class="toolbar-actions">
          <select class="filter-select">
            <option>全部角色</option>
            <option>备课教师</option>
            <option>年级组长</option>
          </select>
          <select class="filter-select">
            <option>账号状态</option>
            <option>已激活</option>
            <option>待审核</option>
            <option>已禁用</option>
          </select>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>教师姓名</th>
            <th>工号</th>
            <th>所属部门</th>
            <th>系统角色</th>
            <th>最近活跃时间</th>
            <th>状态</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">陈</span>
                <span class="user-name">陈明华</span>
              </div>
            </td>
            <td>T20236901</td>
            <td>数学教研组</td>
            <td><span class="role-tag">高级教师</span></td>
            <td>2023-11-24 09:15</td>
            <td><span class="status-tag ok">已激活</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-green">周</span>
                <span class="user-name">周丽君</span>
              </div>
            </td>
            <td>T20236789</td>
            <td>生物教研组</td>
            <td><span class="role-tag">备课教师</span></td>
            <td>2023-11-22 08:45</td>
            <td><span class="status-tag ok">已激活</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-orange">何</span>
                <span class="user-name">何建国</span>
              </div>
            </td>
            <td>T20235990</td>
            <td>历史教研组</td>
            <td><span class="role-tag">教研组长</span></td>
            <td>2023-11-21 17:20</td>
            <td><span class="status-tag ok">已激活</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">刘</span>
                <span class="user-name">刘晓彤</span>
              </div>
            </td>
            <td>T20234881</td>
            <td>信息技术组</td>
            <td><span class="role-tag">平台管理员</span></td>
            <td>2023-11-19 11:05</td>
            <td><span class="status-tag ok">已激活</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-green">李</span>
                <span class="user-name">李春彤</span>
              </div>
            </td>
            <td>T20236445</td>
            <td>语文教研组</td>
            <td><span class="role-tag">备课教师</span></td>
            <td>2023-11-23 16:40</td>
            <td><span class="status-tag ok">已激活</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-orange">王</span>
                <span class="user-name">王小波</span>
              </div>
            </td>
            <td>T20231802</td>
            <td>英语教研组</td>
            <td><span class="role-tag">年级组长</span></td>
            <td>2023-11-20 10:22</td>
            <td><span class="status-tag disabled">已停用</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">张</span>
                <span class="user-name">张凯齐</span>
              </div>
            </td>
            <td>T20231555</td>
            <td>物理教研组</td>
            <td><span class="role-tag">备课教师</span></td>
            <td>2023-11-24 14:30</td>
            <td><span class="status-tag ok">已激活</span></td>
            <td class="col-actions">
              <button type="button" class="icon-btn">✏️</button>
              <button type="button" class="icon-btn">⛔</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <span class="footer-text">显示 1-10 条，共 1,280 条教师记录</span>
        <div class="pagination">
          <button type="button" class="page-btn">‹</button>
          <button type="button" class="page-btn active">1</button>
          <button type="button" class="page-btn">2</button>
          <button type="button" class="page-btn">3</button>
          <span class="page-ellipsis">…</span>
          <button type="button" class="page-btn">128</button>
          <button type="button" class="page-btn">›</button>
        </div>
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
  margin-bottom: 18px;
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

.primary-btn {
  border: none;
  border-radius: 999px;
  padding: 10px 18px;
  background: #2563eb;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
}

.stat-label {
  margin: 0 0 4px;
  font-size: 14px;
  color: #64748b;
}

.stat-value {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.stat-value.online {
  color: #16a34a;
}

.stat-value.pending {
  color: #f97316;
}

.stat-extra {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
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

.role-tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 12px;
}

.status-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
}

.status-tag.ok {
  background: #dcfce7;
  color: #15803d;
}

.status-tag.disabled {
  background: #fee2e2;
  color: #b91c1c;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  margin-left: 4px;
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

.page-ellipsis {
  font-size: 12px;
  color: #9ca3af;
}
</style>

