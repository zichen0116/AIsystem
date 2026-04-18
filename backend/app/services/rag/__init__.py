"""
RAG 服务包。

避免在包导入时立即加载图谱相关依赖，这样即使可选依赖未安装，
向量检索和知识资产处理链路也能正常工作。
"""

from importlib import import_module

__all__ = ["VectorStore", "DashScopeReranker", "GraphStore"]


def __getattr__(name):
    if name == "VectorStore":
        return import_module("app.services.rag.vector_store").VectorStore
    if name == "DashScopeReranker":
        return import_module("app.services.rag.reranker").DashScopeReranker
    if name == "GraphStore":
        return import_module("app.services.rag.graph_store").GraphStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
