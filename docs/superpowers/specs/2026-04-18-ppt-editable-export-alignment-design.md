# PPT Editable Export Alignment Design

**日期:** 2026-04-18  
**范围:** AIsystem PPT 可编辑导出对齐 banana-slides

---

## 1. 目标

将 AIsystem 当前“整页图片铺底 + 标题描述文本层”的简化版可编辑导出，升级为对齐 `D:/banana-slides` 的元素级可编辑导出链路，使导出结果尽可能保留文本、图片、表格与版面可编辑能力。

## 2. 现状与根因

当前 AIsystem 的导出任务位于 `backend/app/generators/ppt/celery_tasks.py`，调用 `backend/app/generators/ppt/ppt_export_service.py` 的 `create_pptx_from_images(..., add_text_layer=True)`。

这意味着：

- 每页首先作为整页背景图铺入 PPT
- 仅额外叠加 `title / description / notes`
- 页面主体正文、表格、图表与局部元素仍停留在背景图中

因此当前实现只能提供“部分可编辑”，并不是真正的元素级可编辑 PPTX。

## 3. 对齐目标

对齐 `banana-slides` 的可编辑导出能力，补齐以下关键能力：

- 文本提取策略：支持 `mineru` / `hybrid`
- 背景修复策略：支持 `generative` / `baidu` / `hybrid`
- 元素级重建：文本框、图片、表格、局部元素按 bbox 重建
- 失败回退：允许在完整导出失败时退回现有 Beta 导出
- 项目级设置：将导出策略保存在 `project.settings`

## 4. 设计决策

1. 采用“双轨保底”方案  
   默认优先走完整元素级可编辑导出；失败时按项目设置决定是否回退到当前 Beta 导出。

2. 后端优先补齐，前端只补配置入口  
   前端保持现有导出按钮与轮询任务逻辑，不改用户主流程，只新增导出设置入口。

3. 环境变量统一以后端为准  
   可编辑导出依赖 `backend/.env` 中的 `GOOGLE_API_KEY`、`MINERU_TOKEN`、`BAIDU_API_KEY` 等配置，不从 `teacher-platform/.env.development` 读取。

## 5. 变更范围

### 5.1 后端

- `backend/app/generators/ppt/ppt_export_service.py`
  - 接入或移植 banana-slides 的元素级导出主逻辑
  - 保留当前简化版导出函数，作为 fallback

- `backend/app/generators/ppt/celery_tasks.py`
  - 重写 `export_editable_pptx_task`
  - 从 `project.settings` 读取导出策略
  - 完整导出失败时根据设置决定是否回退

- `backend/app/generators/ppt/banana_routes.py`
  - 保持现有异步导出接口不变
  - 如有必要补充结果中的 warning / fallback 信息

- `backend/app/generators/ppt/banana_schemas.py`
  - 补充项目设置字段 schema

- `backend/app/generators/ppt/banana_models.py`
  - 无需新增专门列，继续复用 `PPTProject.settings`

### 5.2 前端

- `teacher-platform/src/views/ppt/PptPreview.vue`
  - 在现有项目设置入口中补充 editable export 配置项
  - 允许用户设置提取方式、修复方式、允许返回半成品

## 6. 数据设计

导出设置写入 `PPTProject.settings`：

```json
{
  "export_extractor_method": "hybrid",
  "export_inpaint_method": "hybrid",
  "export_allow_partial": true
}
```

默认值：

- `export_extractor_method = "hybrid"`
- `export_inpaint_method = "hybrid"`
- `export_allow_partial = true`

## 7. 错误与回退策略

完整导出过程中的错误分层：

- 配置错误：缺少 `MINERU_TOKEN` / `BAIDU_API_KEY` / `GOOGLE_API_KEY`
- 提取失败：OCR / MinerU / vision 样式提取失败
- 修复失败：背景抹除或生成式背景失败
- 构建失败：PPTXBuilder 添加元素失败

处理策略：

- 若 `export_allow_partial=true`，则记录 warning 并回退到当前 Beta 导出
- 若 `export_allow_partial=false`，则任务直接失败并返回错误信息

## 8. 测试策略

### 后端

- 为导出设置读取与默认值补回写测试
- 为完整导出失败时的 fallback 测试
- 为未配置关键 API key 时的错误路径测试

### 前端

- 为导出设置保存逻辑增加测试
- 为任务状态结果展示保留现有行为

## 9. 非目标

本次不处理：

- 新增独立“导出设置”页面
- 重构整个 PPT 生成链路
- 迁移 banana-slides 全量设置中心

## 10. 验收标准

- 用户可在 AIsystem 中配置 editable export 的提取与修复策略
- 任务优先走元素级可编辑导出
- 配置缺失或导出失败时能给出明确反馈
- 在允许半成品时可回退到当前 Beta 导出
- 现有普通 PPTX / PDF / 图片导出不回归
