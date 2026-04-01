# PPT生成模块 - 前端实现计划

> [!WARNING]
> 本文档已被新版计划替代，请优先参考：
> `docs/superpowers/plans/2026-03-31-ppt-frontend-design-v2.md`
>
> 替代原因：
> - 前端原型已删除，本文档中原型映射与 CSS 复用策略已不再适用。
> - 当前实现采用 `LessonPrep -> PptIndex -> currentPhase` 状态机流程，与本文档旧描述存在偏差。
> - Description/Preview 后续能力以 banana-slides 高一致性对齐为准，尤其单页图片在线编辑。

> **Date:** 2026-03-28
> **Status:** Draft
> **Author:** Claude
> **原型来源:** `docs/superpowers/prototypes/ppt-*.html`

## 1. 概述

### 1.1 项目背景

将 banana-slides 的 PPT 生成功能集成到 AIsystem 教学智能体平台。前端基于 Vue 3 + Vite + Pinia，后端基于 FastAPI。UI 设计参考已完成的 HTML 原型（`docs/superpowers/prototypes/`），Vue 实现时需将原型中的 CSS/JS 逻辑转换为 Vue SFC 组件。

### 1.2 设计目标

- 5个独立页面：欢迎页、对话页、大纲页、描述页、预览页
- 3个入口流程：对话生成、文件生成、PPT翻新
- 线性流程，不可跳步，可返回上一步
- 状态通过 Pinia Store 跨页面共享
- **UI 样式直接复用原型 CSS，转换为 Vue `<style scoped>`**
- 不引入 Tailwind CSS

### 1.3 原型文件清单

| 原型文件 | 对应页面 | 说明 |
|---------|---------|------|
| `ppt-home-v4.html` | PptHome | 欢迎页，含3个入口 |
| `ppt-dialog.html` | PptDialog | 对话页，含意图澄清工作台 |
| `ppt-outline.html` | PptOutline | 大纲编辑页 |
| `ppt-description.html` | PptDescription | 描述页，3列网格 |
| `ppt-preview.html` | PptPreview | 预览页 |

### 1.4 缺失功能补全

以下功能在 banana-slides 源码中有，但未在原型中体现，需在实现时补充：

| 功能 | 所属页面 | 说明 |
|------|---------|------|
| 模板搜索/分类tab | PptHome | 模板网格需增加搜索和分类过滤 |
| 素材中心 | 全局 | MaterialCenterModal，素材管理 |
| 导出任务面板 | 全局 | ExportTasksPanel，导出进度追踪 |
| 项目设置弹窗 | 全局 | ProjectSettingsModal，横竖版切换 |
| 参考文件预览 | PptOutline | FilePreviewModal，PDF/图片预览 |
| 参考文件解析进度 | PptOutline | parseStatus 状态显示 |
| 单页描述编辑 | PptDescription | 点击卡片进入编辑模式 |
| 批量生成操作 | PptDescription | 批量生成/删除/重新生成 |
| 版本历史 | PptPreview | PageImageVersion 版本下拉 |
| 单页重新生成 | PptPreview | 重新生成单页图片 |

> **实现原则：** 原型 HTML 中的 CSS 完整可直接复用，JS 逻辑（状态管理、交互）需转换为 Vue Composition API。

---

## 2. 路由设计

> **路由架构决策**：采用 tab 组件切换模式，不使用子路由。PPT 生成是线性流程，各页面共享 Pinia store 状态，tab 切换配合 `<keep-alive>` 保存组件状态，用户不需要也不能直接通过 URL 跳转页面。

### 2.1 URL 规范

```
/lesson-prep?tab=ppt          → PptHome（欢迎页，默认）
/lesson-prep?tab=dialog      → PptDialog（对话页）
/lesson-prep?tab=outline     → PptOutline（大纲页）
/lesson-prep?tab=description → PptDescription（描述页）
/lesson-prep?tab=preview     → PptPreview（预览页）
```

> **历史项目**：复用现有 `/courseware` 页面，不新建独立 PptHistory 路由。

### 2.2 路由配置

**不做任何改动**，复用现有的 `LessonPrep.vue` 和 `router/index.js`。

