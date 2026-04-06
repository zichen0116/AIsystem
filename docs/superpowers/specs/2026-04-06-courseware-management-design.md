# Courseware Management - Real Data Integration Design

> Date: 2026-04-06
> Branch: feat/courseware-management
> Status: Approved

## Overview

将课件管理页面从硬编码 mock 数据切换为真实后端数据，聚合展示 PPT 项目、教案、用户上传文件三类课件。保留现有页面样式与交互，仅替换数据获取和卡片映射逻辑。

## Decisions

| 决策点 | 结论 |
|---|---|
| 上传文件存储 | 扩展现有 Courseware 模型，新增字段 |
| 数据聚合 | 后端聚合接口，一次请求返回三类数据 |
| PPT 封面缓存 | Redis 旁路缓存 + 主动失效 |
| 卡片跳转 | 复用 /lesson-prep + query 参数 |

---

## Section 1: Data Model & Backend API

### 1.1 Courseware Table Migration

在现有 `courseware` 表上新增字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_type` | `VARCHAR(20)` | `'ppt'` / `'lesson_plan'` / `'uploaded'`，默认 `'uploaded'` |
| `file_name` | `VARCHAR(255)` | 原始文件名 |
| `file_size` | `BIGINT` | 文件大小（字节），nullable |
| `file_type` | `VARCHAR(20)` | `'pdf'`/`'ppt'`/`'word'`/`'video'`/`'image'` |
| `tags` | `VARCHAR(500)` | 用户自定义标签，逗号分隔 |
| `remark` | `TEXT` | 用户备注 |
| `uploaded_at` | `DateTime(tz)` | 上传时间，仅 uploaded 类型使用 |

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

**ID prefix strategy:** `"ppt_{id}"` / `"lp_{id}"` / `"up_{id}"`

**Aggregation logic (server-side):**
1. Query `ppt_projects` WHERE `user_id` = current → map to `source_type='ppt'`, `file_type='ppt'`
2. Query `lesson_plans` WHERE `user_id` = current → map to `source_type='lesson_plan'`, `file_type='word'`
3. Query `courseware` WHERE `user_id` = current AND `source_type='uploaded'` → direct map
4. Merge, sort by `COALESCE(uploaded_at, updated_at)` DESC
5. PPT covers fetched via Redis cache-aside

### 1.3 PPT Cover Redis Cache

- **Key:** `ppt:cover:{project_id}`
- **Value:** cover URL string (empty string = no cover)
- **TTL:** 24 hours
- **Invalidation:** on image generate complete, image edit complete, page delete/reorder → delete key
- PptHistory page also uses this cache

### 1.4 Upload Endpoint: `POST /api/v1/courseware/upload`

- Accepts `multipart/form-data`: `file` + optional `title`, `tags`, `remark`
- Calls `oss_service.upload_file()` for OSS storage
- Inserts `courseware` record with `source_type='uploaded'`, recording file_name, file_size, file_type, file_url, uploaded_at
- Returns new CoursewareItem

### 1.5 Edit/Delete/Download

- **`PATCH /api/v1/courseware/{id}`** — extend existing: allow editing `title`, `tags`, `remark`, `file_type`
- **`DELETE /api/v1/courseware/{id}`** — existing, kept as-is (also cleans up OSS file for uploaded type)
- **`GET /api/v1/courseware/download?id={prefixed_id}`** — new: accepts prefixed id (e.g. `ppt_123`, `lp_456`, `up_789`), parses prefix to determine source type. uploaded → 302 redirect to OSS URL; PPT → export PPTX URL; lesson plan → DOCX export

### 1.6 PPT/Lesson Plan Title Edit (Proxy)

For editing titles of PPT and lesson plan items, the courseware aggregation service proxies:
- PPT title → `PUT /api/v1/ppt/projects/{source_id}` with `{title: ...}`
- Lesson plan title → `PATCH /api/v1/lesson-plan/{source_id}` with `{title: ...}`

---

## Section 2: Frontend Data Layer & Store

### 2.1 coursewareStore Rewrite

Replace all mock data. New state:

```js
{
  coursewareList: [],        // CoursewareItem[] from aggregation API
  loading: false,
  error: null,
  favorites: new Set(),     // in-memory only, not persisted
}
```

**Actions:**

| Action | Description |
|---|---|
| `fetchCoursewareList(filters?)` | GET /api/v1/courseware/all with source_type/file_type/date_range |
| `toggleFavorite(id)` | Set add/delete, pure memory |
| `deleteCourseware(id)` | Parse id prefix → call appropriate delete API → remove from list |
| `updateCourseware(id, data)` | `up_` → PATCH courseware; `ppt_`/`lp_` → proxy title edit |
| `uploadCourseware(file, meta)` | POST /api/v1/courseware/upload → unshift to list |
| `downloadCourseware(item)` | GET /api/v1/courseware/{id}/download → trigger browser download |

**Getter:**
- `favoritedList` → `coursewareList.filter(i => favorites.has(i.id))`

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
- Filter change → re-fetch from API (no client-side filtering)

### 2.4 PersonalCenter Compatibility

- Continues using `coursewareStore.favoritedList`
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

### 3.2 LessonPrep Route Param Handling

`LessonPrep.vue` onMounted reads `route.query`:
- `mode=ppt&projectId=X` → switch to PPT module, load project X, jump to preview
- `mode=lesson-plan&id=X` → switch to lesson plan module, load plan X, expand editor

### 3.3 Card Action Menu (⋮ dropdown)

Each card has a `⋮` button (top-right), expanding to:

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

### 3.5 Delete Confirmation

Dialog: "确定要删除「{name}」吗？此操作不可恢复。"
- `ppt_` → DELETE /api/v1/ppt/projects/{source_id}
- `lp_` → DELETE /api/v1/lesson-plan/{source_id}
- `up_` → DELETE /api/v1/courseware/{source_id} (also cleans OSS file)

### 3.6 Download Behavior

- `ppt_` → call export PPTX endpoint, return download link
- `lp_` → POST /api/v1/lesson-plan/export/docx, return DOCX file
- `up_` → direct download from `file_url` (OSS)

---

## Section 4: Upload, Favorites & Edge Cases

### 4.1 "Add Courseware" Button

- Click → upload modal (reuse existing modal style)
- Select file → POST /api/v1/courseware/upload (via OSS)
- Optional fields: title (default: filename), tags, remark
- Success → unshift to coursewareList, Toast "上传成功"
- File types: `.pdf, .ppt, .pptx, .doc, .docx, .mp4`
- Max size: 50MB

### 4.2 Favorites Logic

- Memory-only: `favorites: Set<string>` in store
- Star click → toggleFavorite(id), Set add/delete
- favoritedList getter filters coursewareList
- Reset on page refresh (no persistence per requirement)
- PersonalCenter favorites tab uses same getter

### 4.3 Edge Cases

| Scenario | Handling |
|---|---|
| Empty title | PPT: "未命名PPT", lesson plan: "未命名教案", uploaded: original filename |
| No cover image | PPT without image: default PPT-colored background; lesson plan/uploaded: default background by file_type |
| No file size | Display "—" |
| Date filter boundary | Backend UTC: today = 00:00 UTC today; week = 7 days; month = 30 days; year = 365 days |
| Sort order for uploaded files | `uploaded_at` field; AI content uses `updated_at`; unified via `COALESCE(uploaded_at, updated_at)` DESC |
| Empty list | Show: "暂无课件，点击添加课件上传或前往备课生成" |
| Pagination | Not implemented; no pagination controls shown |
| List/grid toggle | Preserved as-is |

### 4.4 No Changes

- Page layout, CSS styles unchanged
- List/grid view toggle preserved
- Type filter tabs preserved (all/pdf/ppt/video/word)
- Date filter tabs preserved (all/week/month/year)
- Card thumbnail gradient backgrounds + type badges preserved
