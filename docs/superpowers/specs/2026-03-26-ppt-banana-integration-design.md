# PPT生成模块（banana-slides集成）设计文档

> [!WARNING]
> 本文档已被 `docs/superpowers/specs/2026-03-31-ppt-backend-design-v2.md` 取代。
> 
> 取代原因：
> - 旧文档包含与当前代码实现不一致的接口路径与能力描述。
> - 当前版本已按 `backend/app/generators/ppt` 实际实现重写基线，并补充了与 banana-slides 的能力差距和分阶段补齐路线。
> - 新需求（Description/Preview 高一致性、在线编辑闭环）以 V2 为准。

> **Date:** 2026-03-26
> **Status:** Draft
> **Author:** Claude

## 1. 概述

### 1.1 项目背景

AIsystem 教学智能体需要集成 banana-slides 作为 PPT 生成引擎。用户选定模板、输入主题后，智能体与用户多轮对话确定真实意图，生成初版大纲，再将大纲传入 banana-slides 的"从大纲生成"入口完成后续 PPT 生成流程。

### 1.2 集成目标

- 将 banana-slides 重构为 AIsystem 的 `app/generators/ppt/` 子模块
- Dialog 页（`creation_type="dialog"`）自研多轮意图澄清对话系统（PPTSession 持久化 + checkpoint 恢复），参考 lesson-plan LangGraph 模式，banana 内部映射为 `creation_type="idea"`
- 大纲解析（`parse_outline_text`）使用通义千问（DashScope）
- 页面描述和图片生成使用 banana-slides 原生 provider（Gemini/OpenAI 等）
- 支持用户与智能体对话持久化（PPTSession）

## 2. 架构设计

### 2.1 目录结构

```
backend/app/
├── generators/
│   └── ppt/                        # PPT生成子模块
│       ├── __init__.py
│       ├── banana_models.py         # SQLAlchemy 模型（PPTProject, PPTPage, PPTTask, etc.）
│       ├── banana_schemas.py        # Pydantic 请求/响应模型
│       ├── banana_routes.py         # FastAPI 路由
│       ├── banana_service.py        # AIService（去Flask依赖）
│       ├── banana_providers.py      # AI providers（text/image）
│       ├── prompts.py               # AI提示词（沿用banana-slides）
│       ├── task_manager.py          # Celery任务封装
│       ├── export_service.py         # 导出服务（PPTX/PDF）
│       ├── file_service.py          # 文件存储（OSS）
│       └── celery_tasks.py           # Celery Task定义
└── api/
    └── __init__.py                  # ⚠️ 路由聚合在 api/__init__.py，不是 api/v1/
```

> **注意**：当前仓库路由聚合在 `backend/app/api/__init__.py`，ppt 路由将添加到这个文件中，不是单独新建 `api/v1/ppt.py`。

### 2.2 技术栈

| 组件 | 技术 |
|------|------|
| 主框架 | FastAPI (AIsystem) |
| PPT生成引擎 | banana-slides（重构后） |
| 数据库 | PostgreSQL (AIsystem) |
| 文件存储 | 阿里云 OSS |
| 异步任务 | Celery (AIsystem) |
| 大纲生成LLM | 通义千问（DashScope） |
| 页面描述/图片生成LLM | banana-slides providers（Gemini/OpenAI等） |

### 2.3 数据流

```
┌──────────────────────────────────────────────────────────────┐
│  Dialog 层（自研）                                            │
│  用户对话澄清意图 → 生成结构化 outline → 写入 PPTProject      │
│  (PPTSession 持久化，支持断点恢复)                            │
└──────────────────────────────────────────────────────────────┘
    ↓ outline_text 确认
┌──────────────────────────────────────────────────────────────┐
│  Banana-slides 层（复用）                                      │
│  Outline 页（用户编辑大纲）                                    │
│      ↓ outline_text / outline_pages                           │
│  Description 页（generate_descriptions — banana provider）      │
│      ↓ description_content                                   │
│  Preview 页（generate_images — banana provider）               │
│      ↓ generated_image_path (OSS URL)                         │
│  导出（export_service — 4种格式 → OSS）                       │
└──────────────────────────────────────────────────────────────┘
```

## 3. 数据模型设计

### 3.1 复用AIsystem现有模型

**Courseware 表扩展**（在 `models/courseware.py` 中）：

> ⚠️ **重要**：仅在 Courseware 侧维护 `ppt_project_id` FK，PPTProject **不**持有 `courseware_id` FK，避免双向 FK 导致的写入一致性问题。

```python
class Courseware(Base):
    # ... 现有字段 ...
    ppt_project_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="SET NULL"), nullable=True, unique=True  # ⚠️ 1:1 关系，加 unique 约束
    )
    # ⚠️ 单向关系，不使用 back_populates（避免要求 PPTProject 维护反向 FK）
    ppt_project: Mapped[Optional["PPTProject"]] = relationship(
        "PPTProject", foreign_keys=[ppt_project_id]
    )
```

> **关系说明**：
> - `Courseware.ppt_project_id` 加 `unique=True`，确保业务上 1:1 约束
> - PPTProject **不**维护 `courseware_id` FK，关系由 Courseware 侧单向持有

### 3.2 新建模型（banana_models.py）

> ⚠️ 本节字段表与实际代码完全对应，**不是** banana-slides 原始字段。

**PPTProject** — PPT项目主表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| user_id | Integer FK | → users.id |
| title | String(255) | 项目名称 |
| description | Text | 项目描述 |
| creation_type | String(20) | 'dialog'/'file'/'renovation' |
| outline_text | Text | 用户确认的结构化大纲文本 |
| settings | JSONB | 项目配置（生成模式/详细程度等） |
| theme | String(50) | 主题/风格 |
| knowledge_library_ids | ARRAY(Integer) | 用户选择的知识库ID列表，Dialog生成时RAG检索用 |
| status | String(20) | 'PLANNING'/'GENERATING'/'COMPLETED'/'FAILED' |
| exported_file_url | String(500) | 最近一次导出的OSS URL |
| exported_at | DateTime | 导出时间 |
| created_at | DateTime |  |
| updated_at | DateTime |  |

