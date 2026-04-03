# PPT 生成模块 - 后端设计文档 V2（按代码现状对齐）

> Date: 2026-03-31
> Status: Active Draft
> Owner: AIsystem Backend
> Supersedes: docs/superpowers/specs/2026-03-26-ppt-banana-integration-design.md

## 1. 文档目的与范围

本版本用于替代旧版后端设计文档中与当前实现不一致的部分，目标是：

- 以 AIsystem 当前代码为唯一事实来源（backend/app/generators/ppt）。
- 对齐 banana-slides 的核心能力现状与差距。
- 为 Description/Preview 的高一致性对齐给出可执行后端补齐路线。
- 明确当前必做闭环：单页图片在线编辑（任务 + 版本 + 回切）。

本文件覆盖后端接口、模型、任务系统与实施优先级，不展开前端实现细节。

---

## 2. 现状基线（代码事实）

### 2.1 路由挂载

- 路由前缀：router prefix 为 /ppt。
- 全局前缀：app.main 统一挂载 /api/v1。
- 实际访问前缀：/api/v1/ppt。

### 2.2 数据模型（已落地）

核心模型位于 banana_models.py：

- PPTProject
- PPTPage
- PPTTask
- PPTMaterial
- PPTReferenceFile
- PPTSession
- UserTemplate
- PageImageVersion

关联事实：

- User 已有 ppt_projects 一对多关系。
- Courseware 持有 ppt_project_id（单向 FK，unique=True）。
- PPTProject 不维护 courseware_id 反向 FK。

### 2.3 异步任务（Celery）

已实现任务：

- banana-slides.generate_descriptions
- banana-slides.generate_images
- banana-slides.export_pptx
- banana-slides.export_pdf
- banana-slides.export_images
- banana-slides.export_editable_pptx（当前委托 export_pptx）
- banana-slides.renovation_parse
- banana-slides.edit_page_image

任务状态统一写入 PPTTask：PENDING/PROCESSING/COMPLETED/FAILED，progress 为 0-100。

---

## 3. 实际接口基线（按分组）

说明：以下路径均为 /api/v1/ppt 下的相对路径。

### 3.1 项目管理

- POST /projects
- GET /projects
- GET /projects/{project_id}
- PUT /projects/{project_id}
- DELETE /projects/{project_id}
- POST /projects/batch-delete
- PUT /projects/{project_id}/settings

### 3.2 页面管理

- POST /projects/{project_id}/pages
- GET /projects/{project_id}/pages
- PUT /projects/{project_id}/pages/{page_id}
- DELETE /projects/{project_id}/pages/{page_id}
- POST /projects/{project_id}/pages/reorder

### 3.3 大纲与描述生成

- POST /projects/{project_id}/outline/generate
- POST /projects/{project_id}/outline/generate/stream
- POST /projects/{project_id}/descriptions/generate
- POST /projects/{project_id}/descriptions/generate/stream

### 3.4 生成与自然语言修改

- POST /projects/{project_id}/images/generate
- POST /projects/{project_id}/refine/outline
- POST /projects/{project_id}/refine/descriptions
- POST /projects/{project_id}/pages/{page_id}/edit/image

### 3.5 导出与导出任务

- GET /projects/{project_id}/export/{format}（format: pptx|pdf|images）
- POST /projects/{project_id}/export/editable-pptx
- GET /projects/{project_id}/export-tasks
- GET /export-tasks/{task_id}

### 3.6 素材与参考文件

- GET /projects/{project_id}/materials
- POST /projects/{project_id}/materials/upload
- DELETE /projects/{project_id}/materials/{material_id}
- GET /materials
- POST /projects/{project_id}/reference-files
- POST /projects/{project_id}/reference-files/{file_id}/parse
- GET /projects/{project_id}/reference-files/{file_id}
- POST /projects/{project_id}/reference-files/{file_id}/confirm
- GET /reference-files/{file_id}

### 3.7 Dialog 与意图确认

- GET /projects/{project_id}/sessions
- POST /projects/{project_id}/sessions
- POST /projects/{project_id}/chat
- POST /projects/{project_id}/intent/confirm
- GET /projects/{project_id}/intent
- POST /projects/{project_id}/dialog/generate-outline

