"""
数据分析（Excel -> 图表）相关 schema
"""

from __future__ import annotations

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field


ChartType = Literal[
    "histogram",
    "bar_count",
    "pie",
    "line",
    "scatter",
    "boxplot",
    "corr_heatmap",
]


class DataColumnInfo(BaseModel):
    name: str
    dtype: str
    non_null: int
    unique: int
    sample_values: list[Any] = Field(default_factory=list)


class ChartOption(BaseModel):
    id: str = Field(..., description="图表选项ID（用于后续生成）")
    type: ChartType
    title: str
    description: str
    columns: list[str] = Field(default_factory=list, description="该图表建议使用的列")


class UploadAndAnalyzeResponse(BaseModel):
    file_id: str
    filename: str
    sheet_name: str
    rows: int
    columns: int
    column_infos: list[DataColumnInfo]
    suggested_charts: list[ChartOption]
    analysis_summary: Optional[str] = None
    assistant_reply: Optional[str] = Field(
        None,
        description="对话式回复文本（可用于前端聊天气泡展示）",
    )


class GenerateChartsRequest(BaseModel):
    file_id: str
    chart_ids: list[str] = Field(..., min_length=1, description="用户多选的图表ID列表")
    sheet_name: Optional[str] = Field(None, description="可选：指定 sheet；不传默认首次分析用的 sheet")


class GenerateChartsResponse(BaseModel):
    task_id: str
    file_id: str
    combined_image_url: str
    report_url: Optional[str] = None


class DataAnalysisChatResponse(BaseModel):
    file_id: str = Field(..., description="用于后续对话的文件ID")
    assistant_reply: str = Field(..., description="纯对话模式下的大模型回复")

