# 教案历史记录删除功能设计

**日期**: 2026-03-17
**状态**: 待审查
**作者**: Claude (Opus 4.6)

## 概述

为教案生成功能添加删除历史记录的能力，允许用户从侧边栏删除不需要的教案会话。采用硬删除方案，删除后数据不可恢复。

## 目标

- 用户可以删除不需要的教案历史记录
- 删除操作有明确的确认提示，防止误操作
- 删除当前会话时自动回到欢迎页，避免状态不一致
- 提供清晰的错误处理和用户反馈

## 架构设计

### 整体流程

1. 用户在侧边栏历史记录项上 hover，显示删除按钮
2. 点击删除按钮，弹出原生确认框（`window.confirm`）
3. 用户确认后，前端调用后端 DELETE API
4. 后端验证权限，删除数据库记录（级联删除关联数据）
5. 前端判断：如果删除的是当前会话，调用 `startNewConversation()` 回到欢迎页
6. 前端刷新侧边栏列表，显示成功提示

### 涉及的组件

**前端：**
- `LessonPlanSidebar.vue` - 添加删除按钮和删除逻辑
- `LessonPlanPage.vue` - 接收删除事件，处理当前会话删除

**后端：**
- `backend/app/api/lesson_plan.py` - 新增 DELETE 端点

**数据库：**
- 依赖现有的外键级联删除机制

### 数据流

```
用户点击删除
  ↓
原生确认框
  ↓
DELETE /api/v1/lesson-plan/{id}
  ↓
验证 user_id 匹配
  ↓
手动删除 chat_history (通过 session_id)
  ↓
删除 lesson_plan 记录
  ↓
级联删除 lesson_plan_reference (通过 lesson_plan_id)
  ↓
返回 204 No Content
  ↓
前端检查是否为当前会话
  ↓
是：调用 startNewConversation()
否：仅刷新列表
  ↓
显示成功提示
```

## 后端 API 设计

### 新增端点

**DELETE /api/v1/lesson-plan/{lesson_plan_id}**

删除指定的教案记录及其关联数据。

**请求：**
- Method: `DELETE`
- Path: `/api/v1/lesson-plan/{lesson_plan_id}`
- Headers: `Authorization: Bearer {token}`
- Path 参数: `lesson_plan_id` (int) - 要删除的教案 ID

**响应：**
- `204 No Content` - 删除成功
- `404 Not Found` - `{"detail": "教案不存在"}`
- `401 Unauthorized` - `{"detail": "无效的认证令牌"}` (由认证中间件处理)

**实现逻辑：**

```python
from fastapi import status, HTTPException
from sqlalchemy import select

@router.delete("/{lesson_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson_plan(
    lesson_plan_id: int,
    user: CurrentUser,
    db: DbSession
):
    # 1. 查询教案记录
    result = await db.execute(
        select(LessonPlan).where(
            LessonPlan.id == lesson_plan_id,
            LessonPlan.user_id == user.id
        )
    )
    plan = result.scalar_one_or_none()

    # 2. 验证存在性和所有权
    if not plan:
        raise HTTPException(404, "教案不存在")

    # 3. 手动删除关联的对话历史（无外键约束）
    hist_result = await db.execute(
        select(ChatHistory).where(ChatHistory.session_id == plan.session_id)
    )
    for msg in hist_result.scalars().all():
        await db.delete(msg)

    # 4. 删除教案记录（触发 lesson_plan_reference 的级联删除）
    await db.delete(plan)
    await db.commit()

    # 5. 返回 204
    return None
```

**级联删除依赖：**

需要确认以下外键已配置 `ondelete="CASCADE"`：
- ✅ `lesson_plan_reference.lesson_plan_id` 关联到 `lesson_plans.id` - 已有外键约束，会自动级联删除

