# Lesson Plan Generation (教案生成) - Design Spec

## Overview

在现有 LessonPrep 页面新增"教案"tab（第2个，位于 PPT 和动画之间），实现类似豆包"帮我写作"的分栏式教案生成与编辑体验。

核心交互：左侧 1/3 AI 对话面板 + 右侧 2/3 Tiptap 富文本编辑器 + 可收起目录导航。

## 技术选型

- **富文本编辑器**: Tiptap（Vue 3 原生支持，稳定可靠）
  - 通过 FloatingMenu / BubbleMenu / Placeholder 等扩展实现类 Notion 块级体验
  - 不选 BlockNote，原因：Vue 适配器不够成熟，竞赛项目稳定性优先
- **Markdown 解析**: markdown-it + markdown-it-task-lists（流式渲染预览层，支持任务列表语法）
- **Markdown 序列化**: tiptap-markdown（从 Tiptap 编辑器导出 Markdown，用于发送给 AI 和导出）
- **DOCX 导出**: pypandoc（后端，一行转换；首次运行时通过 pypandoc.download_pandoc() 自动安装 Pandoc）
- **PDF 导出**: html2pdf.js（前端，从编辑器 DOM 直接生成）
- **MD 导出**: 前端纯文本 Blob 下载

## 前端设计

### 页面布局

```
+-----------------------------------------------------+
|                LessonPrepLessonPlan                  |
|                                                     |
|  +-----+  +------------+  +----------------------+ |
|  | TOC |  | Chat Panel |  |   Tiptap Editor      | |
|  |     |  |            |  |                      | |
|  |可收起|  | 左侧 1/3   |  |  右侧 2/3            | |
|  |     |  |            |  |                      | |
|  |目录  |  | 对话+输入   |  |  富文本编辑区         | |
|  |导航  |  | 文件上传    |  |  + 顶部工具栏         | |
|  |     |  | 知识库选择   |  |  (全屏/复制/下载)     | |
|  +-----+  +------------+  +----------------------+ |
+-----------------------------------------------------+
```

- 初始态：无教案内容，显示引导界面，提示用户描述教学需求
- 生成中：左侧对话显示 AI 消息，右侧预览层流式渲染 Markdown
- 编辑态：左侧可继续对话修改，右侧可自由编辑，TOC 显示文档目录

### 组件拆分

```
LessonPrepLessonPlan.vue        # 主容器，管理三栏布局和全局状态
+-- LessonPlanChat.vue           # 左侧对话面板
|   +-- 消息列表（用户/AI气泡）
|   +-- 知识库多选下拉（分组：用户级 + 系统级）
|   +-- 文件上传按钮
|   +-- 文本输入 + 语音输入
|   +-- 发送按钮
+-- LessonPlanEditor.vue         # 右侧编辑器面板
|   +-- 顶部工具栏（全屏/复制/下载 MD/DOCX/PDF）
|   +-- Tiptap 编辑器实例
+-- LessonPlanTOC.vue            # 左侧目录导航（可收起）
    +-- 从编辑器标题节点提取目录
    +-- 点击跳转到对应位置
```

### 路由集成

在 LessonPrep.vue 的 tabs 数组中插入新 tab：

```
tabs: [ppt, lesson-plan, animation, knowledge, data]
```

通过 `?tab=lesson-plan` query 参数切换，组件为 `LessonPrepLessonPlan.vue`。

### Tiptap 扩展配置

必装扩展：
- StarterKit（段落、标题、列表、粗体、斜体等）
- Placeholder（空块占位提示）
- Heading (h1-h3)
- Table / TableRow / TableCell / TableHeader
- TaskList + TaskItem（知识点清单勾选列表）
- Highlight（重点标记）
- TextAlign
- Underline

可选扩展（提升体验）：
- FloatingMenu（空行弹出块类型选择菜单）
- BubbleMenu（选中文字弹出格式工具栏）
- CharacterCount（字数统计）

### 知识库选择交互

分组列表下拉面板（非模态弹窗）：

```
+-------------------------+
| [folder] 我的知识库      |  <-- 分组标题
|  [x] 高中数学必修一      |
|  [ ] 物理力学专题        |
|--- --- --- --- --- --- --|  <-- 分隔线
| [globe] 公开知识库       |  <-- 分组标题
|  [ ] 高中数学课标        |
|  [x] 新课标教学指南      |
+-------------------------+
```

- 选中的知识库以标签形式显示在输入框上方
- 蓝色标签 = 用户知识库，绿色标签 = 系统知识库
- 标签可单个移除

### 对话面板布局

```
+----------------------+
| 消息列表（可滚动）     |
| +-- 用户气泡 -------+ |
| | 帮我生成一份...    | |
| +-------------------+ |
| +-- AI气泡 ---------+ |
| | 正在为您生成...    | |
| +-------------------+ |
|                       |
+-----------------------+
| 已上传文件标签（可删除）|
| 已选知识库标签（可删除）|
+-----------------------+
| +-------------------+ |
| | 输入框 (textarea) | |
| +-------------------+ |
| [上传] [知识库] [语音] [发送] |
+----------------------+
```

