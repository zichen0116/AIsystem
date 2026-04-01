# PPT生成模块 - 前端实现计划 V2（按现状对齐）

> **Date:** 2026-03-31
> **Status:** Active Draft
> **Owner:** AIsystem Frontend
> **Supersedes:** `docs/superpowers/plans/2026-03-28-ppt-frontend-design.md`

## 1. 文档目的与范围

本版本用于解决“代码实现与旧文档明显偏离”的问题，按以下事实重新定义前端实施计划：

- AIsystem 的 Home / Dialog / Outline / Description / Preview 五页已完成首版 Vue 实现。
- 前端原型文件已删除，不再作为实现依据。
- 流程编排采用 `LessonPrep -> PptIndex -> currentPhase` 状态机，不采用旧文档中的多 query-tab 子流程。
- Description 与 Preview 页面后续功能按 banana-slides 做高一致性对齐。
- 本次明确必做能力：**单页图片在线编辑（edit image）**。

本文件只覆盖前端实现计划，不替代后端总设计文档。

后端契约与能力边界以 `docs/superpowers/specs/2026-03-31-ppt-backend-design-v2.md` 为准，本文仅描述前端接入和实现节奏。

---

## 2. 现状基线（以当前代码为准）

### 2.1 页面与流程编排

- `LessonPrep.vue` 只暴露 `tab=ppt` 入口，PPT 内部流程不依赖路由切换。
- `PptIndex.vue` 通过 `pptStore.currentPhase` 在五个页面间切换：
  - `home`
  - `dialog`
  - `outline`
  - `description`
  - `preview`
- 创建类型驱动入口分流：
  - `dialog` -> 进入 `dialog`
  - `file` -> 进入 `outline`
  - `renovation` -> 进入 `outline`

### 2.2 Store 与 API 现状

- 状态管理：`src/stores/ppt.js`
  - 已包含项目、流程、页面、描述、会话、素材、导出任务、项目设置等基础状态。
- API 封装：`src/api/ppt.js`
  - 已包含项目 CRUD、大纲/描述/图片生成、refine、导出、素材、参考文件、会话、模板等接口封装。
  - SSE 解析采用 `event: message + data.type` 分流。

### 2.3 已落地能力（摘要）

- Home：三入口（对话生成/文件生成/PPT翻新）基础流程可用。
- Dialog：会话读取与发送、意图确认链路可用。
- Outline：页面编辑与排序、refine outline 基础链路可用。
- Description：批量生成、refine descriptions、卡片编辑基础可用。
- Preview：批量/单页生成图片、导出、多选基础可用。

---

## 3. 对齐目标（V2核心要求）

### 3.1 总体原则

1. 不回退现有五页架构，不恢复已删除原型。
2. Description/Preview 以 banana-slides 能力为参照，优先补齐“编辑器体验能力”。
3. 保持与当前后端 API 契约一致，文档中的路径和字段必须可追溯到现代码。
4. 所有新增前端能力必须给出降级策略（后端未完成时的占位行为）。

### 3.2 Description 页对齐目标

#### 已有

- 批量生成描述
- AI refine 描述
- 卡片编辑
- 基础设置项

#### 待补齐（按优先级）

**P0（高优先）**

- `detail_level` 三档可视化切换（concise/default/detailed）并透传接口。
- `detail_level` 枚举兼容层：前端先兼容后端设置侧 `brief/normal/detailed` 与生成侧 `concise/default/detailed` 的差异，后续按后端统一方案收敛为单一枚举。
- 额外字段增强：
  - 字段自定义新增/删除
  - 字段拖拽排序
  - 字段是否参与 image prompt 的开关
- Markdown 导入/导出与增强输入区（支持更复杂编辑场景）。

**P1（中优先）**

- 生成模式（流式/并行）与设置持久化（项目级）。
- 单页描述重试与失败态恢复。
- 翻新模式下的描述轮询与状态展示增强。

**P2（低优先）**

- 高级字段模板（学科预设）。
- 更细颗粒的批量操作（按筛选条件生成）。

### 3.3 Preview 页对齐目标

#### 已有

- 缩略图 + 大图预览
- 批量/单页图片生成
- 基础导出
- 多选导出

#### 待补齐（按优先级）

**P0（高优先）**

- **单页图片在线编辑（必做）**
  - 输入自然语言编辑指令
  - 调用 `POST /api/v1/ppt/projects/{id}/pages/{page_id}/edit/image`
  - 展示任务状态、完成后刷新页面图
- 图片版本历史与切换
  - 版本列表查看
  - 版本回滚为当前图
- 模板切换能力（预设模板 + 用户模板）与页面再生成联动。

**P1（中优先）**

- 项目设置弹窗（比例、导出提取策略、导出修复策略等）。
- 导出任务面板（异步导出任务进度、完成下载入口）。
- 素材中心联动（选素材参与编辑/生成）。

**P2（低优先）**

- 区域选图与上下文图组合编辑。
- 编辑参数缓存（按 page 记忆最近编辑上下文）。

### 3.4 未完善/未做功能补充（前端执行清单）

以下条目为“文档已要求但前端尚未完整落地”或“后端已具备但前端尚未接满”的功能：

