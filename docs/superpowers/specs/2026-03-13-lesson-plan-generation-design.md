# Lesson Plan Generation (教案生成) - Design Spec

## Overview

在现有 LessonPrep 页面新增"教案"tab（第2个，位于 PPT 和动画之间），实现类似豆包"帮我写作"的分栏式教案生成与编辑体验。

核心交互：左侧 1/3 AI 对话面板 + 右侧 2/3 Tiptap 富文本编辑器 + 可收起目录导航。

## 数据模型

所有业务数据必须持久化到 PostgreSQL，不必要不采用前端本地存储方案。

### 新增模型

**LessonPlan（教案表）**

```python
class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id    = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)  # 关联 ChatHistory
    title         = Column(String(255), nullable=False, default="未命名教案")
    content       = Column(Text, nullable=False, default="")                              # Markdown 全文
    status        = Column(String(20), nullable=False, default="draft")                   # draft / generating / completed
    created_at    = Column(DateTime(timezone=True), default=now_utc)
    updated_at    = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
```

**LessonPlanReference（教案参考文件表）**

```python
class LessonPlanReference(Base):
    __tablename__ = "lesson_plan_references"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    user_id        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_plan_id = Column(Integer, ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    filename       = Column(String(255), nullable=False)
    file_path      = Column(String(500), nullable=False)       # 磁盘存储路径
    parsed_content = Column(Text, nullable=False, default="")  # 解析后的纯文本
    created_at     = Column(DateTime(timezone=True), default=now_utc)
```

### 复用模型

**ChatHistory（已有）** — 通过 `session_id` 关联到 `LessonPlan.session_id`，存储教案对话的完整历史（包括 AI 真实回复内容，不是固定文案）。

### 数据生命周期

1. 用户首次发送消息时 -> 创建 `LessonPlan` 记录（status=draft, session_id=新 UUID）
2. 每条用户消息和 AI 回复 -> 写入 `ChatHistory`（role=user/assistant, session_id 关联）
3. AI 生成完毕 -> 更新 `LessonPlan.content`（完整 Markdown）、`LessonPlan.status=completed`
4. 用户手动编辑 -> 前端定时/失焦时调用 `PATCH /lesson-plan/{id}` 保存最新内容
5. 上传参考文件 -> 文件存磁盘，解析文本存 `LessonPlanReference.parsed_content`
6. 用户再次进入教案 tab -> 从数据库加载最近的教案和对话历史

## 技术选型

- **富文本编辑器**: Tiptap（Vue 3 原生支持，稳定可靠）
  - 通过 FloatingMenu / BubbleMenu / Placeholder 等扩展实现类 Notion 块级体验
  - 不选 BlockNote，原因：Vue 适配器不够成熟，竞赛项目稳定性优先
- **Markdown 解析**: markdown-it + markdown-it-task-lists（流式渲染预览层，支持任务列表语法）
- **Markdown 序列化**: tiptap-markdown（从 Tiptap 编辑器导出 Markdown，用于发送给 AI 和导出）
- **DOCX 导出**: pypandoc（后端转换；应用启动时检测 Pandoc 是否可用，不可用则调用 `pypandoc.download_pandoc()` 自动安装）
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
- FloatingMenu（空行弹出块类型选择菜单：标题、列表、表格等 — 实现类 Notion "+" 菜单）
- BubbleMenu（选中文字弹出格式工具栏：加粗、斜体、高亮等 — 实现类 Notion 内联格式栏）

可选扩展：
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
- 使用 Intersection Observer 观察编辑器中的各级标题元素，动态更新 `activeHeadingIndex` 实现当前标题高亮
- 流式生成期间 TOC 暂停更新（预览层不经过 Tiptap，无法提取标题节点），生成完毕后一次性刷新

### Tab 切换与 Tiptap 生命周期

Tiptap 的 ProseMirror EditorView 在 DOM 被 keep-alive 移出时可能出现异常。处理策略：
- `onDeactivated`: abort 当前 SSE 请求、销毁编辑器实例
- `onActivated`: 从数据库重新加载教案内容和对话历史，重建编辑器实例
- 数据安全：所有状态都在数据库中，切 tab 不会丢失任何内容

### 对话历史管理