### 3.8 模板、版本与任务

- GET /templates/presets
- GET /templates/user
- POST /user-templates/upload
- POST /user-templates
- DELETE /user-templates/{template_id}
- GET /projects/{project_id}/pages/{page_id}/versions
- POST /projects/{project_id}/pages/{page_id}/versions
- POST /projects/{project_id}/pages/{page_id}/versions/{version_id}/set-current
- GET /projects/{project_id}/tasks
- GET /projects/{project_id}/tasks/{task_id}
- POST /projects/{project_id}/template

### 3.9 翻新与扩展接口

- POST /projects/renovation
- POST /projects/{project_id}/pages/{page_id}/regenerate-renovation
- POST /extract-style

---

## 4. 关键契约快照（前后端对齐必看）

### 4.1 Chat（Dialog）

请求体：

- content: string
- round?: int
- metadata?: object

响应核心：

- message
- round
- intent_state
  - confirmed[]
  - pending[]
  - scores(goal/audience/structure/interaction)
  - confidence
  - ready_for_confirmation
  - summary
  - intent_summary
- intent_summary

说明：当前已实现“意图澄清”多轮状态机风格回复，不是简单问答。

### 4.2 SSE 协议（当前实现）

统一格式：

- event: message
- data: JSON（通过 data.type 区分事件）

当前已确认事件类型：

- outline_chunk（大纲流式分片）
- page（单页描述完成）
- done
- error

注意：progress/material_generated/export_task_progress/export_task_completed 目前未在路由层稳定对外推送，异步任务主要依赖查询 tasks/export-tasks 轮询。

### 4.3 单页图片在线编辑（必做闭环）

接口：POST /projects/{project_id}/pages/{page_id}/edit/image

请求体：

- edit_instruction: string
- context_images?:
  - use_template: bool
  - desc_image_urls: string[]
  - uploaded_image_ids: string[]

当前行为：

- 接口创建 PPTTask（task_type=edit_page_image）并异步执行。
- 任务完成后更新 PPTPage.image_url/image_version。
- 写入 PageImageVersion(operation=edit,prompt=edit_instruction,is_active=true)。

备注：当前任务实现尚未实际消费 context_images 字段，仅使用当前页图作为 ref image。

### 4.4 导出行为（当前实现边界）

- GET /export/{format}：
  - pptx、pdf 可同步返回流。
  - images 虽在路径参数白名单中，但当前分支逻辑返回“请使用导出任务接口”，且无对应导出图片任务路由入口。
- POST /export/editable-pptx：异步任务已接入，但当前底层委托 export_pptx，尚未形成真正“可编辑重建”差异。

### 4.5 设置字段一致性风险

存在枚举不一致：

- ProjectSettingsUpdate.detail_level: brief|normal|detailed
- GenerateDescriptionsStreamRequest.detail_level: concise|default|detailed

需要统一，否则前端设置与流式生成参数存在语义漂移。

---

## 5. 与 banana-slides 对齐评估

### 5.1 已对齐/已具备

- 项目/页面 CRUD
- 大纲与描述生成（含 SSE 版本）
- refine/outline 与 refine/descriptions
- 单页图片编辑接口 + 版本历史
- 对话历史持久化与意图确认
- 翻新入口（上传+解析任务）

### 5.2 未完全对齐或需补强

- 素材生成接口（materials/generate）未落地。
- 导出任务进度 SSE 推送未落地（仅轮询）。
- 导出 images 的公开路由闭环不完整。
- 项目模板上传接口当前为占位返回。
- editable-pptx 仍是“与普通 pptx 同实现”的过渡态。
- edit/image 的 context_images 还未真正参与生成逻辑。

### 5.3 与 banana-slides 路径映射差异（命名层）

为避免联调误判，需明确以下“同能力不同路径命名”的差异：

- banana-slides 版本接口使用 `image-versions`，AIsystem 使用 `versions`。
- banana-slides 素材生成有 `POST /projects/{id}/materials/generate`，AIsystem 当前仅有 `materials/upload` 与列表/删除。
- banana-slides 可编辑导出为 `POST /projects/{id}/export/editable-pptx`（异步），AIsystem 路径一致但当前实现仍为过渡态。

