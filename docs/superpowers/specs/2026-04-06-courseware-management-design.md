# Courseware Management - Real Data Integration Design

> Date: 2026-04-06
> Branch: feat/courseware-management
> Status: Approved (rev2 - incorporated code review)

## Overview

将课件管理页面从硬编码 mock 数据切换为真实后端数据，聚合展示 PPT 项目、教案、用户上传文件三类课件。保留现有页面样式与交互，仅替换数据获取和卡片映射逻辑。

## Decisions

| 决策点 | 结论 |
|---|---|
| 上传文件存储 | 扩展现有 Courseware 模型，新增字段。**courseware 表仅存手动上传文件**，PPT/教案数据始终从各自表查询，不冗余写入 courseware |
| 数据聚合 | 后端聚合接口，一次请求返回三类数据 |
| PPT 封面缓存 | Redis 旁路缓存 + 主动失效 |
| 卡片跳转 | 复用 /lesson-prep + query 参数，需改造 LessonPrep.vue 解析参数 |

---

## Section 1: Data Model & Backend API

### 1.1 Courseware Table Migration

courseware 表**仅承载手动上传文件**。新增字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `file_name` | `VARCHAR(255)` | 原始文件名 |
| `file_size` | `BIGINT` | 文件大小（字节），nullable |
| `file_type` | `VARCHAR(20)` | `'pdf'`/`'ppt'`/`'word'`/`'video'`/`'image'` |
| `tags` | `VARCHAR(500)` | 用户自定义标签，逗号分隔 |
| `remark` | `TEXT` | 用户备注 |

不新增 `source_type` 和 `uploaded_at`。上传文件用现有 `created_at` 记录上传时间，`updated_at` 在编辑元数据时自动刷新。

现有字段保留不动：`title`, `type`, `content_json`, `status`, `file_url`, `ppt_project_id`, `created_at`, `updated_at`。

### 1.2 Aggregation Endpoint: `GET /api/v1/courseware/all`

**Request parameters:**
- `source_type`: optional, `'ppt'`/`'lesson_plan'`/`'uploaded'`/`'all'` (default: all)
- `file_type`: optional, `'pdf'`/`'ppt'`/`'word'`/`'video'`
- `date_range`: optional, `'week'`/`'month'`/`'year'`

**Response (`CoursewareAggregateResponse`):**
```json
{
  "items": [
    {
      "id": "ppt_123",
      "source_type": "ppt",
      "name": "量子力学基础PPT",
      "file_type": "ppt",
      "file_size": null,
      "status": "COMPLETED",
      "cover_image": "https://oss.../cover.png",
      "updated_at": "2026-04-05T10:30:00Z",
      "source_id": 123,
      "tags": null,
      "remark": null,
      "file_url": null,
      "page_count": 12
    }
  ],
  "total": 42
}
```

**ID prefix strategy:** `"ppt_{id}"` / `"lp_{id}"` / `"up_{id}"` — 前端用于区分来源和路由跳转。

**Aggregation logic (server-side):**
1. Query `ppt_projects` WHERE `user_id` = current → map to `source_type='ppt'`, `file_type='ppt'`
2. Query `lesson_plans` WHERE `user_id` = current → map to `source_type='lesson_plan'`, `file_type='word'`
3. Query `courseware` WHERE `user_id` = current（此表只存上传文件）→ map to `source_type='uploaded'`
4. 合并三列表，**统一按 `updated_at` 倒序排序**（三张表都有 updated_at 字段）
5. PPT 封面查询走 Redis 旁路缓存
6. 应用 source_type / file_type / date_range 筛选（筛选时间统一基于 `updated_at`）

### 1.3 PPT Cover Redis Cache

- **Key:** `ppt:cover:{project_id}`
- **Value:** cover URL string (empty string = no cover)
- **TTL:** 24 hours
- **Invalidation:** on image generate complete, image edit complete, page delete/reorder → delete key
- PptHistory page also uses this cache

### 1.4 Upload Endpoint: `POST /api/v1/courseware/upload`

- Accepts `multipart/form-data`: `file` + optional `title`, `tags`, `remark`
- Calls `oss_service.upload_file()` for OSS storage
- Inserts `courseware` record，recording file_name, file_size, file_type, file_url
- title 默认用原始文件名（去掉扩展名），用户可自定义
- Returns new CoursewareItem（同聚合接口的 item 结构）

### 1.5 Edit Endpoint: `PATCH /api/v1/courseware/{id}`

扩展现有 `CoursewareUpdate` schema，新增可写字段：

| 字段 | 类型 | 校验规则 |
|---|---|---|
| `title` | `str` | 1-255 字符（已有） |
| `tags` | `str | None` | 最长 500 字符，逗号分隔 |
| `remark` | `str | None` | 无长度限制 |
| `file_type` | `str | None` | 仅允许 `pdf`/`ppt`/`word`/`video`/`image` |

