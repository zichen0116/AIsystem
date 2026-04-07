# PPT 翻新后端设计规格

**日期:** 2026-04-07
**分支:** `feature/ppt-renovation`
**需求文档:** `tasks.md`

---

## 1. 目标

在 AIsystem 中实现完整的 PPT 翻新后端流水线，对齐 `banana-slides` 的翻新能力。用户上传 PDF/PPT/PPTX 后，系统逐页解析并提取结构化内容，支持部分成功和单页重试。

## 2. 已确认决策

1. 整体实现严格对齐 `banana-slides` 的翻新链路
2. 后端直接支持 LibreOffice 将 PPT/PPTX 转为 PDF
3. 翻新任务采用"部分成功"策略：允许部分页面失败，失败页可单独重试
4. 本阶段只做后端，不做前端适配
5. PDF 解析方案：MinerU 优先 + fitz fallback
6. AI 服务：DashScope（通义千问）
7. 并发策略：ThreadPoolExecutor（每线程独立 DB session + event loop）
8. 代码组织：新建 `renovation_service.py` 集中翻新逻辑
9. 模型扩展：PPTPage +2 字段, PPTProject +1 字段（最小扩展）
10. 单页 PDF 持久化：上传到 OSS

## 3. 整体流程

```
用户上传文件 (PDF/PPT/PPTX)
  │
  ├─ [路由层] create_renovation_project
  │   ├─ 校验文件类型
  │   ├─ 上传原始文件到 OSS
  │   ├─ 创建 PPTProject (status=PARSE)
  │   ├─ 创建 PPTReferenceFile
  │   ├─ 若 PPT/PPTX → LibreOffice 转 PDF
  │   ├─ PDF 渲染逐页 PNG → 上传 OSS
  │   ├─ 为每页创建 PPTPage + PageImageVersion
  │   ├─ 创建 PPTTask (renovation_parse)
  │   ├─ 触发 Celery 任务
  │   └─ 返回 {project_id, task_id, file_id, page_count}
  │
  ├─ [Celery] renovation_parse_task
  │   ├─ 下载 PDF → 拆分为单页 PDF → 上传 OSS
  │   ├─ ThreadPoolExecutor 并行逐页:
  │   │   ├─ 单页 PDF → markdown (MinerU/fitz)
  │   │   ├─ markdown → AI 提取 {title, points, description}
  │   │   ├─ 可选: 页面图片 → layout caption
  │   │   └─ 写回 PPTPage (独立 DB session)
  │   ├─ 聚合 outline_text / description_text → PPTProject
  │   ├─ 更新任务状态 (COMPLETED/FAILED) + result
  │   └─ 更新项目状态 (DESCRIPTIONS_GENERATED/FAILED)
  │
  └─ [路由层] regenerate_page_renovation
      ├─ 校验 creation_type == 'renovation'
      ├─ 从 OSS 下载对应单页 PDF
      ├─ 重新解析: markdown → AI 提取 → 可选 layout caption
      ├─ 更新 PPTPage (清除 renovation_error)
      ├─ 重新聚合项目级 outline_text / description_text
      └─ 返回更新后的页面数据
```

## 4. 文件结构

### 4.1 变更文件

```
backend/app/generators/ppt/
├─ banana_routes.py       # 修改: 重写两个翻新路由
├─ banana_models.py       # 修改: PPTPage +2字段, PPTProject +1字段
├─ banana_schemas.py      # 修改: 响应模型增加翻新字段
├─ celery_tasks.py        # 修改: 重写 renovation_parse_task
├─ renovation_service.py  # 新建: 翻新核心逻辑
├─ ppt_parse_service.py   # 保留: 复用 split_pdf_to_pages
├─ file_service.py        # 保留: 复用 OSS 操作
└─ ...

backend/alembic/versions/
└─ 20260407_add_renovation_fields.py  # 新建: migration

backend/tests/
└─ test_ppt_renovation.py  # 新建: 翻新测试
```

### 4.2 OSS 存储结构

