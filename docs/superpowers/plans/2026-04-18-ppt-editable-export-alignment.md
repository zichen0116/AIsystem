# PPT Editable Export Alignment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AIsystem 的“可编辑 PPTX（Beta）”升级为优先走 banana-slides 风格的元素级导出，并保留当前简化版作为回退方案。

**Architecture:** 后端以 `project.settings` 为配置源，补齐 editable export 所需设置并改写 `export_editable_pptx_task` 的执行路径。前端保持现有导出入口，只增加导出设置的读写入口，避免改变用户主流程。

**Tech Stack:** FastAPI, SQLAlchemy, Celery, python-pptx, Vue 3, Pinia, pytest, Vitest

---

## Chunk 1: Tests First

### Task 1: 后端导出设置与回退逻辑测试

**Files:**
- Modify: `backend/tests/test_ppt_export_helpers.py`

- [ ] 为导出设置默认值、结果下载信息或 helper 行为补测试
- [ ] 新增对 editable export fallback 判定的最小测试
- [ ] 运行目标测试并确认先失败

### Task 2: 前端导出设置读写测试

**Files:**
- Modify: `teacher-platform/src/api/http.spec.js`
- Create or Modify: `teacher-platform/src/views/ppt/PptPreview` 相关测试文件（若仓库无现成测试，则至少补 API 层测试）

- [ ] 为项目设置保存 payload 补测试
- [ ] 运行目标测试并确认先失败

## Chunk 2: Backend Export Alignment

### Task 3: 让项目设置支持 editable export 字段

**Files:**
- Modify: `backend/app/generators/ppt/banana_schemas.py`
- Modify: `backend/app/generators/ppt/template_settings.py`

- [ ] 补充 `export_extractor_method`、`export_inpaint_method`、`export_allow_partial`
- [ ] 保证 settings merge 不破坏现有模板字段
- [ ] 运行相关测试

### Task 4: 在导出服务中加入完整导出入口和 fallback

**Files:**
- Modify: `backend/app/generators/ppt/ppt_export_service.py`

- [ ] 引入或移植 banana-slides 可编辑导出主流程需要的最小逻辑
- [ ] 保留当前 `create_pptx_from_images(..., add_text_layer=True)` 作为 fallback
- [ ] 暴露一个统一的 editable export 调用入口
- [ ] 运行相关测试

### Task 5: 重写 editable export 任务逻辑

**Files:**
- Modify: `backend/app/generators/ppt/celery_tasks.py`

- [ ] 从 `project.settings` 读取导出策略
- [ ] 优先调用完整导出
- [ ] 完整导出失败时按 `export_allow_partial` 回退或报错
- [ ] 将 warning / fallback 信息写入任务结果
- [ ] 运行相关测试

## Chunk 3: Frontend Settings Entry

### Task 6: 补前端设置读写入口

**Files:**
- Modify: `teacher-platform/src/views/ppt/PptPreview.vue`

- [ ] 在现有项目设置入口中加入 editable export 配置
- [ ] 保存到 `/projects/{id}/settings`
- [ ] 不影响现有比例、模板设置行为
- [ ] 运行前端相关测试

## Chunk 4: Verification

### Task 7: 完整验证

**Files:**
- Modify: as needed

- [ ] 运行后端目标测试
- [ ] 运行前端目标测试
- [ ] 如条件允许，补一次手动导出链路验证
- [ ] 记录未完成项或真实限制

Plan complete and saved to `docs/superpowers/plans/2026-04-18-ppt-editable-export-alignment.md`. Ready to execute.