现有代码已实现 tab 切换逻辑：

```js
// LessonPrep.vue
const activeTab = computed(() => {
  const t = route.query.tab
  const tab = typeof t === 'string' ? t : ''
  return validTabs.includes(tab) ? tab : 'ppt'
})

const currentComponent = computed(() => {
  const map = {
    ppt: LessonPrepPpt,           // 欢迎页
    'lesson-plan': LessonPlanPage,
    animation: LessonPrepAnimation,
    knowledge: LessonPrepKnowledge,
    mindmap: LessonPrepMindmap,
    data: LessonPrepData
  }
  return map[activeTab.value]
})
```

### 2.3 PPT Tab 切换逻辑

PPT 相关的 tab 定义在 `LessonPrep.vue` 的 `tabs` 数组中：

```js
const tabs = [
  { id: 'ppt', label: 'PPT生成' },       // 欢迎页
  { id: 'dialog', label: '对话生成' },   // 对话页（dialog 入口专属）
  { id: 'outline', label: '大纲编辑' }, // 大纲页
  { id: 'description', label: '页面描述' }, // 描述页
  { id: 'preview', label: '预览导出' }   // 预览页
]
```

### 2.4 流程守卫（在组件内部处理）

页面级别的流程控制在各 Vue 组件的 `onMounted` 中处理，不依赖路由守卫：

```js
// PptDialog.vue
onMounted(async () => {
  const pptStore = usePptStore()
  // 对话页仅对话生成入口可访问
  if (!pptStore.projectId || pptStore.creationType !== 'dialog') {
    router.replace({ path: '/lesson-prep', query: { tab: 'outline' } })
  }
})

// PptOutline.vue
onMounted(async () => {
  const pptStore = usePptStore()
  if (!pptStore.projectId) {
    router.replace({ path: '/lesson-prep', query: { tab: 'ppt' } })
  }
})
```

---

## 3. 流程设计

### 3.1 三个入口流程

| 入口 | 欢迎页操作 | 后续流程 |
|------|-----------|---------|
| 对话生成 | 选择模板 + 输入主题 | → 对话页 → 大纲页 → 描述页 → 预览页 |
| 文件生成 | 上传参考文件（PDF/DOCX） | → 大纲页 → 描述页 → 预览页 |
| PPT翻新 | 上传旧PPT/PDF | → 大纲页 → 描述页 → 预览页 |

### 3.2 线性流程规则

- **不可跳步**：必须按顺序完成每个页面
- **可返回上一步**：每个页面有"上一步"按钮
- **流程汇合**：文件生成和PPT翻新跳过对话页，但从大纲页开始汇入同一流程
- **对话页限制**：仅对话生成入口可进入，文件生成和PPT翻新禁止访问

---

## 4. 状态管理

### 4.1 Pinia Store

**文件**: `src/stores/ppt.js`

```js
export const usePptStore = defineStore('ppt', {
  state: () => ({
    // 项目信息
    projectId: null,
    projectStatus: null,

    // 流程控制
    creationType: null,

    // 模板与风格
    selectedTemplate: null,
    selectedPresetTemplateId: null,
    templateStyle: '',
    aspectRatio: '16:9',

    // 参考文件
    referenceFiles: [],

    // 大纲数据
    outlineText: '',
    outlinePages: [],

    // 描述数据
    descriptions: {},

    // 对话历史（对话页用）
    sessions: [],
    sessionMetrics: {
      round: 0,
      confidence: 0,
      phase: 'clarifying'
    },

    // 生成进度
    generationProgress: { total: 0, completed: 0, failed: 0 },

    // 错误状态
    error: null,
    errorMessage: null
  }),

  actions: {
    async createProject(data) { ... },
    async fetchProject(projectId) { ... },
    async saveSession(role, content) { ... },
    async fetchSessions(projectId) { ... },
    async parseOutline() { ... },
    async generateDescriptions() { ... },
    addPage(page) { ... },
    deletePage(pageId) { ... },
    updatePage(pageId, data) { ... },
    reorderPages(newOrder) { ... },
    setError(error, message) { ... },
    clearError() { ... },
    resetState() { ... }
  }
})
```