```
ppt/renovation/{user_id}/{uuid}/
├─ original.{ext}           # 原始上传文件
├─ converted.pdf            # LibreOffice 转换产物 (仅 ppt/pptx)
├─ pages/
│   ├─ page_1.png           # 逐页渲染图片
│   └─ ...
└─ split_pages/
    ├─ page_1.pdf           # 单页 PDF (供重试复用)
    └─ ...
```

## 5. 数据模型变更

### 5.1 PPTPage 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `renovation_status` | String(20), nullable | `pending` / `completed` / `failed`，仅 renovation 项目使用，其他类型为 NULL |
| `renovation_error` | Text, nullable | 页面翻新解析失败时的错误信息 |

- `title`、`description` 使用现有字段
- `points` 存在现有 `config` JSONB 中 (`config["points"]`)，与当前大纲编辑器逻辑一致

### 5.2 PPTProject 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `description_text` | Text, nullable | 聚合所有页面的 description，翻新完成后写入 |

- `outline_text` 已存在，翻新完成后从各页 title + points 聚合写入

### 5.3 Alembic Migration

一个 migration 文件 `20260407_add_renovation_fields.py`，新增：
- `ppt_pages.renovation_status` (String(20), nullable)
- `ppt_pages.renovation_error` (Text, nullable)
- `ppt_projects.description_text` (Text, nullable)

## 6. 状态机

### 6.1 项目状态 (renovation)

```
创建 → PARSE → DESCRIPTIONS_GENERATED (≥1页成功)
             → FAILED (0页成功 或 致命错误)
```

**状态兼容性说明：**

- `PARSE` 是现有状态，已在当前翻新路由中使用（`banana_routes.py:2689`）
- `DESCRIPTIONS_GENERATED` 是新增状态，仅 renovation 项目使用
- `FAILED` 是现有状态
- 当前前端 `PptHistory.vue` 的 `getStatusText()` 对未识别的状态会 fallback 到基于 `page_count` / `cover_image_url` 的判断逻辑。renovation 项目在 `DESCRIPTIONS_GENERATED` 状态下有 `page_count > 0`，前端会显示为"待生成图片"，行为合理
- **本阶段只做后端，前端暂不适配这些状态。** 前端适配（如在历史页显示"翻新解析中"/"部分失败"等）留到后续前端阶段处理

### 6.2 任务状态

```
PENDING → PROCESSING → COMPLETED (≥1页成功, result 含 failed_pages)
                     → FAILED (0页成功 或 致命错误)
```

### 6.3 任务结果 PPTTask.result

```json
{
  "total_pages": 10,
  "success_count": 8,
  "failed_count": 2,
  "partial_success": true,
  "failed_pages": [
    {"page_id": 5, "page_number": 3, "error": "AI 提取超时"},
    {"page_id": 8, "page_number": 6, "error": "markdown 解析失败"}
  ]
}
```

### 6.4 页面翻新状态

```
创建时 pending → 解析成功 completed / 解析失败 failed
单页重试: failed → completed (清除 renovation_error)
```

### 6.5 错误分级

| 类型 | 场景 | 结果 |
|------|------|------|
| **致命** | 文件不存在、LibreOffice 转换失败、PDF 无法渲染任何页、全局 DB 异常 | task=FAILED, project=FAILED |
| **页面级** | 单页 markdown 解析失败、AI 提取超时/失败 | page.renovation_status=failed, 其他页继续 |
| **部分成功** | success_count > 0 且 failed_count > 0 | task=COMPLETED, partial_success=true |

## 7. 核心服务设计

### 7.1 RenovationService

