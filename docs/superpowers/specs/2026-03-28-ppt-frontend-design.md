# PPT生成模块 - 前端设计文档

> **Date:** 2026-03-28
> **Status:** Draft
> **Author:** Claude

## 1. 概述

### 1.1 项目背景

将 banana-slides 的 PPT 生成功能集成到 AIsystem 教学智能体平台。前端基于 Vue 3 + Vite + Pinia，后端基于 FastAPI。页面设计参考 banana-slides 原型，但路由和状态管理融入 AIsystem 现有架构。

### 1.2 设计目标

- 5个独立页面：欢迎页、对话页、大纲页、描述页、预览页
- 3个入口流程：对话生成、文件生成、PPT翻新
- 线性流程，不可跳步，可返回上一步
- 状态通过 Pinia Store 跨页面共享
- 样式采用普通 CSS，不引入 Tailwind

## 2. 路由设计

### 2.1 路由结构

```
/lesson-prep/ppt              → PptHome（欢迎页）
/lesson-prep/ppt/dialog      → PptDialog（对话页）
/lesson-prep/ppt/outline     → PptOutline（大纲页）
/lesson-prep/ppt/description → PptDescription（描述页）
/lesson-prep/ppt/preview     → PptPreview（预览页）
```

### 2.2 路由配置

```js
// router/index.js
{
  path: '/lesson-prep',
  component: () => import('../views/LessonPrep.vue'),
  children: [
    { path: '', redirect: '/lesson-prep/ppt' },
    { path: 'ppt', component: () => import('../views/ppt/PptHome.vue') },
    { path: 'ppt/dialog', component: () => import('../views/ppt/PptDialog.vue') },
    { path: 'ppt/outline', component: () => import('../views/ppt/PptOutline.vue') },
    { path: 'ppt/description', component: () => import('../views/ppt/PptDescription.vue') },
    { path: 'ppt/preview', component: () => import('../views/ppt/PptPreview.vue') },
  ]
}
```

### 2.3 导航守卫

**LessonPrep.vue 父组件**: 作为布局容器，仅包含 `<router-view>` 和顶部导航，不做业务逻辑。

**路由守卫实现**:

```js
// router/index.js - 新增 ppt 子路由的导航守卫
router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // 首屏恢复登录态
  if (!authRestored) {
    authRestored = true
    if (getToken()) {
      await userStore.fetchUser()
    }
  }

  // 非 lesson-prep/ppt 路由继续原有逻辑
  if (!to.path.startsWith('/lesson-prep/ppt')) return true

  // 无需登录检查（页面公开）

  // 检查 projectId
  const pptStore = usePptStore()
  const isPptRoute = to.path.startsWith('/lesson-prep/ppt')
  const isHome = to.path === '/lesson-prep/ppt'

  if (!isHome && !pptStore.projectId) {
    return { path: '/lesson-prep/ppt' }
  }

  // 对话页仅对话生成入口可访问
  if (to.path === '/lesson-prep/ppt/dialog' && pptStore.creationType !== 'dialog') {
    return { path: '/lesson-prep/ppt/outline' }
  }

  return true
})
```

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

### 3.3 页面流转图

```
[对话生成入口]
  欢迎页(选模板+主题) → 创建项目 → 对话页 → 大纲页 → 描述页 → 预览页

[文件生成入口]
  欢迎页(上传文件) → 创建项目 → 大纲页 → 描述页 → 预览页

[PPT翻新入口]
  欢迎页(上传旧PPT) → 创建项目 → 大纲页 → 描述页 → 预览页
```

## 4. 状态管理

### 4.1 Pinia Store

**文件**: `src/stores/ppt.js`