**PPTPage** — PPT页面表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| project_id | Integer FK | → ppt_projects.id |
| page_number | Integer | 页面序号 |
| title | String(255) | 页面标题 |
| description | Text | AI生成的页面描述 |
| image_prompt | Text | 生图提示词 |
| notes | Text | 备注/演讲者笔记 |
| image_url | String(500) | 生成的图片OSS URL |
| image_version | Integer | 当前图片版本号 |
| config | JSONB | 页面配置（背景色/布局等） |
| description_mode | String(20) | 'auto'/'manual' |
| is_description_generating | Boolean | 描述是否生成中 |
| is_image_generating | Boolean | 图片是否生成中 |
| material_ids | ARRAY(Integer) | 关联的素材ID列表 |
| created_at | DateTime |  |
| updated_at | DateTime |  |

**PPTTask** — 异步任务表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| project_id | Integer FK | → ppt_projects.id |
| task_id | String(100) | Celery任务ID，唯一 |
| task_type | String(50) | 'generate_image'/'export_pptx'/'export_pdf'/'export_images'/'export_editable_pptx'/'renovation_parse'/'material_generate'/'edit_page_image' |
| status | String(20) | 'PENDING'/'PROCESSING'/'COMPLETED'/'FAILED' |
| progress | Integer | 进度0-100 |
| result | JSONB | 任务结果或错误信息 |
| page_id | Integer FK | → ppt_pages.id，nullable，关联特定页面 |
| created_at | DateTime |  |
| updated_at | DateTime |  |
| completed_at | DateTime | nullable |

**PPTMaterial** — 素材表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| user_id | Integer FK | → users.id |
| project_id | Integer FK | → ppt_projects.id，nullable |
| filename | String(255) | 文件名 |
| oss_path | String(500) | OSS存储路径 |
| url | String(500) | 访问URL |
| file_type | String(20) | 'pdf'/'pptx'/'ppt'/'docx'/'png'/'jpg'/'jpeg' |
| file_size | Integer | 文件大小（字节） |
| material_type | String(20) | 'reference'/'template'/'image'/'text' |
| is_parsed | Boolean | 是否已解析 |
| parsed_content | JSONB | 解析结果 |
| created_at | DateTime |  |

**PPTReferenceFile** — 参考文件表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| project_id | Integer FK | → ppt_projects.id |
| user_id | Integer FK | → users.id |
| filename | String(255) | 文件名 |
| oss_path | String(500) | OSS存储路径 |
| url | String(500) | 访问URL |
| file_type | String(20) | 'pdf'/'pptx'/'ppt'/'docx' |
| file_size | Integer | 文件大小 |
| parse_status | String(20) | 'pending'/'processing'/'completed'/'failed' |
| parse_error | Text | 解析错误信息 |
| parsed_outline | JSONB | 从文件解析出的大纲结构 |
| created_at | DateTime |  |

**PPTSession** — 对话会话表（Dialog持久化）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| project_id | Integer FK | → ppt_projects.id |
| user_id | Integer FK | → users.id |
| role | String(20) | 'user'/'assistant' |
| content | Text | 对话内容 |
| metadata | JSONB | 附加数据（如追问选项等） |
| round | Integer | 对话轮次 |
| created_at | DateTime |  |

> PPTSession 中同一 project_id 的所有记录构成完整对话历史，按 round 和 created_at 排序。

**UserTemplate** — 用户自定义模板表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| user_id | Integer FK | → users.id |
| name | String(100) | 模板名称 |
| description | Text | 模板描述 |
| template_data | JSONB | 模板数据（页面结构/主题配置） |
| cover_url | String(500) | 封面图URL |
| source | String(20) | 'user'/'system'（预置模板可复制） |
| usage_count | Integer | 使用次数 |
| created_at | DateTime |  |
| updated_at | DateTime |  |

> UserTemplate 是用户级资产，通过 user_id 挂在 User 下，不属于任何 Project。

**PageImageVersion** — 页面图片版本表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| page_id | Integer FK | → ppt_pages.id |
| user_id | Integer FK | → users.id |
| version | Integer | 版本号 |
| image_url | String(500) | 图片OSS URL |
| operation | String(20) | 'generate'/'edit' |
| prompt | Text | 自然语言编辑提示词（仅edit类型有） |
| is_active | Boolean | 是否当前活跃版本 |
| created_at | DateTime |  |

### 3.3 表关联

```
User
  └── PPTProject[] ── 1:0..n ──→ PPTPage[]
                            ├── PPTTask[]
                            ├── PPTMaterial[]
                            ├── PPTReferenceFile[]
                            └── PPTSession[]

  └── Courseware ── ppt_project_id (unique, 1:1) ──→ PPTProject

UserTemplate: 用户级资产，独立于Project存在，通过 user_id 挂在 User 下
```

> **关系说明**：
> - `User.ppt_projects` 通过 back_populates 持有对 `PPTProject` 的引用（一对多）
> - `PPTProject.pages` cascade="all, delete-orphan"，删除项目时自动删除所有页面
> - `Courseware.ppt_project_id` 加 `unique=True`，确保业务上 1:1 约束，PPTProject **不**维护反向 FK
> - `PPTSession` 通过 `project_id` 挂在 `PPTProject` 下，记录该PPT项目的教学智能体对话历史

## 4. API路由设计

### 4.1 路由挂载

所有路由挂载在 `/api/v1/ppt/` 前缀下。

> **注意**：由 `app.main` 统一加 `/api/v1` 前缀（main.py:46），`banana_routes` 自身的 prefix 仅 `/ppt`，最终组合为 `/api/v1/ppt/`。

> **前端集成说明**：前端适配细节参见 `docs/superpowers/specs/2026-03-28-ppt-banana-frontend-adaptation.md`，gap analysis 参见该文档 Section 15。

