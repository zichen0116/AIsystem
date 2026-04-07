# PPT 文件生成后端设计文档

## 概述

实现 `creation_type='file'` 的 PPT 文件生成后端完整闭环，支持用户通过上传文档文件和/或粘贴文本，自动解析并生成结构化大纲和页面骨架。

## 已确认决策

1. **方案 A + Celery 异步** — 新增 `POST /api/v1/ppt/projects/file-generation` 一站式入口，文件解析 + 大纲生成作为 Celery 异步任务执行
2. **统一用 ParserFactory** — 文件解析统一走 `services/parsers/factory.py`，不使用 `ppt_parse_service.py`
3. **复用 `parse_outline_text()`** — 大纲生成复用 `banana_service.parse_outline_text()`，非流式调用
4. **单一 Celery 任务** — `file_generation_task` 串行完成解析 → 组合 → 大纲生成 → 页面骨架创建
5. 第一版只支持单文件，文件类型限 pdf/doc/docx
6. 不复用翻新任务逻辑

## 数据模型变更

### PPTReferenceFile 新增字段

```python
parsed_content = Column(JSONB, nullable=True)
```

用于文件生成场景的结构化解析结果持久化，与现有 `parsed_outline`（翻新场景）区分。

存储结构：

```json
{
  "normalized_text": "拼接后的标准化文本",
  "chunks_meta": [
    {"content": "...", "page": 1, "has_image": false}
  ],
  "images": ["img1.png"]
}
```

### PPTTask.task_type 新增值

新增 `"file_generation"` 类型，不复用 `"renovation_parse"`。

### PPTProject

无需新增字段。`outline_text` 存放最终组合文本源，`status` 用现有值。

## API 接口设计

### POST /api/v1/ppt/projects/file-generation

**Content-Type:** `multipart/form-data`

**参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 至少一个 | 单个文档文件（pdf/doc/docx） |
| source_text | str | 至少一个 | 用户粘贴的文本 |
| title | str | 否 | 项目标题，默认"未命名PPT" |
| theme | str | 否 | 主题 |
| template_style | str | 否 | 模板风格 |
| settings | str(JSON) | 否 | 项目设置 |

**校验规则：**
- `file` 和 `source_text` 至少提供一个，否则 400
- `file` 类型限制 `.pdf`、`.doc`、`.docx`，否则 400

**返回：**

```json
{
  "project_id": 123,
  "task_id": "uuid-string",
  "status": "processing",
  "reference_file_id": 456
}
```

**路由处理流程：**

1. 创建 `PPTProject`（`creation_type='file'`, `status='GENERATING'`）
2. 如果有文件：上传到 OSS，创建 `PPTReferenceFile` 记录
3. 创建 `PPTTask`（`task_type='file_generation'`）
4. 启动 Celery 任务 `file_generation_task`
5. 返回项目 ID + 任务 ID

**任务状态查询：** 复用现有 `GET /projects/{id}/tasks/{task_id}` 接口。

## Celery 任务设计

### file_generation_task

```python
file_generation_task(project_id, file_id=None, source_text=None, task_id_str)
```

**步骤 1 — 文件解析**（仅当 `file_id` 存在时）

- 从 OSS 下载文件到临时目录
- 调用 `ParserFactory.parse_file(tmp_path)` 获取 `ParseResult`
- 标准化：将 `chunks` 按顺序拼接为 `normalized_text`
  - 保留标题、段落、表格文本
  - 图片描述转可读文本
  - 避免原始 metadata 进入 prompt
- 持久化：将结构化结果写入 `PPTReferenceFile.parsed_content`
- 更新 `PPTReferenceFile.parse_status = 'completed'`
- 更新 `task.progress = 30`

**步骤 2 — 组合输入源**

- 情况 A（仅文件）：`outline_source = normalized_text`
- 情况 B（仅文本）：`outline_source = source_text`
- 情况 C（文件+文本）：
  ```
  {normalized_text}

  ---
  用户补充说明：
  {source_text}
  ```
- 将 `outline_source` 写入 `project.outline_text`
- 更新 `task.progress = 40`

**步骤 3 — AI 生成大纲**

- 调用 `banana_service.parse_outline_text(outline_source, theme, language)`
- 返回结构化 JSON（pages 数组）
- 更新 `task.progress = 70`

**步骤 4 — 创建页面骨架**

- 解析 JSON，支持 simple 和 part-based 两种格式
  - Simple: `[{"title": "...", "points": [...]}]`
  - Part-based: `[{"part": "Part 1", "pages": [{...}]}]`
- 为每页创建 `PPTPage`：
  - `page_number`
  - `title`
  - `config.points`
  - `config.part`（如有）
- 更新 `task.progress = 100`

**步骤 5 — 更新状态**

- 成功：`project.status = 'PLANNING'`，`task.status = 'COMPLETED'`
- 失败：`project.status = 'FAILED'`，`task.status = 'FAILED'`

**错误处理：**

- 文件解析失败 → `PPTReferenceFile.parse_status = 'failed'`，`parse_error` 记录原因，任务终止
- 大纲生成失败 → 文件解析结果已保留（可重试），任务标记失败

## 文件变更清单

| 文件 | 变更类型 | 内容 |
|------|---------|------|
| `banana_models.py` | 修改 | `PPTReferenceFile` 新增 `parsed_content` 字段 |
| `banana_schemas.py` | 修改 | 新增 `FileGenerationResponse` schema |
| `banana_routes.py` | 修改 | 新增 `POST /projects/file-generation` 路由 |
| `celery_tasks.py` | 修改 | 新增 `file_generation_task` Celery 任务 |
| `alembic migration` | 新增 | `parsed_content` 字段迁移脚本 |

**不改动的文件：**
- `banana_service.py` — 直接复用 `parse_outline_text()`
- `factory.py` — 直接复用 `ParserFactory.parse_file()`
- `ppt_parse_service.py` — 不使用
- `renovation_service.py` — 不复用

## 测试

新增 `tests/test_file_generation.py`，覆盖：
- 仅文件输入
- 仅文本输入
- 文件 + 文本混合输入
- 文件类型校验（不支持的类型返回 400）
- 文件解析失败场景
- 大纲生成失败场景