修改后自动刷新 `updated_at`（SQLAlchemy `onupdate` 已处理）。响应返回完整的 CoursewareItem 包含新字段。

### 1.6 Delete Endpoint

- **`DELETE /api/v1/courseware/{id}`** — 已有接口，保留。对上传文件同时清理 OSS 文件。

### 1.7 Download Endpoint: `GET /api/v1/courseware/download`

统一下载入口，通过 query 参数区分来源：

- **`GET /api/v1/courseware/download?source_type=uploaded&source_id={id}`**
  → 302 redirect to OSS URL
- **`GET /api/v1/courseware/download?source_type=ppt&source_id={id}`**
  → 调用现有 `export_project(format='pptx')` 返回文件
- **`GET /api/v1/courseware/download?source_type=lesson_plan&source_id={id}`**
  → 调用现有 lesson plan 导出逻辑，查 DB 拿 content + title，生成 DOCX 返回 FileResponse

### 1.8 PPT/Lesson Plan Title Edit

前端直接调对应接口，不通过 courseware 代理：
- PPT title → `PUT /api/v1/ppt/projects/{source_id}` with `{title: ...}`
- Lesson plan title → `PATCH /api/v1/lesson-plan/{source_id}` with `{title: ...}`

---

## Section 2: Frontend Data Layer & Store

### 2.1 coursewareStore Rewrite

Replace all mock data. New state with**双列表分层**：

```js
{
  allCoursewareList: [],      // 完整数据（无筛选），用于收藏 getter
  filteredCoursewareList: [], // 当前筛选结果，用于 CoursewareManage 页面展示
  loading: false,
  error: null,
  favorites: new Set(),       // in-memory only, not persisted
}
```

**双列表策略解决收藏问题：**
- `fetchAll()` 无筛选参数，获取全量数据存入 `allCoursewareList`
- `fetchFiltered(filters)` 带筛选参数，结果存入 `filteredCoursewareList`
- `favoritedList` getter 基于 `allCoursewareList`，不受筛选影响
- CoursewareManage 页面 mount 时同时调 `fetchAll()` 和 `fetchFiltered()`
- PersonalCenter 页面 mount 时只调 `fetchAll()`

**Actions:**

| Action | Description |
|---|---|
| `fetchAll()` | GET /api/v1/courseware/all (无筛选) → 写入 allCoursewareList |
| `fetchFiltered(filters?)` | GET /api/v1/courseware/all with source_type/file_type/date_range → 写入 filteredCoursewareList |
| `toggleFavorite(id)` | Set add/delete, pure memory |
| `deleteCourseware(id)` | Parse id prefix → call appropriate delete API → remove from both lists |
| `updateCourseware(id, data)` | `up_` → PATCH /api/v1/courseware/{source_id}; `ppt_`/`lp_` → 直接调对应接口改 title → update both lists |
| `uploadCourseware(file, meta)` | POST /api/v1/courseware/upload → unshift to both lists |
| `downloadCourseware(item)` | GET /api/v1/courseware/download?source_type=X&source_id=Y → trigger browser download |

**Getter:**
- `favoritedList` → `allCoursewareList.filter(i => favorites.has(i.id))`

### 2.2 Card Field Mapping

| Card UI Field | Data Source |
|---|---|
| Title | `name`, fallback: "未命名教案" / "未命名PPT" |
| Type badge | `file_type` (pdf/ppt/word/video) |
| Cover image | `cover_image`; PPT has real cover; lesson plan/uploaded use default colored backgrounds by file_type |
| Modify time | `updated_at`, computed by dayjs: "今天/3天前/2026年2月15日" |
| File size | `file_size`, formatted "12.4 MB" or "—" when null |
| Source label | `source_type`: "AI生成" for ppt/lesson_plan, "手动上传" for uploaded |
| subject/grade | **Removed** — backend has no such data |

### 2.3 Filter Logic

- Type filter → passed as `file_type` param to backend; lesson plan maps to `word`
- Date filter → passed as `date_range` param to backend
- Filter change → re-fetch `fetchFiltered()`（不影响 allCoursewareList）

### 2.4 PersonalCenter Compatibility

- Uses `coursewareStore.favoritedList`（基于 allCoursewareList）
- mount 时调 `fetchAll()` 确保数据加载
- Favorites are memory-only, reset on page refresh
- Card rendering identical to CoursewareManage

---

## Section 3: Card Interactions

### 3.1 Card Click Navigation