### 4.2 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/projects` | 创建PPT项目 |
| GET | `/projects` | 列出当前用户的项目 |
| GET | `/projects/{id}` | 获取项目详情 |
| PUT | `/projects/{id}` | 更新项目 |
| DELETE | `/projects/{id}` | 删除项目 |
| PUT | `/projects/{id}/settings` | 更新项目设置（横竖版/导出方式） |
| POST | `/projects/{id}/outline/generate` | 解析大纲（通义千问） |
| POST | `/projects/{id}/outline/generate/stream` | 流式解析大纲（SSE），请求体：`{"idea_prompt"?: string, "language"?: "zh"\|"en"\|"ja"\|"auto"}` |
| POST | `/projects/{id}/descriptions/generate` | 批量生成页面描述 |
| POST | `/projects/{id}/descriptions/generate/stream` | 流式生成页面描述（SSE），请求体：`{"language"?: "zh"\|"en"\|"ja"\|"auto", "detail_level"?: "concise"\|"default"\|"detailed"}` |
| POST | `/projects/{id}/refine/outline` | 自然语言修改大纲（banana-slides原生） |
| POST | `/projects/{id}/refine/descriptions` | 自然语言批量修改页面描述（banana-slides原生） |
| POST | `/projects/{id}/pages/{page_id}/edit/image` | 单页图片自然语言编辑（Preview页，异步），请求体：`{"edit_instruction": string, "context_images"?: {"use_template": boolean, "desc_image_urls": string[], "uploaded_image_ids": string[]}}`（支持JSON或multipart/form-data） |
| PUT | `/projects/{id}/pages/{page_id}` | 更新页面 |
| POST | `/projects/{id}/pages/reorder` | 批量重排序页面 |
| POST | `/projects/{id}/images/generate` | 批量生成页面图片 |
| GET | `/projects/{id}/export/pptx` | 导出PPTX（图片版，同步） |
| GET | `/projects/{id}/export/pdf` | 导出PDF（同步） |
| GET | `/projects/{id}/export/images` | 导出图片/ZIP（同步） |
| POST | `/projects/{id}/export/editable-pptx` | 导出可编辑PPTX（异步，返回 task_id） |
| GET | `/projects/{id}/export-tasks` | 获取导出任务列表 |
| GET | `/export-tasks/{task_id}` | 获取单个导出任务状态 |
| POST | `/projects/{id}/materials/upload` | 上传素材 |
| GET | `/projects/{id}/materials` | 获取素材列表 |
| DELETE | `/projects/{id}/materials/{material_id}` | 删除素材 |
| POST | `/projects/{id}/reference-files` | 上传参考文件 |
| POST | `/projects/{id}/reference-files/{file_id}/parse` | 解析参考文件 |
| POST | `/projects/{id}/reference-files/{file_id}/confirm` | 确认参考文件 |
| GET | `/projects/{id}/tasks` | 获取项目任务列表 |
| GET | `/projects/{id}/tasks/{task_id}` | 获取任务状态 |
| POST | `/projects/{id}/chat` | 发送对话消息 |
| GET | `/projects/{id}/sessions` | 获取项目对话历史 |
| POST | `/projects/{id}/sessions` | 写入对话消息 |
| POST | `/projects/{id}/dialog/generate-outline` | Dialog页确认后，从对话历史生成结构化outline（自研） |
| GET | `/templates/presets` | 获取预设模板列表 |
| GET | `/templates/user` | 获取用户模板列表 |

### 4.3 认证

所有接口使用 AIsystem 现有的 JWT Bearer Token 认证。banana-slides 原生的 `ACCESS_CODE` 认证废弃。

### 4.4 事务风格

**沿用 AIsystem 现有代码风格**（显式 `await db.commit()`），与 `courseware.py` 等现有路由保持一致。`get_db` 依赖在 yield 结束后自动 commit，新模块不使用隐式提交。

## 5. AI服务设计

### 5.1 大纲解析（通义千问）

**服务**：`generators/ppt/banana_service.py`

**方法**：`parse_outline_text(project_context, language='zh')`

- 复用 AIsystem 现有 `DashScopeService.chat()`（`services/ai/dashscope_service.py:199`）
- **不**使用 `generate_text_stream`（该方法不存在），如需流式解析，需先新建统一的流式适配层
- 提示词沿用 banana-slides 的 `get_outline_parsing_prompt_markdown()`，通过 `DashScopeService.chat()` 非流式调用获取 JSON 结构化大纲

> **注意**：banana 原实现中 `parse_outline_text` 走 JSON 解析路径（同步），`generate_outline_stream` 走 Markdown 流式路径。接入 DashScope 时优先保持 JSON 同步路径，后续如需 SSE 流式返回再扩展流式适配层。

**creation_type 映射（AIsystem → banana 内部）**：

| AIsystem creation_type | banana 内部值 | 行为 |
|---|---|---|
| `dialog` | `idea` | 用户输入想法，AI 生成大纲 |
| `file` | `outline` | 用户输入大纲文本，AI 解析为结构化大纲 |
| `renovation` | `ppt_renovation` | 上传旧 PPT/PDF，AI 解析并翻新 |

> 映射发生在 `banana_service.py` 或 `banana_routes.py` 层，banana prompts.py 仍使用内部值。

**容错与重试规则**：
- LLM 返回内容可能包含 markdown 代码块（如 \`\`\`json...），需先清洗再解析
- 解析失败时（`json.JSONDecodeError`），最多重试 2 次，每次更换 prompt 措辞
- 重试仍失败时，返回原始文本供人工处理，不中断流程

### 5.2 页面描述生成（banana-slides原生）

**服务**：`generators/ppt/banana_providers.py`

- 封装 Gemini/OpenAI/Anthropic 等 provider
- 复用 banana-slides 的 `generate_descriptions_stream()` 流式生成
- AI Provider 配置存储在 banana-slides 的 `Settings` 表（或迁移到 AIsystem 的 config）

**自然语言修改接口（banana-slides原生）**：

| 接口 | 功能 | 位置 |
|---|---|---|
| `POST /projects/{id}/refine/outline` | 用户在 Outline 页输入自然语言指令，AI 批量修改大纲结构（添加/删除/重排页面、修改标题和要点） | Outline 页 |
| `POST /projects/{id}/refine/descriptions` | 用户在 Description 页输入自然语言指令（如"让描述更详细"），AI 批量修改所有页面描述内容 | Description 页 |
| `POST /projects/{id}/pages/{page_id}/edit/image` | 用户在 Preview 页点击"编辑"按钮，输入自然语言指令（如"把背景改成蓝色"），AI 基于当前图片重新生成，支持传入上下文图片（模板/描述图片/上传图片） | Preview 页 |

第三个接口（单页图片编辑）是异步任务（返回 `task_id`），使用 `edit_page_image_task`，编辑前自动保存当前版本到 `PageImageVersion`。前端在 Preview 页提供编辑弹窗（`editPrompt` 输入框 + 上下文图片选项），用户可选择"仅保存大纲/描述"或"生成图片"。

这两个接口由 banana-slides 的 `ai_service.refine_outline()` 和 `ai_service.refine_descriptions()` 实现，前端使用 `AiRefineInput` 组件（带历史记录和 Ctrl+Enter 快捷键）。**与 Dialog 自研系统的分工**：Dialog 系统负责生成初版 outline；refine 接口负责在 Outline/Description/Preview 阶段按用户指令修改已有内容。

### 5.3 图片生成

**服务**：`generators/ppt/banana_providers.py` (ImageProvider)

- 复用 banana-slides 的 `ImageProvider` 体系
- 支持 Gemini/OpenAI/Anthropic 等图片生成模型

### 5.4 Dialog 自研系统（多轮意图澄清）

> **重要说明**：`creation_type="dialog"` 的 Dialog 页是 AIsystem **自研**的功能，不在 banana-slides 原生代码中。banana-slides 只有单次 `generate_outline()` 调用，没有多轮对话澄清意图的机制。

#### 5.4.1 定位与分工

| 层 | 负责 | 技术 |
|---|---|---|
| **Dialog 层**（自研） | 多轮对话澄清意图，生成结构化 outline | DashScope（或任意LLM）+ PPTSession 持久化 |
| **Banana-slides 层** | 接收 outline，后续生成描述/图片/导出 | 迁移 banana-slides 的 service |

**关键约束**：Dialog 页生成结构化 outline 后，直接存入 `PPTProject.outline_text`（或解析为 `PPTPage[]`），**不需要**调用 banana-slides 的 `generate_outline` API，避免重复生成。

#### 5.4.2 Dialog → Banana-slides 完整流程

```
用户选择 creation_type="dialog"
       ↓
