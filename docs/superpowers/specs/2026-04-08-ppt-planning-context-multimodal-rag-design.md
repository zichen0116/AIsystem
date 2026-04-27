# PPT 对话生成 Planning Context 与多模态 RAG 设计

## 概述

本设计将 `PPT 对话生成` 从“直接拿对话文本生成大纲”升级为“先构建 Planning Context，再由用户确认后生成大纲和页面描述”的可解释流程。  
本次只覆盖 `creation_type='dialog'` 的 PPT 生成链路，重点打通三类上下文：

1. 用户意图
2. 项目内参考资料的多模态解析结果
3. 知识库检索结果

最终生成链路固定为：

`用户意图 + 项目资料解析 + 知识库补充 -> Planning Context -> 用户确认/编辑 -> 生成大纲 -> 生成页面描述`

## 设计目标

1. 在大纲页左侧显式展示系统对本次 PPT 的规划结果，提升可解释性。
2. 让上传的图片、视频、文档不只是“存起来”，而是真正参与大纲和页面描述生成。
3. 让 `knowledge_library_ids` 在对话模式下成为真实可用的检索输入。
4. 将图片/视频解析升级为 `Gemini-primary + 旧链路 fallback`，并同时覆盖 PPT 项目资料解析与知识库资产入库解析。
5. 把项目资料解析任务从 `file_generation_task` 中拆出，避免逻辑复用错位。

## 用户交互

### PptHome

- 新增知识库选择器，样式与“教案生成”一致，区分 `个人知识库 / 系统知识库`。
- 对话模式支持上传 `pdf/doc/docx/ppt/pptx/png/jpg/jpeg/webp/gif/mp4/mov/avi/mkv`。
- 创建项目时保存 `knowledge_library_ids`。
- 创建项目成功后，参考资料立即真实上传到后端，并触发独立的异步解析任务。

### PptOutline

- 左侧 `PPT构想框` 升级为四段式 `Planning Context`，顺序固定为：
  1. 用户意图摘要
  2. 项目资料提炼
  3. 知识库补充
  4. 生成策略
- 进入页面后自动刷新一次 `Planning Context`，但不再自动生成大纲。
- 用户可直接编辑该构想框。
- 按钮固定为：
  - `刷新构想`
  - `生成大纲`

### 编辑与覆盖规则

- 用户手动编辑构想框后，任何异步解析完成都不得自动覆盖当前文本。
- 若有新的解析结果到达，只提示“有新的资料解析结果可用，点击刷新构想即可更新”。
- `刷新构想` 允许返回 `partial=true`；即使仍有资料未解析完成，`生成大纲` 也不禁用，只提示“当前基于已完成解析内容生成”。

## Planning Context 结构

`Planning Context` 面向用户展示，默认拼接为单个可编辑 `textarea` 文本，但后端会同时保存结构化 sections。

### 四段定义

#### 1. 用户意图摘要

- 主题
- 学段/学科
- 页数要求
- 课型/目标
- 风格偏好
- 用户强调的重点知识点

#### 2. 项目资料提炼

- 项目上传资料中提取出的知识点、案例、实验步骤、图示含义、可复用视觉元素
- 图片/视频解析结果优先走 Gemini
- 文本/结构化文档继续走本地解析器

#### 3. 知识库补充

- 来自 `knowledge_library_ids` 对应知识库的检索摘要
- 侧重标准定义、补充事实、教学案例、章节背景

#### 4. 生成策略

- 推荐页数分配
- 各页重点
- 哪些资料用于内容知识，哪些资料用于风格参考
- 哪些知识库内容用于补充讲解

## Prompt 边界

- `Planning Context` 不是最终 prompt 全文。
- 前端展示的是“用户可读、可编辑的规划摘要”。
- 后端发给模型的实际 prompt 由三部分组成：
  1. 系统约束
  2. 格式与 JSON 输出规则
  3. `Planning Context` 数据块