### 4.2 状态初始化时机

| 页面 | 状态前置条件 |
|------|------------|
| 欢迎页 | 无，resetState() 清空所有状态 |
| 对话页 | projectId 存在，creationType === 'dialog' |
| 大纲页 | projectId 存在，outlineText 或 outlinePages 有数据 |
| 描述页 | outlinePages 有数据 |
| 预览页 | descriptions 有数据 |

---

## 5. 页面实现计划

### 5.1 PptHome.vue（欢迎页）

**原型:** `ppt-home-v4.html`

**实现步骤:**
1. 从原型提取 CSS 变量和样式规则，转换为 Vue `<style scoped>`
2. 将 3 个 mode-tab（对话生成/文件生成/PPT翻新）转换为 Vue 的 v-if/v-show 逻辑
3. 模板选择器、图片上传、文字风格切换等交互转为 Vue 响应式状态
4. "下一步"按钮根据当前 mode 调用不同 action 并跳转

**关键组件:**
- `CreationTypeSelector` — 3个入口 tab
- `DialogCreationForm` — 对话生成表单（模板选择+主题输入）
- `FileCreationForm` — 文件上传表单
- `RenovationForm` — PPT翻新表单
- `TemplateSelector` — 模板网格选择
- `TextStyleSelector` — 文字风格面板

**CSS 复用:** 原型中的 CSS 变量（`--bg-main`, `--ink-strong`, `--brand` 等）直接复制到 Vue 文件的 `<style>` 中。

### 5.2 PptDialog.vue（对话页）

**原型:** `ppt-dialog.html`

**实现步骤:**
1. 提取原型的 `workspace` 布局系统（grid 3列/响应式）
2. 将 JS 状态（`round`, `confidence`, `draftReady`, `confirmed`, `pending` 等）迁移到 Pinia store
3. `ContextRibbon`（4格上下文）使用 computed 属性从 store 读取
4. `ChatMessages` 使用 `v-for` 渲染 sessions 数组
5. `InsightPanel`（右侧看板）各卡片使用独立 computed 属性
6. `QuickActions` 按钮点击填充输入框，使用 `messageInput.value` 触发
7. 流式响应使用 `fetch` + `ReadableStream`，参考 spec 文档中的 SSE 处理

**关键组件:**
- `ContextRibbon` — 模板/主题/课时/页数 4格展示
- `ChatMessage` — 单条消息气泡
- `QuickActions` — 快捷补充按钮组
- `Composer` — 输入框+发送按钮+工具栏
- `InsightPanel` — 意图结构看板
  - `IntentMatrix` — 置信度条形图
  - `ConfirmedList` — 已确认诉求列表
  - `PendingList` — 待确认要点列表
  - `SnapshotList` — 轮次摘要
  - `DraftBlock` — 初版大纲预览
- `FlowStrip` — 顶部4步流程指示器

**AI 对话状态机:** 原型中的 `roundPlaybook` 数组定义 AI 回复逻辑，Vue 实现时由后端控制，前端仅处理 SSE 流事件。

### 5.3 PptOutline.vue（大纲页）

**原型:** `ppt-outline.html`

**实现步骤:**
1. 双栏布局：左侧 380px 固定宽度 sticky，右侧 flex:1
2. `OutlineCard` 使用 `v-for` + `DraggableOutlineList` 渲染
3. 拖拽使用原生 HTML5 Drag API，每个卡片 `outline-card` 的 header 包含 drag-handle
4. AI 优化输入框实时更新 store，提交时调用 `parseOutline()`
5. 添加/删除页面直接操作 `store.outlinePages`
6. 参考文件列表展示 store 中的 `referenceFiles`

**关键组件:**
- `OutlineEditor` — 双栏布局容器
- `LeftPanel` — AI优化输入+大纲文本区+参考文件
- `RightPanel` — 大纲卡片列表
- `OutlineCard` — 单页大纲卡片（标题+要点列表+Part标签）
- `DraggableOutlineList` — 可拖拽排序容器
- `AIOptimizeInput` — AI优化输入框
- `ReferenceFileList` — 参考文件列表

### 5.4 PptDescription.vue（描述页）

**原型:** `ppt-description.html`