- 对话历史持久化到数据库，复用现有 `ChatHistory` 模型（session_id 关联到 LessonPlan）
- 每条用户消息和 AI 真实回复内容都写入 `ChatHistory`（不是固定文案）
- AI 回复内容：流式生成时累积完整回复文本，生成完毕后写入数据库
- 前端加载时通过 `GET /lesson-plan/{id}/history` 从数据库读取历史消息
- 每次发送修改请求时，带上最近 10 条对话历史（从数据库读取，避免 token 过长）
- 切换 tab 后前端组件状态可丢失，因为数据在数据库中持久化，重新进入时重新加载

### 错误处理与取消

- **取消请求**: 使用 AbortController（与现有 LessonPrepAnimation 一致），在 `onDeactivated`（keep-alive 切 tab）和 `onBeforeUnmount`（组件销毁）时 abort 当前 SSE 连接
- **SSE 错误检查**: 前端在读取 SSE 流前必须先检查 `res.ok`，非 200 响应直接抛错；SSE 事件中的 error 字段必须正确冒泡到调用方
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

所有教案相关端点均需 JWT 认证（使用 CurrentUser 依赖注入，与 chat.py 保持一致），无一例外。

### 1. 教案生成（初次，LangGraph 检索 + 流式生成）

```
POST /api/v1/lesson-plan/generate (SSE streaming, 需认证)

Request Body:
{
  "query": "帮我生成一份高一数学函数与方程的教案",
  "library_ids": ["lib_1", "lib_2"],
  "file_ids": ["file_1"],
  "session_id": "xxx"         // 可选，不传则自动创建
}

Response: SSE stream
data: {"content": "# 函数与方程 -- 教案\n\n"}
data: {"content": "## 课程导入\n"}
...
data: [DONE]
```

后端流程：
1. 创建 `LessonPlan` 记录（status=generating）
2. 将用户消息写入 `ChatHistory`
3. **检索阶段**（不流式）: 通过 library_ids 调用 RAG 检索知识库、通过 file_ids 从 `LessonPlanReference.parsed_content` 读取文件文本、可选搜索网络
4. **生成阶段**（流式）: 拼接 prompt + 上下文 -> LLM astream() -> 逐 token SSE 返回
5. 生成完毕后将完整 Markdown 写入 `LessonPlan.content`（status=completed）
6. 将 AI 完整回复写入 `ChatHistory`

注意：AI 的 system prompt 应包含指令——若用户描述的教学需求信息不足（如缺少年级、学科、课题等），AI 应主动提问澄清而非直接生成，以对齐赛题"主动澄清需求并总结确认"的评分要求。

### 2. 教案修改（迭代，轻量直连 LLM）

```
POST /api/v1/lesson-plan/modify (SSE streaming, 需认证)

Request Body:
{
  "lesson_plan_id": 1,
  "instruction": "把教学目标改成三维目标的形式",
  "current_content": "当前编辑器的完整markdown",
  "file_ids": ["file_1"],
  "library_ids": ["lib_1"]
}

Response: SSE stream（同上格式，返回修改后的完整markdown）
```

后端流程：
1. 将用户修改指令写入 `ChatHistory`
2. 从数据库读取最近 10 条对话历史
3. 通过 file_ids 从 `LessonPlanReference.parsed_content` 读取参考文本
4. 通过 library_ids 做轻量向量检索
5. 拼接 prompt -> LLM astream() 流式返回
6. 生成完毕后更新 `LessonPlan.content`
7. 将 AI 完整回复写入 `ChatHistory`

### 3. 文件上传（持久化到数据库 + 磁盘）

```
POST /api/v1/lesson-plan/upload (需认证)

Request: FormData (file, lesson_plan_id)
Response: {"file_id": 1, "filename": "参考教案.pdf"}
```

后端流程：
1. 将文件保存到磁盘（`uploads/lesson_plan/` 目录）
2. 调用现有 parsers factory 解析文件，提取纯文本
3. 创建 `LessonPlanReference` 记录：file_path, parsed_content, user_id, lesson_plan_id
4. 返回 file_id（数据库自增 ID）

支持格式对齐后端解析器能力：PDF, DOCX, PNG, JPG（不含 PPTX — 解析器不支持，避免降级为二进制转文本）。

### 4. 教案内容保存

```
PATCH /api/v1/lesson-plan/{id} (需认证)

Request Body:
{
  "content": "更新后的完整markdown",
  "title": "函数与方程教案"       // 可选
}

Response: {"id": 1, "updated_at": "..."}
```

用于用户手动编辑后保存。前端在编辑器失焦或定时（如 30 秒）时自动调用。

