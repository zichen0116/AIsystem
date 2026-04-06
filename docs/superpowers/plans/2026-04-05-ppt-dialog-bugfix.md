# PPT 对话工作台 Bug 修复与体验优化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 PPT 教学意图澄清工作台的 6 个 bug（按钮禁用、要点丢失、引导语、导航回退、历史查看、图片动效），并新增历史项目入口与回顾功能。

**Architecture:** 前端修改集中在 PptDialog.vue（问题 1-4）、PptPreview.vue（问题 6）、新增 PptHistory.vue（问题 5/历史项目）。后端修改集中在 banana_routes.py（confirmed/pending 确定性合并 + 引导语 + 项目列表增强）。

**Tech Stack:** Vue 3 Composition API, Pinia, FastAPI, Python asyncio, CSS animations

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/generators/ppt/banana_routes.py` | 修改 | chat() confirmed/pending 确定性合并、system prompt 引导语、list_projects 增强（返回页数+封面） |
| `backend/app/generators/ppt/banana_schemas.py` | 修改 | 新增 PPTProjectListItem 响应模型（含 page_count, cover_image_url） |
| `teacher-platform/src/views/ppt/PptDialog.vue` | 修改 | 按钮三态、confirmed 累积合并、pending 与合并后 confirmed 校正、onMounted 恢复、返回按钮 |
| `teacher-platform/src/views/ppt/PptPreview.vue` | 修改 | 图片生成流光卡片、弹跳等待动画、揭露过渡 |
| `teacher-platform/src/views/ppt/PptHome.vue` | 修改 | 添加"历史项目"入口按钮 |
| `teacher-platform/src/views/ppt/PptHistory.vue` | 新增 | 历史项目列表页（深色背景、大卡片、封面缩略图、状态标签） |
| `teacher-platform/src/views/ppt/PptIndex.vue` | 修改 | 注册 history phase 与组件映射 |
| `teacher-platform/src/stores/ppt.js` | 修改 | 新增 restoreProject action（从历史项目恢复工作流状态） |
| `teacher-platform/src/api/ppt.js` | 修改 | 新增 listProjectsWithSummary API 函数（如需） |

---

### Task 1: 后端 — chat() 中 confirmed/pending 确定性合并 + AI 引导语

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py:1897-1968`

- [ ] **Step 1: 在 system prompt 末尾追加引导语规则**

在 `banana_routes.py` 中找到 intent_system_prompt 的末尾（第 1961 行）：
```python
- 当 ready_for_confirmation=true 时，intent_summary 字段必须完整填写"""
```

替换为：
```python
- 当 ready_for_confirmation=true 时，intent_summary 字段必须完整填写
- 当 ready_for_confirmation=true 时，你的 reply 最后一句必须是：请点击右侧按钮「确认意图，进入大纲页」，进一步生成大纲。"""
```

- [ ] **Step 2: 在 system prompt 之后注入历史已确认要点**

在 intent_system_prompt 赋值结束（第 1961 行 `"""`）之后、`response = await dashscope.chat_with_history(` 之前，添加：

```python
        # 注入历史已确认要点到 system prompt
        hist_confirmed = set()
        for s in sessions:
            if s.role == 'assistant' and s.session_metadata:
                old_state = s.session_metadata.get('intent_state', {})
                for item in old_state.get('confirmed', []):
                    if isinstance(item, str) and item.strip():
                        hist_confirmed.add(item.strip())
        if hist_confirmed:
            intent_system_prompt += f"\n\n之前轮次已确认的要点：{', '.join(hist_confirmed)}。请在你的回复中保留这些已确认要点，不要丢弃。"
```

- [ ] **Step 3: 在 _parse_intent_state 之后做 confirmed/pending 确定性合并**

在第 1968 行 `ai_content, intent_state = _parse_intent_state(raw_content)` 之后，`except` 块之前，添加：

