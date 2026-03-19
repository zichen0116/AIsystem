# AI PPT 生成功能实施计划（单次交付版）

更新时间：2026-03-18

> 本计划用于直接指导实现。本计划对应一次性交付版本，不做一期 / 二期拆分；实现顺序可以分步推进，但最终验收必须满足规格文档中的完整能力要求。

关联规格：

- [spec文档.md](/d:/123/AIsystem/docs/superpowers/specs/spec文档.md)

## 1. 实施原则

### 1.1 必须遵守的技术约束

- 前端流式方案统一使用 `fetch + reader`
- 不使用原生 `EventSource`
- 不引入 WebSocket 替代 SSE
- 前端不直连 Docmee，统一走后端代理
- 前端复用 [http.js](/d:/123/AIsystem/teacher-platform/src/api/http.js) 的请求模式
- 前端入口复用 [LessonPrepPpt.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrepPpt.vue)
- 预览复用 Docmee 官方 `ppt2svg.js` / `ppt2canvas.js`
- 数据库变更统一使用 Alembic
- LangGraph 只围绕业务主链路落地，不做不必要扩张

### 1.2 本次交付目标

完成本计划后，用户应能在当前项目中直接完成以下完整链路：

1. 新建 PPT 会话
2. 选择知识库与模板
3. 输入需求并流式生成大纲
4. 自动配图
5. 编辑并审批大纲
6. 生成 PPT 并看到流式进度
7. 预览、继续修改、元素级编辑
8. 保存版本并做版本对比
9. 下载结果

## 2. 文件调整方案

## 2.1 后端新增文件

| 文件 | 作用 |
|------|------|
| `backend/app/models/ppt_session.py` | PPT 会话模型 |
| `backend/app/models/ppt_outline.py` | PPT 大纲版本模型 |
| `backend/app/models/ppt_message.py` | PPT 会话消息模型 |
| `backend/app/models/ppt_result.py` | PPT 结果版本模型 |
| `backend/app/schemas/ppt.py` | PPT 相关请求响应 schema |
| `backend/app/services/ppt/docmee_client.py` | Docmee 代理客户端 |
| `backend/app/services/ppt/image_search.py` | 自动配图服务 |
| `backend/app/services/ppt/state.py` | LangGraph 状态定义 |
| `backend/app/services/ppt/nodes.py` | LangGraph 节点实现 |
| `backend/app/services/ppt/workflow.py` | LangGraph 工作流 |
| `backend/app/services/ppt/serializer.py` | `pptx_property` 解压 / 序列化辅助 |
| `backend/app/api/ppt.py` | PPT API 路由 |
| `backend/alembic/versions/XXXX_add_ppt_tables.py` | 数据库迁移 |

## 2.2 后端修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/models/__init__.py` | 导出新模型 |
| `backend/app/api/__init__.py` | 注册 PPT 路由 |
| `backend/.env.example` | 新增 Docmee / Unsplash 配置 |

## 2.3 前端新增文件

| 文件 | 作用 |
|------|------|
| `teacher-platform/src/api/ppt.js` | PPT API 封装 |
| `teacher-platform/src/components/ppt/PptWorkspace.vue` | PPT 页面主工作区 |
| `teacher-platform/src/components/ppt/PptSidebar.vue` | 会话与版本侧栏 |
| `teacher-platform/src/components/ppt/WelcomePanel.vue` | 欢迎页 |
| `teacher-platform/src/components/ppt/TemplateSelector.vue` | 模板选择器 |
| `teacher-platform/src/components/ppt/KnowledgeLibraryModal.vue` | 知识库选择弹窗 |
| `teacher-platform/src/components/ppt/ChatPanel.vue` | 对话页 |
| `teacher-platform/src/components/ppt/ChatMessage.vue` | 聊天气泡 |
| `teacher-platform/src/components/ppt/OutlineCard.vue` | 大纲卡片 |
| `teacher-platform/src/components/ppt/PptResultCard.vue` | 结果卡片 |
| `teacher-platform/src/components/ppt/PptPreviewPanel.vue` | 预览页 |
| `teacher-platform/src/components/ppt/PptThumbnailList.vue` | 缩略图列表 |
| `teacher-platform/src/components/ppt/PptCanvas.vue` | 大图预览 |
| `teacher-platform/src/components/ppt/PptToolbar.vue` | 顶部工具栏 |
| `teacher-platform/src/components/ppt/PptVersionCompareDialog.vue` | 版本对比弹窗 |
| `teacher-platform/src/components/ppt/ChatInput.vue` | 通用输入框 |
| `teacher-platform/src/utils/ppt2svg.js` | 复用官方渲染器 |
| `teacher-platform/src/utils/ppt2canvas.js` | 复用官方缩略图渲染器 |

