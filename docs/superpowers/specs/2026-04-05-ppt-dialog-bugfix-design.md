# PPT 对话工作台 Bug 修复与体验优化设计

## 概述

修复 PPT 教学意图澄清工作台的 6 个问题：按钮禁用逻辑、要点累积存储、AI 引导语、页面导航回退、历史记录查看、图片生成动态效果。

## 问题清单

| # | 问题 | 根因 | 影响 |
|---|------|------|------|
| 1 | 待确认要点未全部确认时按钮仍可点击 | 按钮 disabled 条件只检查 `intentConfirmed \|\| isGenerating`，未检查 `pending` 状态 | 用户可能跳过关键意图澄清 |
| 2 | 已确认要点在新一轮对话后被刷新丢失 | `applyIntentState` 每次完全覆盖 `confirmed` 数组，不做累积 | 多轮对话中已确认的信息丢失 |
| 3 | AI 整理完意图后缺少操作引导 | 后端 prompt 中未要求 AI 在 ready_for_confirmation 时给出点击按钮的提示 | 用户不知道下一步操作 |
| 4 | 从大纲页回退后无法重新进入大纲页 | `intentConfirmed` 是组件本地 reactive 状态，回退后重新 mount 时虽然恢复了 `confirmedIntent`，但按钮仍被 disabled | 用户无法在工作流步骤间自由切换 |
| 5 | 无法回退到欢迎页、无法查看对话历史 | 各 phase 组件缺少统一的导航返回机制 | 用户被困在当前阶段，只能刷新 |
| 6 | 图片生成过程中前端无动态效果 | PptPreview 中图片生成时仅显示静态占位 | 用户体验差，不知道生成进度 |

## 设计方案

### 1. 按钮禁用逻辑修正

**文件：** `teacher-platform/src/views/ppt/PptDialog.vue`

**当前代码（第 598 行）：**
```html
<button :disabled="state.intentConfirmed || isGenerating" @click="confirmIntentAndGo">
```

**修改为三态按钮：**

| 状态 | 条件 | 按钮文本 | disabled | 提示信息 |
|------|------|----------|----------|----------|
| 澄清中 | `pending.length > 0 && !readyForConfirmation` | 确认意图，进入大纲页 | true | 红色提示"请继续完善：XXX、YYY" |
| 可确认 | `readyForConfirmation && !intentConfirmed` | 确认意图，进入大纲页 | false | 无 |
| 已确认 | `intentConfirmed` | 返回大纲页 | false | 点击直接跳转大纲页 |

**新增计算属性：**
```javascript
const confirmBtnDisabled = computed(() => {
  if (isGenerating.value) return true
  if (state.intentConfirmed) return false  // 已确认时可点击（变为"返回大纲页"）
  if (!state.readyForConfirmation) return true  // 未就绪时禁用
  return false
})

const confirmBtnText = computed(() => {
  if (isGenerating.value) return '确认中...'
  if (state.intentConfirmed) return '返回大纲页 →'
  return '确认意图，进入大纲页'
})
```

**修改 `confirmIntentAndGo`：**
- 如果 `state.intentConfirmed` 为 true，直接调用 `pptStore.setPhase('outline')` 跳转
- 否则执行原有确认逻辑

### 2. 待确认要点累积存储

需要前后端双保险，确保已确认要点不会因模型输出遗漏而丢失。

#### 2a. 后端确定性合并（必做）

**文件：** `backend/app/generators/ppt/banana_routes.py` — `_parse_intent_state` 及 chat 端点

在保存 intent_state 到 session_metadata **之前**，从数据库读取之前所有轮次的 confirmed，与当前轮次 AI 返回的 confirmed 做确定性 merge（set union）。这样即使 AI 某轮漏掉了之前的要点，持久化的 intent_state 仍然完整。

```python
# 在 chat() 函数中，_parse_intent_state 之后、保存 session 之前
previous_confirmed = set()
for s in sessions:
    if s.role == 'assistant' and s.session_metadata:
        old_state = s.session_metadata.get('intent_state', {})
        for item in old_state.get('confirmed', []):
            if isinstance(item, str) and item.strip():
                previous_confirmed.add(item.strip())

# 确定性合并：当前轮 confirmed ∪ 历史 confirmed
current_confirmed = set(intent_state.get('confirmed', []))
intent_state['confirmed'] = list(previous_confirmed | current_confirmed)
```

同时在 system prompt 中注入历史已确认要点，让 AI 知晓上下文：
```python
if previous_confirmed:
    system_prompt += f"\n\n之前轮次已确认的要点：{', '.join(previous_confirmed)}。请在你的回复中保留这些已确认要点，不要丢弃。"
```

#### 2b. 前端累积合并（防御性）

**文件：** `teacher-platform/src/views/ppt/PptDialog.vue` — `applyIntentState` 函数

```javascript
function applyIntentState(intentState, pushSummary = true) {
  if (!intentState || typeof intentState !== 'object') return

  // 累积合并 confirmed（去重），即使后端已做合并，前端也做防御性合并
  if (Array.isArray(intentState.confirmed)) {
    const newConfirmed = intentState.confirmed.filter(item => typeof item === 'string' && item.trim())
    const existingSet = new Set(state.confirmed)
    newConfirmed.forEach(item => existingSet.add(item))
    state.confirmed = [...existingSet]
  }

  // pending 以后端最新返回为准
  if (Array.isArray(intentState.pending)) {
    state.pending = intentState.pending.filter(item => typeof item === 'string' && item.trim())
  }

  // ...其余逻辑不变
}
```

### 3. AI 整理完意图后的引导语

**文件：** `backend/app/generators/ppt/banana_routes.py` — intent system prompt

