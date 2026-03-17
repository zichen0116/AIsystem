# 教案生成对话历史持久化 - 设计文档

**日期**: 2026-03-17
**作者**: Claude
**状态**: 待审核

## 1. 概述

### 1.1 背景

当前教案生成功能存在以下问题：
1. 后端已经将对话历史保存到 `chat_history` 表，但前端未对接
2. 前端的对话历史只存在于内存中，页面刷新后丢失
3. 侧边栏使用硬编码的mock数据，无法显示真实的历史会话
4. 用户无法查看和恢复之前的对话

### 1.2 目标

实现对话历史的完整持久化，使用户能够：
- 查看所有历史教案会话列表
- 点击历史会话恢复完整的对话内容
- 在历史会话中继续对话
- 每次打开教案生成页面都显示欢迎界面（新会话状态）

### 1.3 设计原则

- **最小改动** - 只新增API端点，不修改现有逻辑
- **向后兼容** - 不影响现有功能
- **用户隔离** - 严格的权限验证
- **清晰职责** - 每个端点功能单一

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                          │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │ LessonPlanSidebar│         │  LessonPlanPage  │     │
│  │  - 加载历史列表   │         │  - 恢复对话状态   │     │
│  │  - 选择会话      │────────▶│  - 继续对话      │     │
│  └──────────────────┘         └──────────────────┘     │
└─────────────────────────────────────────────────────────┘
                        │
                        │ HTTP/REST API
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  后端 (FastAPI)                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  GET /api/v1/lesson-plan/list                    │  │
│  │  GET /api/v1/lesson-plan/{id}                    │  │
│  │  GET /api/v1/lesson-plan/{id}/messages           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                数据库 (PostgreSQL)                       │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │  lesson_plans    │         │  chat_history    │     │
│  │  - id            │         │  - session_id    │     │
│  │  - session_id ◀──┼─────────┼─ user_id        │     │
│  │  - title         │         │  - role          │     │
│  │  - content       │         │  - content       │     │
│  └──────────────────┘         └──────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

**用户操作流程：**

1. **首次打开页面**
   ```
   用户点击"教案生成" → 显示WelcomePanel（欢迎界面）
   侧边栏自动加载历史列表 → GET /lesson-plan/list
   ```

2. **点击历史会话**
   ```
   用户点击侧边栏某个会话
   ↓
   并行请求：
   - GET /lesson-plan/{id} → 获取教案详情
   - GET /lesson-plan/{id}/messages → 获取对话历史
   ↓
   恢复完整状态（messages + markdown + ids）
   ↓
   显示对话界面，用户可继续对话
   ```

3. **新建会话**
   ```
   用户点击"新建会话" → 清空所有状态 → 显示WelcomePanel
   ```

4. **继续对话**
   ```
   用户在历史会话中发送消息
   ↓
   使用现有 sessionId 继续对话
   ↓
   消息自动保存到 chat_history
   ↓
   lesson_plan.updated_at 自动更新
   ↓
   侧边栏列表刷新，该会话移到顶部
   ```

## 3. API设计

### 3.1 GET /api/v1/lesson-plan/list

获取当前用户的所有教案列表，按更新时间倒序排列。

**请求：**
```http
GET /api/v1/lesson-plan/list?limit=100&offset=0
Authorization: Bearer <token>
```

**查询参数：**
- `limit` (可选): 返回记录数量，默认100，最大200
- `offset` (可选): 跳过的记录数，默认0

**响应：**
```json
{
  "items": [
    {
      "id": 123,
      "session_id": "uuid-string",
      "title": "小学数学-分数加减法",
      "status": "completed",
      "created_at": "2026-03-17T10:30:00Z",
      "updated_at": "2026-03-17T11:45:00Z"
    }
  ],
  "total": 150
}
```

**说明：**
- `session_id` 为 UUID 类型，响应时转换为字符串格式
- 侧边栏显示的时间为 `updated_at`（最后修改时间）

