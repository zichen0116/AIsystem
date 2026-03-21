"""资源搜索（Dify 工作流）请求/响应"""
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ResourceSearchRequest(BaseModel):
    """与前端筛选一致；工作流侧映射为 course_name + node_name（及附加上下文）。"""

    keyword: str = Field("", description="搜索关键词 / 主题 / 知识点")
    grade: str = Field("全部年级", description="年级筛选")
    subject: str = Field("全部学科", description="学科筛选")
    file_type: str = Field("全部类型", description="资源类型筛选")
    sort_by: str = Field("相关度优先", description="排序方式（传给模型作参考）")


class ResourceItem(BaseModel):
    id: str
    title: str
    tag: str = ""
    desc: str = ""
    icon: str = "📚"
    url: Optional[str] = Field(None, description="资源直达链接（Markdown [标题](url) 解析或 JSON 字段）")


class ResourceSearchResponse(BaseModel):
    items: List[ResourceItem]
    raw_output: Optional[str] = Field(None, description="工作流原始文本（调试用，可截断）")
    workflow_run_id: Optional[str] = None
