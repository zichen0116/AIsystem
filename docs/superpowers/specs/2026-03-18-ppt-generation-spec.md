# AI PPT 生成功能规格说明（单次交付版）

更新时间：2026-03-18

## 1. 文档目标

本文档定义当前项目中的 AI PPT 生成功能规格。本文档对应的是一次性交付版本，不做“一期 / 二期”拆分；实现顺序可以分阶段推进，但交付目标是功能整体可用。

本次交付在保留完整业务能力的前提下，统一技术路线，避免实现过程中出现以下问题：

- 前端流式方案与现有项目模式不一致
- Docmee 接入路线摇摆
- 预览能力与业务接口脱节
- 过度理想化的工作流设计阻塞主功能落地

## 2. 本次交付范围

### 2.1 必须实现

- 新建 PPT 会话、查看历史会话、恢复上次进度
- 选择知识库并结合知识库生成 PPT 大纲
- 选择模板并生成 PPT
- 大纲流式生成
- 大纲编辑、审批、版本保留
- 自动配图
- PPT 生成进度流式更新
- 使用官方 `ppt2svg` / `ppt2canvas` 进行缩略图与大图预览
- 预览阶段继续通过聊天方式修改 PPT 成品
- 预览阶段支持元素级在线编辑
  - 本次交付范围内至少支持文本编辑、位置移动、缩放、旋转
- PPT 结果版本保留与版本对比
- 下载生成结果

### 2.2 明确不做

- WebSocket 替代 SSE

说明：

- 本次交付仍然保留流式生成能力。
- 流式传输继续使用 `text/event-stream + fetch + reader`，不额外引入 WebSocket。

## 3. 与现有项目对齐的核心决策

| 主题 | 决策 |
|------|------|
| 前端入口 | 复用现有 [LessonPrepPpt.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrepPpt.vue) 作为页面入口，不新增新的课前准备 tab |
| 前端流式方案 | 复用教案页 [LessonPlanPage.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPlanPage.vue) 的 `fetch + reader` 模式，不使用原生 `EventSource` |
| 前端 API 基础设施 | 复用 [http.js](/d:/123/AIsystem/teacher-platform/src/api/http.js) 的 `resolveApiUrl` / `authFetch` / `apiRequest` 模式，不新建 axios 体系 |
| 后端接入方式 | 所有 Docmee 请求均由后端代理，前端不直连 Docmee |
| Docmee 主路线 | 业务主链路优先使用 Docmee V2；如渐进预览必须依赖旧接口，由后端在内部做兼容适配，前端不感知 V1 / V2 差异 |
| PPT 预览 | 复用 Docmee 官方前端项目中的 `ppt2svg.js` 与 `ppt2canvas.js`，并在当前项目内封装使用 |
| 数据库存储 | 使用 Alembic 管理迁移；不依赖 `create_all` 作为最终交付方案 |
| 状态管理 | 页面主状态以 PPT 页面根组件管理为主，可按需拆出 API/预览辅助模块；避免为了功能上线额外引入不必要的全局复杂度 |
| LangGraph 作用 | LangGraph 用于支撑知识检索、生成、审批中断、修改再生成等核心业务流程，但设计必须服务业务，不追求过度复杂的图结构 |
| 安全策略 | Markdown 渲染必须显式做转义或 sanitize，不能直接假设 `marked` 自动安全 |

## 4. 用户流程

### 4.1 阶段 1：欢迎页

用户进入 PPT 页面后，默认进入欢迎页。

欢迎页包含：

- 标题与引导说明
- 常用预设卡片
- 文本输入框
- 模板入口
- 知识库选择入口
- 可选附件入口

用户可以通过三种方式进入生成流程：

- 点击预设卡片
- 直接输入需求
- 先选择模板 / 知识库，再输入需求

### 4.2 阶段 2：对话与大纲页

用户输入需求后进入对话页。

对话页负责：

- 展示用户消息与系统消息
- 展示流式生成中的文字
- 展示当前大纲卡片
- 支持编辑大纲
- 支持审批大纲
- 在已有大纲基础上继续补充需求

当用户审批通过后，系统开始 PPT 生成。

### 4.3 阶段 3：预览页

PPT 进入生成或生成完成后进入预览页。

预览页负责：

- 左侧显示聊天上下文与继续修改输入框
- 左侧显示缩略图列表
- 右侧显示大图预览
- 显示生成进度
- 支持切换版本
- 支持元素级编辑
- 支持保存编辑快照
- 支持下载

### 4.4 继续修改 PPT 成品

继续修改是本次交付范围内必须支持的能力。

定义如下：

- 用户在预览阶段输入自然语言修改要求
- 系统基于“当前有效大纲 + 当前 PPT 结果 + 用户指令”重新生成新的大纲版本和 / 或新的 PPT 版本
- 新版本生成后保留旧版本，用户可以做版本对比并切换