消息气泡样式沿用现有项目风格（与动画/数据 tab 一致）：
- 用户消息：右对齐，浅蓝背景 #E0EDFE
- AI 消息：左对齐，白色背景

### 流式渲染策略

SSE 事件格式（与现有 html_chat 保持一致）：
- token 事件: `data: {"content": "..."}`
- 完成事件: `data: [DONE]`

生成中（SSE 流式接收）：
1. `editor.setEditable(false)` 锁定编辑器
2. 编辑器上方覆盖 Markdown 预览层（v-html 渲染，markdown-it + markdown-it-task-lists 解析）
3. SSE chunk 累积到 markdown buffer，实时渲染到预览层

生成完毕（收到 `[DONE]`）：
1. 拿完整 Markdown，用 tiptap-markdown 的 setContent 写入 Tiptap（tiptap-markdown 扩展直接支持 Markdown 输入，无需手动转 HTML）
2. 移除预览层
3. `editor.setEditable(true)` 恢复可编辑

修改时的更新策略：AI 返回修改后的完整 Markdown，前端整体 setContent 替换。教案文档体量不大（几千字），整体替换性能无问题。

### Tiptap 内容序列化（编辑器 -> Markdown）

使用 `tiptap-markdown` 扩展，双向支持：
- **写入**: `editor.commands.setContent(markdown)` 直接接受 Markdown
- **读取**: `editor.storage.markdown.getMarkdown()` 导出 Markdown
- 用于：发送修改请求时获取 current_content、MD 导出、DOCX 导出

### TOC 目录生成

- 监听 Tiptap 的 `update` 事件
- 遍历文档 JSON，提取所有 heading 节点的文本和层级
- 渲染为目录列表，点击时 scrollIntoView 跳转
- Intersection Observer 高亮当前视口内的标题
- 流式生成期间 TOC 暂停更新（预览层不经过 Tiptap，无法提取标题节点），生成完毕后一次性刷新

### Tab 切换与 Tiptap 生命周期

Tiptap 的 ProseMirror EditorView 在 DOM 被 keep-alive 移出时可能出现异常。处理策略：
- `onDeactivated`: 将编辑器内容（Markdown）保存到响应式变量，销毁编辑器实例
- `onActivated`: 用保存的 Markdown 重建编辑器实例
- 对话历史（messages 数组）保存在响应式状态中，不受编辑器生命周期影响

### 对话历史管理

- 对话历史保存在组件状态中（messages 数组）
- 每次发送修改请求时，带上最近 10 条对话历史（避免 token 过长）
- 切换 tab 后对话历史通过响应式变量保留
- 不做服务端持久化

### 错误处理与取消

- **取消请求**: 使用 AbortController（与现有 LessonPrepAnimation 一致），用户发送新请求或切换 tab 时 abort 当前 SSE 连接
- **生成失败**: 若 SSE 中途断开或报错，恢复编辑器到生成前的状态（保存在临时变量中），预览层移除，显示错误提示
- **并发冲突**: 生成/修改进行中时，禁用发送按钮，防止重复请求

## 教案内容结构

AI 生成的教案以 Markdown 输出，包含以下模块：

```markdown
# {课程名称} -- 教案

## 课程导入
...

## 教学目标
...

## 知识点清单
- [ ] 知识点1
- [ ] 知识点2

## 教学方法
...

## 教学过程
| 环节 | 时间 | 内容 | 教师活动 | 学生活动 |
|------|------|------|---------|---------|
| ... | ... | ... | ... | ... |

## 课堂活动设计
...

## 板书设计
...

## 课后作业
...

## 教学反思
...

## 课时安排
...
```

## 后端 API 设计

所有教案相关端点均需 JWT 认证（使用 CurrentUser 依赖注入，与 chat.py 保持一致）。

### 1. 教案生成（初次，LangGraph 检索 + 流式生成）

```
POST /api/v1/lesson-plan/generate (SSE streaming, 需认证)

Request Body:
{
  "query": "帮我生成一份高一数学函数与方程的教案",
  "library_ids": ["lib_1", "lib_2"],
  "file_ids": ["file_1"],
  "session_id": "xxx"
}

Response: SSE stream
data: {"content": "# 函数与方程 -- 教案\n\n"}
data: {"content": "## 课程导入\n"}
...
data: [DONE]
```

流程（两阶段）：
1. **检索阶段**（不流式）: 调用 LangGraph 工作流中的 tools 能力 -- 检索知识库（library_ids）、解析上传文件（file_ids）、可选搜索网络 -- 收集参考资料上下文
2. **生成阶段**（流式）: 将检索到的上下文 + 教案模板 + 用户 query 拼接为 prompt，直接调用 LLM 的 astream() 方法，逐 token 流式返回 Markdown

注意：不使用 LangGraph 的 graph.astream()（它只流式返回节点完成事件，不返回 token），而是将 LangGraph 拆分为"检索"和"生成"两个独立步骤。