**实现步骤:**
1. 3列网格布局，使用 `grid-template-columns: repeat(3, 1fr)`
2. `DescriptionCard` 使用 `v-for` 遍历 `store.outlinePages`
3. 每个卡片显示：页码badge、状态badge（pending/completed/generating）、描述内容、额外字段
4. 批量生成按钮触发 `store.generateDescriptions()`，流式更新各卡片状态
5. 设置下拉面板（生成模式、额外字段）使用 Vue 的 `v-show`
6. 描述生成要求折叠区使用 `max-height` 动画

**关键组件:**
- `DescriptionGrid` — 3列网格容器
- `DescriptionCard` — 单页描述卡片
  - `CardHeader` — 页码+状态+操作按钮
  - `CardContent` — Markdown 描述内容渲染
  - `ExtraFields` — 视觉元素/焦点/排版/备注 4字段展示
- `BatchGenerateButton` — 批量生成按钮
- `SettingsDropdown` — 设置下拉（生成模式+额外字段）
- `ImportExportMenu` — 导入导出菜单
- `ProgressIndicator` — 进度显示 "X/Y 页已完成"

### 5.5 PptPreview.vue（预览页）

**原型:** `ppt-preview.html`

**实现步骤:**
1. 左侧缩略图列表（280px），垂直滚动，渲染 `store.outlinePages`
2. 右侧大预览区，`transform: scale()` 实现缩放
3. 缩略图点击切换当前预览页
4. 导航按钮（上/下一页）更新 `currentPageIndex`
5. 导出按钮触发下载，调用 `GET /projects/:id/export/pptx`
6. 版本历史下拉使用 `v-show`，展示 `PageImageVersion` 数据
7. 底部进度条绑定 `store.generationProgress`

**关键组件:**
- `ThumbnailList` — 缩略图垂直列表
- `ThumbnailItem` — 单个缩略图卡片
- `Toolbar` — 工具栏（编辑描述/重新生成/导出/版本/缩放）
- `SlidePreview` — 大预览区
- `ZoomControls` — 缩放控制（缩小/百分比/放大/适应）
- `ExportDropdown` — 导出格式下拉（PPTX/PDF/图片）
- `VersionDropdown` — 历史版本下拉
- `ProgressBar` — 底部进度条

---

## 6. API 层设计

> **API 封装说明**：复用现有 `src/api/http.js` 的 `apiRequest`（JSON 请求）和 `authFetch`（流式请求），不新增 `axios` 或其他封装。

### 6.1 API 模块

**文件**: `src/api/ppt.js`

```js
import { apiRequest, authFetch } from '@/api/http'

const API = '/api/v1/ppt'

// 项目
export const createProject = (data) => apiRequest(`${API}/projects`, { method: 'POST', body: JSON.stringify(data) })
export const getProject = (id) => apiRequest(`${API}/projects/${id}`)
export const updateProject = (id, data) => apiRequest(`${API}/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteProject = (id) => apiRequest(`${API}/projects/${id}`, { method: 'DELETE' })
export const listProjects = () => apiRequest(`${API}/projects`)

// 大纲
export const generateOutline = (id) => apiRequest(`${API}/projects/${id}/outline/generate`, { method: 'POST' })
export const generateOutlineStream = (id) => authFetch(`${API}/projects/${id}/outline/generate/stream`, { method: 'POST' })

// 描述
export const generateDescriptions = (id) => apiRequest(`${API}/projects/${id}/descriptions/generate`, { method: 'POST' })

// 页面
export const updatePage = (projectId, pageId, data) => apiRequest(`${API}/projects/${projectId}/pages/${pageId}`, { method: 'PUT', body: JSON.stringify(data) })
export const reorderPages = (projectId, pageIds) => apiRequest(`${API}/projects/${projectId}/pages/reorder`, { method: 'POST', body: JSON.stringify({ page_ids: pageIds }) })

// 图片
export const generateImages = (id, pageIds) => apiRequest(`${API}/projects/${id}/images/generate`, { method: 'POST', body: JSON.stringify({ page_ids: pageIds }) })