| ID Prefix | Target | Notes |
|---|---|---|
| `ppt_` | `/lesson-prep?mode=ppt&projectId={source_id}` | Load PPT project into preview phase |
| `lp_` | `/lesson-prep?mode=lesson-plan&id={source_id}` | Load lesson plan, expand rich text editor |
| `up_` | No navigation | Toast: "该课件为手动上传，暂不支持在线编辑" |

### 3.2 LessonPrep Route Param Handling — 改造范围

当前 `LessonPrep.vue` 只通过 tab 切换模块，不识别 query 参数。需要改造：

**LessonPrep.vue 改造：**
- `onMounted` / `watch(route.query)` 中解析 `mode` 参数
- `mode=ppt` → 切换到 PPT tab，调用 `pptStore.loadProject(projectId)` 加载项目，设置 `currentPhase = 'preview'`
- `mode=lesson-plan` → 切换到教案 tab，传 `id` 给 LessonPlanPage 组件

**LessonPlanPage.vue 改造：**
- 当前进入页面会重置会话。增加逻辑：如果 route 带 `id` 参数，跳过新建流程，直接调 `GET /api/v1/lesson-plan/{id}` 加载已有教案内容到编辑器，展开富文本编辑区
- 不触发 `loadHistory()` 的自动新建行为

**PptIndex.vue 改造：**
- 当 pptStore 已有 `projectId` 且 `currentPhase` 被设为 `preview` 时，直接渲染 PptPreview 组件，跳过 home/dialog/outline 流程

### 3.3 Card Action Menu (⋮ dropdown)

Each card has a `⋮` button (top-right corner of thumbnail area), click to expand dropdown:

| Action | All Types | Behavior |
|---|---|---|
| Edit info | Yes | Open edit modal |
| Download | Yes | Trigger download |
| Delete | Yes | Confirmation dialog → delete |

### 3.4 Edit Modal

| Field | ppt_ | lp_ | up_ |
|---|---|---|---|
| Title | Editable | Editable | Editable |
| Tags | No | No | Editable |
| File type | Locked (ppt) | Locked (word) | Editable (pdf/ppt/word/video) |
| Remark | No | No | Editable |

API calls:
- `ppt_` → `PUT /api/v1/ppt/projects/{source_id}` with `{title}`
- `lp_` → `PATCH /api/v1/lesson-plan/{source_id}` with `{title}`
- `up_` → `PATCH /api/v1/courseware/{source_id}` with `{title, tags, remark, file_type}`

### 3.5 Delete Confirmation

Dialog: "确定要删除「{name}」吗？此操作不可恢复。"
- `ppt_` → DELETE /api/v1/ppt/projects/{source_id}
- `lp_` → DELETE /api/v1/lesson-plan/{source_id}
- `up_` → DELETE /api/v1/courseware/{source_id} (also cleans OSS file)

### 3.6 Download Behavior

统一调 `GET /api/v1/courseware/download?source_type=X&source_id=Y`：
- `uploaded` → 302 redirect to OSS URL, browser auto-downloads
- `ppt` → returns PPTX file stream
- `lesson_plan` → returns DOCX file stream

---

## Section 4: Upload, Favorites & Edge Cases

### 4.1 "Add Courseware" Button

- Click → upload modal (reuse existing modal style)
- Select file → POST /api/v1/courseware/upload (via OSS)
- Optional fields: title (default: filename without extension), tags, remark
- Success → unshift to both allCoursewareList and filteredCoursewareList, Toast "上传成功"
- File types: `.pdf, .ppt, .pptx, .doc, .docx, .mp4`
- Max size: 50MB

### 4.2 Favorites Logic

- Memory-only: `favorites: Set<string>` in store
- Star click → toggleFavorite(id), Set add/delete
- favoritedList getter filters **allCoursewareList**（不受筛选影响）
- Reset on page refresh (no persistence per requirement)
- PersonalCenter favorites tab uses same getter

### 4.3 Edge Cases

| Scenario | Handling |
|---|---|
| Empty title | PPT: "未命名PPT", lesson plan: "未命名教案", uploaded: original filename |
| No cover image | PPT without image: default PPT-colored background; lesson plan/uploaded: default background by file_type |
| No file size | Display "—" |
| Date filter boundary | Backend uses `updated_at` for all types: week = 7 days, month = 30 days, year = 365 days from now |
| Time display & sort | **统一用 `updated_at`**。上传文件编辑元数据后 updated_at 自动刷新，排序和展示时间一致 |
| Empty list | Show: "暂无课件，点击添加课件上传或前往备课生成" |
| Pagination | Not implemented; no pagination controls shown |
| List/grid toggle | Preserved as-is |

### 4.4 No Changes

- Page layout, CSS styles unchanged
- List/grid view toggle preserved
- Type filter tabs preserved (all/pdf/ppt/video/word)
- Date filter tabs preserved (all/week/month/year)
- Card thumbnail gradient backgrounds + type badges preserved
