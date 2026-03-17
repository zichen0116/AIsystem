# 教案对话历史持久化 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现教案生成功能的对话历史持久化，使用户能够查看、恢复和继续之前的对话会话。

**Architecture:** 后端新增3个REST API端点（列表、详情、消息），前端修改侧边栏和主页面组件以加载和显示历史会话。采用并行请求优化加载速度，所有数据按用户隔离。

**Tech Stack:**
- 后端：FastAPI, SQLAlchemy (async), PostgreSQL
- 前端：Vue 3 Composition API, Fetch API
- 认证：JWT (现有)

---

## 文件结构

### 后端新增/修改文件
- **修改**: `backend/app/api/lesson_plan.py` - 新增3个路由端点
- **修改**: `backend/app/schemas/lesson_plan.py` - 新增响应schema
- **新增**: `backend/tests/test_lesson_plan_api.py` - API端点测试

### 前端修改文件
- **修改**: `teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue` - 删除mock，加载真实历史
- **修改**: `teacher-platform/src/views/LessonPlanPage.vue` - 添加历史会话加载逻辑

---

## Task 1: 后端 - 新增响应Schema

**Files:**
- Modify: `backend/app/schemas/lesson_plan.py`

- [ ] **Step 1: 添加列表响应schema**

在文件末尾添加：

```python
class LessonPlanListItem(BaseModel):
    id: int
    session_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    model_config = ConfigDict(from_attributes=True)


class LessonPlanListResponse(BaseModel):
    items: list[LessonPlanListItem]
    total: int
```

- [ ] **Step 2: 添加消息列表响应schema**

继续添加：

```python
class ChatMessageInfo(BaseModel):
    role: str
    content: str
    created_at: str


class LessonPlanMessagesResponse(BaseModel):
    messages: list[ChatMessageInfo]
```

- [ ] **Step 3: 验证schema定义**

检查导入是否完整，确保 `BaseModel`, `ConfigDict` 已导入。

运行语法检查：
```bash
python -m py_compile backend/app/schemas/lesson_plan.py
```