该能力是“内容层修改”的主链路。

### 4.5 元素级在线编辑

元素级在线编辑也是本次交付范围内必须支持的能力。

定义如下：

- 基于官方 `ppt2svg` 的编辑能力在前端直接修改当前预览对象
- 至少支持文本修改、移动、缩放、旋转
- 编辑结果保存为当前 PPT 结果的“编辑态快照”
- 用户刷新页面后可以恢复编辑态

说明：

- 元素编辑与“继续修改 PPT 成品”是两条并行能力
- 内容级修改用于重新生成
- 元素级编辑用于快速微调展示

## 5. 总体架构

### 5.1 后端架构

后端新增 `app/services/ppt/` 模块，职责如下：

- Docmee API 封装
- 大纲生成与审批工作流
- 自动配图
- 结果版本管理
- 编辑快照持久化
- SSE 流式输出

核心分层：

- `models/`：PPT 会话、消息、大纲、结果
- `schemas/`：PPT 相关请求与响应
- `services/ppt/`：Docmee、工作流、图片搜索、编辑快照
- `api/ppt.py`：对外 REST / SSE 接口

### 5.2 前端架构

前端沿用当前项目的“页面根组件负责业务编排，子组件负责显示”的模式。

入口页面：

- [LessonPrepPpt.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrepPpt.vue)

页面根组件负责：

- 当前阶段切换
- 流式请求控制
- 会话加载与恢复
- 当前消息 / 大纲 / 模板 / 结果 / 版本状态

子组件负责：

- 欢迎页
- 聊天流
- 大纲卡片
- PPT 结果卡片
- 预览面板
- 缩略图列表
- 工具栏
- 版本对比弹窗

### 5.3 流式协议

本项目不使用原生 `EventSource`。

统一采用：

- 后端返回 `text/event-stream`
- 前端使用 `fetch + reader`
- 每个 SSE 块统一只发送 `data: {...}\n\n`
- 前端通过 JSON 中的 `type` 字段区分事件类型

这样可以直接复用教案页的解析逻辑，减少协议复杂度。

## 6. Docmee 集成策略

### 6.1 主路线

业务主链路优先按 Docmee V2 设计，能力目标包括：

- 创建任务
- 生成内容 / 大纲
- 更新内容
- 生成 PPT
- 加载 PPT
- 下载 PPT
- 查询模板

### 6.2 兼容策略

若 Docmee 渐进预览能力在实际接入时需要依赖旧接口，例如：

- 生成过程中轮询当前页数
- 在生成进行中读取临时 `pptxProperty`

则由后端封装为统一服务能力，前端仍只使用本项目自己的 `/api/v1/ppt/...` 接口。

### 6.3 前端不直接持有 Docmee token

禁止前端直接：

- 创建 Docmee API token
- 直接请求 `https://docmee.cn/api/...`
- 在浏览器保存 Docmee 凭证

所有 Docmee token 均由后端读取环境变量并代理请求。

## 7. 数据模型设计

### 7.1 `ppt_sessions`

表示一次完整的 PPT 创作会话。

关键字段：

- `id`
- `user_id`
- `title`
- `status`
- `current_outline_id`
- `current_result_id`
- `created_at`
- `updated_at`

建议状态：

- `draft`
- `generating_outline`
- `outline_ready`
- `generating_ppt`
- `preview_ready`
- `completed`
- `failed`

### 7.2 `ppt_outlines`

表示会话中的大纲版本。

关键字段：

- `id`
- `session_id`
- `version`
- `content`
- `image_urls`
- `template_id`
- `knowledge_library_ids`
- `is_current`
- `created_at`

说明：

- 大纲审批、修改、继续生成都要保留版本

### 7.3 `ppt_messages`

表示用户与系统在会话中的消息记录。

关键字段：

- `id`
- `session_id`
- `role`
- `message_type`
- `content`
- `metadata`
- `created_at`

建议 `message_type`：

- `text`
- `outline`
- `ppt_result`
- `error`
- `system`

### 7.4 `ppt_results`

表示某个会话中的 PPT 结果版本。

关键字段：

- `id`
- `session_id`
- `outline_id`
- `version`
- `is_current`
- `template_id`
- `docmee_ppt_id`
- `source_pptx_property`
- `edited_pptx_property`
- `file_url`
- `status`
- `current_page`
- `total_pages`
- `created_at`
- `completed_at`

说明：

- `source_pptx_property` 表示 Docmee 返回的原始预览数据
- `edited_pptx_property` 表示前端元素编辑后保存的最新快照
- 预览时优先使用 `edited_pptx_property`，没有则退回 `source_pptx_property`

## 8. 后端接口设计

### 8.1 模板与会话