## 2.4 前端修改文件

| 文件 | 变更 |
|------|------|
| `teacher-platform/src/views/LessonPrepPpt.vue` | 由占位页面改造成 PPT 功能入口页 |
| `teacher-platform/package.json` | 如确有缺失则补充 `pako` / `base64-js` / Markdown 相关依赖 |

说明：

- 不新增新的课前准备 tab
- 不修改 [LessonPrep.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrep.vue) 的导航结构
- 直接替换当前 `ppt` 页签对应的实现

## 3. 实施步骤

## Phase 1：数据库与基础模型

**目标：** 为会话、大纲版本、消息、结果版本建立稳定数据基础。

- [ ] 新建 Alembic 迁移 `XXXX_add_ppt_tables.py`
- [ ] 创建 `ppt_sessions`
- [ ] 创建 `ppt_outlines`
- [ ] 创建 `ppt_messages`
- [ ] 创建 `ppt_results`
- [ ] 为 `ppt_outlines` 和 `ppt_results` 增加 `version`、`is_current`
- [ ] 为 `ppt_results` 增加：
  - [ ] `source_pptx_property`
  - [ ] `edited_pptx_property`
  - [ ] `current_page`
  - [ ] `total_pages`
- [ ] 编写对应 SQLAlchemy 模型
- [ ] 编写 `backend/app/schemas/ppt.py`

**验证：**

- [ ] 运行迁移成功
- [ ] 新模型可被 `Base.metadata` 正确识别
- [ ] 补充基础 CRUD 测试

## Phase 2：Docmee 客户端与模板代理

**目标：** 封装 Docmee 的模板、内容生成、PPT 生成、结果加载与下载能力。

- [ ] 创建 `backend/app/services/ppt/docmee_client.py`
- [ ] 封装模板列表获取
- [ ] 封装内容 / 大纲生成
- [ ] 封装内容更新
- [ ] 封装 PPT 生成
- [ ] 封装结果加载
- [ ] 封装下载地址获取
- [ ] 封装 `pptx_property` 解压辅助
- [ ] 所有请求统一由后端读取 `DOCMEE_API_TOKEN`

**关键要求：**

- [ ] 前端完全不感知 Docmee token
- [ ] 若主链路采用 V2，但渐进预览需兼容旧接口，兼容逻辑仅存在于后端客户端中

**验证：**

- [ ] 新建 `tests/test_docmee_client.py`
- [ ] mock 成功 / 失败 / 超时场景
- [ ] 手工验证模板列表与结果加载

## Phase 3：自动配图服务

**目标：** 在大纲生成完成后自动补充页面配图。

- [ ] 创建 `backend/app/services/ppt/image_search.py`
- [ ] 从 Markdown 大纲中提取页面标题
- [ ] 使用 LLM 翻译关键词
- [ ] 调用 Unsplash 搜索横版图片
- [ ] 将结果写入 `ppt_outlines.image_urls`

**要求：**

- [ ] 配图失败不阻塞后续审批与生成
- [ ] 返回空图集时流程仍可继续

**验证：**

- [ ] 新建 `tests/test_image_search.py`
- [ ] 测试大纲解析
- [ ] 测试关键词翻译
- [ ] 测试 API 失败兜底

## Phase 4：LangGraph 工作流

**目标：** 实现服务于业务的生成、审批、修改工作流。