```js
export const usePptStore = defineStore('ppt', {
  state: () => ({
    // 项目信息
    projectId: null,
    projectStatus: null,  // 'DRAFT' | 'OUTLINE_GENERATED' | 'DESCRIPTIONS_GENERATED' | 'PREVIEW_READY'

    // 流程控制
    creationType: null,   // 'dialog' | 'file' | 'renovation'

    // 模板与风格
    selectedTemplate: null,
    selectedPresetTemplateId: null,
    templateStyle: '',     // 文字描述风格
    aspectRatio: '16:9',

    // 参考文件
    referenceFiles: [],    // [{ id, filename, parseStatus, markdownContent }]

    // 大纲数据
    outlineText: '',      // 用户编辑的大纲原始文本
    outlinePages: [],     // [{ pageId, orderIndex, title, points, part }]

    // 描述数据
    descriptions: {},       // { [pageId]: Description }

    // 对话历史
    sessions: [],          // [{ id, role, content, createdAt }]

    // 生成进度
    generationProgress: {
      total: 0,
      completed: 0,
      failed: 0
    },

    // 错误状态
    error: null,
    errorMessage: null
  }),

  actions: {
    // 创建项目
    async createProject(data) { ... },

    // 获取项目详情
    async fetchProject(projectId) { ... },

    // 保存对话消息
    async saveSession(role, content) { ... },

    // 获取对话历史
    async fetchSessions(projectId) { ... },

    // 解析大纲（调用后端）
    async parseOutline() { ... },

    // 生成页面描述（流式）
    async generateDescriptions() { ... },

    // 页面 CRUD
    addPage(page) { ... },
    deletePage(pageId) { ... },
    updatePage(pageId, data) { ... },
    reorderPages(newOrder) { ... },

    // 错误处理
    setError(error, message) { ... },
    clearError() { ... },

    // 重置状态
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

## 5. 页面设计

### 5.1 欢迎页 (PptHome)

**路由**: `/lesson-prep/ppt`

**功能**:
- 3个入口按钮：对话生成、文件生成、PPT翻新
- 对话生成：模板选择 + 主题输入
- 文件生成：文件上传（PDF/DOCX）
- PPT翻新：文件上传（PPT/PDF）

**组件结构**:
```
PptHome.vue
├── HeroSection（标题区）
├── CreationTypeSelector（3个入口按钮）
├── DialogCreationForm（对话生成：模板+主题输入）
│   ├── TemplateSelector（模板选择）
│   ├── TextStyleSelector（文字风格选择）
│   └── TopicInput（主题输入框）
├── FileCreationForm（文件生成：文件上传）
│   ├── FileUploader
│   └── TemplateSelector
└── RenovationForm（PPT翻新：文件上传）
    └── FileUploader
```

**创建项目后跳转**:
- 对话生成 → `/lesson-prep/ppt/dialog`
- 文件生成/PPT翻新 → `/lesson-prep/ppt/outline`

### 5.2 对话页 (PptDialog)

**路由**: `/lesson-prep/ppt/dialog`

**功能**:
- 与 AI 多轮对话，澄清用户真实教学意图
- AI 生成初版大纲
- 确认后进入大纲页

**组件结构**:
```
PptDialog.vue
├── ContextRibbon（显示模板、主题等上下文）
├── ChatMessages（对话消息列表）
│   ├── UserMessage
│   └── AIMessage
├── QuickActions（快捷补充按钮）
├── Composer（输入框+发送按钮）
└── InsightPanel（意图结构看板）
    ├── IntentMatrix（意图置信度）
    ├── ConfirmedList（已确认诉求）
    ├── PendingList（待确认要点）
    └── DraftOutline（初版大纲预览）