Home 页（选择模板 + 输入主题/想法）
       ↓ 创建 PPTProject
Dialog 页（多轮 AI 对话澄清意图）
  - 用户消息存入 PPTSession（role='user'）
  - AI 回复存入 PPTSession（role='assistant'）
  - 参考 lesson-plan 的 LangGraph 模式，使用 checkpoint 机制
  - 支持断点恢复（用户关闭页面后重新打开继续）
       ↓
用户点击"生成初版大纲并展示"
  - AI 基于对话历史生成结构化 outline（DashScope 非流式调用）
  - DraftBlock 展示 outline
       ↓
用户点击"进入后续页面流程"
  - outline_text 写入 PPTProject
  - outline_pages 写入 PPTPage[]（可选，供 Outline 页直接使用）
       ↓ 跳转 Outline 页
Outline 页（用户编辑/调整大纲）—— banana-slides 流程
       ↓
Description 页（生成页面描述）—— banana-slides
       ↓
Preview 页（生成图片）—— banana-slides
       ↓
导出（4种格式）—— banana-slides
```

#### 5.4.3 技术实现

**对话存储**：`PPTSession` 表（见 3.2 节）

```python
class PPTSession(Base):
    id: Mapped[int]         # 主键，自增
    project_id: Mapped[int]  # 关联项目
    user_id: Mapped[int]     # 关联用户
    role: Mapped[str]        # 'user' 或 'assistant'
    content: Mapped[str]     # 对话内容
    metadata: Mapped[dict]   # AI回复的追问选项等附加数据（JSONB）
    round: Mapped[int]       # 对话轮次
    created_at: Mapped[datetime]
    # 同一 project_id 的多条记录按 created_at 构成完整对话历史，无需 session_id
```

**Checkpoint 恢复机制**（参考 lesson-plan LangGraph）：
- Dialog 页前端通过 `project_id` 追踪对话项目
- 用户关闭页面后，重新打开时前端传入 `project_id`，后端从 `PPTSession` 按 `created_at` 顺序加载完整历史
- AI 服务基于历史上下文继续对话

**大纲生成调用**（Dialog 页确认 outline 时）：

```python
# POST /projects/{id}/dialog/generate-outline
async def generate_outline_from_dialog(project_id: int, ...):
    # 1. 从 PPTSession 读取该项目的所有对话历史
    sessions = await db.execute(
        select(PPTSession)
        .where(PPTSession.project_id == project_id)
        .order_by(PPTSession.created_at)
    )
    # 2. 组装对话上下文，调用 DashScope 生成结构化 outline
    outline = await dashscope_service.chat(conversation_context)
    # 3. 写入 PPTProject.outline_text
    project.outline_text = outline
    # 4. 可选：同步解析为 PPTPage[] 供 Outline 页直接使用
    pages = parse_outline_to_pages(outline)
    await db.commit()
    return {"outline": outline, "pages": pages}
```

**与 banana-slides 的接入点**：
- `outline_text` 字段直接复用 banana-slides 的 `parse_outline_text` 解析结果格式
- Outline 页可以直接使用 `outline_text` 或 `outline_pages`
- 后续 Description/Preview/导出流程完全复用 banana-slides 的 service

#### 5.4.4 banana-slides 提供的 vs 自研的

| 功能 | banana-slides 有无 | AIsystem 实现 |
|---|---|---|
| 多轮意图澄清对话 | ❌ 无 | **自研**（PPTSession + DashScope） |
| Checkpoint 断点恢复 | ❌ 无 | **自研**（session_id 追踪） |
| 从 idea 生成 outline | ✅ 有（单次） | 自研（Dialog 页生成 outline 后直接用） |
| 结构化 outline 解析 | ✅ 有 | 复用 `parse_outline_text` |
| 页面描述生成 | ✅ 有 | 复用 banana-slides |
| 图片生成 | ✅ 有 | 复用 banana-slides |
| 4种格式导出 | ✅ 有 | 复用 banana-slides |

## 6. 任务系统设计

### 6.1 Celery Task 封装

**队列**：与 AIsystem 共用 worker，通过 `task_routes` 将 `banana-slides.*` 任务路由到 `default` 队列。

**Task 定义**（`celery_tasks.py`）：

```python
@celery_app.task(bind=True, name="banana-slides.generate_descriptions")
def generate_descriptions_task(self, project_id: int, language: str = "zh"):
    ...

@celery_app.task(bind=True, name="banana-slides.generate_images")
def generate_images_task(self, project_id: int, page_ids: List[int]):
    ...

@celery_app.task(bind=True, name="banana-slides.export_pptx")
def export_pptx_task(self, project_id: int, page_ids: List[int] = None):
    ...
