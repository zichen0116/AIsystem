<template>
  <div class="admin-page">
    <div class="admin-header">
      <h1 class="admin-title">管理员控制台</h1>
      <p class="admin-subtitle">这里将展示平台运营数据与管理功能（占位页面，可后续补充内容）。</p>
    </div>
    <div class="admin-content">
      <div class="admin-card">
        <h2 class="card-title">用户与角色管理</h2>
        <p class="card-desc">后续可在此查看教师账号、分配角色与权限。</p>
      </div>
      <div class="admin-card">
        <h2 class="card-title">内容与资源统计</h2>
        <p class="card-desc">后续可在此统计课件数量、知识库内容与使用情况。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  min-height: 100%;
  padding: 32px 32px 40px;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.admin-header {
  margin-bottom: 24px;
}

.admin-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.admin-subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.admin-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.admin-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px 18px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}

.card-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
}

@media (max-width: 720px) {
  .admin-page { padding: 20px 16px 24px; }
  .admin-title { font-size: 22px; }
  .admin-content { gap: 12px; }
}

@media (max-width: 480px) {
  .admin-page { padding: 16px 12px 20px; }
  .admin-title { font-size: 20px; }
}
</style>

