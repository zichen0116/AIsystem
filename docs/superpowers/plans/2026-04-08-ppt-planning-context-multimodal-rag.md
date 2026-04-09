# PPT Planning Context 与多模态 RAG 实施计划

> 执行目标：完成对话模式下的 `Planning Context + 多模态解析 + 知识库检索` 闭环，并确保前后端都可回归验证。

## 总体原则

1. 先稳定共享解析器，再接 PPT 后端，再接前端交互。
2. `Planning Context` 先用单个 `textarea` 承载，不做富文本编辑器。
3. 项目资料检索 v1 采用轻量排序，不引入新的项目级向量索引。
4. 旧知识库资产重解析先提供脚本入口，不做前端 UI。

## Chunk 1：PptHome 入口改造

- 接入知识库选择器，区分 `个人知识库 / 系统知识库`
- 在项目创建请求中写入 `knowledge_library_ids`
- 对话模式参考资料改为真实上传
- 上传成功后立即触发参考资料解析任务

验收：

- 新建对话项目后，后端能看到 `knowledge_library_ids`
- 上传的图片/视频/文档在后端有真实文件记录

## Chunk 2：项目状态恢复

- store 增加：
  - `selectedKnowledgeLibraryIds`
  - `planningContext`
  - `planningContextSections`
  - `planningContextMeta`
  - `planningContextDirty`
- 重新进入项目时恢复：
  - 已选知识库
  - 参考文件列表
  - Planning Context

验收：

- 历史项目重新进入 outline 页时能继续看到上次保存的构想和资料状态

## Chunk 3：独立 reference_parse 任务链

- 新增 `reference_parse` 任务类型
- 新增 dispatcher / runner 分发
- 上传参考资料后只解析资料，不创建页面、不动 outline
- 上传接口改为真实保存到 OSS 或本地 fallback

验收：

- 参考资料解析不会误触发 `file_generation_task`
- `GET /reference-files` 能看到解析状态与错误信息

## Chunk 4：Gemini 多模态解析

- 图片解析改为 `Gemini-primary + legacy fallback`
- 视频解析改为 `Gemini-primary + legacy fallback`
- fallback 只在硬失败时自动触发
- 结果统一补充元数据：
  - `parser_provider`
  - `fallback_reason`
  - `is_partial`
  - `searchable_text`

验收：

- Gemini 成功时标记 `parser_provider=gemini`
- Gemini 硬失败时标记 `parser_provider=legacy_fallback`

## Chunk 5：Planning Context 服务与接口

- 新增 `planning_context_service`
- 新增 `POST /planning-context/refresh`
- 固定输出四段式 sections 与可编辑文本
- 支持 `partial=true`
- 持久化到 `project.settings`

验收：

- 未完成解析的资料不会阻塞 refresh
- refresh 可以返回待完成文件列表

## Chunk 6：PptOutline 交互改造

- 左侧构想框替换为四段式 `Planning Context`
- 页面首次进入自动刷新一次构想
- 新增按钮：
  - `刷新构想`
  - `生成大纲`
- 去掉自动生成大纲逻辑
- 用户编辑后标记 dirty，后续异步结果不自动覆盖

验收：

- 进入 outline 页只看到构想，不会直接开始生成大纲
- 用户修改构想后，只能手动刷新覆盖

## Chunk 7：大纲与页面描述生成接入

- 大纲生成消费：
  - `planning_context_text`
  - 用户补充要求
- 页面描述生成消费：
  - 已保存的 `planning_context_text`
  - 项目资料局部检索
  - 知识库局部检索

验收：

- 修改构想框内容后，生成结果会随之变化
- 页面描述能体现当前页的资料来源和知识补充

## Chunk 8：旧知识库资产重解析脚本

- 新增 `backend/scripts/reparse_multimodal_assets.py`
- 支持：
  - `--library-id`
  - `--asset-id`
  - `--types image,video`
  - `--dry-run`
- 每个目标资产先删除旧向量，再调用最新共享 parser 重建

验收：

- `--dry-run` 仅列出目标资产
- 指定资产或指定库可以重解析，不做全量重跑

## Chunk 9：联调与回归

后端验证：

- `pytest tests/test_ppt_planning_context.py`
- `pytest tests/test_multimodal_fallback.py`
- `pytest tests/test_reparse_multimodal_assets.py`
- `py_compile` 校验修改文件

前端验证：

- `npm run build`

联调重点：

- 知识库选择
- 参考资料真实上传
- Planning Context 首次自动刷新
- 构想框编辑保护
- 手动生成大纲
- 页面描述融合资料与知识库

## 风险与处理

### 风险 1：Gemini 不可用

- 处理：自动回退到旧链路，仅在硬失败时触发

### 风险 2：资料解析较慢

- 处理：refresh 返回 `partial`，允许先生成大纲

### 风险 3：历史知识库资产仍是旧解析结果

- 处理：只提供脚本式重解析，比赛阶段回填演示库

### 风险 4：用户手改构想被系统覆盖

- 处理：dirty 后仅提示刷新，不自动写回