上述差异属于可控适配项，不应被误判为功能不存在；前后端文档以 AIsystem 路径为准，对齐说明中保留 banana 路径映射。

### 5.4 未完善/未做功能补充（后端执行清单）

以下条目是当前代码中“未做完”或“能力存在但未闭环”的功能，需纳入开发排期：

1. `materials/generate` 未落地：需补路由、任务、结果落库与前端可消费响应。
2. `export/images` 导出未闭环：当前路径参数允许但分支返回不一致，需统一为可用链路。
3. 导出任务进度推送缺失：当前主要轮询，需补推送通道或统一任务事件机制。
4. 项目模板上传未完成：`POST /projects/{project_id}/template` 仍为占位返回。
5. `edit_page_image_task` 未消费 `context_images`：需将模板图、描述图、上传图纳入生成输入。
6. `export_editable_pptx` 仍委托 `export_pptx`：需升级为真实可编辑重建流程。
7. `detail_level` 枚举不一致：设置与流式生成枚举需统一。
8. 导出任务能力暴露不完整：任务层已具备 `export_pptx/export_pdf/export_images`，但路由触发策略需统一文档与实现。
9. 翻新单页再生可观测性不足：需补充任务/状态反馈与错误可追踪字段。

每一项都应满足“可调用、可观测、可失败重试”的三要素验收。

---

## 6. 分阶段实施计划（后端）

### Phase A（P0，1 周）

1. 完成 Preview 必要闭环：
   - 保持 edit/image -> task -> versions -> set-current 的稳定链路。
   - 在任务 result 中统一返回 url 与版本号。
2. 修复导出路径一致性：
   - 明确 images 导出策略（二选一）：
     - A: 开放同步 images ZIP 返回。
     - B: 新增 POST /projects/{id}/export/images 异步任务入口并文档化。
3. 统一 detail_level 枚举（settings 与 stream 请求一致）。
4. 落地 projects/{id}/template 实际上传与持久化。

### Phase B（P1，1-2 周）

1. 补充素材生成接口与任务（material_generate）。
2. 让 edit_page_image_task 消费 context_images。
3. 增加导出任务进度推送通道（SSE 或统一事件总线）。

### Phase C（P2，2 周+）

1. 将 editable-pptx 从委托实现升级为真实可编辑重建链路。
2. 增强 renovation 单页再生能力（按页解析、失败回退、重试策略）。
3. 整理 extract-style 在业务流中的正式接入位置。

---

## 7. 测试与验收标准

### 7.1 必过项（当前迭代）

- Home/Dialog/Outline/Description/Preview 对应后端接口全链路可调用。
- edit/image 能返回 task_id，任务完成后页面图与版本号可见变化。
- versions/set-current 可回切历史图。
- 描述流式接口可稳定输出 page/done/error。

补充必过项：

- `materials/generate` 可用，生成结果可在素材中心查询。
- `export/images` 可稳定导出，不再出现路径可访问但功能不可用的状态。
- `projects/{project_id}/template` 完成真实上传与持久化。
- `edit_page_image_task` 对 `context_images` 生效，结果可通过版本历史验证。

### 7.2 一致性检查

- 文档接口与 banana_routes.py 声明一致。
- 文档模型字段与 banana_models.py 一致。
- 文档中的“未实现项”必须在代码中可被证伪，不得写成“已支持”。

---

## 8. 非目标（本版不做）

- 不在本文件展开前端组件交互设计。
- 不替代数据库迁移脚本逐条说明。
- 不把历史原型文档作为实现依据。

---

## 9. 与前端 V2 对齐清单

对应文档：`docs/superpowers/plans/2026-03-31-ppt-frontend-design-v2.md`

- 版本历史能力口径：后端已提供 versions 三接口；前端文档按“已具备、待全量接入”描述。
- SSE 口径：双方统一为 `event: message + data.type`，当前稳定事件类型以 `outline_chunk/page/done/error` 为准。
- 导出口径：
  - pptx/pdf 可同步导出。
  - images 当前未闭环，列入 P0。
  - editable-pptx 为异步任务模式，前端走任务链路。
- detail_level 口径：双方均保留“枚举不一致需统一”的风险说明，前端先做兼容映射，后端在 P0 收敛枚举。