**实现要点：**
- 查询条件：`user_id = current_user.id`
- 排序：`ORDER BY updated_at DESC`
- 返回字段：id, session_id, title, status, created_at, updated_at
- 分页：支持可选的 `limit` 和 `offset` 查询参数（默认 limit=100）
- 性能：确保 `updated_at` 列有索引以支持高效排序

### 3.2 GET /api/v1/lesson-plan/{lesson_plan_id}

获取指定教案的详细信息（不包含对话历史）。

**设计说明：**
此端点只返回教案本身的信息，不包含 messages 字段。对话历史通过独立的 `/messages` 端点获取。这样设计的原因：
- 职责分离：教案详情和对话历史是两个独立的关注点
- 灵活性：允许独立加载大量消息历史，不影响教案详情的加载速度
- 可扩展性：未来可以为消息历史添加分页等功能

**请求：**
```http
GET /api/v1/lesson-plan/123
Authorization: Bearer <token>
```

**响应：**
```json
{
  "id": 123,
  "session_id": "uuid-string",
  "title": "小学数学-分数加减法",
  "content": "# 小学数学-分数加减法 — 教案\n\n## 课程导入...",
  "status": "completed",
  "created_at": "2026-03-17T10:30:00Z",
  "updated_at": "2026-03-17T11:45:00Z"
}
```

**说明：**
- `session_id` 为 UUID 类型，响应时转换为字符串格式

**实现要点：**
- 验证：`lesson_plan.user_id == current_user.id`
- 不存在或无权限：返回 404
- 返回完整的教案信息（不含消息）

### 3.3 GET /api/v1/lesson-plan/{lesson_plan_id}/messages

获取指定教案的对话历史，只返回对话消息，不包含教案内容快照。

**请求：**
```http
GET /api/v1/lesson-plan/123/messages
Authorization: Bearer <token>
```

**响应：**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "帮我生成一份小学三年级数学分数加减法的教案",
      "created_at": "2026-03-17T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "好的，我需要了解一些信息...",
      "created_at": "2026-03-17T10:30:05Z"
    }
  ]
}
```

**说明：**
- 如果该教案没有对话历史，返回空数组 `{"messages": []}`
- 消息按时间正序排列（从早到晚）

**实现要点：**
- 验证：先获取 lesson_plan，确认 user_id 匹配
- 查询：`session_id = lesson_plan.session_id`
- 过滤：排除教案快照（`role='assistant' AND content.startswith('#') AND len(content) > 100`）
- 排序：`ORDER BY created_at ASC`
- 空历史：如果没有消息记录，返回空数组

### 3.4 数据库注意事项

**索引优化：**
- `lesson_plans.updated_at` 需要有索引以支持高效排序
- `lesson_plans.user_id` 已有索引（外键）
- `chat_history.session_id` 已有索引

**外键约束：**
- 当前 `chat_history.session_id` 和 `lesson_plans.session_id` 之间没有外键约束
- 这是设计决策：允许灵活性，但需要在应用层保证数据一致性
- 未来可考虑添加外键约束以防止孤儿记录

### 3.5 安全性

所有端点都需要：
1. **JWT认证** - 通过 `CurrentUser` 依赖注入
2. **用户隔离** - 只能访问自己的数据
3. **404处理** - 资源不存在或无权限时返回404
4. **错误响应** - 统一格式 `{"detail": "错误描述"}`

## 4. 前端设计

### 4.1 LessonPlanSidebar.vue 改动

**删除内容：**
- 删除所有 mock 数据（`mockHistory`）

**新增状态：**
```javascript
const historyList = ref([])  // 真实历史列表
const loading = ref(false)   // 加载状态
const activeId = ref(null)   // 当前选中的会话ID
```

**新增方法：**
```javascript
// 加载历史列表
async function loadHistory() {
  loading.value = true
  try {
    const response = await fetch('/api/v1/lesson-plan/list', {
      headers: { Authorization: `Bearer ${getToken()}` }
    })
    const data = await response.json()
    historyList.value = data.items
  } catch (error) {
    console.error('加载历史失败:', error)
  } finally {
    loading.value = false
  }
}

