# 教案历史记录删除功能 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为教案生成功能添加删除历史记录的能力，用户可从侧边栏删除不需要的教案会话，删除当前会话时自动回到欢迎页。

**Architecture:** 后端新增 DELETE API 端点，通过外键级联删除关联数据。前端在侧边栏添加删除按钮，使用 authFetch 调用 API，删除当前会话时调用 startNewConversation() 清空状态。数据库迁移添加 chat_history 外键约束。

**Tech Stack:**
- 后端：FastAPI, SQLAlchemy (async), Alembic, PostgreSQL
- 前端：Vue 3 Composition API, authFetch
- 测试：pytest (后端), 手动测试 (前端)

---

## 文件结构

### 后端新增/修改文件
- **新增**: `backend/alembic/versions/xxxx_add_cascade_delete_for_chat_history.py` - 数据库迁移脚本
- **修改**: `backend/app/api/lesson_plan.py` - 添加 DELETE 端点
- **新增**: `backend/tests/test_lesson_plan_delete.py` - DELETE 端点测试

### 前端修改文件
- **修改**: `teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue` - 添加删除按钮和逻辑
- **修改**: `teacher-platform/src/views/LessonPlanPage.vue` - 处理删除事件

---

## Task 1: 数据库迁移 - 添加外键约束

**Files:**
- Create: `backend/alembic/versions/xxxx_add_cascade_delete_for_chat_history.py`

- [ ] **Step 1: 生成迁移文件**

```bash
cd backend
alembic revision -m "add cascade delete for chat_history"
```

预期：生成新的迁移文件，文件名类似 `xxxx_add_cascade_delete_for_chat_history.py`

- [ ] **Step 2: 编写迁移脚本**

在生成的迁移文件中添加以下内容：

```python
"""add cascade delete for chat_history

Revision ID: xxxx
Revises: yyyy
Create Date: 2026-03-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxxx'  # 保持自动生成的值
down_revision = 'yyyy'  # 保持自动生成的值
branch_labels = None
depends_on = None


def upgrade():
    # 1. 清理孤儿消息（session_id 在 lesson_plans 中不存在的记录）
    op.execute("""
        DELETE FROM chat_history
        WHERE session_id NOT IN (
            SELECT session_id FROM lesson_plans
        )
    """)

    # 2. 添加外键约束，支持级联删除
    op.create_foreign_key(
        'fk_chat_history_session_id',
        'chat_history',
        'lesson_plans',
        ['session_id'],
        ['session_id'],
        ondelete='CASCADE'
    )


def downgrade():
    # 移除外键约束
    op.drop_constraint(
        'fk_chat_history_session_id',
        'chat_history',
        type_='foreignkey'
    )
```

- [ ] **Step 3: 运行迁移**

```bash
alembic upgrade head
```

预期：迁移成功，输出 "Running upgrade ... -> xxxx, add cascade delete for chat_history"

- [ ] **Step 4: 验证外键约束**

```bash
# 连接数据库查看约束
psql -U <user> -d <database> -c "\d chat_history"
```