- [ ] 创建 `backend/app/services/ppt/state.py`
- [ ] 定义状态字段：
  - [ ] `session_id`
  - [ ] `user_id`
  - [ ] `messages`
  - [ ] `selected_library_ids`
  - [ ] `template_id`
  - [ ] `outline_markdown`
  - [ ] `outline_id`
  - [ ] `outline_approved`
  - [ ] `image_urls`
  - [ ] `result_id`
  - [ ] `next_action`
- [ ] 创建 `nodes.py`
- [ ] 至少实现以下节点：
  - [ ] 检索 / 工具调用
  - [ ] 大纲生成
  - [ ] 自动配图
  - [ ] 审批中断
  - [ ] PPT 生成准备
  - [ ] 修改再生成
- [ ] 创建 `workflow.py`
- [ ] 编译工作流并支持审批中断恢复

**关键要求：**

- [ ] 工作流必须支持继续修改场景
- [ ] 工作流复杂度控制在可测试范围内
- [ ] 不在服务层使用错误的 `async with get_db() as db` 写法

**验证：**

- [ ] 新建 `tests/test_ppt_workflow.py`
- [ ] 测试初次生成
- [ ] 测试审批恢复
- [ ] 测试继续修改创建新版本

## Phase 5：后端 API 与流式输出

**目标：** 提供完整的会话、流式生成、编辑保存、版本查询接口。

- [ ] 新建 `backend/app/api/ppt.py`
- [ ] 实现 `GET /ppt/templates`
- [ ] 实现 `POST /ppt/sessions`
- [ ] 实现 `GET /ppt/sessions`
- [ ] 实现 `GET /ppt/sessions/{session_id}`
- [ ] 实现 `POST /ppt/stream/outline`
- [ ] 实现 `POST /ppt/outlines/{outline_id}/approve`
- [ ] 实现 `POST /ppt/stream/generate`
- [ ] 实现 `POST /ppt/results/{result_id}/modify`
- [ ] 实现 `POST /ppt/results/{result_id}/edit-snapshot`
- [ ] 实现 `GET /ppt/results/{result_id}`
- [ ] 实现 `POST /ppt/results/{result_id}/download`
- [ ] 实现 `GET /ppt/sessions/{session_id}/versions`

### 5.1 流式输出约束

- [ ] 所有流式接口统一使用 `StreamingResponse`
- [ ] 统一输出 `data: {"type":"..."}` 的 JSON 事件
- [ ] 不使用 `event: xxx` 自定义事件名
- [ ] 事件格式与教案页的流式解析逻辑兼容

### 5.2 渐进预览要求

- [ ] 若 Docmee 返回页级预览数据，则输出 `page_ready`
- [ ] 若暂时无法页级返回，则至少持续输出 `progress`
- [ ] 最终必须返回完整结果并支持预览恢复

**验证：**

- [ ] 使用 curl / Postman 验证 `text/event-stream`
- [ ] 验证大纲流
- [ ] 验证 PPT 生成流
- [ ] 验证错误事件

## Phase 6：前端 API 与页面主状态

**目标：** 在不引入额外复杂基础设施的前提下，搭建 PPT 页面业务主控。

- [ ] 新建 `teacher-platform/src/api/ppt.js`
- [ ] 复用 [http.js](/d:/123/AIsystem/teacher-platform/src/api/http.js) 的请求模式
- [ ] 封装：
  - [ ] 获取模板
  - [ ] 新建会话
  - [ ] 加载会话
  - [ ] 审批大纲
  - [ ] 获取结果
  - [ ] 保存编辑快照
  - [ ] 下载结果
  - [ ] 版本列表
- [ ] 改造 [LessonPrepPpt.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrepPpt.vue) 为 PPT 页面根组件
- [ ] 在根组件中维护：
  - [ ] 阶段状态
  - [ ] 当前会话
  - [ ] 消息列表
  - [ ] 当前大纲
  - [ ] 当前模板
  - [ ] 当前结果
  - [ ] 当前版本列表
  - [ ] 当前 `pptxObj`
  - [ ] 流式状态

### 6.1 前端流式实现

- [ ] 参考 [LessonPlanPage.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPlanPage.vue) 实现通用 `streamSSE`
- [ ] 使用 `fetch + reader`
- [ ] 解析 `data:` JSON
- [ ] 根据 `type` 字段分发更新页面状态