```
RenovationService
│
├─ convert_to_pdf(file_path, file_ext) → str
│   调用 LibreOffice headless 转换 PPT/PPTX → PDF
│   命令: soffice --headless --convert-to pdf --outdir {output_dir} {input_file}
│   Windows: 查找 C:\Program Files\LibreOffice\program\soffice.exe
│   超时: 120s
│   错误: 找不到 soffice → 明确报错; 超时 → 超时错误; 非零退出 → 返回 stderr
│   已知风险: 服务端字体差异影响排版
│
├─ render_pdf_to_images(pdf_path, output_dir) → list[str | None]
│   PyMuPDF (fitz), matrix=fitz.Matrix(2, 2), 输出 PNG
│   单页渲染失败返回 None，不阻塞其他页
│   提取首页尺寸用于宽高比归一化
│
├─ split_pdf_to_pages(pdf_path, output_dir) → list[str]
│   委托 ppt_parse_service.split_pdf_to_pages()
│
├─ parse_page_markdown(page_pdf_path, filename) → (str|None, str|None)
│   MinerU API 优先; token 未配或失败时 fitz 文本提取 fallback
│   返回 (markdown_content, error_message)
│
├─ extract_page_content(markdown_text, language="zh") → dict
│   DashScope qwen 模型, JSON 输出
│   返回 {title, points, description}
│
├─ generate_layout_caption(image_url_or_path) → str
│   DashScope 视觉模型, 仅 keep_layout=true 时调用
│   输出中文布局描述
│
└─ process_single_page(page_pdf_path, page_image_url,
                        keep_layout, language) → dict
    单页完整流水线: parse → extract → 可选 caption
    返回 {title, points, description} 或抛异常
```

### 7.2 AI Prompt — 复用 banana-slides

**内容提取 prompt** 直接复用 banana-slides 的 `get_ppt_page_content_extraction_prompt()`（`prompts.py:949-988`）。该 prompt 已经过验证，核心逻辑：

- 输入：单页 PDF 解析出的 markdown 文本
- 输出：JSON `{title, points, description}`
- 规则：title 忠实提取不修改、points 逐条保留原文、description 包含完整页面内容（文字+图表+表格等）
- 支持 language 参数控制输出语言

在 AIsystem 中的适配：将 prompt 文本搬到 `renovation_service.py`，调用方式改为 DashScope（原版用的是 banana 内部 AI service），其余保持一致。

**布局描述 prompt** 直接复用 banana-slides 的 `get_layout_caption_prompt()`（`prompts.py:991-1013`）。核心逻辑：

- 输入：PPT 页面图片
- 输出：中文布局描述（整体结构、标题位置、内容区域、视觉元素）
- 仅描述空间布局，不描述颜色/文字内容/风格

在 AIsystem 中的适配：同样搬到 `renovation_service.py`，通过 DashScope 视觉模型调用。

**语言指令** 复用 banana-slides 的 `get_language_instruction()` 逻辑，根据 language 参数附加语言约束指令。

## 8. API 接口

### 8.1 创建翻新项目

```
POST /api/v1/ppt/projects/renovation
Content-Type: multipart/form-data

参数:
  file: File (必填, pdf/ppt/pptx)
  keep_layout: bool (可选, 默认 false)
  template_style: str (可选)
  language: str (可选, 默认 "zh")

响应 200:
{
  "project_id": 42,
  "task_id": "uuid-string",
  "file_id": 7,
  "page_count": 10
}

错误:
  400: 不支持的文件类型
  500: LibreOffice 转换失败 / PDF 渲染失败
```

同步处理步骤：
1. 校验文件类型
2. 保存临时文件 → 上传 OSS
3. 创建 PPTProject (creation_type='renovation', status='PARSE')
4. 创建 PPTReferenceFile
5. 若 ppt/pptx → LibreOffice 转 PDF → 上传 PDF 到 OSS
6. PDF 渲染逐页 PNG → 上传 OSS
7. 为每页创建 PPTPage (renovation_status='pending') + PageImageVersion
8. 将 keep_layout / language 存入 project.settings
9. 创建 PPTTask → 触发 Celery
10. 返回响应

### 8.2 单页翻新重试

