<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">系统日志 · 审计记录</h1>
        <p class="page-subtitle">监控教学平台内的所有关键操作，确保系统安全可追溯。</p>
      </div>
      <button type="button" class="primary-btn">导出日志数据</button>
    </header>

    <section class="filter-bar">
      <div class="filter-group">
        <button type="button" class="chip active">全部日志</button>
        <button type="button" class="chip normal">正常</button>
        <button type="button" class="chip warn">警告</button>
        <button type="button" class="chip error">错误</button>
      </div>
      <div class="filter-group right">
        <span class="filter-label">日期范围：</span>
        <input type="date" class="date-input" />
        <span>至</span>
        <input type="date" class="date-input" />
      </div>
    </section>

    <section class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>操作人</th>
            <th>操作内容</th>
            <th>日志级别</th>
            <th>IP 地址</th>
            <th>时间戳</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">张</span>
                <span class="user-name">张晓华</span>
              </div>
            </td>
            <td>成功登录教学系统 · 认证模块</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">192.168.1.124</span></td>
            <td>2023-10-27 14:32:01</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr class="row-warn">
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-gray">系</span>
                <span class="user-name">系统通知</span>
              </div>
            </td>
            <td>每日自动备份任务失败</td>
            <td><span class="level-tag warn">警告</span></td>
            <td><span class="ip-tag">127.0.0.1</span></td>
            <td>2023-10-27 04:00:15</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">李</span>
                <span class="user-name">李教务</span>
              </div>
            </td>
            <td>尝试修改高三数学教学文件夹</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">10.0.24.56</span></td>
            <td>2023-10-22 11:20:44</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">王</span>
                <span class="user-name">王管理员</span>
              </div>
            </td>
            <td>重置了个人主页面布局配置</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">114.22.45.19</span></td>
            <td>2023-10-26 18:05:32</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">赵</span>
                <span class="user-name">赵敏</span>
              </div>
            </td>
            <td>重置了学生账户（ID: 8823）的密码</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">192.168.1.35</span></td>
            <td>2023-10-26 15:44:12</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-gray">系</span>
                <span class="user-name">系统任务</span>
              </div>
            </td>
            <td>自动清理过期会话 · 42 条记录被移除</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">127.0.0.1</span></td>
            <td>2023-10-26 03:10:02</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">周</span>
                <span class="user-name">周教务</span>
              </div>
            </td>
            <td>批量导入 60 名新生账号</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">10.0.12.8</span></td>
            <td>2023-10-25 16:32:40</td>
            <td class="col-actions">👁</td>
          </tr>
          <tr>
            <td>
              <div class="user-cell">
                <span class="user-avatar avatar-blue">曾</span>
                <span class="user-name">曾运维</span>
              </div>
            </td>
            <td>手动触发系统健康检查 · 所有服务正常</td>
            <td><span class="level-tag ok">正常</span></td>
            <td><span class="ip-tag">192.168.2.10</span></td>
            <td>2023-10-25 09:18:21</td>
            <td class="col-actions">👁</td>
          </tr>
        </tbody>
      </table>

      <div class="table-footer">
        <span class="footer-text">显示 1-5 条 / 共 1,248 条审计记录</span>
        <div class="pagination">
          <button type="button" class="page-btn">‹</button>
          <button type="button" class="page-btn active">1</button>
          <button type="button" class="page-btn">2</button>
          <button type="button" class="page-btn">3</button>
          <span class="page-ellipsis">…</span>
          <button type="button" class="page-btn">250</button>
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

.primary-btn {
  border: none;
  border-radius: 999px;
  padding: 9px 18px;
  background: #2563eb;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chip {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  padding: 6px 12px;
  background: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

.chip.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.chip.normal {
  color: #16a34a;
}

.chip.warn {
  color: #f97316;
}

.chip.error {
  color: #ef4444;
}

.filter-label {
  font-size: 14px;
  color: #64748b;
}

.date-input {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
}

.table-card {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  padding: 20px 20px 22px;
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

.avatar-gray {
  background: #94a3b8;
}

.user-name {
  color: #0f172a;
}

.level-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
}

.level-tag.ok {
  background: #dcfce7;
  color: #15803d;
}

.level-tag.warn {
  background: #fef3c7;
  color: #b45309;
}

.ip-tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e5e7eb;
  font-size: 11px;
  color: #374151;
}

.row-warn {
  background: #fff7ed;
}

.col-actions {
  text-align: center;
  font-size: 16px;
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
  font-size: 13px;
  color: #9ca3af;
}

@media (max-width: 1100px) {
  .admin-page { padding: 20px 20px 24px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .filter-bar { flex-direction: column; align-items: stretch; gap: 10px; }
}

@media (max-width: 720px) {
  .admin-page { padding: 16px 12px 20px; }
  .page-title { font-size: 20px; }
  .filter-group { flex-wrap: wrap; }
  .table-card { padding: 12px; overflow-x: auto; }
  .data-table { min-width: 580px; font-size: 13px; }
  .table-footer { flex-direction: column; gap: 8px; align-items: flex-start; }
}

@media (max-width: 480px) {
  .admin-page { padding: 12px 10px 16px; }
  .page-title { font-size: 18px; }
}
</style>