**验证：**

- [ ] 根组件能完成一次大纲流式生成
- [ ] 根组件能完成一次 PPT 生成流式更新

## Phase 7：欢迎页与对话页

**目标：** 落地 Stage 1 与 Stage 2。

- [ ] 创建 `WelcomePanel.vue`
- [ ] 创建 `TemplateSelector.vue`
- [ ] 创建 `KnowledgeLibraryModal.vue`
- [ ] 创建 `ChatPanel.vue`
- [ ] 创建 `ChatMessage.vue`
- [ ] 创建 `OutlineCard.vue`
- [ ] 创建 `PptResultCard.vue`
- [ ] 创建通用 `ChatInput.vue`

### 7.1 欢迎页要求

- [ ] 提供预设卡片
- [ ] 提供文本输入
- [ ] 提供模板选择入口
- [ ] 提供知识库选择入口

### 7.2 对话页要求

- [ ] 展示消息历史
- [ ] 展示流式文字
- [ ] 展示大纲卡片
- [ ] 支持编辑大纲
- [ ] 支持审批大纲
- [ ] 在已有大纲后继续追问

**验证：**

- [ ] 从欢迎页输入需求后可进入对话页
- [ ] 大纲卡片可编辑并提交

## Phase 8：预览页与官方渲染内核接入

**目标：** 落地 Stage 3 预览。

- [ ] 将官方 `ppt2svg.js` 复制到 `src/utils/`
- [ ] 将官方 `ppt2canvas.js` 复制到 `src/utils/`
- [ ] 处理必要依赖
- [ ] 创建 `PptCanvas.vue`
- [ ] 创建 `PptThumbnailList.vue`
- [ ] 创建 `PptToolbar.vue`
- [ ] 创建 `PptPreviewPanel.vue`

### 8.1 预览要求

- [ ] 支持缩略图切换
- [ ] 支持大图预览
- [ ] 支持窗口 resize
- [ ] 支持从服务端恢复预览
- [ ] 优先加载 `edited_pptx_property`

### 8.2 生成中预览要求

- [ ] 生成中显示进度
- [ ] 有 `page_ready` 时更新已完成页
- [ ] 无 `page_ready` 时仍显示进度与最终完整结果

**验证：**

- [ ] 可正确解压 `pptx_property`
- [ ] 缩略图和大图渲染正常
- [ ] 刷新后可恢复当前结果

## Phase 9：继续修改 PPT 成品

**目标：** 在预览阶段支持“继续修改”并生成新版本。

- [ ] 在 `PptPreviewPanel.vue` 中保留聊天输入入口
- [ ] 输入修改指令后调用 `/results/{id}/modify`
- [ ] 后端基于当前大纲 / 当前结果 / 用户指令创建新版本
- [ ] 前端在生成新版本时更新进度
- [ ] 新版本完成后更新当前结果并保留旧版本

**验证：**

- [ ] 用户可在预览阶段输入修改指令
- [ ] 会生成新的 PPT 结果版本
- [ ] 可在版本列表中切换回旧版本

## Phase 10：元素级在线编辑

**目标：** 支持预览中的元素级编辑并保存快照。

- [ ] 在 `PptCanvas.vue` 中接入官方 edit 模式
- [ ] 暴露 `onchange` 回调
- [ ] 在根组件中维护“已编辑未保存”状态
- [ ] 支持保存编辑快照到后端
- [ ] 支持刷新后恢复编辑态

### 10.1 本次交付最少支持

- [ ] 文本编辑
- [ ] 位置拖拽
- [ ] 缩放
- [ ] 旋转

### 10.2 保存约束

- [ ] 保存时提交最新 `edited_pptx_property`
- [ ] 后端持久化后更新当前结果

**验证：**

- [ ] 编辑文本后刷新仍可恢复
- [ ] 拖拽、缩放、旋转后保存成功

## Phase 11：版本管理与版本对比

**目标：** 支持大纲版本与 PPT 结果版本查看、切换、对比。

- [ ] 在侧栏中展示会话历史
- [ ] 在当前会话中展示大纲版本列表
- [ ] 展示 PPT 结果版本列表
- [ ] 创建 `PptVersionCompareDialog.vue`
- [ ] 支持选择两个版本做对比

