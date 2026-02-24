# 知识库系统设计文档

**日期**：2026-02-24
**状态**：已审批，待实现

---

## 一、需求概述

1. 每个用户可创建多个知识库，对自己的知识库有完整的增删改查权限
2. 不同知识库之间实现隔离（命名空间），方便检索时按库过滤
3. 系统管理员可创建系统级知识库，可选择是否公开；公开后普通用户可在对话时手动选用

---

## 二、数据模型

### 新增：`knowledge_libraries` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| owner_id | INT FK → users.id | 创建者 |
| name | VARCHAR(100) | 知识库名称 |
| description | VARCHAR(500) | 描述（可空） |
| is_system | BOOL default False | 是否为系统级库（仅管理员可置 True） |
| is_public | BOOL default False | 是否公开（仅系统库有意义） |
| is_deleted | BOOL default False | 软删除标记 |
| created_at | DATETIME | 创建时间 |

### 修改：`knowledge_assets` 表

| 变更 | 说明 |
|------|------|
| 新增 `library_id` INT FK → knowledge_libraries.id | 文件归属知识库（nullable，兼容旧数据） |
| `vector_status` Boolean → VARCHAR(20) | 枚举：`pending / processing / completed / failed` |

### 修改：`users` 表

| 变更 | 说明 |
|------|------|
| 新增 `is_admin` BOOL default False | 管理员标识，通过数据库直接写入，不暴露 API |

### 关系

```
User 1──* KnowledgeLibrary
KnowledgeLibrary 1──* KnowledgeAsset
```

---

## 三、命名空间隔离方案

**选用方案二：单 Collection + Metadata Filter**

所有文档写入同一个 ChromaDB collection（`knowledge_base`），metadata 增加 `library_id` 字段。

**理由**：
- 多库同时检索只需一次查询，传 `{"library_id": {"$in": [1,3,5]}}` 即可，无需跨 collection 合并重排
- ChromaDB 支持 `collection.delete(where={"library_id": X})` 批量删除
- HNSW O(log N) 复杂度，单 collection 性能可接受

**写入 metadata 结构**（在现有基础上增加 `library_id`）：
```python
{
    "user_id": 1,
    "library_id": 3,
    "source": "file.pdf",
    "chunk_index": 0,
    ...
}
```

**BM25 索引 key** 从 `user_id` 改为 `library_id`，多库检索时按 `library_ids` 列表分别取各库 BM25 结果，与向量结果一起做 RRF 融合。

---

## 四、API 设计

### 4.1 知识库管理 `/api/v1/libraries`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/libraries` | 创建知识库 | 登录用户（管理员可设 is_system/is_public） |
| GET | `/libraries?scope=personal` | 我的知识库列表 | 登录用户 |
| GET | `/libraries?scope=system` | 所有公开系统库列表 | 登录用户 |
| PATCH | `/libraries/{id}` | 更新名称/描述/is_public | 拥有者（is_public 仅管理员） |
| DELETE | `/libraries/{id}` | 软删除，触发 Celery 异步清理 | 拥有者 |

### 4.2 知识资产 `/api/v1/knowledge`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/knowledge` | 上传文件（传 library_id），立即返回，Celery 后台处理 |
| GET | `/knowledge?library_id=1` | 按库列出文件 |
| GET | `/knowledge/{id}/status` | 轻量状态查询：pending/processing/completed/failed |
| DELETE | `/knowledge/{id}` | 删除文件 + ChromaDB 对应向量 |

### 4.3 对话 `/api/v1/chat`

**Request Body 调整**：

```json
{
  "session_id": "uuid-xxxx",
  "library_ids": [1, 3, 5],
  "temp_files": ["file_uuid_a"],
  "message": "请根据系统教学法和我的语文备课库，帮我生成第一课的教案",
  "input_type": "text"
}
```

- `session_id`：不传则新建会话，保证会话隔离
- `library_ids`：本次检索的知识库列表（个人库 + 公开系统库）
- `temp_files`：临时参考资料，直接注入上下文，不向量化
- `input_type`：预留字段，区分 text / voice

---

## 五、数据流设计

### 5.1 文件上传流

```
POST /knowledge  {library_id, file}
  │
  ├─ 保存文件 → DB 插入（vector_status="pending"）→ 立即返回
  │
  └─ Celery Task: process_knowledge_asset(asset_id)
       ├─ vector_status = "processing"
       ├─ ParserFactory 解析
       ├─ 语义/递归分块
       ├─ ChromaDB add_documents（metadata 含 library_id）
       ├─ 成功 → vector_status = "completed"
       └─ 失败 → vector_status = "failed"，指数退避重试
```

### 5.2 对话检索流

```
POST /chat
  │
  ├─ 1. 解析/创建 session
  │
  ├─ 2. temp_files 处理（按文件类型分支）
  │     ├─ 文本类（PDF/DOCX/TXT）
  │     │   └─ ParserFactory 解析 → 截断（单文件 ≤3000 tokens，总量 ≤8000 tokens）
  │     │       → 拼入文本 context
  │     └─ 视觉类（图片/视频）
  │         ├─ 图片：Base64 编码
  │         └─ 视频：提取关键帧（≤15帧）→ 各帧 Base64
  │             → 组装多模态消息结构 → 传入 Qwen-VL
  │
  ├─ 3. 向量检索（有 library_ids 时）
  │     └─ HybridRetriever.search(
  │           query=message,
  │           filter={"library_id": {"$in": library_ids}}
  │        )  → RRF 融合 → top-k 文档
  │
  ├─ 4. 组装 prompt
  │     └─ [系统提示] + [RAG文档] + [temp_files内容] + [历史消息] + [用户消息]
  │
  └─ 5. LangGraph 工作流（agent → tools → grader → outline_approval → finalize）
```

### 5.3 删除知识库流（软删除 + 异步清理）

```
DELETE /libraries/{id}
  ├─ 校验所有权
  ├─ DB: is_deleted = True → commit → 立即返回 200
  │
  └─ Celery Task: cleanup_library(library_id)
       ├─ ChromaDB: collection.delete(where={"library_id": id})
       ├─ 物理删除本地文件（逐个 file_path）
       └─ DB: 物理删除 KnowledgeAsset + KnowledgeLibrary
              （失败则指数退避重试）
```

---

## 六、已有功能（无需重复实现）

- Celery 异步任务框架（`tasks.py`）
- ParserFactory 多格式解析（PDF/DOCX/视频/图片）
- BM25 + 向量混合检索（`hybrid_retriever.py`）
- RRF 融合（`hybrid_retriever.py`）
- LangGraph 工作流（`services/ai/graph/`）
- JWT 认证与依赖注入（`core/auth.py`）
- DashScope 视觉能力（`services/ai/dashscope_service.py`）

---

## 七、不在本次范围内

- 管理员 API 端点（管理员通过数据库直接写入 is_admin）
- 知识库访问统计
- 向量库迁移/备份