### 2. 教案修改（迭代，轻量直连 LLM）

```
POST /api/v1/lesson-plan/modify (SSE streaming, 需认证)

Request Body:
{
  "instruction": "把教学目标改成三维目标的形式",
  "current_content": "当前编辑器的完整markdown",
  "history": [...最近10条对话],
  "file_ids": ["file_1"],
  "library_ids": ["lib_1"],
  "session_id": "xxx"
}

Response: SSE stream（同上格式，返回修改后的完整markdown）
```

流程：通过 file_ids 捞已解析文本 + 通过 library_ids 做轻量向量检索（用 instruction 作为 query）-> 拼接 system prompt + 参考资料 + 当前教案 + 修改指令 -> LLM astream() 流式返回。

### 3. 文件上传

```
POST /api/v1/lesson-plan/upload

Request: FormData (file)
Response: {"file_id": "xxx", "filename": "参考教案.pdf"}
```

复用现有文件解析管线（parsers factory），提取文本内容存储供生成时引用。

### 4. 导出下载（仅 DOCX 需要后端）

```
POST /api/v1/lesson-plan/export/docx

Request Body:
{
  "content": "完整markdown",
  "title": "教案标题"
}

Response: 文件流 (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
```

后端使用 pypandoc.convert_text() 一行转换（首次调用时自动下载 Pandoc）。

MD 和 PDF 在前端处理：
- MD: 通过 tiptap-markdown 获取 Markdown，Blob 下载
- PDF: html2pdf.js 从编辑器 DOM 生成

## 数据流

### 流程一：初次生成教案

```
用户输入描述 + 选择知识库 + 上传文件
  |
  v
POST /lesson-plan/generate (SSE)
  |
  v
后端（两阶段）:
  阶段1 - 检索（不流式）:
    调用 RAG 检索知识库(library_ids)
    解析上传文件(file_ids) 提取文本
    可选: 搜索网络补充资料
    收集所有参考上下文
  阶段2 - 生成（流式）:
    拼接: system prompt + 教案模板 + 参考上下文 + 用户 query
    LLM astream() -> 逐 token 返回 SSE
  |
  v
前端:
  1. 左侧对话区显示 AI 气泡 "正在生成教案..."
  2. 右侧切换到预览层，流式渲染 Markdown
  3. 收到 [DONE] -> tiptap-markdown setContent -> 恢复可编辑
  4. TOC 从编辑器标题节点生成
```

### 流程二：对话迭代修改

```
用户在左侧输入修改指令
  |
  v
前端: 收集 current_content（编辑器当前 Markdown）
  |
  v
POST /lesson-plan/modify (SSE)
  body: { instruction, current_content, history, file_ids?, library_ids? }
  |
  v
后端: 拼接 prompt + 参考资料 + 当前教案 + 指令 -> 直连 LLM -> 流式返回
  |
  v
前端:
  1. 左侧 AI 气泡流式显示回复
  2. 右侧预览层覆盖，流式渲染新内容
  3. 收到 [DONE] -> setContent 替换 -> 恢复可编辑
```

### 流程三：用户手动编辑

```
用户直接在 Tiptap 编辑器中修改
  -> 编辑器 update 事件 -> 更新内部 markdown 状态 + 更新 TOC
  -> 无需调后端
```

### 流程四：导出下载

```
用户点击下载按钮 -> 选择格式
  +-- MD:   前端 Blob 下载
  +-- PDF:  前端 html2pdf.js
  +-- DOCX: POST /lesson-plan/export/docx -> pypandoc -> 文件流下载
```

## AI 生成策略（混合方案）

- **初次生成**: 两阶段流程 -- 先调用 RAG/工具检索知识库和解析文件（展示智能体能力，评分要点），再将检索上下文喂给 LLM 流式生成教案 Markdown。不使用完整 LangGraph graph.astream()（它只能流式返回节点事件，无法流式返回 token）。
- **迭代修改**: 走轻量流式端点，把编辑器当前内容 + 用户修改指令 + 对话历史 + 可选的参考资料发给 LLM，直接流式返回。保证修改响应速度。

## 前置修复

现有 LangGraph 工作流中 `should_retry` 函数（nodes.py）返回 `"end"` 但 workflow 的条件边映射只有 `{"agent", "outline_approval"}`，会导致运行时错误。此 bug 需在实现本功能前修复。

## 依赖新增

### 前端 (teacher-platform/)
- `@tiptap/vue-3` + `@tiptap/starter-kit` + 各扩展包（Table, TaskList, Highlight, TextAlign, Underline, Placeholder, FloatingMenu, BubbleMenu, CharacterCount）
- `tiptap-markdown`（Tiptap <-> Markdown 双向转换）
- `markdown-it` + `markdown-it-task-lists`（流式预览层 Markdown 渲染）
- `html2pdf.js`（前端 PDF 导出）

### 后端 (backend/)
- `pypandoc`（Markdown -> DOCX 转换，首次运行自动下载 Pandoc）