```

### 6.2 进度追踪

- `PPTTask` 表记录任务状态和进度
- SSE 流式接口实时推送进度

### 6.3 SSE 事件类型

> **SSE 协议**：统一使用 `event: message`，所有事件通过 `data.type` 字段区分。前端按 `data.type` 分流，不依赖 event 名。

| data.type | 说明 | 数据结构 |
|---|---|---|
| `page` | 单页描述/图片生成完成 | `{"type": "page", "page_id": int, "content": str}` |
| `progress` | 生成进度更新 | `{"type": "progress", "total": int, "completed": int, "failed": int}` |
| `done` | 生成全部完成 | `{"type": "done"}` |
| `error` | 生成出错 | `{"type": "error", "message": str}` |
| `material_generated` | 素材生成完成 | `{"type": "material_generated", "material_id": int, "url": str}` |
| `export_task_progress` | 导出任务进度 | `{"type": "export_task_progress", "task_id": str, "progress": float}` |
| `export_task_completed` | 导出任务完成 | `{"type": "export_task_completed", "task_id": str, "url": str}` |

## 7. 文件存储设计

### 7.1 OSS Bucket 结构

```
aicourseware/
  └── ppt/
      └── {user_id}/
          └── {project_id}/
              ├── template/
              │   └── template.png
              ├── pages/
              │   └── {page_id}_{timestamp}.png
              ├── materials/
              ├── exports/
              │   └── {filename}.pptx
              ├── reference_files/
              └── user_templates/
```

### 7.2 OSS上传/下载

**文件服务**（`file_service.py`），使用 `app.core.config.settings` 中的现有配置字段：

```python
class OSSFileService:
    def __init__(self):
        self.bucket = oss2.Bucket(
            oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET),
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET  # 注意：使用 config.py 中实际的字段名 OSS_BUCKET
        )

    def upload_file(self, local_path: str, oss_key: str) -> str:
        """上传文件，返回访问URL（公网 endpoint）"""

    def upload_bytes(self, data: bytes, oss_key: str) -> str:
        """上传 bytes 数据，返回访问URL"""

    def get_signed_url(self, oss_key: str, expires: int = 3600) -> str:
        """获取带签名的访问URL（私有 bucket 用）"""

    def download_file(self, oss_key: str, local_path: str):
        """下载文件"""

    def delete_file(self, oss_key: str):
        """删除文件"""
```

> **配置字段对齐**：config.py 中实际字段为 `OSS_BUCKET`、`OSS_ENDPOINT`、`OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`，文档中原 `OSS_BUCKET_NAME` 和 `OSS_PUBLIC_ENDPOINT` 已修正。

### 7.3 导出流程

支持四种导出格式，统一经由 `OSSFileService` 上传到 OSS 后返回 URL：

**1. PPTX（图片版）— 同步**
```
ExportService.create_pptx_from_images()  →  bytes
  → 临时文件  → OSSFileService.upload_file()  →  OSS URL
```

**2. PDF — 同步**
```
ExportService.create_pdf_from_images()  →  bytes（img2pdf 转换）
  → 临时文件  → OSSFileService.upload_file()  →  OSS URL
```

**3. 图片 — 同步**
```
单张：shutil.copy2()  →  OSSFileService.upload_file()
多张：zipfile打包  →  bytes  →  OSSFileService.upload_bytes()  →  OSS URL
```

**4. 可编辑 PPTX — 异步（Celery）**
```
ExportService.create_editable_pptx_with_recursive_analysis()  →  bytes
  （内部：ImageEditabilityService AI分析布局 + PPTXBuilder重建可编辑元素）
  → 临时文件  → OSSFileService.upload_file()  →  OSS URL