```python
        ai_content, intent_state = _parse_intent_state(raw_content)

        # ---- 确定性合并：历史已确认要点 ∪ 当前轮已确认要点 ----
        previous_confirmed = set()
        for s in sessions:
            if s.role == 'assistant' and s.session_metadata:
                old_state = s.session_metadata.get('intent_state', {})
                for item in old_state.get('confirmed', []):
                    if isinstance(item, str) and item.strip():
                        previous_confirmed.add(item.strip())
        current_confirmed = set(
            item for item in intent_state.get('confirmed', [])
            if isinstance(item, str) and item.strip()
        )
        merged_confirmed = previous_confirmed | current_confirmed
        intent_state['confirmed'] = list(merged_confirmed)

        # ---- pending 与合并后 confirmed 校正：从 pending 中移除已被 confirmed 覆盖的维度 ----
        merged_text = "\n".join(merged_confirmed)
        dimension_covered = {
            "受众基础层次": any(k in merged_text for k in ["受众", "年级", "学生", "基础"]),
            "核心教学目标": any(k in merged_text for k in ["目标", "学习目标", "达成", "掌握"]),
            "课时与目标页数": any(k in merged_text for k in ["课时", "时长", "页数", "时间", "页"]),
            "互动与约束条件": any(k in merged_text for k in ["互动", "约束", "活动", "限制", "形式"]),
        }
        corrected_pending = [
            p for p in intent_state.get('pending', [])
            if not dimension_covered.get(p, False)
        ]
        intent_state['pending'] = corrected_pending

        # 如果 pending 被清空且有足够 confirmed，标记可确认
        if not corrected_pending and len(merged_confirmed) >= 4:
            intent_state['ready_for_confirmation'] = True
```

- [ ] **Step 4: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add backend/app/generators/ppt/banana_routes.py
git commit -m "fix(ppt): deterministic confirmed/pending merge + AI guidance prompt"
```

---

### Task 2: 前端 — PptDialog 按钮三态 + confirmed 累积 + pending 校正

**Files:**
- Modify: `teacher-platform/src/views/ppt/PptDialog.vue:86-98,113-145,206-243,598-603`

- [ ] **Step 1: 修改 applyIntentState 做累积合并**

在 `PptDialog.vue` 第 116-118 行，将：
```javascript
  if (Array.isArray(intentState.confirmed)) {
    state.confirmed = intentState.confirmed.filter(item => typeof item === 'string' && item.trim())
  }
```

替换为：
```javascript
  if (Array.isArray(intentState.confirmed)) {
    const newConfirmed = intentState.confirmed.filter(item => typeof item === 'string' && item.trim())
    const existingSet = new Set(state.confirmed)
    newConfirmed.forEach(item => existingSet.add(item))
    state.confirmed = [...existingSet]
  }
```

- [ ] **Step 2: 新增按钮计算属性（直接绑定 pending.length）**

在 `generateBlockReason` 计算属性（第 90 行）之后，添加：

```javascript
const confirmBtnDisabled = computed(() => {
  if (isGenerating.value) return true
  if (state.intentConfirmed) return false
  // 直接绑定 pending.length，不仅依赖 readyForConfirmation
  if (state.pending.length > 0) return true
  if (!state.readyForConfirmation) return true
  return false
})

const confirmBtnText = computed(() => {
  if (isGenerating.value) return '确认中...'
  if (state.intentConfirmed) return '返回大纲页 →'
  return '确认意图，进入大纲页'
})
```

- [ ] **Step 3: 修改 confirmIntentAndGo 支持已确认状态直接跳转**

将第 206-243 行的 `confirmIntentAndGo` 函数替换为：

```javascript
async function confirmIntentAndGo() {
  if (!pptStore.projectId) {
    showToast('项目未创建，请返回首页重新开始。')
    return
  }

  // 已确认过意图，直接跳转大纲页
  if (state.intentConfirmed) {
    pptStore.setPhase('outline')
    return
  }

  isGenerating.value = true

  try {
    await pptStore.confirmIntent(pptStore.projectId)
    state.intentConfirmed = true
    state.readyForConfirmation = true
    state.pending = []
    state.confidence = Math.max(state.confidence, 95)
    pushSnapshot('系统：意图已确认，准备进入大纲页。')

    messages.value.push({
      role: 'ai',
      content: '太棒了！教学意图已确认，我们准备进入大纲页，系统会根据你确认的意图生成大纲。',
      time: nowText()
    })

    setTimeout(() => {
      pptStore.setPhase('outline')
    }, 800)
  } catch (error) {
    console.error('确认意图失败:', error)
    messages.value.push({
      role: 'ai',
      content: '确认意图时出现错误，请稍后重试。',
      time: nowText()
    })
  }

  isGenerating.value = false
  await nextTick()
  scrollToBottom()
}
```

- [ ] **Step 4: 更新模板中按钮的绑定**

将第 598 行的按钮：
```html
            <button class="btn secondary" :disabled="state.intentConfirmed || isGenerating" @click="confirmIntentAndGo">
              {{ isGenerating ? '确认中...' : '确认意图，进入大纲页' }}
            </button>