- `GET /api/v1/ppt/templates`
  - 获取模板列表
  - 由后端代理 Docmee 模板接口

- `POST /api/v1/ppt/sessions`
  - 创建会话

- `GET /api/v1/ppt/sessions`
  - 获取当前用户的会话列表

- `GET /api/v1/ppt/sessions/{session_id}`
  - 获取会话详情
  - 返回消息列表、当前大纲、当前 PPT 结果、结果版本列表

### 8.2 大纲生成与审批

- `POST /api/v1/ppt/stream/outline`
  - 流式生成大纲
  - 输入：`session_id`、`user_input`、`knowledge_library_ids`、`template_id`

- `POST /api/v1/ppt/outlines/{outline_id}/approve`
  - 审批大纲
  - 可带修改后的大纲内容

### 8.3 PPT 生成与修改

- `POST /api/v1/ppt/stream/generate`
  - 流式生成 PPT
  - 输入：`session_id`、`outline_id`、`template_id`

- `POST /api/v1/ppt/results/{result_id}/modify`
  - 在当前 PPT 基础上继续修改
  - 输入：自然语言修改指令
  - 结果：创建新的大纲版本和 / 或新的 PPT 版本

### 8.4 编辑态保存与结果恢复

- `POST /api/v1/ppt/results/{result_id}/edit-snapshot`
  - 保存编辑后的 `pptx_property`

- `GET /api/v1/ppt/results/{result_id}`
  - 获取指定 PPT 结果详情

- `POST /api/v1/ppt/results/{result_id}/download`
  - 获取下载地址

### 8.5 版本对比

- `GET /api/v1/ppt/sessions/{session_id}/versions`
  - 返回大纲版本与 PPT 结果版本摘要

版本对比本次交付采用务实设计：

- 大纲版本对比：比较文本内容、更新时间、关联模板、关联结果
- PPT 版本对比：比较版本元信息、缩略图、关联大纲、生成时间、编辑状态

不做像素级自动 diff，但必须支持用户在界面中选两个版本并进行并排查看。

## 9. SSE 事件协议

### 9.1 大纲流

后端统一输出 JSON 事件：

```text
data: {"type":"meta","session_id":1}

data: {"type":"assistant_chunk","content":"我将先整理需求..."}

data: {"type":"outline_chunk","content":"# 标题\n"}

data: {"type":"outline_ready","outline_id":12,"content":"...","image_urls":{}}

data: {"type":"done"}
```

### 9.2 PPT 生成流

```text
data: {"type":"progress","current":1,"total":10,"result_id":8}

data: {"type":"page_ready","page_index":0,"pptx_property":"..."}

data: {"type":"result_ready","result_id":8,"ppt_id":"docmee_xxx","file_url":"..."}

data: {"type":"done"}
```

### 9.3 错误事件

所有流式接口统一使用：

```text
data: {"type":"error","message":"..."}
```

## 10. 前端组件设计

建议目录：

```text
teacher-platform/src/components/ppt/
├── PptWorkspace.vue
├── PptSidebar.vue
├── WelcomePanel.vue
├── TemplateSelector.vue
├── KnowledgeLibraryModal.vue
├── ChatPanel.vue
├── ChatMessage.vue
├── OutlineCard.vue
├── PptResultCard.vue
├── PptPreviewPanel.vue
├── PptThumbnailList.vue
├── PptCanvas.vue
├── PptToolbar.vue
├── PptVersionCompareDialog.vue
└── ChatInput.vue
```

说明：

- 入口页仍为 [LessonPrepPpt.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrepPpt.vue)
- 上述组件目录用于承载新 PPT 功能

## 11. 预览与编辑设计

### 11.1 预览

使用官方渲染工具：

- `ppt2svg.js`：大图预览
- `ppt2canvas.js`：缩略图

前端在读取结果时执行：

1. 取 `edited_pptx_property`
2. 若为空，则取 `source_pptx_property`
3. 解压为对象
4. 渲染缩略图与当前页

### 11.2 元素编辑

元素编辑基于官方 `ppt2svg` 的 edit 模式实现。

本次交付支持：

- 文本修改
- 位置拖拽
- 缩放
- 旋转

编辑行为触发时：

1. 更新当前 `pptxObj`
2. 标记当前结果为“已编辑未保存”
3. 用户点击保存后调用 `edit-snapshot` 接口
4. 后端保存最新 `edited_pptx_property`

### 11.3 下载行为

下载默认下载当前有效 PPT 结果。

若存在已保存的编辑快照，则界面需要明确提示：

- 当前下载对应最近一次生成结果
- 编辑快照主要用于会话内预览恢复与继续修改参考

说明：

- 若后续确认 Docmee 或本地转换链路支持“编辑快照导出为真实 PPTX”，可在实现中扩展
- 但本次交付不能因为导出能力未完全闭环而放弃元素编辑