### 11.1 对比范围

- [ ] 大纲文本内容
- [ ] 模板与知识库差异
- [ ] PPT 结果缩略图与元信息
- [ ] 是否包含元素编辑快照

**验证：**

- [ ] 同一会话中能看到多个版本
- [ ] 可并排查看两个版本

## Phase 12：错误处理与恢复

**目标：** 补齐可用性。

- [ ] Docmee 接口失败提示
- [ ] Unsplash 接口失败提示
- [ ] SSE 中断提示
- [ ] 权限错误处理
- [ ] 会话不存在兜底
- [ ] 生成中禁止重复提交
- [ ] 页面刷新恢复当前会话 / 当前结果 / 当前编辑态

**验证：**

- [ ] 模拟接口失败
- [ ] 模拟流中断
- [ ] 模拟会话恢复

## Phase 13：测试

**目标：** 关键路径可验证。

### 13.1 后端测试

- [ ] `tests/test_ppt_models.py`
- [ ] `tests/test_docmee_client.py`
- [ ] `tests/test_image_search.py`
- [ ] `tests/test_ppt_workflow.py`
- [ ] `tests/test_ppt_api.py`

### 13.2 前端测试

- [ ] 流式解析函数测试
- [ ] `pptx_property` 解压测试
- [ ] 关键组件渲染测试

### 13.3 联调验证

- [ ] 创建会话
- [ ] 生成大纲
- [ ] 配图
- [ ] 审批
- [ ] 生成 PPT
- [ ] 预览
- [ ] 继续修改
- [ ] 元素编辑
- [ ] 版本对比
- [ ] 下载

## Phase 14：文档与交付整理

**目标：** 让功能可以被真实使用和维护。

- [ ] 更新 README
- [ ] 补充环境变量说明
- [ ] 写使用说明
- [ ] 写接口说明
- [ ] 写部署检查项

## 4. 时间评估

本计划对应一次性交付版本，时间评估需要更现实。

### 建议总工期

- 15 到 20 个工作日

### 建议拆分

- 3 天：数据库、模型、Docmee 客户端
- 3 天：工作流、自动配图、后端流式接口
- 4 天：欢迎页、对话页、预览页基础
- 3 天：继续修改、元素编辑、版本管理
- 2 到 4 天：联调、测试、文档、修复

## 5. 关键风险与应对

### 风险 1：Docmee 渐进预览能力与 V2 主链路不完全一致

应对：

- 优先按 V2 实现业务主链路
- 必要时在后端内部做兼容适配
- 前端不感知具体 Docmee 细节

### 风险 2：元素级编辑后导出链路边界不清晰

应对：

- 本次先确保编辑快照可保存、可恢复、可继续修改参考
- 下载默认保留最近生成结果下载能力
- 在界面中清晰提示编辑态与下载稿关系

### 风险 3：版本对比功能范围失控

应对：

- 本次版本对比以并排查看为主
- 不做像素级 diff
- 重点保证“能切换、能看差异、能回退”

## 6. Claude 实施提示

若将本计划交给 Claude / Codex / 其他 agentic 工具实施，必须遵守：

- 优先复用现有项目代码模式
- 不引入新的前端请求体系
- 不用原生 `EventSource`
- 不新增 WebSocket 方案
- 不让前端直连 Docmee
- 不把当前交付拆成一期 / 二期
- 不因为实现难度而删除：
  - 自动配图
  - 继续修改 PPT 成品
  - 元素级在线编辑
  - 版本对比

### 6.1 可直接发送给 Claude 的实施约束摘要

下面这段可以直接作为实现任务说明发送给 Claude。建议与规格文档、计划文档一起提供。

