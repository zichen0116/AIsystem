from __future__ import annotations

import json
from typing import Any, Optional

from app.services.html_llm import _call_llm  # 复用 html 小游戏同一套 DeepSeek(OpenAI兼容)调用


_SYSTEM = (
    "你是数据分析助手。你会根据用户上传的 Excel 表格字段信息，"
    "用通俗中文输出：1) 对话式回复（像在聊天，包含要点、结论、下一步建议）；2) 推荐用户可生成的图表列表。"
    "输出必须是严格 JSON，不能包含额外文字。"
)


def _allowed_types() -> list[str]:
    return ["histogram", "bar_count", "pie", "line", "scatter", "boxplot", "corr_heatmap"]


async def plan_charts_with_llm(
    *,
    filename: str,
    sheet_name: str,
    rows: int,
    cols: int,
    column_infos: list[dict[str, Any]],
    user_requirement: str = "",
    max_options: int = 10,
) -> Optional[dict[str, Any]]:
    """
    使用 html 小游戏同款 LLM（DeepSeek/OpenAI兼容）生成：
    - analysis_summary: str
    - assistant_reply: str
    - suggested_charts: [{type,title,description,columns:[...]}]
    返回 dict；若 LLM 不可用或 JSON 不合法则返回 None
    """
    col_brief = [
        {
            "name": c.get("name"),
            "dtype": c.get("dtype"),
            "non_null": c.get("non_null"),
            "unique": c.get("unique"),
            "sample_values": c.get("sample_values", [])[:5],
        }
        for c in (column_infos or [])
    ]

    user = {
        "task": "excel_data_analysis_chart_recommendation",
        "file": {"filename": filename, "sheet_name": sheet_name, "rows": rows, "columns": cols},
        "user_requirement": (user_requirement or "").strip(),
        "columns": col_brief,
        "constraints": {
            "max_options": max_options,
            "allowed_chart_types": _allowed_types(),
            "rules": [
                "columns 必须是该表真实存在的列名列表",
                "每个 chart 1-2 句话描述用途，title 简短",
                "结合 user_requirement 优先推荐最有价值的图表组合（分布/对比/趋势/相关性/离群点）",
            ],
        },
        "output_json_schema": {
            "analysis_summary": "string",
            "assistant_reply": "string",
            "suggested_charts": [
                {
                    "type": "one of allowed_chart_types",
                    "title": "string",
                    "description": "string",
                    "columns": ["string"],
                }
            ],
        },
    }

    content = await _call_llm(_SYSTEM, json.dumps(user, ensure_ascii=False), max_tokens=1800)
    if not content:
        return None

    # 兼容模型把 JSON 包在 ```json ... ``` 的情况
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # 可能还有 json\n 前缀
        if "\n" in text:
            text = text.split("\n", 1)[1].strip()

    try:
        obj = json.loads(text)
    except Exception:
        return None

    if not isinstance(obj, dict):
        return None

    charts = obj.get("suggested_charts")
    if not isinstance(charts, list):
        return None

    allowed = set(_allowed_types())
    # 基础过滤/裁剪
    cleaned: list[dict[str, Any]] = []
    for c in charts:
        if not isinstance(c, dict):
            continue
        ctype = c.get("type")
        if ctype not in allowed:
            continue
        title = str(c.get("title") or "").strip()
        desc = str(c.get("description") or "").strip()
        cols_list = c.get("columns") or []
        if not isinstance(cols_list, list):
            cols_list = []
        cols_list = [str(x) for x in cols_list if str(x)]
        if not title:
            continue
        cleaned.append({"type": ctype, "title": title, "description": desc, "columns": cols_list})
        if len(cleaned) >= max_options:
            break

    if not cleaned:
        return None

    return {
        "analysis_summary": str(obj.get("analysis_summary") or "").strip() or None,
        "assistant_reply": str(obj.get("assistant_reply") or "").strip() or None,
        "suggested_charts": cleaned,
    }