```
> 可编辑 PPTX 通过 `export_extractor_method`（mineru/hybrid）和 `export_inpaint_method`（generative/baidu/hybrid）配置提取与修复策略，依赖 `MINERU_TOKEN` 和 `BAIDU_API_KEY`。

**通用流程**：
1. 从 `PPTProject.pages` 收集页面图片 OSS key
2. 调用对应格式的 `ExportService` 方法生成 bytes
3. 写入临时文件
4. `OSSFileService.upload_file()` 上传到 OSS
5. 删除临时文件
6. 将 OSS URL 写入数据库（`PPTProject.export_url` 或 `PPTTask.result_url`）
7. 返回给前端

## 8. 分步实施计划

### Step 1: 骨架搭建
- 创建 `generators/ppt/` 目录结构
- 创建 SQLAlchemy 模型（banana_models.py）
- 创建 Pydantic schemas（banana_schemas.py）
- 在 `Courseware` 模型添加 `ppt_project_id` FK
- 数据库迁移脚本

### Step 2: 路由与认证
- 创建 `banana_routes.py`（FastAPI Router）
- 复用 AIsystem JWT 认证
- 基础 CRUD 接口

### Step 3: 核心服务迁移
- 迁移 `AIService`（去除 Flask 依赖）
- 接入 DashScope（通义千问）用于大纲解析
- 接入 banana-slides providers 用于后续生成

### Step 4: 任务系统
- 创建 `celery_tasks.py`
- 将 TaskManager 后台任务改为 Celery Task
- SSE 流式接口支持

### Step 5: OSS存储
- 创建 `OSSFileService`
- 修改 `ExportService` 输出到 OSS
- 素材/参考文件上传到 OSS

### Step 6: 对话持久化
- 创建 `PPTSession` 模型
- 对话写入/读取接口
- 与 LangGraph 工作流对接

## 9. 依赖变更

### 9.1 新增Python依赖

```
oss2>=2.18.0        # 阿里云OSS SDK
```

### 9.2 沿用banana-slides依赖

```
google-genai>=1.52.0
openai>=1.0.0
anthropic>=0.30.0
python-pptx>=1.0.0
img2pdf>=0.5.1
PyMuPDF>=1.24.0
tenacity>=9.0.0
pillow>=12.0.0
```

## 10. Codex审查问题修正记录

> 以下问题由 Codex 两轮审查发现并已修正：

### 第一轮修正（codex-advice.md）

| 问题 | 修正方案 |
|------|---------|
| **高危：模型基类重复定义** | 新模型统一复用 `app.core.database.Base`，不新建 `DeclarativeBase` |
| **高危：DashScope调用接口不存在** | 改用 `DashScopeService.chat()` 非流式调用；流式需先扩展服务层 |
| **高危：Celery任务未注册** | `celery.py` 的 `include` 添加 `app.generators.ppt.celery_tasks`；配置 `task_routes` 绑定 `default` 队列 |
| **高危：双向FK一致性问题** | 仅 `Courseware` 侧维护 `ppt_project_id` FK，`PPTProject` 不维护反向 `courseware_id` FK |
| **中高：OSS配置字段名不一致** | 使用 `settings.OSS_BUCKET`/`OSS_ENDPOINT` 等实际字段名 |
| **中高：SSE格式不正确** | 流式路由 yield SSE 格式字符串帧 |
| **中危：路径偏差** | 修正 Alembic 路径为 `backend/alembic/versions`；测试路径为 `backend/tests` |
| **中危：依赖清单不全** | Task 14 给出完整必须/可选分层清单 |
| **中低：UserTemplate关系矛盾** | 明确为用户级资产，独立于 Project，不挂在 Project 下 |

### 第二轮修正（codex-advice-v2.md）

| 问题 | 修正方案 |
|------|---------|
| **高危：OSS字段名未修干净** | Plan Task 10 中 `OSS_BUCKET_NAME` → `OSS_BUCKET`；`OSS_PUBLIC_ENDPOINT` → 公网 URL 拼接 |
| **高危：单向FK与back_populates冲突** | `Courseware.ppt_project` 改为单向关系（去 `back_populates`），PPTProject 不维护反向 FK |
| **高危：User侧缺少ppt_projects关系** | 在 `User` 模型添加 `ppt_projects` 关系，并在 Task 4 中明确操作步骤 |
| **高危：迁移路径仍有残留错误** | Task 8 中 `backend/migrations/versions` → `backend/alembic/versions` |
| **中危：courseware_id字段表矛盾** | 设计文档字段表中移除 `courseware_id` 行，明确 PPTProject 不持有 FK |
| **中危：关系基数缺约束** | `Courseware.ppt_project_id` 加 `unique=True`，确保业务 1:1 约束 |
| **中危：目录结构与实际不符** | 路由挂载在 `api/__init__.py`，不是 `api/v1/ppt.py` |
| **中低：parse_outline_text容错缺失** | 文档中明确 JSON 解析路径需失败重试与结果清洗规则 |

### 第三轮修正（codex-advice-v3.md）

| 问题 | 修正方案 |
|------|---------|
| **高危：upload_bytes示例写法错误** | Plan Task 10 改为 `return self.get_signed_url(oss_key)` |
| **中危：Plan Task 4 未加unique=True** | 补充 `unique=True`，与 Spec 保持一致 |
| **中危：路由前缀叙述冲突** | Spec 补充说明"由 app.main 统一加 /api/v1，router 自身 prefix 仅 /ppt" |
| **中危：Plan 保留错误路径选项** | Plan Task 13 去掉"或 api/v1/__init__.py"分支 |
| **中低：事务风格不明确** | Spec/Plan 补充"沿用现有显式 commit 风格" |

## 11. 已知限制与后续优化

1. **AI Provider配置迁移**：banana-slides 的 Settings 表需要迁移或简化，可先硬编码配置
2. **MinerU文件解析**：参考文件的 MinerU 解析暂不迁移，保持本地处理
3. **可编辑PPTX导出**：通过 AI 分析页面布局重建可编辑元素，支持 element 级编辑
4. **前端集成**：本设计仅覆盖后端，前端Vue改造另作计划
5. **parse_outline_text 流式**：当前使用非流式调用，后续如需 SSE 流式返回，需先在 DashScopeService 扩展流式接口

---

### 12.1 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/projects` | 分页获取用户项目列表（含筛选） |
| POST | `/projects` | 创建项目 |
| GET | `/projects/{id}` | 获取项目详情 |
| PUT | `/projects/{id}` | 更新项目名称等基本信息 |
| DELETE | `/projects/{id}` | 删除项目 |
| POST | `/projects/batch-delete` | 批量删除项目 |
| PUT | `/projects/{id}/settings` | 更新项目设置（横竖版/导出方式） |
| POST | `/projects/{id}/dialog/generate-outline` | Dialog页确认后生成结构化outline（自研） |

### 12.2 模板管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/templates/presets` | 获取预设模板列表（含分类） |
| GET | `/templates/user` | 获取用户上传的模板 |

### 12.3 素材管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/projects/{id}/materials` | 获取项目素材列表 |
| POST | `/projects/{id}/materials/upload` | 上传素材图片 |
| DELETE | `/projects/{id}/materials/{material_id}` | 删除素材 |
| GET | `/materials` | 获取全局素材中心列表 |

### 12.4 导出任务

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/projects/{id}/export/pptx` | 导出PPTX（图片版，同步） |
| GET | `/projects/{id}/export/pdf` | 导出PDF（同步） |
| GET | `/projects/{id}/export/images` | 导出图片/ZIP（同步） |
| POST | `/projects/{id}/export/editable-pptx` | 导出可编辑PPTX（异步） |
| GET | `/projects/{id}/export-tasks` | 获取导出任务列表及状态 |
| GET | `/export-tasks/{task_id}` | 获取单个导出任务详情 |

### 12.5 图片版本

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/projects/{id}/pages/{page_id}/versions` | 获取页面图片版本历史 |
| POST | `/projects/{id}/pages/{page_id}/versions` | 创建新版本（重新生成时） |

### 12.6 自然语言修改（banana-slides原生）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/projects/{id}/refine/outline` | 自然语言修改大纲（添加/删除/重排页面、修改标题要点） |
| POST | `/projects/{id}/refine/descriptions` | 自然语言批量修改页面描述 |
| POST | `/projects/{id}/pages/{page_id}/edit/image` | 单页图片自然语言编辑（异步，返回 task_id） |

### 12.7 翻新任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/projects/renovation` | 创建PPT翻新项目（异步，返回 `project_id` + `task_id`） |
| GET | `/projects/{id}/tasks/{task_id}` | 获取翻新任务状态（轮询） |

### 12.8 参考文件

> 遵循 AIsystem 风格：资源 project-scoped（除全局预览）。banana 原生扁平路径适配为 RESTful 风格。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/projects/{id}/reference-files` | 上传参考文件（multipart/form-data，banana原为 `/upload`） |
| POST | `/projects/{id}/reference-files/{file_id}/parse` | 触发参考文件解析（异步） |
| GET | `/projects/{id}/reference-files/{file_id}` | 获取参考文件详情（含 `parse_status`） |
| POST | `/projects/{id}/reference-files/{file_id}/confirm` | 确认参考文件解析完成（banana原为 `/associate`） |
| GET | `/reference-files/{file_id}` | 获取参考文件预览URL（全局，无需 project_id） |

### 12.9 模板

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/templates/presets` | 获取预设模板列表（含分类） |
| POST | `/projects/{id}/template` | 上传项目模板图片（覆盖当前项目模板） |
| GET | `/templates/user` | 获取用户上传的模板列表 |
| POST | `/user-templates` | 上传用户模板（multipart/form-data，banana原路径） |
| DELETE | `/user-templates/{id}` | 删除用户模板（banana原路径） |