**修改点：** 在 system prompt 中加入规则：

```
当你判断所有核心要点都已澄清（ready_for_confirmation 为 true），整理输出已确认的教学意图后，
你的回复最后一句必须是：
"请点击右侧按钮「确认意图，进入大纲页」，进一步生成大纲。"
```

**备选前端方案：** 如果后端 prompt 不方便改动，可在前端 `sendMessage` 中，当检测到 `response.intent_state.ready_for_confirmation === true` 时，自动在 AI 回复末尾追加引导语。

### 4. 从大纲页回退后允许重新进入

**文件：** `teacher-platform/src/views/ppt/PptDialog.vue`

**修改 onMounted 恢复逻辑：**
```javascript
if (pptStore.confirmedIntent && Object.keys(pptStore.confirmedIntent).length > 0) {
  state.intentSummary = pptStore.confirmedIntent
  state.intentConfirmed = true
  state.readyForConfirmation = true  // 新增：确保按钮可用
  state.confidence = Math.max(state.confidence, 95)  // 新增
  state.pending = []  // 新增：已确认则无待确认
}
```

**修改按钮行为：** 当 `intentConfirmed` 时，按钮文本变为"返回大纲页 →"，点击直接跳转，不再 disabled。

### 5. 导航回退支持

**文件：** 多个 phase 组件

#### 5a. PptDialog 添加返回按钮

PptDialog 当前缺少返回首页的 UI 按钮（`goBack()` 函数已存在但无触发入口）。

在 topbar 的 `identity` 区域前添加返回按钮：
```html
<button class="back-btn" @click="goBack" title="返回首页">
  ← 返回
</button>
```

#### 5b. 校验 PptOutline / PptDescription / PptPreview 现有返回行为

这几个组件当前已存在返回按钮或返回逻辑。**不重复添加 UI**，仅校验：
- 返回按钮是否可见并可点击
- 回退时是否保留已有数据（outlinePages、descriptions 等）
- 如发现问题则微调，无问题则不改动

#### 5c. 确保回退不清除数据

**关键原则：**
- 回退操作不清除已有数据（outlinePages、descriptions 等）
- 前进时如果数据已存在则不重新生成

### 6. 图片生成动态效果

**文件：** `teacher-platform/src/views/ppt/PptPreview.vue`

#### 6a. 流光卡片占位

图片生成中，每个缩略图和主预览区显示流光动画占位卡片：

```css
.image-generating-placeholder {
  background: linear-gradient(
    110deg,
    #f0f4ff 0%, #f0f4ff 40%,
    #e0ebff 50%,
    #f0f4ff 60%, #f0f4ff 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s ease-in-out infinite;
  border-radius: 12px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### 6b. 可爱弹跳等待指示器

在流光卡片中心放置 3 个小画笔/小星星图标做弹跳动画：

```html
<div class="bouncing-indicator">
  <span class="bounce-dot">&#9998;</span>  <!-- 小画笔 -->
  <span class="bounce-dot">&#10024;</span> <!-- 小星星 -->
  <span class="bounce-dot">&#9998;</span>
</div>
```

```css
.bounce-dot {
  display: inline-block;
  font-size: 20px;
  animation: bounce 1.2s ease-in-out infinite;
}
.bounce-dot:nth-child(2) { animation-delay: 0.15s; }
.bounce-dot:nth-child(3) { animation-delay: 0.3s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-12px); }
}
```

#### 6c. 图片揭露过渡效果

图片生成完成后的过渡动画：
- 图片初始 opacity: 0 + scale: 0.95 + filter: blur(8px)
- 完成时过渡到 opacity: 1 + scale: 1 + filter: blur(0)
- 过渡时间 0.6s ease-out

```css
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

#### 6d. 循环等待动画（替代进度条）

不使用进度条，而是采用类似 AI 对话加载动画的循环跳动效果。参考 Claude/GPT/Gemini 的等待加载风格，在流光卡片中心展示循环动画表示"正在创作中"。

在缩略图上叠加一个旋转的小圆环 + "正在创作中..." 文字：

```css
.spin-loader {
  width: 24px; height: 24px;
  border: 3px solid #e0ebff;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
```

**数据源：** 图片生成状态通过 `getTask(taskId)` 轮询获取（而非 `pptStore.generationProgress`），根据每个 page 的 `isImageGenerating` 状态决定是否显示加载动画。

## 数据流变更

### 变更前

```
AI 回复 → applyIntentState 完全覆盖 confirmed/pending → 之前轮次数据丢失
```

### 变更后

```
AI 回复 → applyIntentState 累积合并 confirmed + 以最新 pending 为准 → 历史确认保留
```

### 导航状态变更

```
变更前：phase 单向递进，回退后丢失本地状态
变更后：phase 可自由切换，intentConfirmed 通过 pptStore.confirmedIntent 持久化恢复
```

## 涉及文件

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `teacher-platform/src/views/ppt/PptDialog.vue` | 修改 | 按钮逻辑、累积合并、导航返回、状态恢复 |
| `teacher-platform/src/views/ppt/PptOutline.vue` | 修改 | 添加返回意图页按钮 |
| `teacher-platform/src/views/ppt/PptDescription.vue` | 修改 | 添加返回上一步按钮 |
| `teacher-platform/src/views/ppt/PptPreview.vue` | 修改 | 图片生成动态效果 |
| `backend/app/generators/ppt/banana_routes.py` | 修改 | system prompt 加引导语 + 注入已确认要点 |

## 不涉及的内容

- 不修改数据模型或数据库结构
- 不新增 API 端点
- 不引入新的 npm 依赖
- 不修改 pptStore 的 state 结构
