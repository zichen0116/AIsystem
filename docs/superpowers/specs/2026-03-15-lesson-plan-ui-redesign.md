# 教案生成页面 UI 重设计

## 概述

对教案生成页面进行全面重设计，从当前的三栏同时展示布局改为「对话模式 + 写作编辑模式」双模式互斥切换，仿照豆包网页版写作模型的交互范式。

## 设计决策

| 项目 | 方案 |
|------|------|
| 实现方式 | 全部重写，新建组件体系 |
| 布局 | 对话模式（边栏+全幅对话区）↔ 写作模式（边栏收起+40%对话+60%编辑器）|
| 历史边栏 | 仅前端 UI 壳，mock 数据，不对接后端多会话 API |
| 模式切换 | SSE meta 事件（含 lesson_plan_id）自动检测切换 |
| TOC 目录 | 融入编辑器内部，浮动导航 |
| 格式工具栏 | Notion 风格浮动工具栏（选中文字出现） |
| 输入框 | 功能按钮（上传/语音/知识库）在输入框内部底部，两模式共用组件 |
| 预设提示词 | 9 宫格卡片，内容后续提供，先占位 |
| 响应式 | 仅 PC 端 |
| 深色模式 | 本次不做 |
| 动画 | 模式切换淡入淡出、侧边栏滑动、打字机效果、按钮 hover |

## 组件架构

```
LessonPrep.vue (已有 tab 容器，不变)
└── LessonPlanPage.vue (顶层状态管理)
    ├── LessonPlanSidebar.vue (左侧历史边栏)
    │   ├── 新建对话按钮
    │   └── 历史对话列表 (UI 壳，mock 数据)
    │
    ├── [对话模式] LessonPlanDialog.vue
    │   ├── WelcomePanel.vue (阶段1：欢迎页 + 预设提示词卡片)
    │   └── ChatFlow.vue (阶段2：对话消息流)
    │       ├── ChatMessage.vue (单条消息：用户/AI)
    │       └── DocumentCard.vue (文档卡片，切换触发器)
    │
    ├── [写作模式] LessonPlanWriter.vue
    │   ├── WriterChat.vue (左侧40%：对话流，复用 ChatFlow)
    │   └── WriterEditor.vue (右侧60%：富文本编辑器)
    │       ├── EditorToolbar.vue (顶部操作栏：返回/导出)
    │       ├── FloatingToolbar.vue (选中文字浮动格式栏)
    │       └── EditorTOC.vue (浮动目录导航)
    │
    └── ChatInput.vue (通用底部输入组件，两模式共用)
        ├── 文本输入框
        └── 输入框内底部：功能按钮（上传/语音/知识库）+ 发送按钮
```

## 核心状态（LessonPlanPage.vue）

```javascript
const mode = ref('dialog')           // 'dialog' | 'writer'
const sidebarCollapsed = ref(false)  // 边栏是否折叠
const messages = ref([])             // 对话消息列表
const currentMarkdown = ref('')      // 编辑器内容
const lessonPlanId = ref(null)       // 当前教案 ID
const sessionId = ref(null)          // 会话 ID
const isSending = ref(false)         // 是否正在发送
const streamingMarkdown = ref('')    // 流式内容
const hasContent = ref(false)        // 是否已有教案内容（区分阶段1和阶段2）
```

## 三阶段界面

### 阶段 1：初始对话首页

- 左侧：历史边栏（240px），新建对话按钮 + 历史列表
- 右侧主区域：
  - 居中：欢迎标题 + 副标题
  - 下方：9 宫格预设提示词卡片（3x3）
  - 底部：输入框（功能按钮在输入框内部底部）

### 阶段 2：对话交互中

- 左侧：历史边栏不变
- 右侧主区域变为对话消息流：
  - 用户消息：右对齐，蓝色背景，白色文字
  - AI 消息：左对齐，白色背景，灰色边框
  - AI 消息底部：操作按钮（复制、重新生成、点赞、点踩）
  - 流式回复时显示打字动画
- 底部输入框保持不变

### 阶段 3：写作编辑模式

触发：SSE 流收到包含 `lesson_plan_id` 的 meta 事件后，使用内容启发式判断——当流式内容以 `#` 开头（表示 Markdown 标题，说明 AI 在生成文档而非对话回复）时自动切换到写作模式。原因：后端 `_sse_generate` 对 generate 和 modify 都会发送 meta 事件，仅靠 meta 事件无法区分 AI 是在对话还是生成文档。

- 侧边栏自动收起，出现展开按钮
- 展开时为悬浮层，不挤压内容区
- 对话流中插入一条「文档卡片」消息
- 布局变为双栏：
  - 左侧 40%：对话流 + 底部输入框（可发送修改意见）
  - 右侧 60%：富文本编辑器
    - 顶部操作栏：左「返回对话」、右「复制全文 / 下载 Word / Markdown」（PDF 使用 html2pdf.js 客户端生成）
    - 编辑区：Tiptap 富文本编辑器，流式内容直接填充
    - 浮动格式栏：选中文字时出现（加粗、斜体、下划线、标题、列表、链接）
    - 浮动 TOC：编辑器右侧内嵌目录导航

## 模式切换流程