预期：无输出表示语法正确。

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/lesson_plan.py
git commit -m "feat(schema): 添加教案列表和消息响应schema"
```

---

## Task 2: 后端 - 实现GET /lesson-plan/list端点

**Files:**
- Modify: `backend/app/api/lesson_plan.py`

- [ ] **Step 1: 添加必要的导入**

在文件顶部添加：

```python
from sqlalchemy import func
```

确保已导入 `LessonPlanListResponse`, `LessonPlanListItem`。

- [ ] **Step 2: 实现列表端点**

在文件末尾添加新路由：

```python
@router.get("/list")
async def get_lesson_plan_list(
    user: CurrentUser,
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
):
    """获取当前用户的所有教案列表，按更新时间倒序"""
    # 查询总数
    count_result = await db.execute(
        select(func.count(LessonPlan.id)).where(LessonPlan.user_id == user.id)
    )
    total = count_result.scalar()

    # 查询列表
    result = await db.execute(
        select(LessonPlan)
        .where(LessonPlan.user_id == user.id)
        .order_by(LessonPlan.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    plans = result.scalars().all()

    return {
        "items": [
            {
                "id": p.id,
                "session_id": str(p.session_id),
                "title": p.title,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in plans
        ],
        "total": total,
    }
```

- [ ] **Step 3: 测试端点（手动）**

启动后端服务：
```bash
cd backend
python run.py
```

使用curl测试（需要有效token）：
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/lesson-plan/list
```

预期：返回JSON格式的教案列表。

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/lesson_plan.py
git commit -m "feat(api): 添加教案列表查询端点"
```

---

## Task 3: 后端 - 实现GET /lesson-plan/{id}端点

**Files:**
- Modify: `backend/app/api/lesson_plan.py`

- [ ] **Step 1: 实现详情端点**

在 `/list` 端点后添加：

```python
@router.get("/{lesson_plan_id}")
async def get_lesson_plan_detail(
    lesson_plan_id: int,
    user: CurrentUser,
    db: DbSession,
):
    """获取指定教案的详细信息"""
    result = await db.execute(
        select(LessonPlan)
        .where(LessonPlan.id == lesson_plan_id, LessonPlan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(404, "教案不存在")

    return {
        "id": plan.id,
        "session_id": str(plan.session_id),
        "title": plan.title,
        "content": plan.content,
        "status": plan.status,
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
    }
```

- [ ] **Step 2: 测试端点（手动）**

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/lesson-plan/1
```

预期：返回指定教案的详细信息，或404。

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/lesson_plan.py
git commit -m "feat(api): 添加教案详情查询端点"
```

---

## Task 4: 后端 - 实现GET /lesson-plan/{id}/messages端点

**Files:**
- Modify: `backend/app/api/lesson_plan.py`

- [ ] **Step 1: 实现消息查询端点**

在详情端点后添加：

```python
@router.get("/{lesson_plan_id}/messages")
async def get_lesson_plan_messages(
    lesson_plan_id: int,
    user: CurrentUser,
    db: DbSession,
):
    """获取指定教案的对话历史"""
    # 验证教案所有权
    result = await db.execute(
        select(LessonPlan)
        .where(LessonPlan.id == lesson_plan_id, LessonPlan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(404, "教案不存在")

    # 查询对话历史
    messages_result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == plan.session_id)
        .order_by(ChatHistory.created_at.asc())
    )
    all_messages = messages_result.scalars().all()

    # 过滤教案快照
    filtered_messages = []
    for msg in all_messages:
        # 过滤掉教案快照：assistant消息，以#开头，长度>100
        if (
            msg.role == "assistant"
            and msg.content.strip().startswith("#")
            and len(msg.content) > 100
        ):
            continue
        filtered_messages.append(msg)

    return {
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in filtered_messages
        ]
    }
```

- [ ] **Step 2: 测试端点（手动）**

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/lesson-plan/1/messages
```

预期：返回过滤后的对话消息列表。

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/lesson_plan.py
git commit -m "feat(api): 添加教案对话历史查询端点"
```

---

## Task 5: 前端 - 修改LessonPlanSidebar组件

**Files:**
- Modify: `teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue`

- [ ] **Step 1: 删除mock数据**

找到并删除 `mockHistory` 相关代码（约第11-41行）。

- [ ] **Step 2: 添加真实数据状态和事件定义**

在 `<script setup>` 中添加：

```javascript
import { ref, onMounted } from 'vue'
import { resolveApiUrl, getToken } from '../../api/http.js'

const historyList = ref([])
const loading = ref(false)
const activeId = ref(null)

// 定义事件
const emit = defineEmits(['select-conversation', 'new-conversation'])
```

- [ ] **Step 3: 实现加载历史列表方法**

添加方法：

```javascript
async function loadHistory() {
  loading.value = true
  try {
    const response = await fetch(resolveApiUrl('/api/v1/lesson-plan/list'), {
      headers: { Authorization: `Bearer ${getToken()}` }
    })

    if (!response.ok) {
      console.error('加载历史失败:', response.status)
      return
    }

    const data = await response.json()
    historyList.value = data.items
  } catch (error) {
    console.error('加载历史失败:', error)
  } finally {
    loading.value = false
  }
}
```

- [ ] **Step 4: 实现选择会话方法**

添加方法：

```javascript
function selectConversation(item) {
  activeId.value = item.id
  emit('select-conversation', {
    lessonPlanId: item.id,
    sessionId: item.session_id,
    title: item.title
  })
}
```

- [ ] **Step 5: 实现时间格式化方法**

添加方法：

```javascript
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

- [ ] **Step 6: 添加生命周期钩子和暴露刷新方法**

添加：

```javascript
onMounted(() => {
  loadHistory()
})

// 暴露刷新方法供父组件调用
defineExpose({
  loadHistory
})
```

- [ ] **Step 7: 更新模板渲染**

将模板中的 `mockHistory` 替换为 `historyList`，添加加载状态：

```vue
<div class="history-section">
  <div v-if="loading" class="loading-state">加载中...</div>
  <div v-else-if="historyList.length === 0" class="empty-state">
    暂无历史会话
  </div>
  <div v-else class="history-list">
    <div
      v-for="item in historyList"
      :key="item.id"
      :class="['history-item', { active: activeId === item.id }]"
      @click="selectConversation(item)"
    >
      <div class="item-title">{{ item.title }}</div>
      <div class="item-time">{{ formatTime(item.updated_at) }}</div>
    </div>
  </div>
</div>
```

- [ ] **Step 8: 添加select-conversation事件到defineEmits**

确保 `defineEmits` 包含新事件：

```javascript
defineEmits(['toggle', 'new-conversation', 'select-conversation'])
```

- [ ] **Step 9: 测试组件（手动）**

启动前端：
```bash
cd teacher-platform
npm run dev
```

访问教案生成页面，检查：
- 侧边栏显示真实历史列表
- 点击历史会话触发事件

- [ ] **Step 10: Commit**

```bash
git add teacher-platform/src/components/lesson-plan-v2/LessonPlanSidebar.vue
git commit -m "feat(frontend): 侧边栏加载真实历史会话列表"
```

---

## Task 6: 前端 - 修改LessonPlanPage组件

**Files:**
- Modify: `teacher-platform/src/views/LessonPlanPage.vue`

- [ ] **Step 1: 删除onActivated和isFirstMount相关逻辑**

找到 `onMounted` 函数（约第336行），删除 `loadLatest()` 调用和 `isFirstMount` 赋值：

```javascript
onMounted(() => {
  // 删除 loadLatest() 调用
  // 删除 isFirstMount = false
  // 只显示欢迎界面
})
```

找到 `onActivated` 函数（约第379行），完全删除该函数及其内容：

```javascript
// 删除整个 onActivated 函数
// onActivated(() => {
//   ...
// })
```

找到 `isFirstMount` 变量声明（约第69行），删除该变量：

```javascript
// 删除这一行
// let isFirstMount = true
```

在 `<script setup>` 中添加新方法：

```javascript
async function handleSelectConversation({ lessonPlanId, sessionId, title }) {
  try {
    // 并行请求教案详情和对话历史
    const [planRes, messagesRes] = await Promise.all([
      fetch(resolveApiUrl(`/api/v1/lesson-plan/${lessonPlanId}`), {
        headers: { Authorization: `Bearer ${getToken()}` }
      }),
      fetch(resolveApiUrl(`/api/v1/lesson-plan/${lessonPlanId}/messages`), {
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
    showToast('加载历史会话失败')
    console.error(error)
  }
}
```

- [ ] **Step 3: 修改startNewConversation方法（增量修改）**

找到现有的 `startNewConversation` 函数，在现有清理逻辑基础上添加状态清空：

**保留现有的清理逻辑**（如 `abortController?.abort()`, `clearTimeout(saveTimer)`, `destroyEditor()` 等），然后添加：

```javascript
function startNewConversation() {
  // 保留现有的清理逻辑（不要删除）
  // 例如：abortController?.abort()
  // 例如：clearTimeout(saveTimer)
  // 例如：writerRef.value?.destroyEditor()

  // 添加状态清空
  messages.value = []
  currentMarkdown.value = ''
  lessonPlanId.value = null
  sessionId.value = null
  streamingText.value = ''
  streamingMarkdown.value = ''
  restoredFiles.value = []

  // 切换到对话模式
  mode.value = 'dialog'

  // 刷新侧边栏历史列表
  if (sidebarRef.value) {
    sidebarRef.value.loadHistory()
  }
}
```

**注意**：这是增量修改，不要替换整个函数，保留现有的清理代码。

找到约第356行的消息过滤代码并删除：

```javascript
// 删除这段
const isLessonPlan = msg.role === 'assistant' &&
                     msg.content.trim().startsWith('#') &&
                     msg.content.length > 100
```

因为后端已经过滤了教案快照。

- [ ] **Step 5: 添加侧边栏ref和更新模板绑定**

在 `<script setup>` 顶部添加侧边栏ref：

```javascript
const sidebarRef = ref(null)
```

在模板中找到 `<LessonPlanSidebar>`，添加ref和事件绑定：

```vue
<LessonPlanSidebar
  ref="sidebarRef"
  :collapsed="sidebarCollapsed"
  :is-overlay="mode === 'writer'"
  @toggle="sidebarCollapsed = !sidebarCollapsed"
  @new-conversation="startNewConversation"
  @select-conversation="handleSelectConversation"
/>
```

- [ ] **Step 6: 在教案生成完成后刷新侧边栏**

找到教案生成完成的位置（`save_after_stream` 调用后或SSE流结束后），添加刷新调用：

```javascript
// 在教案生成完成后
if (sidebarRef.value) {
  sidebarRef.value.loadHistory()
}
```

- [ ] **Step 7: 测试完整流程（手动）**

1. 打开教案生成页面 → 应显示欢迎界面
2. 侧边栏显示历史列表
3. 点击历史会话 → 恢复对话和教案内容
4. 点击"新建会话" → 回到欢迎界面
5. 刷新页面 → 回到欢迎界面

- [ ] **Step 8: Commit**

```bash
git add teacher-platform/src/views/LessonPlanPage.vue
git commit -m "feat(frontend): 实现历史会话加载和恢复功能"
```

---

## Task 7: 集成测试和验证

**Files:**
- N/A (手动测试)

- [ ] **Step 1: 完整功能测试**

测试场景：
1. 用户登录后进入教案生成页面
2. 验证显示欢迎界面（不自动加载历史）
3. 验证侧边栏显示历史会话列表
4. 点击历史会话，验证对话和教案内容正确恢复
5. 在历史会话中发送新消息，验证功能正常
6. 点击"新建会话"，验证回到欢迎界面
7. 刷新页面，验证回到欢迎界面
8. 重新打开刚才的会话，验证新消息已保存

- [ ] **Step 2: 错误场景测试**

测试场景：
1. 网络断开时点击历史会话 → 显示错误提示
2. 访问不存在的教案ID → 显示"会话不存在"
3. Token过期 → 显示"登录已过期"

- [ ] **Step 3: 性能测试**

验证：
1. 历史列表加载速度（应<1秒）
2. 会话恢复速度（并行请求，应<2秒）
3. 多个会话切换流畅

- [ ] **Step 4: 浏览器兼容性测试**

测试浏览器：
- Chrome
- Firefox
- Edge

- [ ] **Step 5: 记录测试结果**

创建测试报告文档（可选）。

---

## Task 8: 最终提交和文档更新

**Files:**
- Modify: `ISSUES.md` (删除已完成的任务)

- [ ] **Step 1: 验证所有功能正常**

确认：
- 所有API端点工作正常
- 前端功能完整
- 无控制台错误
- 用户体验流畅

- [ ] **Step 2: 更新ISSUES.md**

删除已完成的任务：
```markdown
## 教案生成部分存在以下问题， 请修复

1. ~~先了解一下现阶段的后端教案生成的对话历史记录保存状态~~
2. ~~目前前端的对话历史记录没有与后端对接，无法持久化，只有前端写死的几条记录，你需要完成持久化任务~~
```

- [ ] **Step 3: 最终commit**

```bash
git add ISSUES.md
git commit -m "docs: 更新ISSUES.md，标记对话历史持久化任务已完成"
```

- [ ] **Step 4: 推送分支**

```bash
git push origin feature/lesson-plan-history-persistence
```

- [ ] **Step 5: 准备PR描述**

PR标题：`feat: 实现教案对话历史持久化功能`

PR描述：
```markdown
## 功能描述
实现教案生成功能的对话历史持久化，用户可以查看、恢复和继续之前的对话会话。

## 改动内容

### 后端
- 新增 `GET /api/v1/lesson-plan/list` - 获取教案列表
- 新增 `GET /api/v1/lesson-plan/{id}` - 获取教案详情
- 新增 `GET /api/v1/lesson-plan/{id}/messages` - 获取对话历史
- 新增响应schema：`LessonPlanListResponse`, `LessonPlanMessagesResponse`

### 前端
- 修改 `LessonPlanSidebar.vue` - 删除mock数据，加载真实历史列表
- 修改 `LessonPlanPage.vue` - 实现历史会话加载和恢复功能

## 测试
- [x] API端点功能测试
- [x] 前端功能测试
- [x] 错误场景测试
- [x] 浏览器兼容性测试

## 相关文档
- 设计文档：`docs/superpowers/specs/2026-03-17-lesson-plan-conversation-history-design.md`
- 实现计划：`docs/superpowers/plans/2026-03-17-lesson-plan-history-persistence.md`
```

---

## 完成标准

- [ ] 所有8个任务的步骤全部完成
- [ ] 后端3个API端点正常工作
- [ ] 前端历史会话列表正确显示
- [ ] 点击历史会话能正确恢复对话
- [ ] 每次打开页面显示欢迎界面
- [ ] 错误处理正确（404、401等）
- [ ] 代码已提交到分支
- [ ] 准备好创建PR

---

**预计总时间**: 2-3小时
**关键风险**: 无（最小改动，向后兼容）
**依赖**: 现有的认证系统和数据库表
