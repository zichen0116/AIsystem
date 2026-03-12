from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.services.data_analysis.analyzer import DataProfile, new_id


def _titleize(s: str) -> str:
    return s.replace("_", " ").strip()


def suggest_charts(profile: DataProfile, max_options: int = 20) -> list[dict[str, Any]]:
    """
    生成“可多选”的图表建议列表（不依赖外部 LLM，保证离线可用）。
    返回结构与 schemas.ChartOption 一致的 dict 列表。
    """
    df = profile.df
    numeric = profile.numeric_cols
    cat = profile.categorical_cols
    dt = profile.datetime_cols

    options: list[dict[str, Any]] = []

    # 1) 单变量：数值分布直方图
    for col in numeric[:8]:
        options.append(
            {
                "id": f"hist_{col}_{new_id()[:6]}",
                "type": "histogram",
                "title": f"{_titleize(col)} 分布直方图",
                "description": f"查看 `{col}` 的取值分布与集中趋势。",
                "columns": [col],
            }
        )

    # 2) 单变量：类别计数条形图
    for col in cat[:8]:
        options.append(
            {
                "id": f"bar_{col}_{new_id()[:6]}",
                "type": "bar_count",
                "title": f"{_titleize(col)} 类别计数",
                "description": f"统计 `{col}` 各类别出现次数（取前 20 类）。",
                "columns": [col],
            }
        )

    # 3) 饼图：类别占比（类别不宜太多）
    for col in cat[:8]:
        nunique = int(df[col].nunique(dropna=True)) if col in df.columns else 0
        if 2 <= nunique <= 10:
            options.append(
                {
                    "id": f"pie_{col}_{new_id()[:6]}",
                    "type": "pie",
                    "title": f"{_titleize(col)} 占比饼图",
                    "description": f"展示 `{col}` 各类别占比（最多 10 类）。",
                    "columns": [col],
                }
            )

    # 4) 趋势：时间序列折线（dt + numeric）
    if dt and numeric:
        tcol = dt[0]
        for ncol in numeric[:3]:
            options.append(
                {
                    "id": f"line_{tcol}_{ncol}_{new_id()[:6]}",
                    "type": "line",
                    "title": f"{_titleize(ncol)} 随 {_titleize(tcol)} 变化趋势",
                    "description": f"按时间 `{tcol}` 聚合（天）查看 `{ncol}` 的变化趋势。",
                    "columns": [tcol, ncol],
                }
            )

    # 5) 相关性热力图（数值列 >= 2）
    if len(numeric) >= 2:
        cols = numeric[:10]
        options.append(
            {
                "id": f"corr_{new_id()[:6]}",
                "type": "corr_heatmap",
                "title": "数值特征相关性热力图",
                "description": "查看数值列之间的相关性强弱。",
                "columns": cols,
            }
        )

    # 6) 散点：两个数值变量关系
    if len(numeric) >= 2:
        x, y = numeric[0], numeric[1]
        options.append(
            {
                "id": f"scatter_{x}_{y}_{new_id()[:6]}",
                "type": "scatter",
                "title": f"{_titleize(x)} vs {_titleize(y)} 散点图",
                "description": f"观察 `{x}` 与 `{y}` 的关系与离群点。",
                "columns": [x, y],
            }
        )

    # 7) 箱线图：类别对数值分布影响
    if cat and numeric:
        ccol, ncol = cat[0], numeric[0]
        options.append(
            {
                "id": f"box_{ccol}_{ncol}_{new_id()[:6]}",
                "type": "boxplot",
                "title": f"{_titleize(ncol)} 在不同 {_titleize(ccol)} 下的分布",
                "description": f"比较不同 `{ccol}` 类别下 `{ncol}` 的分布差异。",
                "columns": [ccol, ncol],
            }
        )

    # 截断
    return options[:max_options]