// 选择会话
function selectConversation(item) {
  activeId.value = item.id
  emit('select-conversation', {
    lessonPlanId: item.id,
    sessionId: item.session_id,
    title: item.title
  })
}

// 时间格式化
function formatTime(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`

  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
```

**生命周期：**
```javascript
onMounted(() => {
  loadHistory()
})
```

**新增事件：**
- `@select-conversation` - 用户点击历史会话时触发

### 4.2 LessonPlanPage.vue 改动

**修改 onMounted：**
```javascript
onMounted(() => {
  // 删除 loadLatest() 调用
  // 只显示欢迎界面
  isFirstMount = false
})
```

**新增方法：**
```javascript
// 处理选择历史会话
async function handleSelectConversation({ lessonPlanId, sessionId, title }) {
  try {
    // 并行请求教案详情和对话历史
    const [planRes, messagesRes] = await Promise.all([
      fetch(`/api/v1/lesson-plan/${lessonPlanId}`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      }),
      fetch(`/api/v1/lesson-plan/${lessonPlanId}/messages`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
    ])

    if (!planRes.ok || !messagesRes.ok) {
      if (planRes.status === 404 || messagesRes.status === 404) {
        showToast('会话不存在')
      } else {
        showToast('加载失败，请稍后重试')
      }
      return
    }

    const plan = await planRes.json()
    const { messages: historyMessages } = await messagesRes.json()

    // 恢复状态
    lessonPlanId.value = plan.id
    sessionId.value = plan.session_id
    currentMarkdown.value = plan.content

    // 恢复对话历史
    messages.value = historyMessages.map(msg => ({
      role: msg.role,
      content: msg.content
    }))

    // 如果有教案内容，添加文档卡片
    if (plan.content && plan.content.trim()) {
      messages.value.push({
        type: 'document-card',
        title: plan.title
      })
    }

    // 切换到对话模式
    mode.value = 'dialog'

  } catch (error) {
    showToast('网络错误，请检查连接')
    console.error(error)
  }
}
```

**修改 startNewConversation：**
```javascript
function startNewConversation() {
  messages.value = []
  currentMarkdown.value = ''
  lessonPlanId.value = null
  sessionId.value = null
  streamingText.value = ''
  streamingMarkdown.value = ''
  mode.value = 'dialog'
  // 不调用 loadLatest()
}
```

**删除内容：**
```javascript
// 删除前端的启发式过滤逻辑（约第356行）
const isLessonPlan = msg.role === 'assistant' &&
                     msg.content.trim().startsWith('#') &&
                     msg.content.length > 100
// 因为后端已经过滤了教案快照
```

**模板改动：**
```vue
<LessonPlanSidebar
  @select-conversation="handleSelectConversation"
  @new-conversation="startNewConversation"
  ...
/>
```

## 5. 实现细节

### 5.1 消息过滤逻辑

**问题：**
`chat_history` 表中既有对话消息，也有完整的教案内容快照。

**解决方案：**
后端在返回消息时过滤掉教案快照：
- 条件：`role='assistant' AND content.startswith('#') AND len(content) > 100`
- 保留所有 user 消息
- 保留短消息和不以 # 开头的 assistant 消息

**示例：**
```python
# 保留
user: "帮我生成小学数学教案"
assistant: "好的，我需要了解..."
assistant: "# 标题"  # 长度<100

# 过滤
assistant: "# 小学数学 — 教案\n\n## 课程导入..."  # 教案快照
```

### 5.2 状态同步

**侧边栏列表刷新时机：**
1. 组件挂载时加载一次
2. 用户完成教案生成后刷新（新会话出现）
3. 用户点击"新建会话"后刷新

**会话选中状态：**
- 点击历史会话时高亮
- 点击"新建会话"时取消高亮
- 刷新页面后不保持选中状态

### 5.3 错误处理

**后端错误码：**
- `401 Unauthorized` - JWT token无效或过期
- `404 Not Found` - 教案不存在或不属于当前用户
- `500 Internal Server Error` - 服务器内部错误

**前端错误处理：**
```javascript
if (response.status === 404) {
  showToast('会话不存在')
} else if (response.status === 401) {
  showToast('登录已过期，请重新登录')
  // 跳转到登录页
} else {
  showToast('加载失败，请稍后重试')
}
```

**降级策略：**
- 侧边栏加载失败 → 显示"加载失败"，但不影响新建会话
- 历史会话加载失败 → 显示toast，保持当前状态
- 消息加载失败 → 只加载教案内容，不显示对话历史

## 6. 边界情况

### 6.1 会话中途刷新页面
- **行为**：状态丢失，回到欢迎界面
- **原因**：符合"每次打开都是新会话"的设计
- **用户操作**：可从侧边栏重新打开该会话

### 6.2 用户在历史会话中发送消息后刷新
- **行为**：消息已保存到数据库，刷新后回到欢迎界面
- **用户操作**：从侧边栏重新打开，可看到刚才的消息

### 6.3 多个标签页同时操作
- **行为**：每个标签页独立状态
- **影响**：侧边栏列表可能不同步
- **接受度**：可接受，竞赛项目不需要实时同步

### 6.4 教案生成失败的会话
- **行为**：仍然保存在列表中（status = "draft"）
- **显示**：标题为"未命名教案"
- **用户操作**：可以打开继续对话

### 6.5 空会话（只有用户消息，无AI回复）
- **行为**：正常显示在列表中
- **内容**：content 为空字符串
- **用户操作**：可以打开继续对话

## 7. 测试策略

### 7.1 后端测试

**单元测试：**
```python
# test_lesson_plan_api.py

def test_list_lesson_plans():
    """测试获取教案列表"""
    # 创建多个教案
    # 验证返回当前用户的所有教案
    # 验证按 updated_at 倒序排列
    # 验证不返回其他用户的教案

def test_get_lesson_plan():
    """测试获取教案详情"""
    # 验证返回正确的教案
    # 验证访问不存在的ID返回404
    # 验证访问其他用户的教案返回404

def test_get_lesson_plan_messages():
    """测试获取对话历史"""
    # 验证返回该会话的所有对话消息
    # 验证正确过滤教案快照
    # 验证消息按时间正序排列
    # 验证访问其他用户的教案返回404

def test_message_filtering():
    """测试消息过滤逻辑"""
    # 场景1：正常对话消息（保留）
    # 场景2：教案快照（过滤）
    # 场景3：短消息（保留）
    # 场景4：澄清问题（保留）
```

### 7.2 前端测试

**组件测试：**
```javascript
// LessonPlanSidebar.spec.js
- 组件挂载时自动加载历史列表
- 点击历史会话触发 select-conversation 事件
- 点击"新建会话"触发 new-conversation 事件
- 加载失败时显示错误提示
- 空列表时显示"暂无历史会话"
- 当前选中的会话高亮显示

// LessonPlanPage.spec.js
- 初始状态显示 WelcomePanel
- 点击历史会话后正确恢复对话和教案内容
- 在历史会话中继续对话，使用正确的 sessionId
- 点击"新建会话"清空所有状态
- 网络请求失败时显示 toast 提示
- 教案内容存在时显示 document-card
```

**集成测试场景：**
```
场景1：完整的新会话流程
1. 打开页面 → 看到欢迎界面
2. 输入消息 → 生成教案
3. 刷新页面 → 回到欢迎界面
4. 点击侧边栏刚才的会话 → 看到完整对话历史

场景2：继续历史会话
1. 打开历史会话
2. 发送新消息
3. 侧边栏该会话的时间更新
4. 刷新页面后重新打开，新消息仍在

场景3：多个会话切换
1. 打开会话A
2. 点击会话B → 内容切换
3. 点击"新建会话" → 回到欢迎界面
4. 再次打开会话A → 内容正确
```

### 7.3 手动测试检查清单

```
□ 首次打开页面显示欢迎界面
□ 侧边栏显示历史会话列表（按更新时间倒序）
□ 点击历史会话正确加载对话和教案
□ 在历史会话中继续对话功能正常
□ 点击"新建会话"清空状态
□ 刷新页面后回到欢迎界面
□ 教案标题和时间显示正确
□ 网络错误时有友好提示
□ 不同用户之间数据隔离
□ 删除前端mock数据后功能正常
□ 教案快照不出现在对话历史中
□ 空会话和失败会话正常显示
```

## 8. 性能优化

### 8.1 后端优化

**数据库索引：**
- `lesson_plans.user_id` - 已有索引
- `lesson_plans.session_id` - 已有唯一索引
- `chat_history.session_id` - 已有索引
- `chat_history.user_id` - 已有索引

**查询优化：**
- 使用索引查询，性能良好
- 消息过滤在应用层完成（数量不大，可接受）

**未来扩展：**
- 如需分页：`GET /lesson-plan/list?page=1&size=20`
- 当前竞赛项目会话数量有限，暂不需要

### 8.2 前端优化

**并行请求：**
```javascript
const [planRes, messagesRes] = await Promise.all([...])
// 减少等待时间
```

**缓存策略：**
- 侧边栏列表缓存在组件状态中
- 切换会话时不重新加载列表
- 只在必要时刷新（新会话创建、手动刷新）

**用户体验：**
- 加载状态提示（loading spinner）
- 即时反馈（点击后立即高亮）
- 平滑的过渡动画

## 9. 安全性

### 9.1 数据隔离
- 所有查询都按 `user_id` 过滤
- 前端传递的 `lesson_plan_id` 在后端验证所有权
- 不同用户之间完全隔离

### 9.2 SQL注入防护
- 使用 SQLAlchemy ORM，自动防护
- 不拼接原始SQL

### 9.3 XSS防护
- Vue自动转义HTML
- 教案内容使用markdown渲染，已有XSS防护

### 9.4 认证和授权
- JWT token验证
- 每个请求都需要有效token
- Token过期后自动跳转登录

## 10. 部署和回滚

### 10.1 数据库迁移
- **无需新建表或修改表结构**
- **无需运行迁移脚本**
- 使用现有的 `lesson_plans` 和 `chat_history` 表

### 10.2 向后兼容
- 新增的API端点不影响现有功能
- 现有的 `/latest` 端点保持不变
- 前端改动不影响其他页面

### 10.3 回滚策略
- 如果出现问题，可以快速回滚代码
- 数据库无改动，回滚无风险
- 用户数据不会丢失

### 10.4 部署步骤
1. 部署后端代码（新增3个API端点）
2. 部署前端代码（修改2个组件）
3. 验证功能正常
4. 如有问题，回滚代码即可

## 11. 总结

### 11.1 设计特点

✅ **最小改动** - 只新增2个API端点，不修改现有逻辑
✅ **清晰职责** - 每个端点功能单一，易于维护
✅ **用户体验** - 每次打开都是新会话，符合用户预期
✅ **数据安全** - 严格的用户隔离和权限验证
✅ **易于测试** - 清晰的测试策略和检查清单
✅ **向后兼容** - 不影响现有功能，可安全部署
✅ **性能良好** - 并行请求，利用数据库索引

### 11.2 实现范围

**后端：**
- 新增 `GET /api/v1/lesson-plan/list`
- 新增 `GET /api/v1/lesson-plan/{id}`
- 新增 `GET /api/v1/lesson-plan/{id}/messages`

**前端：**
- 修改 `LessonPlanSidebar.vue`（删除mock，加载真实数据）
- 修改 `LessonPlanPage.vue`（添加历史会话加载逻辑）

**数据库：**
- 无需改动

### 11.3 预期效果

用户可以：
1. 查看所有历史教案会话（按更新时间排序）
2. 点击历史会话恢复完整对话
3. 在历史会话中继续对话
4. 每次打开页面都是新会话状态
5. 刷新页面后数据不丢失（可从侧边栏恢复）

---

**文档版本**: 1.0
**最后更新**: 2026-03-17