---

## 13. 各页面功能详细说明

### 13.1 入口与项目列表

#### 13.1.1 新建项目入口（LessonPrepPpt.vue）

**入口设计（3-Tab）：**

| Tab | creation_type | 欢迎页操作 | 后续流程 |
|-----|--------------|-----------|---------|
| 对话生成 | `dialog` | 选择模板 + 输入主题/想法 + 选择知识库 | → 对话页 → 大纲页 → 描述页 → 预览页 |
| 文件生成 | `file` | 上传参考文件（PDF/PPTX/PPT/DOCX） | → 大纲页 → 描述页 → 预览页 |
| PPT翻新 | `renovation` | 上传旧PPT/PDF/PPTX | → 大纲页 → 描述页 → 预览页 |

**知识库选择器：**
- 位于主题输入框下方，支持多选
- 调用 `GET /api/v1/libraries?scope=personal` 获取用户知识库 + `GET /api/v1/libraries?scope=system` 获取公开系统库，合并展示
- 用户选择知识库后，ID列表存入 `PPTProject.knowledge_library_ids`
- Dialog 对话过程中，AI 工具检索时传入 `library_ids` 做 RAG 检索（参考 `lesson_plan_service.retrieve_context` 模式）
- 可选，不选则不启用知识库检索

**PPT翻新异步任务流程：**
```
POST /projects/renovation（上传文件）→ 返回 { project_id, task_id }
前端轮询 GET /projects/{id}/tasks/{task_id} → 显示解析进度
解析完成后自动进入大纲页
```

**参考文件上传流程：**
```
POST /projects/{id}/reference-files（上传）→ 返回 file + parse_status
如果 parse_status='pending' → POST /projects/{id}/reference-files/{file_id}/parse（触发解析）
前端显示 parse_status 状态（pending/parsing/completed/failed）
GET /reference-files/{file_id}（预览文件）
```

**模板选择：**
- 预设模板网格 + 分类 tab 切换
- 用户模板列表（`GET /templates/user`）
- 模板搜索输入框
- 文字风格模式开关（`templateStyle` 文字输入作为风格参考）

**其他欢迎页功能：**
- 素材生成弹窗（MaterialGeneratorModal）：`POST /projects/{id}/materials/generate`
- 素材中心弹窗（MaterialCenterModal）：`GET /materials`
- 主题/语言切换（前端状态）
- 粘贴图片上传（剪贴板截取图片文件）

### 13.2 大纲页（PptOutline）

**核心功能：**

| 功能 | API | 说明 |
|------|-----|------|
| 生成大纲 | `POST /projects/{id}/generate/outline/stream` | SSE 流式，返回 pages |
| 重新生成大纲 | 同上 + 确认弹窗 | 可选"锁定页数"防止减少页数 |
| 自然语言修改大纲 | `POST /projects/{id}/refine/outline` | AiRefineInput 组件 |
| 拖拽排序页面 | `PUT /projects/{id}` with `pages_order` | Native HTML5 Drag API |
| 更新单页 | `PUT /projects/{id}/pages/{page_id}` | 标题/要点/part/大纲内容 |
| 添加页面 | `POST /projects/{id}/pages` | 追加新空白页 |
| 删除页面 | `DELETE /projects/{id}/pages/{page_id}` | 确认后删除 |
| 导入大纲.md | `POST /projects/{id}/pages`（多次） | 解析 .md 文件追加页面 |
| 导出大纲.md | 客户端 `exportProjectToMarkdown()` | 纯文本大纲下载 |

**自动保存：**
- 大纲文本输入框、生成要求字段（`outline_requirements`）1秒防抖自动保存
- `PUT /projects/{id}` with `{ outline_requirements, outline_text }`

**参考文件展示：**
- 左侧面板列出已关联的参考文件（`GET /projects/{id}/reference-files`）
- 文件预览弹窗（FilePreviewModal）：`GET /reference-files/{file_id}`
- 解析进度状态显示（parse_status）

**翻新模式单页重新生成：**
- `POST /projects/{id}/pages/{page_id}/regenerate-renovation`：重新解析原PDF该页并生成大纲描述

### 13.3 描述页（PptDescription）

**核心功能：**

| 功能 | API | 说明 |
|------|-----|------|
| 批量生成描述 | `POST /projects/{id}/descriptions/generate/stream` | SSE 流式 |
| 自然语言修改描述 | `POST /projects/{id}/refine/descriptions` | AiRefineInput 组件 |
| 更新单页描述 | `PUT /projects/{id}/pages/{page_id}` | description_content |
| 添加新页面 | `POST /projects/{id}/pages` | |
| 导入描述.md | 解析后 `addPage()` | |
| 导出描述.md | 客户端 `exportProjectToMarkdown()` | |

**生成设置：**
- 生成模式：流式 / 并行（通过 `description_generation_mode` 字段控制）
- 详细程度：concise / default / detailed
- 额外字段管理：启用/禁用 视觉元素/视觉焦点/排版布局/演讲者备注，可拖拽排序，顺序保存到 `description_extra_fields`
- 图片提示字段：`image_prompt_extra_fields` 控制哪些字段传入生图 prompt
- 描述生成要求（`description_requirements`）：独立文本框，自动保存

**自动保存：**
- 描述要求文本 1 秒防抖 → `PUT /projects/{id}` with `{ description_requirements }`
- 设置变更 800ms 防抖 → `PUT /settings` with `{ description_generation_mode, description_extra_fields, image_prompt_extra_fields, detail_level }`

### 13.4 预览页（PptPreview）

**核心功能：**

| 功能 | API | 说明 |
|------|-----|------|
| 缩略图列表 | 本地读取 `pages[].generated_image_path` | 左侧 280px 面板 |
| 大图预览 | — | CSS `transform: scale()` 居中显示 |
| 批量生成图片 | `POST /projects/{id}/images/generate` | |
| 批量生成（部分） | 同上 + `page_ids` 参数 | 多选模式下使用 |
| 重新生成（全部） | 同上 + 确认弹窗 | 历史版本自动保存 |
| 重新生成（选中） | 同上 + 确认弹窗 | |
| 单页编辑 | `POST /projects/{id}/pages/{page_id}/edit/image` | 自然语言编辑图片（异步） |
| 仅保存大纲/描述 | `updatePageLocal()` | 不触发图片生成 |
| 导出PPTX | `GET /projects/{id}/export/pptx?page_ids=...` | 图片版PPTX |
| 导出PDF | `GET /projects/{id}/export/pdf?page_ids=...` | |
| 导出图片 | `GET /projects/{id}/export/images?page_ids=...` | 单张或ZIP打包 |
| 导出可编辑PPTX | `POST /projects/{id}/export/editable-pptx` | 异步，返回 task_id |
| 导出（选中页） | 同上 + `?page_ids=...` | 多选模式 |