```

**AI 对话机制**:
- 使用 ReAct 循环（类似 LangGraph）
- AI 思考 → 调用工具 → 生成响应
- 对话消息通过 `POST /ppt/sessions/:projectId` 保存到后端
- 对话历史通过 `GET /ppt/sessions/:projectId` 获取
- 最终生成初版大纲，保存到 `store.outlineText`，跳转到大纲页

**ReAct 循环实现**（前端）:
```js
// PptDialog.vue - 对话发送
async function sendMessage(userContent) {
  // 1. 保存用户消息
  await pptStore.saveSession('user', userContent)

  // 2. 追加 AI 思考消息（显示 loading）
  showTypingIndicator()

  // 3. 调用后端 ReAct 循环
  const response = await fetch(`${API_BASE}/api/v1/ppt/projects/${pptStore.projectId}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ message: userContent })
  })

  // 4. 解析 SSE 流式响应
  const reader = response.body.getReader()
  // ... 解析 events: thinking, message, draft_outline

  // 5. 保存 AI 响应
  await pptStore.saveSession('assistant', aiContent)

  // 6. 如果 AI 生成了初版大纲，保存并提示用户确认
  if (draftOutline) {
    pptStore.outlineText = draftOutline
    showDraftReadyPrompt()
  }
}
```

### 5.3 大纲页 (PptOutline)

**路由**: `/lesson-prep/ppt/outline`

**功能**:
- 显示/编辑大纲内容
- 参考文件提取内容可编辑
- AI 优化大纲
- 添加/删除/重排页面

**组件结构**:
```
PptOutline.vue
├── OutlineEditor（双栏布局）
│   ├── LeftPanel
│   │   ├── AIOptimizeInput（AI优化输入框）
│   │   ├── OutlineTextarea（大纲编辑区）
│   │   └── ReferenceFileList（参考文件列表）
│   └── RightPanel
│       ├── ActionBar（添加页面、生成大纲按钮）
│       └── DraggableOutlineList（可拖拽大纲卡片）
│           └── OutlineCard
│               ├── CardHeader（页码、Part标签、标题、删除）
│               └── CardBody（要点列表、添加要点）
└── BottomBar（上一步、下一步）
```

**拖拽排序**: 使用 `@dnd-kit/core` 实现

### 5.4 描述页 (PptDescription)

**路由**: `/lesson-prep/ppt/description`

**功能**:
- 3列网格布局，每列一个 DescriptionCard
- 显示页面描述、视觉元素、排版布局等
- 批量生成描述
- 单个重新生成

**组件结构**:
```
PptDescription.vue
├── TopBar
│   ├── BackButton
│   ├── AIRefineInput（AI修改输入框）
│   └── ProgressIndicator（进度：X/Y 页已完成）
├── ActionBar
│   ├── BatchGenerateButton（批量生成）
│   ├── SettingsDropdown（设置下拉）
│   └── ImportExportMenu（导入/导出）
├── DescriptionGrid（3列网格）
│   └── DescriptionCard
│       ├── CardHeader（页码、状态badge）
│       ├── CardContent（描述Markdown渲染）
│       ├── ExtraFields（视觉元素、视觉焦点、排版、备注）
│       └── CardActions（编辑、重新生成、删除）
└── BottomBar（上一步、下一步）
```

### 5.5 预览页 (PptPreview)

**路由**: `/lesson-prep/ppt/preview`

**功能**:
- 左侧垂直缩略图列表
- 右侧大预览区
- 缩放控制
- 导出 PPT/PDF

**组件结构**:
```
PptPreview.vue
├── LeftPanel（缩略图列表）
│   ├── ThumbnailItem（序号、缩略图、页码）
│   └── ThumbnailList（垂直滚动）
├── RightPanel（大预览区）
│   ├── Toolbar
│   │   ├── EditDescriptionButton
│   │   ├── RegenerateButton
│   │   ├── ExportDropdown（PPTX/PDF/图片）
│   │   ├── VersionDropdown（版本切换）
│   │   └── ZoomControls（缩小、百分比、放大、适应窗口）
│   ├── SlidePreview（大预览图）
│   └── ProgressBar（底部进度条）
└── BottomBar（上一步）
```

## 6. API 层设计

### 6.1 API 模块

**文件**: `src/api/ppt.js`

### 6.2 核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ppt/projects` | 创建PPT项目 |
| GET | `/ppt/projects/:id` | 获取项目详情 |
| PUT | `/ppt/projects/:id` | 更新项目 |
| DELETE | `/ppt/projects/:id` | 删除项目 |
| GET | `/ppt/projects` | 列出用户项目 |
| POST | `/ppt/projects/:id/outline/generate` | 生成大纲（非流式） |
| POST | `/ppt/projects/:id/outline/generate/stream` | 流式生成大纲（SSE） |
| POST | `/ppt/projects/:id/descriptions/generate` | 生成描述 |
| POST | `/ppt/projects/:id/descriptions/generate/stream` | 流式生成描述（SSE） |
| PUT | `/ppt/projects/:id/pages/:pageId` | 更新页面 |
| POST | `/ppt/projects/:id/pages/reorder` | 批量更新页面顺序 |
| POST | `/ppt/projects/:id/images/generate` | 生成图片 |
| GET | `/ppt/projects/:id/export/pptx` | 导出PPTX |
| POST | `/ppt/projects/:id/reference-files` | 上传参考文件 |
| GET | `/ppt/projects/:id/reference-files` | 获取参考文件列表 |
| POST | `/ppt/projects/:id/reference-files/:fileId/parse` | 解析参考文件 |
| GET | `/ppt/sessions/:projectId` | 获取对话历史 |
| POST | `/ppt/sessions/:projectId` | 写入对话消息 |
| GET | `/ppt/templates/presets` | 预设模板列表 |
| GET | `/ppt/templates/user` | 用户模板列表 |
| POST | `/ppt/templates/upload` | 上传用户模板 |

### 6.3 主要数据结构和请求/响应格式

**创建项目 POST /ppt/projects**
```js
// Request
{
  creation_type: 'dialog' | 'file' | 'renovation',
  idea_prompt?: string,           // 对话生成
  outline_text?: string,           // 文件生成（用户编辑后的大纲）
  template_style?: string,
  aspect_ratio?: string
}

// Response
{
  id: number,
  user_id: number,
  creation_type: string,
  status: string,
  created_at: string
}
```

**大纲页面数据结构**
```js
// outlinePages[]
{
  pageId: number,
  orderIndex: number,
  title: string,
  points: string[],
  part?: string  // 章节名称，如"封面"、"内容"、"结尾"
}
```

**描述数据结构**
```js
// descriptions[pageId]
{
  pageId: number,
  content: string,          // Markdown 格式的页面描述
  visualElement: string,    // 视觉元素描述
  visualFocus: string,      // 视觉焦点
  layout: string,           // 排版布局
  speakerNotes: string,     // 演讲者备注
  status: 'pending' | 'generating' | 'completed' | 'failed'
}
```

**对话消息结构**
```js
// sessions[]
{
  id: number,
  role: 'user' | 'assistant',
  content: string,
  createdAt: string
}
```

### 6.4 流式响应处理

流式响应使用 SSE（Server-Sent Events），前端通过 `fetch` + `ReadableStream` 解析。

**SSE 事件格式**: `event: {type}\ndata: {json}\n\n`

**事件类型**:
- `page` - 单个页面数据（如大纲页面、描述卡片）
- `progress` - 进度更新
- `done` - 生成完成
- `error` - 错误

**示例：流式生成大纲**

```js
// api/ppt.js
export async function* generateOutlineStream(projectId) {
  const res = await fetch(`${API_BASE}/api/v1/ppt/projects/${projectId}/outline/generate/stream`, {
    method: 'POST',
    headers: getAuthHeaders()
  })
  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value)
    for (const line of text.split('\n')) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6))
      }
    }
  }
}

// 组件中使用
const pptStore = usePptStore()
for await (const page of generateOutlineStream(pptStore.projectId)) {
  pptStore.outlinePages.push(page)
}
```

**示例：流式生成描述**

```js
// api/ppt.js
export async function* generateDescriptionsStream(projectId) {
  const res = await fetch(`${API_BASE}/api/v1/ppt/projects/${projectId}/descriptions/generate/stream`, {
    method: 'POST',
    headers: getAuthHeaders()
  })
  // ... 同上
}

### 6.5 文件上传与大纲生成流程

**文件生成入口流程**:

1. 用户上传参考文件（PDF/DOCX）
2. 调用 `POST /ppt/projects/:id/reference-files` 上传
3. 调用 `POST /ppt/projects/:id/reference-files/:fileId/parse` 解析文件
4. 解析完成后，后端返回 `markdownContent`
5. 前端将 `markdownContent` 填充到大纲页的 `outlineText`
6. 用户可编辑 `outlineText`，然后调用 `parseOutline()` 生成结构化大纲

**PPT翻新入口流程**:

1. 用户上传旧 PPT/PDF
2. 调用 `POST /ppt/projects/:id/reference-files` 上传
3. 调用 `POST /ppt/projects/:id/reference-files/:fileId/parse` 解析
4. 解析完成后，后端直接生成结构化大纲（跳过 `outlineText` 编辑）
5. 前端跳转到大纲页，显示已生成的大纲

**上传错误处理**:

```js
async function handleFileUpload(file) {
  try {
    const uploadResult = await uploadReferenceFile(pptStore.projectId, file)
    pptStore.referenceFiles.push(uploadResult)

    // 触发解析
    const parseResult = await parseReferenceFile(pptStore.projectId, uploadResult.id)
    if (parseResult.status === 'failed') {
      pptStore.setError('FILE_PARSE_FAILED', parseResult.error_message)
    }
  } catch (error) {
    pptStore.setError('UPLOAD_FAILED', error.message)
  }
}
```

```js
// 上传参考文件
export async function uploadReferenceFile(projectId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/v1/ppt/projects/${projectId}/reference-files`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData
  })
  return res.json()
}
```

## 7. 组件设计

### 7.1 组件列表

| 组件 | 类型 | 说明 |
|------|------|------|
| PptHome | 页面 | 欢迎页主组件 |
| PptDialog | 页面 | 对话页主组件 |
| PptOutline | 页面 | 大纲页主组件 |
| PptDescription | 页面 | 描述页主组件 |
| PptPreview | 页面 | 预览页主组件 |
| TemplateSelector | 共享 | 模板选择器 |
| TextStyleSelector | 共享 | 文字风格选择器 |
| MarkdownTextarea | 共享 | Markdown输入框 |
| ReferenceFileList | 共享 | 参考文件列表 |
| DescriptionCard | 共享 | 描述卡片 |
| OutlineCard | 共享 | 大纲卡片 |
| ChatMessage | 共享 | 聊天消息 |
| AiRefineInput | 共享 | AI优化输入框 |
| PresetCapsules | 共享 | 预设胶囊 |

### 7.2 样式规范

- **不引入 Tailwind CSS**
- 所有样式使用普通 CSS（scoped style in Vue SFC）
- 颜色变量定义在 `:root` 中
- 组件样式文件随 `.vue` 文件放置（`*.module.css` 或 `<style scoped>`）

### 7.3 基础组件

基础 UI 组件（Button、Card、Modal、Toast）使用 AIsystem 现有组件，不重复造轮子。

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
│       └── PresetCapsules.vue
└── router/
    └── index.js（修改）
```

## 9. 已知限制

1. **对话页 ReAct 实现**：具体工具调用和 prompt 设计待后端 API 确定后补充
2. **文件上传后端**：参考文件解析 API 需后端实现
3. **图片生成与预览**：实际图片生成依赖后端 banana-slides providers
4. **导出功能**：PPTX/PDF 导出依赖后端实现
5. **状态持久化**：页面刷新会丢失 Pinia store 状态，需后端支持会话恢复
6. **dnd-kit 集成**：拖拽排序的具体事件处理待实现时补充
7. **响应式布局**：描述页 3 列网格在小屏幕的响应式处理待定

## 10. 与后端文档的关系

本文档覆盖**前端实现**部分。后端 API 设计参见：
- `docs/superpowers/specs/2026-03-26-ppt-banana-integration-design.md`

本文档不重复后端数据模型、AI 服务等设计，仅聚焦前端路由、状态、页面和组件。