预期：在 Foreign-key constraints 中看到 `fk_chat_history_session_id`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): 添加chat_history外键约束支持级联删除"
```

---

## Task 2: 后端 - 实现 DELETE 端点（TDD）

**Files:**
- Create: `backend/tests/test_lesson_plan_delete.py`
- Modify: `backend/app/api/lesson_plan.py`

- [ ] **Step 1: 编写删除成功的测试**

创建 `backend/tests/test_lesson_plan_delete.py`：

```python
"""
教案删除 API 测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson_plan import LessonPlan
from app.models.chat_history import ChatHistory


@pytest.mark.asyncio
async def test_delete_lesson_plan_success(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user_id: int
):
    """测试删除教案成功"""
    # 创建教案
    plan = LessonPlan(user_id=test_user_id, title="测试教案", content="内容", status="draft")
    db_session.add(plan)
    await db_session.flush()

    # 创建关联的对话历史
    msg = ChatHistory(session_id=plan.session_id, user_id=test_user_id, role="user", content="测试")
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(plan)

    plan_id = plan.id
    session_id = plan.session_id

    # 删除教案
    response = await client.delete(f"/api/v1/lesson-plan/{plan_id}", headers=auth_headers)
    assert response.status_code == 204

    # 验证教案已删除
    from sqlalchemy import select
    result = await db_session.execute(select(LessonPlan).where(LessonPlan.id == plan_id))
    assert result.scalar_one_or_none() is None

    # 验证对话历史已级联删除
    result = await db_session.execute(
        select(ChatHistory).where(ChatHistory.session_id == session_id)
    )
    assert result.scalar_one_or_none() is None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd backend
python -m pytest tests/test_lesson_plan_delete.py::test_delete_lesson_plan_success -v
```

预期：FAIL - "404: Not Found" (端点不存在)

- [ ] **Step 3: 实现 DELETE 端点**

在 `backend/app/api/lesson_plan.py` 文件末尾添加：

```python
# --------------- 10. Delete ---------------

@router.delete("/{lesson_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson_plan(
    lesson_plan_id: int,
    user: CurrentUser,
    db: DbSession
):
    """删除指定的教案记录及其关联数据"""
    # 查询教案记录
    result = await db.execute(
        select(LessonPlan).where(
            LessonPlan.id == lesson_plan_id,
            LessonPlan.user_id == user.id
        )
    )
    plan = result.scalar_one_or_none()

    # 验证存在性和所有权
    if not plan:
        raise HTTPException(404, "教案不存在")

    # 删除教案记录（触发级联删除）
    await db.delete(plan)
    await db.commit()

    return None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_lesson_plan_delete.py::test_delete_lesson_plan_success -v
```

预期：PASS

- [ ] **Step 5: 编写 404 测试**

在 `backend/tests/test_lesson_plan_delete.py` 添加：

```python
@pytest.mark.asyncio
async def test_delete_lesson_plan_not_found(client: AsyncClient, auth_headers: dict):
    """测试删除不存在的教案"""
    response = await client.delete("/api/v1/lesson-plan/99999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "教案不存在"
```

- [ ] **Step 6: 运行 404 测试**

```bash
python -m pytest tests/test_lesson_plan_delete.py::test_delete_lesson_plan_not_found -v
```

预期：PASS

- [ ] **Step 7: 编写权限测试**

在 `backend/tests/test_lesson_plan_delete.py` 添加：

```python
@pytest.mark.asyncio
async def test_delete_lesson_plan_unauthorized(
    client: AsyncClient, db_session: AsyncSession, test_user_id: int
):
    """测试删除其他用户的教案"""
    # 用户A创建教案
    plan = LessonPlan(user_id=test_user_id, title="用户A的教案", content="内容", status="draft")
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    # 用户B尝试删除（使用不同的 auth_headers）
    # 注意：需要创建第二个用户的 token，这里假设返回 404（不暴露存在性）
    response = await client.delete(f"/api/v1/lesson-plan/{plan.id}")
    assert response.status_code == 401  # 无 token
```

- [ ] **Step 8: 运行权限测试**

```bash
python -m pytest tests/test_lesson_plan_delete.py::test_delete_lesson_plan_unauthorized -v
```

预期：PASS

- [ ] **Step 9: 运行所有删除测试**

```bash
python -m pytest tests/test_lesson_plan_delete.py -v
```

预期：所有测试 PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/api/lesson_plan.py backend/tests/test_lesson_plan_delete.py
git commit -m "feat(api): 添加教案删除端点及测试"
```

---

## Task 3: 前端 - 侧边栏添加删除按钮

**Files:**
- Modify: `teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue`

- [ ] **Step 1: 更新 HTML 结构**

在 `LessonPlanSidebar.vue` 的模板中，找到历史项的渲染部分（约第13-23行），修改为：

```vue
<div
  v-else
  v-for="item in historyList"
  :key="item.id"
  class="history-item"
  :class="{ active: item.id === activeId }"
  @click="selectHistory(item)"
>
  <div class="item-content">
    <div class="history-title">{{ item.title }}</div>
    <div class="history-time">{{ item.time }}</div>
  </div>
  <button
    class="delete-btn"
    @click.stop="handleDelete(item)"
    title="删除"
  >
    ×
  </button>
</div>
```

- [ ] **Step 2: 添加样式**

在 `<style scoped>` 部分添加：

```css
.history-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.history-item:hover {
  background: #f0f5ff;
}

.history-item.active {
  background: #e8f0fe;
  color: #2563eb;
  font-weight: 500;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.delete-btn {
  opacity: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: #e0e7ff;
  color: #6366f1;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  margin-left: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #c7d2fe;
  color: #4f46e5;
}
```

- [ ] **Step 3: 更新 emit 定义**

在 `<script setup>` 中找到 `defineEmits`（约第42行），修改为：

```javascript
const emit = defineEmits([
  'new-conversation',
  'toggle',
  'select-history',
  'delete-history',
  'toast'
])
```

- [ ] **Step 4: 导入 authFetch**

在 `<script setup>` 顶部的导入语句中（约第34行），修改为：

```javascript
import { resolveApiUrl, getToken, authFetch } from '../../api/http.js'
```

- [ ] **Step 5: 实现删除处理函数**

在 `selectHistory` 函数后添加：

```javascript
// 删除历史记录
async function handleDelete(item) {
  // 原生确认框
  if (!confirm(`确定要删除"${item.title}"吗？此操作不可恢复。`)) {
    return
  }

  try {
    // 调用 DELETE API（authFetch 自动处理 401）
    const response = await authFetch(
      `/api/v1/lesson-plan/${item.id}`,
      { method: 'DELETE' }
    )

    // 错误处理
    if (response.status === 404) {
      emit('toast', '会话不存在（可能已被删除）')
      await loadHistory()
      return
    }

    if (!response.ok) {
      emit('toast', '删除失败，请稍后重试')
      return
    }

    // 成功处理
    emit('delete-history', item.id)
    emit('toast', '删除成功')

    // 刷新列表
    await loadHistory()

  } catch (err) {
    console.error('删除失败:', err)
    emit('toast', '删除失败，请稍后重试')
  }
}
```

- [ ] **Step 6: 手动测试 UI**

启动前端：
```bash
cd teacher-platform
npm run dev
```

测试步骤：
1. 登录并进入教案页面
2. Hover 历史项，验证删除按钮显示
3. 验证删除按钮样式（背景色、hover 效果）
4. 点击历史项，验证不触发删除
5. 点击删除按钮，验证确认框弹出

- [ ] **Step 7: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue
git commit -m "feat(frontend): 侧边栏添加删除按钮和样式"
```

---

## Task 4: 前端 - 主页面处理删除事件

**Files:**
- Modify: `teacher-platform/src/views/LessonPlanPage.vue`

- [ ] **Step 1: 添加删除事件监听**

在 `LessonPlanPage.vue` 的模板中，找到 `<LessonPlanSidebar>` 组件（约第4-9行），添加事件监听：

```vue
<LessonPlanSidebar
  ref="sidebarRef"
  :collapsed="sidebarCollapsed"
  :is-overlay="mode === 'writer'"
  @toggle="sidebarCollapsed = !sidebarCollapsed"
  @new-conversation="startNewConversation"
  @select-history="loadHistorySession"
  @delete-history="handleDeleteHistory"
  @toast="showToast"
/>
```

- [ ] **Step 2: 实现删除处理函数**

在 `<script setup>` 中，找到 `loadHistorySession` 函数后，添加：

```javascript
// ----- Handle Delete History -----
function handleDeleteHistory(deletedId) {
  // 检查是否删除的是当前会话
  if (lessonPlanId.value === deletedId) {
    // 是当前会话，回到欢迎页
    startNewConversation()
  }
  // 否则不需要额外操作，侧边栏已自动刷新
}
```

- [ ] **Step 3: 手动测试删除非当前会话**

测试步骤：
1. 打开会话A
2. 删除会话B
3. 验证仍停留在会话A
4. 验证侧边栏列表已刷新（会话B消失）
5. 验证 toast 提示"删除成功"

- [ ] **Step 4: 手动测试删除当前会话**

测试步骤：
1. 打开会话A
2. 删除会话A
3. 验证自动回到欢迎页
4. 验证 `lessonPlanId` 和 `sessionId` 已清空
5. 验证侧边栏列表已刷新

- [ ] **Step 5: 手动测试错误场景**

测试步骤：
1. 断开网络，尝试删除
2. 验证 toast 提示"删除失败，请稍后重试"
3. 恢复网络，删除已不存在的会话（手动构造）
4. 验证 toast 提示"会话不存在（可能已被删除）"

- [ ] **Step 6: Commit**

```bash
git add teacher-platform/src/views/LessonPlanPage.vue
git commit -m "feat(frontend): 处理删除历史事件，删除当前会话时回到欢迎页"
```

---

## Task 5: 集成测试和文档更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 端到端测试**

完整测试流程：
1. 启动后端和前端
2. 创建新教案
3. 验证侧边栏显示新教案
4. 删除该教案
5. 验证教案从列表消失
6. 验证数据库中教案和对话历史都已删除

- [ ] **Step 2: 验证级联删除**

```bash
# 连接数据库
psql -U <user> -d <database>

# 创建教案并记录 session_id
# 删除教案
# 验证 chat_history 中对应 session_id 的记录已删除
SELECT * FROM chat_history WHERE session_id = '<session_id>';
```

预期：返回 0 行

- [ ] **Step 3: 更新 README**

在 `README.md` 的 API 端点部分添加：

```markdown
- `DELETE /api/v1/lesson-plan/{id}` - 删除教案
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: 更新README添加删除教案API"
```

---

## 完成标准

- [ ] 数据库迁移成功，外键约束已添加
- [ ] 后端 DELETE 端点所有测试通过
- [ ] 前端删除按钮 UI 正确显示和交互
- [ ] 删除非当前会话功能正常
- [ ] 删除当前会话自动回到欢迎页
- [ ] 错误处理正确（404、401、网络错误）
- [ ] 级联删除验证通过
- [ ] 所有代码已提交

---

**预计总时间**: 2-3 小时
**关键风险**: 数据库迁移可能因孤儿数据失败（已通过清理脚本缓解）
**依赖**: 现有的认证系统、数据库连接、前端路由
