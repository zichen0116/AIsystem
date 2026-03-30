# 知识库前后端对接设计文档

## 概述

将知识库页面（列表页 + 详情页）从 mock 数据切换到真实后端 API，并集成阿里云 OSS 文件存储和标签系统。

## 范围

- KnowledgeBase.vue（列表页）前后端对接
- KnowledgeDetail.vue（详情页）前后端对接
- 标签系统（JSON 数组方案，用户私有，各库独立）
- 阿里云 OSS 文件上传集成
- 不包含 3D 知识图谱优化

---

## 1. 数据库变更

### knowledge_libraries 表新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tags` | `JSON` | `[]` | 该知识库的标签数组，如 `["数学", "课程"]` |
| `updated_at` | `DateTime` | `now()` | 自动更新时间戳，`onupdate=func.now()` |

### 标签存储策略

- 标签存储在每个 `KnowledgeLibrary` 的 `tags` JSON 字段中
- **各库标签完全独立**：删除 A 库的标签不影响 B 库的同名标签
- 用户标签池 = 该用户所有未删除库的 tags 去重合集（仅用于搜索自动补全）
- 标签的增删改都通过 `PATCH /libraries/{id}` 操作单个库的 tags 数组
- 不新建任何额外的表

### Migration

一次 Alembic migration，添加 `tags` 和 `updated_at` 两个字段。

---

## 2. 后端 API 变更

### 2.1 新增接口

#### POST /api/v1/upload — 文件上传

- **鉴权**：必须登录（`Depends(get_current_user)`）
- **限制**：文件大小 ≤ 50MB；MIME 白名单（pdf, docx, doc, mp4, mp3, jpg, jpeg, png）
- Content-Type: `multipart/form-data`
- 字段: `file` (UploadFile)
- 上传到 OSS bucket `jishe-v1`，路径 `knowledge/{user_id}/{uuid}.{ext}`
- **file_type 映射**：扩展名自动映射为后端枚举值（docx/doc→word, jpg/jpeg/png→image, mp4→video, mp3→audio, pdf→pdf）
- 响应:

```json
{
  "url": "https://jishe-v1.oss-cn-beijing.aliyuncs.com/knowledge/1/abc123.pdf",
  "file_name": "原始文件名.pdf",
  "file_type": "pdf"
}
```

`file_type` 返回值保证与后端 `FileType` 枚举一致（pdf/word/video/image/audio）。

#### GET /api/v1/libraries/tags — 获取用户标签池

- 查询当前用户所有未删除库的 tags 字段
- 去重后返回标签列表（仅用于搜索自动补全）
- 响应: `["数学", "课程", "安全", ...]`

#### PATCH /api/v1/libraries/tags/rename — 全局重命名标签

- Body: `{ "old_name": "数学", "new_name": "高等数学" }`
- 遍历用户所有未删除库，将 tags 中的 old_name 替换为 new_name
- 用于「管理标签」面板的重命名功能（跨库统一更名的便利操作）
- 响应: `{ "updated_count": 3 }`

### 2.2 修改接口

#### GET /api/v1/libraries — 列表响应增加字段

响应中每个 library 增加:
- `tags`: `string[]` — 标签数组
- `updated_at`: `datetime` — 更新时间
- `asset_count`: `int` — 关联资产数（通过子查询 COUNT 计算）

**scope 参数扩展**：支持 `all`（默认）| `personal` | `system` 三态
- `all`：返回用户自己的库 + 所有系统公开库
- `personal`：仅用户自己的库
- `system`：仅系统公开库

支持按标签筛选和搜索: `GET /api/v1/libraries?scope=all&tag=数学&search=几何`
- `search` 参数同时搜索 `name` 和 `description` 字段（ILIKE 模糊匹配）
- `tag` 参数筛选 tags JSON 数组中包含该标签的知识库

#### PATCH /api/v1/libraries/{id} — 支持更新 tags

Body 增加可选字段 `tags: string[]`，允许完整替换知识库的标签列表。
这是标签增删的唯一入口（单库级别操作，不影响其他库）。

#### POST /api/v1/knowledge — 支持 OSS URL

现有接口的 `file_path` 字段改为支持 OSS URL（`https://...`）。
前端先上传到 OSS 拿到 URL，再调此接口创建资产记录。

#### GET /api/v1/knowledge — 系统库资产可见性

**权限修正**：当 `library_id` 指向系统公开库（`is_system=True, is_public=True`）时，不按 `user_id` 过滤资产，所有登录用户均可查看。仅当查询个人库时才按 `user_id` 过滤。

#### DELETE /api/v1/knowledge/{asset_id} — 增加 OSS 清理