// 导出（直接返回 URL）
export const getExportUrl = (id, format) => {
  const base = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
  return `${base}${API}/projects/${id}/export/${format}`
}

// 文件上传（FormData + authFetch，流式场景）
export const uploadReferenceFile = async (projectId, file) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await authFetch(`${API}/projects/${projectId}/reference-files`, {
    method: 'POST',
    body: formData
  })
  return res.ok ? res.json() : null
}

export const parseReferenceFile = (projectId, fileId) => apiRequest(`${API}/projects/${projectId}/reference-files/${fileId}/parse`, { method: 'POST' })

// 对话
export const getSessions = (projectId) => apiRequest(`${API}/sessions/${projectId}`)
export const saveSession = (projectId, role, content) => apiRequest(`${API}/sessions/${projectId}`, { method: 'POST', body: JSON.stringify({ role, content }) })
export const chat = (projectId, message) => apiRequest(`${API}/projects/${projectId}/chat`, { method: 'POST', body: JSON.stringify({ message }) })

// 模板
export const getPresetTemplates = () => apiRequest(`${API}/templates/presets`)
export const getUserTemplates = () => apiRequest(`${API}/templates/user`)

// 流式生成（使用 authFetch，返回 ReadableStream）
export const generateDescriptionsStream = (projectId) => authFetch(`${API}/projects/${projectId}/descriptions/generate/stream`, { method: 'POST' })
```

### 6.2 流式响应处理

> **SSE 协议**：统一使用 `event: message`，所有事件通过 `data.type` 字段区分。前端按 `data.type` 分流，不依赖 event 名。

```js
// SSE 流式解析工具
// 不依赖 event 名，只解析 data: 行，按 data.type 分流
export async function* streamEvents(url, options = {}) {
  const response = await fetch(url, options)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch (e) { /* ignore */ }
      }
    }
  }
}

// 使用示例：按 data.type 分流
async function handleGenerate(projectId) {
  const pptStore = usePptStore()
  for await (const event of streamEvents(`/projects/${projectId}/descriptions/generate/stream`)) {
    switch (event.type) {
      case 'page':
        pptStore.descriptions[event.page_id] = event.content
        break
      case 'progress':
        pptStore.generationProgress = event
        break
      case 'done':
        showToast('生成完成', 'success')
        break
      case 'error':
        showToast(event.message, 'error')
        break
    }
  }
}
```

---

## 7. 组件清单

### 7.1 页面组件

| 文件 | 说明 | 原型对应 |
|------|------|---------|
| `views/ppt/PptHome.vue` | 欢迎页 | `ppt-home-v4.html` |
| `views/ppt/PptDialog.vue` | 对话页 | `ppt-dialog.html` |
| `views/ppt/PptOutline.vue` | 大纲页 | `ppt-outline.html` |
| `views/ppt/PptDescription.vue` | 描述页 | `ppt-description.html` |
| `views/ppt/PptPreview.vue` | 预览页 | `ppt-preview.html` |

### 7.2 共享组件

| 文件 | 说明 |
|------|------|
| `components/ppt/TemplateSelector.vue` | 模板网格选择器 |
| `components/ppt/TextStyleSelector.vue` | 文字风格选择面板 |
| `components/ppt/MarkdownTextarea.vue` | Markdown 文本输入框 |
| `components/ppt/ReferenceFileList.vue` | 参考文件列表 |
| `components/ppt/DescriptionCard.vue` | 描述卡片 |
| `components/ppt/OutlineCard.vue` | 大纲卡片 |
| `components/ppt/ChatMessage.vue` | 聊天消息气泡 |
| `components/ppt/AiRefineInput.vue` | AI优化输入框 |
| `components/ppt/PresetCapsules.vue` | 预设风格胶囊按钮 |
| `components/ppt/ThumbnailItem.vue` | 缩略图项 |
| `components/ppt/BottomBar.vue` | 底部导航栏 |
| `components/ppt/StatusBadge.vue` | 状态徽章 |
| `components/ppt/FilePreviewModal.vue` | 参考文件预览弹窗 |
| `components/ppt/MaterialCenterModal.vue` | 素材中心弹窗 |
| `components/ppt/ExportTasksPanel.vue` | 导出任务面板 |
| `components/ppt/ProjectSettingsModal.vue` | 项目设置弹窗 |

### 7.3 样式复用策略

**CSS 变量（从原型提取）:**

```css
/* 通用变量 - 放入 App.vue 或 main.css */
:root {
  --bg-primary: #f0f7ff;
  --bg-card: #ffffff;
  --bg-secondary: #f8fafc;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;
  --accent: #3b82f6;
  --accent-light: #dbeafe;
  --accent-hover: #2563eb;
  --banana: #F59E0B;
  --banana-light: #fef3c7;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --border: #e5e7eb;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
  --shadow-lg: 0 8px 32px rgba(0,0,0,0.08);
  --radius: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
}
```

**实现方式:** 原型中的完整 CSS 直接复制到各 Vue 文件的 `<style scoped>` 中，仅将类名选择器改为 Vue scoped 格式。

---

## 8. 文件结构

```
teacher-platform/src/
├── views/
│   └── ppt/
│       ├── PptHome.vue
│       ├── PptDialog.vue
│       ├── PptOutline.vue
│       ├── PptDescription.vue
│       └── PptPreview.vue
├── stores/
│   └── ppt.js
├── api/
│   └── ppt.js
├── components/
│   └── ppt/
│       ├── TemplateSelector.vue
│       ├── TextStyleSelector.vue
│       ├── MarkdownTextarea.vue
│       ├── ReferenceFileList.vue
│       ├── DescriptionCard.vue
│       ├── OutlineCard.vue
│       ├── ChatMessage.vue
│       ├── AiRefineInput.vue
│       ├── PresetCapsules.vue
│       ├── ThumbnailItem.vue
│       ├── BottomBar.vue
│       ├── StatusBadge.vue
│       ├── FilePreviewModal.vue
│       ├── MaterialCenterModal.vue
│       ├── ExportTasksPanel.vue
│       └── ProjectSettingsModal.vue
└── router/
    └── index.js（修改）