这条边界必须保持稳定，避免前端展示文本直接污染模型输出格式。

## 后端架构

### 1. 独立参考资料解析任务

- 新增 `reference_parse` 任务类型。
- `POST /projects/{project_id}/reference-files/{file_id}/parse` 不再复用 `file_generation_task`，而是只负责解析并回写 `PPTReferenceFile.parsed_content`。
- `GET /projects/{project_id}/reference-files` 用于前端获取历史项目的文件列表与解析状态。

### 2. Planning Context 服务

新增 `planning_context_service`，职责如下：

- 读取 `PPTProjectIntent`
- 汇总 `PPTReferenceFile.parsed_content`
- 检索 `knowledge_library_ids`
- 生成四段式 sections 与拼接文本
- 将结果写入 `PPTProject.settings`

持久化键固定为：

- `planning_context_sections`
- `planning_context_text`
- `planning_context_meta`

### 3. 图片/视频解析升级

共享 `image_parser` / `video_parser` 升级为：

- 默认：`Gemini-primary`
- 回退：`legacy fallback`

#### fallback 规则

- 硬失败自动 fallback：
  - API 调用失败
  - 超时
  - 鉴权或配额问题
  - 返回空结果
  - 结构化输出解析失败
- 软失败不自动 fallback：
  - Gemini 返回了结果，但质量一般、内容太泛
  - 此类情况仅记录日志，不切回旧链路

解析结果必须带元数据：

- `parser_provider: gemini | legacy_fallback`
- `fallback_reason?: string`
- `is_partial?: bool`

### 4. 项目资料检索

项目资料检索 v1 不创建项目级向量库，而是直接使用：

- `parsed_content.searchable_text`
- `parsed_content.chunks_meta`

排序规则固定：

- query = `意图摘要 + 当前任务主题 (+ 当前页标题/要点)`
- 按关键词重叠、标题命中、结构化字段命中加权
- 每类来源取 top 2-3 段

### 5. 知识库检索

- 继续复用现有 `hybrid_retriever`
- 输入来自 `knowledge_library_ids`
- 仅作为第三路上下文，不与项目资料混成同一池

## 生成流程

### 大纲生成

输入：

- 当前 `planning_context_text`
- 用户补充要求
- 后端隐藏 prompt 规则

行为：

- 优先使用用户当前编辑后的 `planning_context_text`
- 若页面还没有保存的 context，则先自动构建一次
- 成功后回写 `project.settings["planning_context_text"]`

### 页面描述生成

输入：

- 已保存的 `planning_context_text`
- 当前页标题/要点
- 项目资料局部检索结果
- 知识库局部检索结果

行为：

- 每页做一次局部 query
- 让页面描述真正体现“本次上传资料 + 知识库补充”的融合

## 接口变更

### 新增

- `GET /api/v1/ppt/projects/{project_id}/reference-files`
- `POST /api/v1/ppt/projects/{project_id}/planning-context/refresh`

### 调整

- `GenerateOutlineStreamRequest` 新增 `planning_context_text?: string`
- 参考资料上传改为真实保存到 OSS 或本地 fallback，不再写占位 URL

## 历史资产重解析

- 旧知识库图片/视频资产不做全量自动回填
- 新增后端脚本 `backend/scripts/reparse_multimodal_assets.py`
- 仅支持：
  - `--library-id`
  - `--asset-id`
  - `--types image,video`
- 比赛阶段只回填演示库或指定资产

## 验收标准

1. 对话模式创建项目时，所选知识库会随项目持久化。
2. 上传参考资料后会真实入库并触发独立解析。
3. 进入大纲页时可看到四段式 `Planning Context`，且不会自动生成大纲。
4. 用户编辑过构想框后，后续异步解析完成不会自动覆盖。
5. 图片/视频解析会优先走 Gemini，硬失败时回退旧链路并记录来源元数据。
6. 大纲和页面描述都会同时消费：
   - 用户意图
   - 项目资料解析结果
   - 知识库检索结果