删除资产时同步调用 `OSSService.delete_file(asset.file_path)` 清理 OSS 文件。

---

## 3. OSS 集成

### 3.1 OSS 服务封装

新建 `backend/app/services/oss_service.py`:

```python
class OSSService:
    def upload_file(file: UploadFile, user_id: int) -> str:
        """上传文件到 OSS，返回公开访问 URL"""
        # 路径: knowledge/{user_id}/{uuid}.{ext}

    def delete_file(url: str) -> None:
        """根据 URL 提取 object key 并删除 OSS 文件"""

    def download_to_temp(url: str) -> str:
        """从 OSS 下载到临时目录，返回本地临时文件路径"""
```

使用 `oss2` Python SDK（需加到 `requirements.txt`），从 config 读取:
- `OSS_ENDPOINT`: `https://oss-cn-beijing.aliyuncs.com`
- `OSS_BUCKET`: `jishe-v1`
- `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`

### 3.2 OSS 文件生命周期

| 操作 | OSS 行为 |
|------|---------|
| 上传文件 | `POST /upload` → `OSSService.upload_file()` |
| 删除单个资产 | `DELETE /knowledge/{id}` → `OSSService.delete_file()` |
| 删除整个知识库 | `cleanup_library` Celery 任务中遍历资产 → `OSSService.delete_file()` |
| Celery 解析 | `OSSService.download_to_temp()` → 解析 → 删除临时文件 |

### 3.3 Celery 任务适配

现有 `process_knowledge_asset` 任务需要适配 OSS:
- `file_path` 字段存储 OSS URL
- 任务执行时: 从 OSS 下载到临时目录 → 解析 → 删除临时文件
- `cleanup_library` 任务: 遍历库内所有资产，逐个删除 OSS 文件

### 3.4 上传流程

```
前端选择文件
  → POST /api/v1/upload (multipart/form-data, 需登录, ≤50MB)
  → 后端校验 MIME → 上传到 OSS → 映射 file_type → 返回 { url, file_name, file_type }
前端拿到 url
  → POST /api/v1/knowledge { file_path: url, file_name, file_type, library_id }
  → 后端创建 DB 记录 + 触发 Celery 解析任务
```

### 3.5 依赖

`requirements.txt` 新增 `oss2` 包。

---

## 4. 前端架构

### 4.1 Pinia Store: stores/knowledge.js

```javascript
// State
libraries: []      // 知识库列表
userTags: []       // 用户标签池（仅用于自动补全）
loading: false
error: null

// Actions
fetchLibraries(scope?, search?, tag?)  // GET /libraries
createLibrary(data)                     // POST /libraries
updateLibrary(id, data)                 // PATCH /libraries/{id}（包括更新 tags）
deleteLibrary(id)                       // DELETE /libraries/{id}
fetchUserTags()                         // GET /libraries/tags
renameTag(oldName, newName)             // PATCH /libraries/tags/rename
```

### 4.2 KnowledgeBase.vue 改造

**删除:**
- `systemResources` mock ref
- `personalResources` mock ref
- `allTags` mock ref
- 所有本地 CRUD 函数

**替换为:**
- `onMounted` → `store.fetchLibraries()` + `store.fetchUserTags()`
- 筛选 → 调 API 传 `scope`（all/personal/system）
- 搜索 → 调 API 传 `search`
- 标签筛选 → 调 API 传 `tag`
- 创建/编辑 → `store.createLibrary()` / `store.updateLibrary()`
- 删除 → `store.deleteLibrary()`
- 添加/移除标签 → `store.updateLibrary(id, { tags: [...] })`（单库操作）
- 管理标签重命名 → `store.renameTag()`

### 4.3 KnowledgeDetail.vue 改造

**删除:**
- `allDocs` mock ref
- mock 下载提示

**替换为:**
- `onMounted` → `GET /knowledge?library_id={id}` 获取真实文档列表
- 文件上传 → `POST /upload` + `POST /knowledge`
- 删除文档 → `DELETE /knowledge/{id}`
- 下载文档 → `window.open(doc.file_path)` (OSS URL)
- 状态轮询 → `GET /knowledge/{id}/status` 轮询向量化进度

---

## 5. 错误处理

- API 错误统一由 `http.js` 处理 401（跳登录）
- 上传失败 → 前端 toast 提示，不创建资产记录
- 文件过大/类型不合法 → 后端返回 400，前端展示具体原因
- OSS 不可用 → 返回 500，前端展示错误提示
- Celery 任务失败 → `vector_status` 设为 `failed`，前端展示「处理失败」状态
- OSS 清理失败 → 记录日志，不阻塞删除操作（最终一致性）