```
初始加载
  ├─ 有历史教案 → 对话模式（阶段2，显示历史消息）
  └─ 无历史教案 → 对话模式（阶段1，显示欢迎页）

用户发送消息 → SSE 流开始
  ├─ 收到 meta 事件 + 流式内容以 # 开头 → 切换到写作模式（阶段3）
  │   ├─ 侧边栏自动收起
  │   ├─ 对话消息中插入文档卡片
  │   └─ 流式内容填充到编辑器
  └─ 收到 meta 但内容为普通对话 / 未收到 meta → 保持对话模式（阶段2）

写作模式中
  ├─ 点击「返回对话」→ 切回对话模式（阶段2），currentMarkdown 保留不清空
  │   文档卡片仍可点击，点击后重新进入写作模式加载 currentMarkdown
  │   同一会话中只有一张文档卡片（新生成会替换旧卡片内容）
  ├─ 左侧发送修改意见 → 调用 /lesson-plan/modify，流式更新编辑器
  └─ 直接编辑 → 30秒无操作或编辑器失焦时自动保存
```

## 侧边栏行为

- 对话模式：默认展开（240px）
- 写作模式：自动收起，左侧出现展开按钮
- 手动展开时：悬浮层覆盖，不挤压内容区

## 文档卡片（DocumentCard）

- 在对话流中显示为特殊样式消息卡片
- 包含：文档标题 + 「点击查看」按钮
- 点击后进入/回到写作模式

## 输入框组件（ChatInput）

两模式共用，结构：
```
┌─────────────────────────────────────┐
│  文本输入区域（多行 textarea）         │
│                                     │
│  [📎 上传] [🎙 语音] [📚 知识库]  [▶] │
└─────────────────────────────────────┘
```
- 支持回车发送、文件上传（PDF/DOCX/DOC/PNG/JPG/JPEG）、语音输入、知识库选择
- 写作模式下占位符改为「输入修改意见...」

## 动画效果

- 按钮 hover：轻微放大 + 阴影
- 模式切换：淡入淡出过渡（transition）
- 内容生成：打字机动画 / 流式渲染
- 侧边栏折叠/展开：平滑滑动（300ms）

## 颜色规范

- 主色：`#2563eb`（科技蓝）
- 背景：`#ffffff`（主区域）、`#f7f8fa`（次要区域）
- 文字：`#1a1a2e`（主文本）、`#666`（次要文本）
- 边框：`#eaedf0`
- 用户消息气泡：`#2563eb` 背景 + 白色文字
- AI 消息：`#ffffff` 背景 + `#e8ecf0` 边框

## 复用的后端 API

不新增后端接口，复用现有：

| 接口 | 用途 |
|------|------|
| `GET /lesson-plan/latest` | 加载最近教案 |
| `POST /lesson-plan/generate` | 生成教案（SSE） |
| `POST /lesson-plan/modify` | 修改教案（SSE） |
| `PATCH /lesson-plan/{id}` | 自动保存 |
| `POST /lesson-plan/upload` | 上传参考文件 |
| `POST /lesson-plan/export/docx` | 导出 Word |
| `GET /libraries?scope=personal\|system` | 知识库列表 |

## 删除的旧组件

- `views/LessonPrepLessonPlan.vue`
- `components/lesson-plan/LessonPlanChat.vue`
- `components/lesson-plan/LessonPlanEditor.vue`
- `components/lesson-plan/LessonPlanTOC.vue`

## 视觉原型

参见 `docs/mockup-lesson-plan.html`

## 与全局导航的关系

教案生成页面嵌套在 `LayoutWithNav.vue` 的全局导航中。全局导航侧边栏（200px / 64px 折叠）与教案页面的历史边栏（240px）是独立的两层：
- 全局导航始终存在（由 LayoutWithNav 管理）
- 教案历史边栏在全局导航右侧，属于页面内部的布局
- 写作模式的 40%/60% 分割基于「全局导航右侧剩余空间」计算
- 在写作模式中，如果全局导航也可折叠，建议用户折叠全局导航以获得更大编辑空间，但不强制

## LessonPrep.vue 更新

`LessonPrep.vue` 的 `currentComponent` 映射表中 `'lesson-plan'` 键需从 `LessonPrepLessonPlan` 改为 `LessonPlanPage`。`keep-alive` 保留但需在 `LessonPlanPage` 的 `onDeactivated` 中销毁 Tiptap editor 实例以避免内存泄漏，`onActivated` 中重新初始化。

## 历史边栏 Mock 数据

```javascript
const mockHistory = [
  { id: 1, title: '小学数学分数教案', time: '今天 14:30', preview: '三年级分数的初步认识...' },
  { id: 2, title: '高中物理力学教案', time: '昨天 09:15', preview: '牛顿第二定律应用...' },
  { id: 3, title: '初中英语阅读课', time: '3月12日', preview: 'Reading comprehension...' },
  { id: 4, title: '七年级生物细胞结构', time: '3月10日', preview: '动物细胞与植物细胞...' },
]
```

点击行为：仅高亮选中项，不触发数据加载（UI 壳，后续对接后端后实现真实加载）。

## 错误处理

- SSE 流失败：在对话流中显示错误提示消息
- 修改失败：恢复编辑器之前的内容（备份 + 回滚）
- 自动保存失败：显示非阻塞 toast 提示「保存失败，请稍后重试」
- 文件上传失败：输入框上方显示错误提示

## Z-index 层级

- 历史边栏悬浮层（写作模式展开时）：`z-index: 100`
- 浮动格式工具栏：`z-index: 50`
- 浮动 TOC：`z-index: 40`
- 边栏展开按钮：`z-index: 30`

## 动画时长

- 模式切换（淡入淡出）：300ms
- 侧边栏折叠/展开：300ms
- 按钮 hover：200ms