```

替换为：
```html
            <button class="btn secondary" :class="{ 'btn-confirmed': state.intentConfirmed }" :disabled="confirmBtnDisabled" @click="confirmIntentAndGo">
              {{ confirmBtnText }}
            </button>
```

- [ ] **Step 5: 添加已确认按钮样式**

在 `<style scoped>` 中 `.btn.secondary:hover:not(:disabled)` 规则（约第 1323 行）之后添加：

```css
.btn.btn-confirmed {
  border-color: #059669;
  color: #065f46;
  background: linear-gradient(145deg, #ecfdf5 0%, #d1fae5 100%);
}

.btn.btn-confirmed:hover:not(:disabled) {
  border-color: #047857;
  box-shadow: 0 8px 18px rgba(5, 150, 105, 0.2);
}
```

- [ ] **Step 6: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add teacher-platform/src/views/ppt/PptDialog.vue
git commit -m "fix(ppt): button three-state logic with pending check + cumulative confirmed"
```

---

### Task 3: 前端 — PptDialog 状态恢复与导航回退

**Files:**
- Modify: `teacher-platform/src/views/ppt/PptDialog.vue:298-336,362-384`

- [ ] **Step 1: 修改 onMounted 状态恢复逻辑**

将第 298-336 行的 `onMounted` 回调替换为：

```javascript
onMounted(async () => {
  if (!pptStore.projectId) return

  try {
    // 优先从 confirmedIntent 恢复
    if (pptStore.confirmedIntent && Object.keys(pptStore.confirmedIntent).length > 0) {
      state.intentSummary = pptStore.confirmedIntent
      state.intentConfirmed = true
      state.readyForConfirmation = true
      state.confidence = Math.max(state.confidence, 95)
      state.pending = []
    }

    const sessions = await getSessions(pptStore.projectId)
    if (!Array.isArray(sessions) || sessions.length === 0) return

    messages.value = sessions.map((session) => ({
      role: session.role === 'assistant' ? 'ai' : 'user',
      content: session.content,
      time: formatTime(session.created_at)
    }))

    state.round = sessions.reduce((maxRound, session) => Math.max(maxRound, Number(session.round) || 0), 0)

    // 从所有历史 sessions 累积恢复 confirmed
    if (!pptStore.confirmedIntent || Object.keys(pptStore.confirmedIntent).length === 0) {
      const allConfirmed = new Set()
      let latestIntentState = null

      for (const session of sessions) {
        if (session.role === 'assistant' && session.metadata?.intent_state) {
          latestIntentState = session.metadata.intent_state
          const confirmed = latestIntentState.confirmed || []
          confirmed.forEach(item => {
            if (typeof item === 'string' && item.trim()) allConfirmed.add(item)
          })
        }
      }

      if (latestIntentState) {
        applyIntentState(latestIntentState, false)
        state.confirmed = [...allConfirmed]
      }
    }

    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('加载对话历史失败:', error)
  }
})
```

- [ ] **Step 2: 在 topbar 添加返回首页按钮**

将第 363-369 行：
```html
    <header class="topbar">
      <div class="identity">
        <h1>教学意图澄清工作台</h1>
        <p>将零散想法整理成可执行教学意图</p>
      </div>
```

替换为：
```html
    <header class="topbar">
      <div class="identity">
        <button class="back-btn" @click="goBack" title="返回首页">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回
        </button>
        <h1>教学意图澄清工作台</h1>
        <p>将零散想法整理成可执行教学意图</p>
      </div>
```

- [ ] **Step 3: 添加返回按钮样式**

在 `.identity p` 规则（约第 644 行）之后添加：

```css
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #d5dfed;
  border-radius: 8px;
  background: #f8fbff;
  color: #3f5f82;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  margin-bottom: 4px;
}

.back-btn:hover {
  border-color: #3b82f6;
  background: #eef5ff;
  color: #1e3a8a;
  transform: translateX(-2px);
}
```

- [ ] **Step 4: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add teacher-platform/src/views/ppt/PptDialog.vue
git commit -m "fix(ppt): restore intent state on remount + add back navigation"
```

---

### Task 4: 前端 — PptPreview 图片生成流光卡片与弹跳等待动画

**Files:**
- Modify: `teacher-platform/src/views/ppt/PptPreview.vue:1066-1078,1137-1143,1155-1169,1974-2010`

- [ ] **Step 1: 修改缩略图生成中的占位显示**

将第 1066-1078 行：
```html
            <div class="thumbnail-image">
              <template v-if="page.thumbnail">
                <img :src="page.thumbnail" :alt="page.title">
              </template>
              <template v-else>
                <div class="thumbnail-placeholder">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                  </svg>
                </div>
              </template>
```

替换为：
```html
            <div class="thumbnail-image">
              <template v-if="page.thumbnail">
                <img
                  :src="page.thumbnail"
                  :alt="page.title"
                  class="image-reveal revealed"
                >
              </template>
              <template v-else-if="page.status === 'generating'">
                <div class="thumbnail-generating">
                  <div class="shimmer-bg"></div>
                  <div class="thumb-spin-loader"></div>
                </div>
              </template>
              <template v-else>
                <div class="thumbnail-placeholder">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                  </svg>
                </div>
              </template>
```

- [ ] **Step 2: 修改主预览区生成中的占位显示**

将第 1155-1169 行：
```html
              <template v-else>
                <div class="slide-placeholder">
                  <div class="placeholder-icon">🍌</div>
                  <p class="placeholder-text">
                    {{ currentPage?.status === 'generating' ? '生成中...' : '尚未生成图片' }}
                  </p>
                  <button
                    v-if="currentPage?.status !== 'generating'"
                    class="generate-page-btn"
                    @click="handleGeneratePage(currentPageIndex)"
                  >
                    生成此页
                  </button>
                </div>
              </template>
```

替换为：
```html
              <template v-else>
                <div v-if="currentPage?.status === 'generating'" class="slide-generating">
                  <div class="shimmer-bg"></div>
                  <div class="generating-content">
                    <div class="bouncing-indicator">
                      <span class="bounce-dot">&#9998;</span>
                      <span class="bounce-dot">&#10024;</span>
                      <span class="bounce-dot">&#9998;</span>
                    </div>
                    <p class="generating-text">正在创作中...</p>
                    <div class="generating-spin-wrapper">
                      <div class="spin-loader"></div>
                    </div>
                  </div>
                </div>
                <div v-else class="slide-placeholder">
                  <div class="placeholder-icon">🍌</div>
                  <p class="placeholder-text">尚未生成图片</p>
                  <button
                    class="generate-page-btn"
                    @click="handleGeneratePage(currentPageIndex)"
                  >
                    生成此页
                  </button>
                </div>
              </template>
```

- [ ] **Step 3: 给主预览图片添加揭露动画 class**

将第 1137-1143 行：
```html
                <img
                  ref="previewImageRef"
                  :src="currentPage.imageUrl"
                  :alt="currentPage.title"
                  class="slide-image"
                  draggable="false"
                >
```

替换为：
```html
                <img
                  ref="previewImageRef"
                  :src="currentPage.imageUrl"
                  :alt="currentPage.title"
                  class="slide-image image-reveal revealed"
                  draggable="false"
                >
```

- [ ] **Step 4: 添加动画 CSS 样式**

找到 `.slide-placeholder {` 开始（第 1974 行），到 `.generate-page-btn:hover { background: #2563eb; }` 结束（约第 2010 行），将这整段替换为：

```css
/* ---- 图片生成动画 ---- */
.slide-placeholder {
  width: 100%;
  height: 100%;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  gap: 12px;
}

.placeholder-icon {
  font-size: 64px;
}

.placeholder-text {
  color: #64748b;
  font-size: 14px;
}

.generate-page-btn {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.generate-page-btn:hover {
  background: #2563eb;
}

.shimmer-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, #f0f4ff 0%, #f0f4ff 40%, #e0ebff 50%, #f0f4ff 60%, #f0f4ff 100%);
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.slide-generating {
  width: 100%;
  height: 100%;
  min-height: 300px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 12px;
}

.generating-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.bouncing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bounce-dot {
  display: inline-block;
  font-size: 24px;
  animation: bounce 1.2s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.3));
}

.bounce-dot:nth-child(2) {
  animation-delay: 0.15s;
  font-size: 28px;
}

.bounce-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-14px); }
}

.generating-text {
  color: #475569;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  animation: textPulse 2s ease-in-out infinite;
}

@keyframes textPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.generating-spin-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spin-loader {
  width: 28px;
  height: 28px;
  border: 3px solid #e0ebff;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.thumbnail-generating {
  width: 100%;
  height: 100%;
  min-height: 80px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 6px;
}

.thumb-spin-loader {
  position: relative;
  z-index: 1;
  width: 20px;
  height: 20px;
  border: 2.5px solid #dbeafe;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.image-reveal {
  opacity: 0;
  transform: scale(0.95);
  filter: blur(8px);
  transition: all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.image-reveal.revealed {
  opacity: 1;
  transform: scale(1);
  filter: blur(0);
}
```

- [ ] **Step 5: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add teacher-platform/src/views/ppt/PptPreview.vue
git commit -m "feat(ppt): add shimmer, bounce, spin animations for image generation"
```

---

### Task 5: 后端 — list_projects 增强（返回页数 + 封面图）

**Files:**
- Modify: `backend/app/generators/ppt/banana_schemas.py:114-132`
- Modify: `backend/app/generators/ppt/banana_routes.py:431-442`

- [ ] **Step 1: 新增 PPTProjectListItem 响应模型**

在 `banana_schemas.py` 的 `PPTProjectResponse` 类（第 132 行 `model_config` 之后），添加：

```python
class PPTProjectListItem(BaseModel):
    """PPT项目列表项（含摘要信息）"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    creation_type: str
    status: str
    template_style: Optional[str]
    created_at: datetime
    updated_at: datetime
    page_count: int = 0
    cover_image_url: Optional[str] = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 修改 list_projects 端点返回摘要信息**

将 `banana_routes.py` 第 431-442 行的 `list_projects` 函数替换为：

```python
@router.get("/projects", response_model=list[PPTProjectListItem])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """列出当前用户的所有PPT项目（含页数和封面图）"""
    result = await db.execute(
        select(PPTProject)
        .where(PPTProject.user_id == current_user.id)
        .order_by(PPTProject.updated_at.desc())
    )
    projects = result.scalars().all()

    items = []
    for project in projects:
        # 查询页数和第一张有图的页面
        page_result = await db.execute(
            select(PPTPage)
            .where(PPTPage.project_id == project.id)
            .order_by(PPTPage.page_number)
        )
        pages = page_result.scalars().all()
        cover_url = None
        for p in pages:
            if p.image_url:
                cover_url = p.image_url
                break

        items.append(PPTProjectListItem(
            id=project.id,
            user_id=project.user_id,
            title=project.title or project.outline_text or "未命名项目",
            description=project.description,
            creation_type=project.creation_type or "dialog",
            status=project.status or "DRAFT",
            template_style=project.template_style,
            created_at=project.created_at,
            updated_at=project.updated_at,
            page_count=len(pages),
            cover_image_url=cover_url,
        ))
    return items
```

注意：在文件顶部确认 `PPTProjectListItem` 已 import。在 `banana_routes.py` 的 import 区域（通常在文件头部）添加：

```python
from app.generators.ppt.banana_schemas import PPTProjectCreate, PPTProjectResponse, PPTProjectListItem, ...
```

（如果使用通配符 import 则无需修改。检查文件顶部实际 import 方式。）

- [ ] **Step 3: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add backend/app/generators/ppt/banana_schemas.py backend/app/generators/ppt/banana_routes.py
git commit -m "feat(ppt): enhance list_projects with page_count and cover_image_url"
```

---

### Task 6: 前端 — 历史项目页面（PptHistory.vue）

**Files:**
- Create: `teacher-platform/src/views/ppt/PptHistory.vue`

- [ ] **Step 1: 创建 PptHistory.vue**

参考 banana-slides 的 History.tsx 风格，创建深色背景的历史项目列表页。

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { listProjects, deleteProject, batchDeleteProjects } from '@/api/ppt'

const pptStore = usePptStore()

const projects = ref([])
const isLoading = ref(false)
const errorMsg = ref('')
const selectedIds = ref(new Set())
const isDeleting = ref(false)

const isBatchMode = computed(() => selectedIds.value.size > 0)

onMounted(async () => {
  await loadProjects()
})

async function loadProjects() {
  isLoading.value = true
  errorMsg.value = ''
  try {
    const data = await listProjects()
    projects.value = Array.isArray(data) ? data : (data?.projects || [])
  } catch (e) {
    errorMsg.value = '加载历史项目失败，请重试'
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

function getStatusText(project) {
  const s = project.status
  if (s === 'COMPLETED' || s === 'EXPORTED') return '已完成'
  if (s === 'INTENT_CONFIRMED') return '待生成大纲'
  if (project.page_count > 0 && project.cover_image_url) return '已完成'
  if (project.page_count > 0) return '待生成图片'
  return '进行中'
}

function getStatusClass(project) {
  const text = getStatusText(project)
  if (text === '已完成') return 'status-completed'
  if (text === '待生成图片') return 'status-pending-images'
  return 'status-in-progress'
}

function getProjectPhase(project) {
  if (project.cover_image_url) return 'preview'
  if (project.page_count > 0) return 'outline'
  if (project.creation_type === 'dialog') return 'dialog'
  return 'outline'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

async function openProject(project) {
  if (isBatchMode.value) {
    toggleSelect(project.id)
    return
  }
  try {
    await pptStore.fetchProject(project.id)
    await pptStore.fetchPages(project.id)

    // 恢复意图
    if (project.creation_type === 'dialog') {
      try {
        await pptStore.fetchIntent(project.id)
      } catch (e) {
        // 意图可能不存在
      }
    }

    const phase = getProjectPhase(project)
    pptStore.setPhase(phase)
  } catch (e) {
    console.error('打开项目失败:', e)
  }
}

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

function toggleSelectAll() {
  if (selectedIds.value.size === projects.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(projects.value.map(p => p.id))
  }
}

async function handleDelete(e, project) {
  e.stopPropagation()
  if (!confirm(`确定要删除项目「${project.title}」吗？此操作不可恢复。`)) return
  try {
    await deleteProject(project.id)
    await loadProjects()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

async function handleBatchDelete() {
  const count = selectedIds.value.size
  if (!confirm(`确定要删除选中的 ${count} 个项目吗？此操作不可恢复。`)) return
  isDeleting.value = true
  try {
    await batchDeleteProjects([...selectedIds.value])
    selectedIds.value = new Set()
    await loadProjects()
  } catch (e) {
    console.error('批量删除失败:', e)
  } finally {
    isDeleting.value = false
  }
}

function goHome() {
  pptStore.setPhase('home')
}
</script>

<template>
  <div class="ppt-history">
    <!-- Header -->
    <header class="history-header">
      <div class="header-left">
        <button class="back-btn" @click="goHome">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回首页
        </button>
        <h1>历史项目</h1>
        <p class="subtitle">查看和管理你的所有项目</p>
      </div>
    </header>

    <!-- Batch Actions -->
    <div class="batch-bar">
      <label class="select-all" @click="toggleSelectAll">
        <span class="checkbox-icon" :class="{ checked: selectedIds.size === projects.length && projects.length > 0 }">
          <svg v-if="selectedIds.size === projects.length && projects.length > 0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </span>
        全选
      </label>
      <div v-if="isBatchMode" class="batch-actions">
        <span class="batch-count">已选择 {{ selectedIds.size }} 项</span>
        <button class="batch-cancel" @click="selectedIds = new Set()">取消选择</button>
        <button class="batch-delete-btn" :disabled="isDeleting" @click="handleBatchDelete">
          {{ isDeleting ? '删除中...' : '批量删除' }}
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="history-content">
      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spin-loader"></div>
        <p>加载中...</p>
      </div>

      <!-- Error -->
      <div v-else-if="errorMsg" class="error-state">
        <p>{{ errorMsg }}</p>
        <button @click="loadProjects">重试</button>
      </div>

      <!-- Empty -->
      <div v-else-if="projects.length === 0" class="empty-state">
        <div class="empty-icon">📊</div>
        <h3>暂无历史项目</h3>
        <p>创建你的第一个项目开始使用吧</p>
        <button class="create-btn" @click="goHome">创建项目</button>
      </div>

      <!-- Project List -->
      <div v-else class="project-list">
        <div
          v-for="project in projects"
          :key="project.id"
          class="project-card"
          :class="{ 'card-selected': selectedIds.has(project.id) }"
          @click="openProject(project)"
        >
          <!-- Checkbox -->
          <div class="card-checkbox" @click.stop="toggleSelect(project.id)">
            <span class="checkbox-icon" :class="{ checked: selectedIds.has(project.id) }">
              <svg v-if="selectedIds.has(project.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="12" height="12">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </span>
          </div>

          <!-- Info -->
          <div class="card-info">
            <h3 class="card-title">{{ project.title || '未命名项目' }}</h3>
            <div class="card-meta">
              <span class="meta-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <line x1="3" y1="9" x2="21" y2="9"/>
                </svg>
                {{ project.page_count || 0 }} 页
              </span>
              <span class="meta-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                {{ formatDate(project.updated_at) }}
              </span>
            </div>
            <span class="status-badge" :class="getStatusClass(project)">
              {{ getStatusText(project) }}
            </span>
          </div>

          <!-- Cover Image -->
          <div class="card-cover">
            <template v-if="project.cover_image_url">
              <img :src="project.cover_image_url" :alt="project.title" loading="lazy">
            </template>
            <template v-else>
              <div class="cover-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <polyline points="21 15 16 10 5 21"/>
                </svg>
              </div>
            </template>
          </div>

          <!-- Actions -->
          <div class="card-actions">
            <button class="delete-btn" title="删除" @click="handleDelete($event, project)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
            <div class="enter-arrow">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ppt-history {
  min-height: 100%;
  background: #111827;
  color: #e5e7eb;
  padding: 24px 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.history-header {
  margin-bottom: 20px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 800;
  color: #f9fafb;
  margin: 12px 0 4px;
}

.subtitle {
  font-size: 14px;
  color: #9ca3af;
  margin: 0;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #374151;
  border-radius: 8px;
  background: #1f2937;
  color: #d1d5db;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.back-btn:hover {
  border-color: #6b7280;
  background: #374151;
  color: #f9fafb;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0 16px;
  border-bottom: 1px solid #1f2937;
  margin-bottom: 16px;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #9ca3af;
  cursor: pointer;
  user-select: none;
}

.checkbox-icon {
  width: 18px;
  height: 18px;
  border: 2px solid #4b5563;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.checkbox-icon.checked {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.batch-count {
  font-size: 13px;
  color: #60a5fa;
}

.batch-cancel {
  border: 1px solid #374151;
  border-radius: 6px;
  background: transparent;
  color: #9ca3af;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  font-family: inherit;
}

.batch-delete-btn {
  border: 1px solid #7f1d1d;
  border-radius: 6px;
  background: #7f1d1d;
  color: #fca5a5;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  font-family: inherit;
}

.batch-delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state, .error-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 12px;
  color: #9ca3af;
}

.spin-loader {
  width: 28px;
  height: 28px;
  border: 3px solid #374151;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
}

.create-btn {
  margin-top: 8px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  font-family: inherit;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-card:hover {
  border-color: #4b5563;
  background: #283444;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.project-card.card-selected {
  border-color: #3b82f6;
  background: #1e2a3e;
}

.card-checkbox {
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #9ca3af;
}

.meta-item svg {
  flex-shrink: 0;
}

.status-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
}

.status-completed {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-pending-images {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.status-in-progress {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(96, 165, 250, 0.3);
}

.card-cover {
  width: 180px;
  height: 108px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  background: #111827;
  border: 1px solid #374151;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b5563;
}

.card-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.delete-btn {
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.15s;
}

.delete-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.enter-arrow {
  color: #6b7280;
  transition: color 0.15s;
}

.project-card:hover .enter-arrow {
  color: #d1d5db;
}

@media (max-width: 768px) {
  .ppt-history {
    padding: 16px;
  }

  .project-card {
    flex-wrap: wrap;
    padding: 16px;
  }

  .card-cover {
    width: 100%;
    height: 140px;
    order: -1;
  }

  .card-actions {
    flex-direction: row;
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add teacher-platform/src/views/ppt/PptHistory.vue
git commit -m "feat(ppt): add history projects page with dark theme cards"
```

---

### Task 7: 前端 — 注册历史项目页面 + 首页入口 + store 恢复

**Files:**
- Modify: `teacher-platform/src/views/ppt/PptIndex.vue:1-55`
- Modify: `teacher-platform/src/views/ppt/PptHome.vue`（在底部添加入口）
- Modify: `teacher-platform/src/stores/ppt.js:9-66`

- [ ] **Step 1: 在 PptIndex.vue 注册 history phase**

将 `PptIndex.vue` 全文替换为：

```vue
<script setup>
import { computed, watch } from 'vue'
import { usePptStore } from '@/stores/ppt'
import PptHome from './PptHome.vue'
import PptDialog from './PptDialog.vue'
import PptOutline from './PptOutline.vue'
import PptDescription from './PptDescription.vue'
import PptPreview from './PptPreview.vue'
import PptHistory from './PptHistory.vue'

const pptStore = usePptStore()

const currentPhase = computed(() => {
  if (!pptStore.projectId && pptStore.currentPhase !== 'history') return 'home'
  return pptStore.currentPhase
})

const phaseComponent = computed(() => {
  const map = {
    home: PptHome,
    history: PptHistory,
    dialog: PptDialog,
    outline: PptOutline,
    description: PptDescription,
    preview: PptPreview
  }
  return map[currentPhase.value] || PptHome
})

// Watch for creation type and auto-navigate
watch(() => pptStore.creationType, (type) => {
  if (type === 'dialog' && pptStore.projectId && pptStore.currentPhase === 'home') {
    pptStore.setPhase('dialog')
  } else if (type === 'file' && pptStore.projectId && pptStore.currentPhase === 'home') {
    pptStore.setPhase('outline')
  } else if (type === 'renovation' && pptStore.projectId && pptStore.currentPhase === 'home') {
    pptStore.setPhase('outline')
  }
}, { immediate: true })
</script>

<template>
  <div class="ppt-index">
    <component :is="phaseComponent" />
  </div>
</template>

<style scoped>
.ppt-index {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
```

- [ ] **Step 2: 在 PptHome.vue 添加历史项目入口**

在 `PptHome.vue` 的模板中，找到创建模式选择区域之前或之后合适的位置，添加一个"历史项目"入口按钮。

找到 `<template>` 部分的顶层容器内（具体需根据文件实际结构在顶部或 header 区域添加），添加：

```html
<button class="history-entry-btn" @click="goToHistory">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
  历史项目
</button>
```

在 `<script setup>` 中添加函数：

```javascript
function goToHistory() {
  pptStore.setPhase('history')
}
```

为按钮添加样式（在 `<style scoped>` 中）：

```css
.history-entry-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #d5dfed;
  border-radius: 10px;
  background: #f8fbff;
  color: #3f5f82;
  font-size: 14px;
  font-weight: 600;
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  z-index: 10;
}

.history-entry-btn:hover {
  border-color: #3b82f6;
  background: #eef5ff;
  color: #1e3a8a;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}
```

注意：需确认 PptHome 的顶层容器有 `position: relative` 以支持 absolute 定位。如果没有，改用其他布局方式（如在 header 区域 flex 排列）。

- [ ] **Step 3: 在 pptStore 中确保 setPhase 支持 'history'**

检查 `stores/ppt.js` 中的 `setPhase` action。当前实现是直接赋值 `this.currentPhase = phase`，不需要白名单校验，所以 'history' 值自动支持。

但需确保 `resetState` 不会在切换到 history 时被意外调用。检查 `resetState` action 是否会在 PptHome mount 时触发。

（无需代码修改，仅验证。）

- [ ] **Step 4: 提交**

```bash
cd D:/Develop/Project/AIsystem
git add teacher-platform/src/views/ppt/PptIndex.vue teacher-platform/src/views/ppt/PptHome.vue teacher-platform/src/stores/ppt.js
git commit -m "feat(ppt): register history phase + add entry button on home page"
```

---

### Task 8: 校验现有导航回退 + 前端构建验证

**Files:**
- Verify: `teacher-platform/src/views/ppt/PptOutline.vue:399`
- Verify: `teacher-platform/src/views/ppt/PptDescription.vue:355,385-396`
- Verify: `teacher-platform/src/views/ppt/PptPreview.vue:919`

- [ ] **Step 1: 验证现有回退按钮**

确认以下按钮存在且功能正常：
- PptOutline 第 399 行：`<button class="back-btn" @click="pptStore.setPhase('dialog')">`
- PptDescription 第 355 行：`<button class="back-btn" @click="goToOutline">`
- PptPreview 第 919 行：`<button class="icon-btn" @click="goToDescription" title="返回">`

所有 `setPhase` 调用仅改 `currentPhase`，不清除数据。确认无问题后不做修改。

- [ ] **Step 2: 运行前端构建**

```bash
cd D:/Develop/Project/AIsystem/teacher-platform
npm run build
```

预期：构建成功，无错误。

- [ ] **Step 3: 提交（如有修复）**

如果构建报错需要修复，修复后提交：
```bash
cd D:/Develop/Project/AIsystem
git add -A
git commit -m "fix(ppt): resolve build errors"
```

如果构建成功无修改，跳过此步。