**chat_history 手动删除：**
- ⚠️ `chat_history.session_id` 没有外键约束到 `lesson_plans.session_id`
- 解决方案：在删除 `lesson_plan` 前手动删除关联的 `chat_history` 记录
- 原因：添加外键约束需要数据库迁移，超出本功能范围
- 实现：查询所有 `session_id` 匹配的 `chat_history` 记录并逐个删除

## 前端 UI 设计

### LessonPlanSidebar.vue 修改

#### HTML 结构

```vue
<div
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

#### 样式设计

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
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  margin-left: 8px;
}

.history-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #c7d2fe;
  color: #4f46e5;
}
```

**设计要点：**
- 删除按钮默认隐藏（`opacity: 0`）
- hover 历史项时显示删除按钮（`opacity: 1`）
- 删除按钮背景色 `#e0e7ff` 比历史项 hover 背景 `#f0f5ff` 更深
- 使用 `@click.stop` 阻止事件冒泡，避免触发选择历史

#### 交互逻辑

```javascript
// 新增 emit 事件
const emit = defineEmits([
  'new-conversation',
  'toggle',
  'select-history',
  'delete-history',
  'toast'
])

// 删除处理函数
async function handleDelete(item) {
  // 1. 原生确认框
  if (!confirm(`确定要删除"${item.title}"吗？此操作不可恢复。`)) {
    return
  }

  // 2. 调用 DELETE API
  try {
    const response = await fetch(
      resolveApiUrl(`/api/v1/lesson-plan/${item.id}`),
      {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` }
      }
    )

    // 3. 错误处理
    if (response.status === 404) {
      emit('toast', '会话不存在（可能已被删除）')
      await loadHistory() // 刷新列表
      return
    }

    if (!response.ok) {
      emit('toast', '删除失败，请稍后重试')
      return
    }

    // 4. 成功处理
    emit('delete-history', item.id)
    emit('toast', '删除成功')

    // 5. 刷新列表
    await loadHistory()

  } catch (err) {
    console.error('删除失败:', err)
    emit('toast', '删除失败，请稍后重试')
  }
}
```

### LessonPlanPage.vue 修改

#### 监听删除事件

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

#### 处理删除逻辑

```javascript
function handleDeleteHistory(deletedId) {
  // 检查是否删除的是当前会话
  if (lessonPlanId.value === deletedId) {
    // 是当前会话，回到欢迎页
    startNewConversation()
  }
  // 否则不需要额外操作，侧边栏已自动刷新
}
```

## 错误处理

### 错误场景和处理

| 状态码 | 场景 | 处理方式 |
|--------|------|----------|
| 204 | 删除成功 | Toast "删除成功"，刷新列表 |
| 404 | 教案不存在 | Toast "会话不存在（可能已被删除）"，刷新列表 |
| 401 | 认证失败 | 由 `http.js` 自动处理，跳转登录页 |
| 其他 | 网络错误或服务器错误 | Toast "删除失败，请稍后重试" |

### 特殊情况处理

**删除当前会话：**
- 检测：`lessonPlanId.value === deletedId`
- 处理：调用 `startNewConversation()` 清空状态并回到欢迎页
- 原因：避免页面持有已删除会话的 `sessionId`，导致后续操作失败

**网络异常：**
- 捕获 `fetch` 异常
- 显示通用错误提示
- 不刷新列表（保持当前状态）

## 用户体验

### 交互流程

1. **发现删除功能**：用户 hover 历史项时，删除按钮淡入显示
2. **触发删除**：点击删除按钮（× 图标）
3. **确认操作**：弹出确认框，显示教案标题和警告信息
4. **等待反馈**：删除过程中无 loading 状态（操作快速）
5. **查看结果**：Toast 提示删除成功，列表自动刷新

### 确认框文案

```
确定要删除"[教案标题]"吗？此操作不可恢复。
```

**设计考虑：**
- 显示教案标题，让用户明确删除对象
- 强调"不可恢复"，提醒用户谨慎操作
- 使用原生确认框，简单直接

### Toast 提示

- 删除成功：`"删除成功"`
- 会话不存在：`"会话不存在（可能已被删除）"`
- 删除失败：`"删除失败，请稍后重试"`

## 安全性

### 权限验证

- 后端通过 `CurrentUser` 依赖注入获取当前用户
- 查询时同时验证 `lesson_plan_id` 和 `user_id`
- 确保用户只能删除自己的教案

### 防止误操作

- 使用原生确认框，用户必须明确确认
- 确认框显示教案标题，避免删错
- 强调"不可恢复"，提醒用户谨慎

### 数据一致性

- 使用数据库事务确保删除的原子性
- 级联删除确保关联数据一致性
- 删除当前会话时自动清空前端状态

## 测试计划

### 后端测试

**单元测试** (`tests/test_lesson_plan_api.py`)：

```python
async def test_delete_lesson_plan_success():
    """测试删除教案成功"""
    # 创建教案
    # 调用 DELETE /api/v1/lesson-plan/{id}
    # 验证返回 204
    # 验证数据库记录已删除