```
POST /api/v1/ppt/projects/{project_id}/pages/{page_id}/regenerate-renovation
Content-Type: application/json (可选)

参数 (可选 JSON body):
  language: str (默认 "zh")
  keep_layout: bool (默认从 project.settings 读取)

响应 200:
{
  "status": "completed",
  "page": {
    "id": 5,
    "page_number": 3,
    "title": "提取到的标题",
    "description": "提取到的描述",
    "renovation_status": "completed",
    "renovation_error": null
  }
}

错误:
  400: 项目不是 renovation 类型
  404: 页面/项目不存在
  500: 单页 PDF 不存在 / 解析失败
```

### 8.3 任务查询

复用现有 `GET /api/v1/ppt/projects/{project_id}/tasks/{task_id}`，result 字段包含翻新任务详细信息。

## 9. Celery 任务

### 9.1 renovation_parse_task（重写）

```
输入: project_id, file_id, task_id_str

1. 更新 task → PROCESSING
2. 从 PPTReferenceFile 获取 PDF 的 OSS 路径
3. 下载 PDF 到临时目录
4. split_pdf_to_pages → 临时目录
5. 将单页 PDF 批量上传 OSS (split_pages/page_N.pdf)
6. ThreadPoolExecutor (max_workers=5) 并行处理每页:
   │
   每个线程:
   ├─ 创建独立 event loop + 独立 DB session
   ├─ 调用 renovation_service.process_single_page()
   ├─ 成功: 写回 PPTPage, renovation_status='completed'
   ├─ 失败: renovation_status='failed', renovation_error=str(e)
   └─ 记录到 results dict

7. 统计 success_count / failed_count
8. 聚合 outline_text / description_text → PPTProject
9. 更新 PPTTask.result = {total_pages, success_count, failed_count, partial_success, failed_pages}
10. 如 success_count > 0: task=COMPLETED, project=DESCRIPTIONS_GENERATED
    如 success_count == 0: task=FAILED, project=FAILED
11. 清理临时目录
```

## 10. Schema 变更

**PPTPageResponse 增加：**
- `renovation_status: Optional[str]`
- `renovation_error: Optional[str]`

**PPTProjectResponse 增加：**
- `description_text: Optional[str]`

## 11. 测试

### 11.1 测试文件

`backend/tests/test_ppt_renovation.py`

### 11.2 测试用例

所有测试 mock 外部服务（OSS、DashScope、MinerU、LibreOffice），不依赖真实基础设施。

| # | 测试用例 | 覆盖点 |
|---|---------|--------|
| 1 | 上传 PDF 创建翻新项目成功 | 路由：项目/页面/任务创建、OSS 上传、PDF 渲染 |
| 2 | 上传 PPTX 创建翻新项目成功 | 路由：LibreOffice 转换 + 后续流程 |
| 3 | 上传不支持的文件类型报错 | 路由：文件类型校验返回 400 |
| 4 | LibreOffice 转换失败报错 | 路由：转换异常时返回 500 |
| 5 | 翻新任务全部页面成功 | Celery：逐页写回、聚合、task=COMPLETED |
| 6 | 翻新任务部分成功 | Celery：部分页 failed、partial_success=true |
| 7 | 翻新任务 0 页成功 | Celery：task=FAILED、project=FAILED |
| 8 | 单页重试成功 | 路由：基于单页 PDF 重试、清除 error |
| 9 | 非 renovation 项目单页重试被拒绝 | 路由：返回 400 |

## 12. 依赖

### Python 依赖（均已有，无需新增）

- `PyMuPDF (fitz)` — PDF 渲染/拆分/文本提取
- `python-pptx` — PPTX 读取
- `dashscope` — AI 内容提取
- `Pillow` — 图片处理
- `oss2` — OSS 操作

### 系统依赖

- `LibreOffice` — PPT/PPTX → PDF 转换，需服务器安装

### 外部服务

- `MinerU API`（可选）— 高精度 PDF → markdown
- `DashScope` — AI 提取 + 视觉模型

## 13. 实施顺序

1. 模型变更 + Migration
2. renovation_service.py（核心服务）
3. 重写 POST /projects/renovation 路由
4. 重写 renovation_parse_task Celery 任务
5. 重写单页重试路由
6. Schema 更新
7. 测试