```text
请基于以下约束，直接在当前项目中实现 AI PPT 功能，不要重新发明一套新架构，也不要擅自缩 scope：

1. 交付目标
- 本次是单次交付版本，不拆一期 / 二期。
- 目标是代码写完后，该功能在当前项目中可以直接跑通主链路。
- 必须保留这些能力：自动配图、继续修改 PPT 成品、元素级在线编辑、版本管理与版本对比、完整会话恢复、预览、下载。

2. 前端技术约束
- PPT 页面入口直接复用 `teacher-platform/src/views/LessonPrepPpt.vue`。
- 不新增 tab，不改造 `LessonPrep.vue` 的页面导航结构。
- 前端请求层复用 `teacher-platform/src/api/http.js` 的模式，不要新起一套 axios 或其他请求体系。
- 流式方案必须复用教案页 `teacher-platform/src/views/LessonPlanPage.vue` 的 `fetch + reader` 模式。
- 不使用原生 `EventSource`。
- 不新增 WebSocket 替代 SSE，但仍然必须保留流式生成体验。
- SSE 统一使用 `text/event-stream`，前端解析 `data: {...}` JSON，并根据 `type` 分发事件。

3. Docmee 接入约束
- 前端不能直连 Docmee。
- 前端不能持有 Docmee token。
- 所有 Docmee 请求统一由后端代理。
- 业务主链路优先按 Docmee V2 设计。
- 如果渐进预览必须兼容旧接口，这个兼容逻辑只能放在后端，前端不感知 V1 / V2 差异。

4. PPT 预览与编辑约束
- 预览必须优先复用 Docmee 官方渲染能力：`ppt2svg.js`、`ppt2canvas.js`。
- 需要支持缩略图列表、大图预览、生成中进度更新、结果恢复。
- 元素级编辑至少支持：文本编辑、位置移动、缩放、旋转。
- 元素编辑保存为编辑快照，不要因为导出链路暂时复杂就删掉这个能力。
- 预览阶段的“继续修改 PPT”与“元素级在线编辑”是两条并行能力，都要保留。

5. 后端实现约束
- 数据库变更必须走 Alembic。
- 新增 PPT 会话、大纲版本、消息记录、PPT 结果版本等核心模型。
- LangGraph 需要保留，但只围绕业务主链路实现：知识检索、生成大纲、自动配图、审批中断、生成 PPT、继续修改再生成。
- 不要为了“图编排很完整”而过度设计。
- 服务层注意不要写错误的 `async with get_db() as db` 这种模式。

6. 版本能力约束
- 大纲版本要保留。
- PPT 结果版本要保留。
- 版本对比必须可用，但采用务实方案：
  - 支持用户选两个版本并排查看
  - 支持看大纲文本差异、模板差异、缩略图差异、生成时间、是否有编辑快照
  - 不要求做像素级 diff

7. 明确不要做的事
- 不要把功能拆成一期 / 二期再交付。
- 不要删除自动配图。
- 不要删除继续修改 PPT 成品。
- 不要删除元素级在线编辑。
- 不要删除版本对比。
- 不要把 SSE 改成 WebSocket。
- 不要让前端直接调用 `docmee.cn`。
- 不要为了省事跳过 Alembic。

8. 实现优先级
- 先打通后端数据模型、Docmee 代理、流式接口。
- 再打通前端页面主状态、欢迎页、对话页、流式生成。
- 再接入官方预览内核。
- 再补继续修改、元素级编辑、版本管理与版本对比。
- 最后做错误处理、恢复能力、测试和文档。

9. 完成标准
- 用户可以新建 PPT 会话。
- 用户可以选择知识库和模板。
- 用户可以流式生成并审批大纲。
- 用户可以看到自动配图结果。
- 用户可以流式看到 PPT 生成进度。
- 用户可以在预览页浏览缩略图和大图。
- 用户可以继续通过聊天修改 PPT，并生成新版本。
- 用户可以直接编辑预览中的文本 / 位置 / 缩放 / 旋转，并保存快照。
- 用户可以查看并对比版本。
- 用户刷新页面后可以恢复最近状态。
- 用户可以下载结果。

如果实现过程中发现 Docmee 某个能力和预期不完全一致，不要直接删功能，优先通过后端兼容、降级展示、补充状态说明来保住整体链路。
```

## 7. 完成定义

只有以下事项全部达成，才算计划完成：

- 后端接口可用
- 前端完整链路可跑通
- 所有本次交付功能均已上线到当前项目
- 核心测试通过
- 文档补齐