**多选模式：**
- 勾选框模式，选中多页后"批量生成"/"导出"仅作用于选中页
- `page_ids` 参数传递选中页面 ID 列表

**模板更换：**
- 模板选择弹窗（ProjectSettingsModal）
- 上传新模板 → `POST /projects/{id}/template`
- 预设模板 + 用户模板列表切换

**文字风格模式：**
- 开关切换，用 `template_style` 文字描述代替模板图片作为风格参考
- 风格描述自动保存 → `PUT /projects/{id}` with `{ template_style }`

**图片编辑（编辑按钮）：**
- 输入自然语言指令（`editPrompt`）
- 选择上下文图片：模板图片 / 描述中的图片 / 上传图片
- 区域框选：从当前图片裁剪区域作为参考
- "仅保存大纲/描述" vs "生成图片" 两个按钮

**版本历史：**
- `GET /projects/{id}/pages/{page_id}/versions`：获取版本下拉列表
- `POST /projects/{id}/pages/{page_id}/versions/{version_id}/set-current`：切换版本

**项目设置弹窗：**
- 横竖版切换（`image_aspect_ratio`）
- 导出提取方式（`export_extractor_method`）
- 导出修复方式（`export_inpaint_method`）
- 允许部分导出（`export_allow_partial`）
- 分辨率（1K/2K/4K）— 1K 分辨率时显示警告弹窗

**素材相关：**
- 素材选择弹窗（MaterialCenterModal）：`GET /materials`
- 素材生成弹窗（MaterialGeneratorModal）：`POST /projects/{id}/materials/generate`

**导出任务面板（ExportTasksPanel）：**
- SSE 事件 `export_task_progress` / `export_task_completed` 实时更新
- 轮询 `GET /export-tasks/{task_id}` 获取状态

**其他：**
- 删除页面：`DELETE /projects/{id}/pages/{page_id}`
- 返回描述页编辑：`navigate /lesson-prep?tab=description`
- 刷新同步：`syncProject` → `GET /projects/{id}`

> `refine/outline` 和 `refine/descriptions` 请求体均包含 `user_requirement`（自然语言修改要求）和 `language`（输出语言）。前端使用 `AiRefineInput` 组件实现。

### 13.5 历史项目列表（CoursewareManage PPT Tab）

**位置：** `CoursewareManage.vue` → Tab「PPT」

**功能：** 展示当前用户的所有历史 PPT 项目（`PPTProject`），支持点击进入详情页编辑。

| 功能 | 说明 |
|------|------|
| Tab切换 | CoursewareManage 已有 tab 栏，新增「PPT」Tab |
| 项目卡片列表 | 展示 `PPTProject` 列表，含标题/创建时间/状态 |
| 创建新项目 | 「新建PPT」按钮 → 跳转 `LessonPrepPpt.vue`（创建流程） |
| 打开项目 | 点击卡片 → 进入 4-Tab 详情页（见 13.6） |
| 删除项目 | 单个删除 + 批量删除，调用 `DELETE /projects/{id}` |
| 搜索/筛选 | 按标题搜索，按创建时间排序 |

**路由/状态方案：**

方案A（推荐）：在 `LessonPrep.vue` 增加 `projectId` query 参数
```
/lesson-prep?tab=ppt                           → 新建项目（现有 LessonPrepPpt.vue）
/lesson-prep?tab=ppt&projectId={id}           → 打开已有项目（4-Tab 详情页）
```

方案B：新建独立页面 `LessonPrepPptDetail.vue`，路由 `/lesson-prep/ppt/:projectId`

**API：**

| 接口 | 说明 |
|------|------|
| `GET /ppt/projects` | 获取当前用户的所有 PPTProject（分页） |
| `DELETE /ppt/projects/{id}` | 删除项目 |
| `POST /ppt/projects/batch-delete` | 批量删除 |

### 13.6 PPT项目详情页（4-Tab）

**位置：** `LessonPrep.vue?tab=ppt&projectId={id}` 或独立页面

**4-Tab 结构：** `Dialog` | `Outline` | `Description` | `Preview`

#### 13.6.1 Dialog Tab（对话历史）

**功能：** 查看该项目在创建过程中与 AI 的多轮对话记录（只读）。对话过程中 AI 已根据 `PPTProject.knowledge_library_ids` 检索知识库内容。

| 功能 | 说明 |
|------|------|
| 对话历史列表 | 读取 `PPTSession` 表，按 `round` 和 `created_at` 排序展示 |
| 用户消息 | 左侧气泡 |
| AI回复 | 右侧气泡（包含追问选项等） |
| 元数据展示 | 显示每轮对话的 `metadata`（如追问选项列表） |
| 知识库信息 | 显示该项目的 `knowledge_library_ids` 对应的知识库名称（需两次调用：`GET /api/v1/libraries?scope=personal` + `GET /api/v1/libraries?scope=system`，按 `library_id` 匹配名称） |
| 返回项目列表 | 导航回 CoursewareManage PPT Tab |

**API：**

| 接口 | 说明 |
|------|------|
| `GET /ppt/projects/{id}/sessions` | 获取该项目所有对话记录 |

#### 13.6.2 Outline Tab（大纲编辑）

与 13.2 大纲页（PptOutline）功能一致，加载该项目已有的大纲数据进行编辑。

#### 13.6.3 Description Tab（描述编辑）

与 13.3 描述页（PptDescription）功能一致，加载该项目已有的描述数据进行编辑。

#### 13.6.4 Preview Tab（预览编辑）

与 13.4 预览页（PptPreview）功能一致，加载该项目已有的图片进行预览和编辑。

#### 13.6.5 通用行为

| 行为 | 说明 |
|------|------|
| 进入时加载数据 | `GET /ppt/projects/{id}` 加载项目完整数据 |
| Tab切换 | 保留当前 Tab 状态，切换时无需重新加载 |
| 自动保存 | 各 Tab 内编辑自动保存到后端 |
| 返回项目列表 | Header/导航栏「返回」按钮 → CoursewareManage PPT Tab |