## 12. 自动配图设计

自动配图是本次交付必须实现能力。

设计如下：

- 大纲生成后解析每一页标题
- 通过 LLM 将页面标题翻译为英文图片搜索关键词
- 调用 Unsplash 搜索横版图片
- 将结果写入大纲版本的 `image_urls`
- 对话页的大纲卡片中展示图片预览

错误处理要求：

- 自动配图失败不阻塞大纲审批
- 无图时依然允许继续生成 PPT

## 13. LangGraph 工作流设计

本次交付保留 LangGraph，但要求围绕业务主链路设计，不追求炫技式编排。

建议主流程：

1. 用户输入需求
2. 检索知识库
3. 生成大纲
4. 自动配图
5. 大纲审批中断
6. 审批通过后生成 PPT
7. 结果入库
8. 继续修改时基于当前有效状态重新进入生成流程

要求：

- 支持审批中断恢复
- 支持继续修改触发新版本
- 支持失败重试
- 工作流节点数保持在“可测试、可维护”的范围内

## 14. 安全与约束

### 14.1 安全要求

- 所有 PPT 相关接口必须校验 JWT
- 会话 / 大纲 / 结果必须按 `user_id` 做鉴权
- 前端不得保存 Docmee token
- Markdown 渲染必须转义或 sanitize

### 14.2 工程约束

- 前端流式请求必须复用当前项目模式
- 后端数据库变更必须走 Alembic
- 服务层不得直接使用错误的 `async with get_db() as db` 写法
- 当前交付版本不引入 WebSocket

## 15. 验收标准

以下全部满足，视为当前单次交付完成：

- 用户能新建 PPT 会话
- 用户能选择知识库与模板
- 用户能输入需求并流式生成大纲
- 用户能看到自动配图结果
- 用户能编辑并审批大纲
- 用户能流式看到 PPT 生成进度
- 用户能在预览页浏览缩略图与大图
- 用户能通过聊天继续修改 PPT
- 用户能直接编辑预览中的文本 / 位置 / 尺寸 / 旋转并保存
- 用户能看到版本列表并做版本对比
- 用户能刷新后恢复最近状态
- 用户能下载结果

## 16. 实现风险

### 高风险

- Docmee V2 与渐进预览能力在真实项目中的匹配程度
- 元素编辑后的导出链路能力边界
- 版本对比 UI 的复杂度

### 中风险

- 自动配图的稳定性与速率限制
- LangGraph 审批中断恢复
- 预览渲染在大文件上的性能

### 低风险

- 欢迎页 / 聊天页 / 预览页的 UI 组装
- 会话历史与版本列表展示

## 17. 成功原则

本功能的成功不是“架构最复杂”，而是：

- 在当前项目中真实可用
- 与现有代码风格一致
- Claude 可以按文档直接实施
- 用户从输入需求到下载 PPT 的完整链路可跑通

## 18. 实施备注

若将本规格直接交给 Claude / Codex / 其他 agentic 工具实施，默认还必须遵守以下约束：

- 本次交付为单次交付版本，不拆一期 / 二期
- 不得因为实现难度删除自动配图、继续修改 PPT 成品、元素级在线编辑、版本管理与版本对比
- 只移除“WebSocket 替代 SSE”，但必须保留流式生成体验
- 前端流式方案必须复用教案页的 `fetch + reader` 模式，不使用原生 `EventSource`
- PPT 页面入口复用 [LessonPrepPpt.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrepPpt.vue)，不新增 tab，不调整 [LessonPrep.vue](/d:/123/AIsystem/teacher-platform/src/views/LessonPrep.vue) 导航结构
- 前端请求层复用 [http.js](/d:/123/AIsystem/teacher-platform/src/api/http.js) 的模式，不新起一套 axios / 请求体系
- 前端不能直连 Docmee，不能持有 Docmee token，所有 Docmee 请求统一由后端代理
- Docmee 主链路优先按 V2 设计；如渐进预览需兼容旧接口，只能在后端做兼容，前端不感知 V1 / V2 差异
- 预览必须优先复用官方 `ppt2svg.js` / `ppt2canvas.js`
- 元素级编辑至少支持文本编辑、位置移动、缩放、旋转，且编辑快照必须可保存、可恢复
- 数据库变更必须走 Alembic
- LangGraph 需要保留，但只围绕业务主链路实现，不做过度复杂编排

实现优先级建议：

1. 先打通后端数据模型、Docmee 代理、流式接口
2. 再打通前端页面主状态、欢迎页、对话页、流式生成
3. 再接入官方预览内核
4. 再补继续修改、元素级编辑、版本管理与版本对比
5. 最后补错误处理、恢复能力、测试和文档
