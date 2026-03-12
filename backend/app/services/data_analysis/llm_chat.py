from __future__ import annotations

import json
from typing import Any

import pandas as pd

from app.services.html_llm import _call_llm


_SYSTEM = (
    "你是数据分析对话助手。用户上传了一个 Excel 表格。"
    "你需要基于表格字段信息和用户提问进行回答，给出清晰、友好的解释和建议。"
    "此模式为【纯对话模式】，不要输出图表列表，也不要要求用户选择图表。"
    "可以适当提到“如果需要我也可以生成图表”，但不要进入生成步骤。"
)


def _summarize_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    summary: dict[str, Any] = {"numeric": {}}
    try:
        if numeric_cols:
            desc = df[numeric_cols].describe().to_dict()
            # 只保留关键统计，避免 prompt 太长
            for col, stats in desc.items():
                summary["numeric"][str(col)] = {
                    "count": stats.get("count"),
                    "mean": stats.get("mean"),
                    "min": stats.get("min"),
                    "max": stats.get("max"),
                }
    except Exception:
        pass
    return summary


async def chat_about_excel(
    *,
    filename: str,
    sheet_name: str,
    rows: int,
    cols: int,
    column_infos: list[dict[str, Any]],
    df_preview_summary: dict[str, Any],
    user_message: str,
) -> str:
    payload = {
        "task": "excel_qna_chat",
        "file": {"filename": filename, "sheet_name": sheet_name, "rows": rows, "columns": cols},
        "columns": [
            {
                "name": c.get("name"),
                "dtype": c.get("dtype"),
                "non_null": c.get("non_null"),
                "unique": c.get("unique"),
                "sample_values": (c.get("sample_values") or [])[:5],
            }
            for c in (column_infos or [])
        ],
        "data_summary": df_preview_summary or {},
        "user_message": (user_message or "").strip(),
        "style": {
            "language": "zh-CN",
            "tone": "chatty, helpful, concise",
            "format": "use short paragraphs and bullet points when helpful",
        },
    }

    text = await _call_llm(_SYSTEM, json.dumps(payload, ensure_ascii=False), max_tokens=1800)
    return (text or "").strip()