async def test_delete_lesson_plan_not_found():
    """测试删除不存在的教案"""
    # 调用 DELETE /api/v1/lesson-plan/99999
    # 验证返回 404

async def test_delete_lesson_plan_unauthorized():
    """测试删除其他用户的教案"""
    # 用户A创建教案
    # 用户B尝试删除
    # 验证返回 404（不暴露存在性）

async def test_delete_lesson_plan_cascade():
    """测试级联删除"""
    # 创建教案、对话历史、参考文件
    # 删除教案
    # 验证关联数据也被删除
```

### 前端测试

**手动测试场景：**

1. **基本删除流程**
   - hover 历史项，验证删除按钮显示
   - 点击删除，验证确认框弹出
   - 取消确认，验证无变化
   - 确认删除，验证成功提示和列表刷新

2. **删除当前会话**
   - 打开一个历史会话
   - 删除该会话
   - 验证自动回到欢迎页
   - 验证状态已清空

3. **删除非当前会话**
   - 打开会话A
   - 删除会话B
   - 验证仍停留在会话A
   - 验证列表已刷新

4. **错误处理**
   - 删除不存在的会话（手动构造）
   - 验证 404 提示
   - 网络断开时删除
   - 验证错误提示

5. **UI 交互**
   - 验证删除按钮 hover 效果
   - 验证删除按钮不触发选择历史
   - 验证活动项的删除按钮样式

## 实现顺序

1. **后端 API** - 实现 DELETE 端点和测试
2. **前端 UI** - 添加删除按钮和样式
3. **前端逻辑** - 实现删除交互和错误处理
4. **集成测试** - 端到端测试完整流程
5. **文档更新** - 更新 README 和 API 文档

## 未来改进

以下功能不在本次实现范围内，但可作为未来改进方向：

- **软删除**：添加 `deleted_at` 字段，支持恢复
- **批量删除**：支持选择多个历史记录批量删除
- **删除确认优化**：使用自定义模态框替代原生确认框
- **删除动画**：添加删除时的淡出动画
- **撤销删除**：删除后短时间内支持撤销

## 风险和限制

### 风险

1. **数据永久丢失**：硬删除无法恢复，误操作风险高
   - 缓解：使用确认框，强调"不可恢复"

2. **级联删除失败**：如果外键约束未正确配置，可能导致孤立数据
   - 缓解：实现前验证数据库约束，添加测试覆盖

3. **并发删除**：多个客户端同时删除同一教案
   - 缓解：后端返回 404，前端刷新列表

### 限制

1. **不支持恢复**：删除后数据永久丢失
2. **不支持批量删除**：每次只能删除一个
3. **原生确认框**：样式无法自定义，体验一般

## 总结

本设计实现了教案历史记录的删除功能，采用硬删除方案，通过原生确认框防止误操作。前端提供清晰的 UI 反馈和错误处理，后端确保权限验证和数据一致性。实现简单直接，满足用户基本需求。