```

---

## 9. 依赖安装

```bash
cd teacher-platform

# Markdown 渲染
npm install marked

# 无需安装 axios，使用现有 authFetch / apiRequest 封装
```

---

## 10. 实施顺序

### Phase 1: 基础结构
1. 创建 `stores/ppt.js` — Pinia store 定义
2. 创建 `api/ppt.js` — API 封装
3. 修改 `router/index.js` — 添加 PPT 路由
4. 创建 `views/ppt/` 目录结构

### Phase 2: 页面组件（按顺序）
> **历史项目**：复用现有 `/courseware` 课件管理页，不新建 PptHistory 页面。

1. **PptHome.vue** — 欢迎页，原型 CSS 直接复用
2. **PptOutline.vue** — 大纲页，拖拽排序需额外处理
3. **PptDescription.vue** — 描述页，3列网格布局
4. **PptPreview.vue** — 预览页，缩放和导出逻辑
5. **PptDialog.vue** — 对话页，复杂状态机

### Phase 3: 共享组件
1. `StatusBadge.vue` — 状态徽章
2. `FilePreviewModal.vue` — 参考文件预览
3. `ProjectSettingsModal.vue` — 项目设置
4. `ExportTasksPanel.vue` — 导出任务面板
5. `MaterialCenterModal.vue` — 素材中心
6. 统一样式变量
7. 完善交互细节

### Phase 4: 联调
1. 与后端 API 联调
2. 流式响应处理
3. 错误处理完善

---

## 11. 已知限制

1. **对话页 AI 对话逻辑**：后端 API 确定后补充，前端先使用模拟数据
2. **文件上传后端**：参考文件解析 API 需后端实现，前端先mock
3. **图片生成与预览**：实际图片生成依赖后端，前端先显示占位
4. **导出功能**：后端实现后对接，前端先实现下载触发
5. **状态持久化**：页面刷新会丢失 store 状态，后续可扩展会话恢复

---

## 12. 与后端文档的关系

- 后端 API 设计：参见 `docs/superpowers/specs/2026-03-26-ppt-banana-integration-design.md`
- 前端实现参考：参见 `docs/superpowers/specs/2026-03-28-ppt-banana-frontend-adaptation.md`