1. 单页图片在线编辑面板未完整接入 `context_images` 选择能力。
2. 版本历史入口存在但未形成“列表 -> 切换当前版本 -> 预览刷新”完整闭环。
3. 导出任务面板未完整接入异步导出任务跟踪（尤其 editable-pptx）。
4. `export/images` 未闭环时，前端缺少明确降级提示与禁用策略。
5. Description 页设置项中“生成模式/额外字段/image_prompt 字段映射”仍存在部分仅本地态、未稳定持久化问题。
6. `detail_level` 仍需统一兼容映射层，避免设置值与生成值语义不一致。
7. 素材生成（对齐 banana 的 materials/generate）前端入口未完成。
8. 项目模板上传在后端未落地前，前端需保持占位态并避免误导为可用功能。
9. 翻新模式单页重新生成（regenerate-renovation）在 Preview/Description 的入口与状态反馈仍需补齐。

---

## 4. 关键契约快照（前后端对齐）

### 4.1 已使用 SSE 约定

- 通道：`event: message`
- 解析：按 `data.type` 分流
- 当前稳定 type：`page` / `done` / `error` / `outline_chunk`
- 预留 type：`progress`（前端可兼容接收，但不作为当前稳定依赖）

### 4.2 单页图片在线编辑（必做项）

#### 请求

`POST /api/v1/ppt/projects/{project_id}/pages/{page_id}/edit/image`

```json
{
  "edit_instruction": "把背景改为深蓝色，突出标题区",
  "context_images": {
    "use_template": true,
    "desc_image_urls": [],
    "uploaded_image_ids": []
  }
}
```

#### 前端执行流程

1. Preview 打开“在线编辑”面板。
2. 输入 `edit_instruction` 并提交。
3. 显示任务中状态（按钮 loading + 页面状态标记）。
4. 轮询任务或刷新项目页数据。
5. 更新当前页 `imageUrl`，并提示完成。

#### 失败兜底

- 显示错误 toast。
- 保留原图不覆盖。
- 保留编辑指令以便二次重试。

### 4.3 版本历史接口（已具备，前端待全量接入）

后端当前已提供版本历史接口：

- `GET /api/v1/ppt/projects/{project_id}/pages/{page_id}/versions`
- `POST /api/v1/ppt/projects/{project_id}/pages/{page_id}/versions`
- `POST /api/v1/ppt/projects/{project_id}/pages/{page_id}/versions/{version_id}/set-current`

前端本期目标：

- Preview 完整接入版本列表与切换。
- 在线编辑完成后自动刷新版本列表，并支持一键回切。

### 4.4 导出契约现状（与后端 V2 对齐）

- `GET /api/v1/ppt/projects/{id}/export/pptx`：可用。
- `GET /api/v1/ppt/projects/{id}/export/pdf`：可用。
- `GET /api/v1/ppt/projects/{id}/export/images`：当前后端尚未闭环，需纳入 P0 修复。
- `POST /api/v1/ppt/projects/{id}/export/editable-pptx`：异步任务模式，前端应走任务创建 + 任务查询，不应按同步下载处理。

---

## 5. 实施阶段（前端）

### Phase A：现状清理与对齐（1周）

- 删除页面内与旧原型耦合的描述和注释。
- 补齐 Description/Preview 中已存在但未真正生效的设置字段。
- 统一 store 字段命名与页面消费方式。

### Phase B：P0能力补齐（2~3周）

- Description：detail_level、字段增强、Markdown 编辑增强。
- Preview：单页在线编辑（必做）、版本历史 UI、模板切换。

### Phase C：P1能力补齐（1~2周）

- 项目设置弹窗
- 导出任务面板
- 素材中心联动

### Phase D：P2能力与体验优化（按排期）

- 区域选图
- 编辑参数缓存
- 高级批量策略

---

## 6. 验收标准

### 6.1 必过项（本期）

- 五页面流程可从 Home 连续走到 Preview，不出现死链。
- 单页图片在线编辑可用：
  - 能发起请求
  - 能看到处理中状态
  - 成功后页面图片刷新
  - 失败可重试
- Description `detail_level` 真实影响请求参数。

补充必过项：

- 版本历史可用：可查询版本、切换当前版本并实时刷新预览。
- 导出任务可用：editable-pptx 导出走任务链路，任务状态与结果可追踪。
- `export/images` 未闭环时前端必须有明确提示，不允许“点击后无反馈”。

### 6.2 一致性检查

- 文档中的 API 路径与 `src/api/ppt.js`、后端路由定义一致。
- 文档中的流程描述与 `PptIndex` phase 状态机一致。
- 文档中不再引用已删除前端原型。

---

## 7. 风险与对策

- 风险：前端尚未全量接入已存在的版本历史接口，导致在线编辑后的版本切换体验不完整。
  - 对策：在 Preview P0 中优先打通 versions 列表和 set-current 回切链路。
- 风险：在线编辑为异步任务，弱网下反馈迟缓。
  - 对策：显式任务状态、超时提示、可重试。
- 风险：导出契约存在边界差异（images 导出未闭环、editable 导出为异步任务）。
  - 对策：按后端 V2 的导出策略统一改造前端导出入口与任务面板。
- 风险：Description/Preview 功能迅速扩张导致状态复杂化。
  - 对策：将页面本地状态拆分为 composables，降低组件体积。

---

## 8. 非目标（本次不做）

- 不恢复/重建旧 HTML 原型流程。
- 不改动 LessonPrep 外层路由架构。
- 不在本文件内展开后端数据库迁移方案细节。
