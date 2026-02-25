# RAG Rerank 重排序模型集成设计

## 概述

在现有 RAG 检索流程（BM25 + 向量检索 + RRF 融合）之后，增加基于阿里云百炼 `qwen3-vl-rerank` 模型的重排序阶段，提升检索精度。

## 数据流

```
用户查询
  ↓
HybridRetriever.search(query, user_id, k=10)
  ↓
BM25 召回 15篇 + 向量检索 15篇
  ↓
RRF 融合去重 → 约 20-30 篇候选
  ↓
DashScopeReranker.rerank(query, candidates, top_n=10)  ← 新增
  ↓
返回 top 10 精排文档
  ↓
Agent / Grader 使用
```

## 文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/app/services/rag/reranker.py` | 新增 | DashScopeReranker 类 |
| `backend/app/services/rag/hybrid_retriever.py` | 修改 | search() 改 async，末尾调用 reranker |
| `backend/app/core/config.py` | 修改 | 新增 RERANK_MODEL 配置项 |

不改动：tools.py、nodes.py、workflow.py、state.py（上层完全透明）。

## DashScopeReranker 设计

- 文件：`backend/app/services/rag/reranker.py`
- API：`POST https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank`
- 模型：`qwen3-vl-rerank`（多模态，支持文本/图片/视频）
- 认证：复用 DASHSCOPE_API_KEY
- HTTP 客户端：httpx.AsyncClient
- 输入：LangChain Document 列表 → 转为 `{"text": page_content}` 格式
- 输出：按 rerank score 降序的 Document 列表，score 写入 `metadata["rerank_score"]`
- 错误处理：API 失败时 log 警告，回退返回原始文档顺序

## 配置

- `RERANK_MODEL`：默认 `qwen3-vl-rerank`
- API Key：复用 `DASHSCOPE_API_KEY`

## 召回策略

- BM25 + 向量各召回 k*3 篇（默认各 30 篇）
- RRF 融合去重后约 20-30 篇候选
- Rerank 精排取 top_n（默认 10）

## 错误处理

- API 超时（10秒）→ warning 日志，回退 RRF 结果
- API 错误码 → error 日志，回退 RRF 结果
- 空文档列表 → 直接返回空列表
- 核心原则：Rerank 是增强层，不阻断检索流程