### 5. 加载教案和历史

```
GET /api/v1/lesson-plan/latest (需认证)

Response: {
  "lesson_plan": {"id": 1, "session_id": "...", "title": "...", "content": "...", "status": "..."},
  "messages": [{"role": "user", "content": "..."}, ...],
  "files": [{"id": 1, "filename": "参考教案.pdf"}, ...]
}
```

用户进入教案 tab 时调用，加载最近一份教案及其关联的对话历史和参考文件。

### 6. 导出下载（仅 DOCX 需要后端，需认证）

```
POST /api/v1/lesson-plan/export/docx (需认证)

Request Body:
{
  "content": "完整markdown",
  "title": "教案标题"
}

Response: 文件流 (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
```

后端使用 pypandoc.convert_text() 转换。启动时自动检测 Pandoc 是否安装，未安装则调用 `pypandoc.download_pandoc()` 自动下载。

MD 和 PDF 在前端处理：
- MD: 通过 tiptap-markdown 获取 Markdown，Blob 下载
- PDF: html2pdf.js 从编辑器 DOM 生成

## 数据流

### 流程零：进入教案 Tab

```
前端: GET /lesson-plan/latest
  |
  v
后端: 查询用户最近一份 LessonPlan + 关联 ChatHistory + LessonPlanReference
  |
  v
前端:
  有教案 -> 加载到编辑器 + 恢复对话历史 + 恢复文件标签
  无教案 -> 显示引导界面
```

### 流程一：初次生成教案

```
用户输入描述 + 选择知识库 + 上传文件
  |
  v
POST /lesson-plan/generate (SSE)
  |
  v
后端:
  1. 创建 LessonPlan (status=generating)
  2. 写入 ChatHistory (role=user)
  3. 检索阶段: RAG + 读取 LessonPlanReference.parsed_content
  4. 生成阶段: LLM astream() -> 逐 token 返回 SSE
  5. 完毕: 更新 LessonPlan.content, 写入 ChatHistory (role=assistant)
  |
  v
前端:
  1. 左侧对话区显示用户消息 + AI 流式回复气泡
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
  |
  v
后端:
  1. 写入 ChatHistory (role=user)
  2. 从 DB 读取最近 10 条对话历史
  3. 检索参考资料 (file_ids + library_ids)
  4. LLM astream() -> 流式返回
  5. 完毕: 更新 LessonPlan.content, 写入 ChatHistory (role=assistant)
  |
  v
前端:
  1. 左侧 AI 气泡流式显示真实回复内容
  2. 右侧预览层覆盖，流式渲染新内容
  3. 收到 [DONE] -> setContent 替换 -> 恢复可编辑
```

### 流程三：用户手动编辑

```
用户直接在 Tiptap 编辑器中修改
  -> 编辑器 update 事件 -> 更新 TOC
  -> 失焦或定时 30s -> PATCH /lesson-plan/{id} 保存到数据库
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
- **迭代修改**: 走轻量流式端点，从数据库读取对话历史和参考资料，直接流式返回。保证修改响应速度。
- **主动澄清**: system prompt 中加入指令——若用户输入的教学需求信息不足（缺少年级、学科、课题、教学目标等关键信息），AI 应先提出澄清问题，而非直接生成不完整的教案。这对齐赛题"通过多轮对话理解教学意图"和"主动澄清需求"的评分要求。前端不需要特殊处理，AI 的澄清回复和正常回复走同一条对话通道。

## 前置修复

现有 LangGraph 工作流中 `should_retry` 函数（nodes.py）返回 `"end"` 但 workflow 的条件边映射只有 `{"agent", "outline_approval"}`，会导致运行时错误。此 bug 需在实现本功能前修复。

## 依赖新增

### 前端 (teacher-platform/)
- `@tiptap/vue-3` + `@tiptap/starter-kit` + 各扩展包（Table, TaskList, Highlight, TextAlign, Underline, Placeholder, FloatingMenu, BubbleMenu, CharacterCount）
- `tiptap-markdown`（Tiptap <-> Markdown 双向转换）
- `markdown-it` + `markdown-it-task-lists`（流式预览层 Markdown 渲染）
- `html2pdf.js`（前端 PDF 导出）

### 后端 (backend/)
- `pypandoc`（Markdown -> DOCX 转换，启动时自动下载 Pandoc）
- 新增数据库迁移：`lesson_plans` 表、`lesson_plan_references` 表
