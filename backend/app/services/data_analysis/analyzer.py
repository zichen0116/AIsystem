from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd


@dataclass(frozen=True)
class DataProfile:
    sheet_name: str
    df: pd.DataFrame
    column_infos: list[dict[str, Any]]
    numeric_cols: list[str]
    categorical_cols: list[str]
    datetime_cols: list[str]


def _safe_sample_values(series: pd.Series, limit: int = 5) -> list[Any]:
    try:
        values = series.dropna().unique().tolist()
        return values[:limit]
    except Exception:
        return []


def load_excel_profile(path: str, sheet_name: Optional[str] = None, max_rows: int = 5000) -> DataProfile:
    """
    读取 Excel 并生成基础 profile。
    - 默认读取第一个 sheet
    - 为避免超大文件内存压力，只读取前 max_rows 行用于建议图表与预览分析
    """
    xls = pd.ExcelFile(path)
    target_sheet = sheet_name or (xls.sheet_names[0] if xls.sheet_names else None)
    if not target_sheet:
        raise ValueError("Excel 文件没有可用的 sheet")

    df = pd.read_excel(path, sheet_name=target_sheet, engine="openpyxl")
    if len(df) > max_rows:
        df = df.head(max_rows)

    # 尝试解析 datetime 列（轻量：只对 object 列尝试）
    datetime_cols: list[str] = []
    for col in df.columns:
        if df[col].dtype == "object":
            parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if parsed.notna().sum() >= max(5, int(len(df) * 0.3)):
                df[col] = parsed
                datetime_cols.append(str(col))

    numeric_cols = [str(c) for c in df.select_dtypes(include=["number"]).columns.tolist()]
    dt_cols = [str(c) for c in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()]
    # 合并/去重
    datetime_cols = list(dict.fromkeys([*datetime_cols, *dt_cols]))
    categorical_cols = [
        str(c) for c in df.columns
        if str(c) not in set(numeric_cols) and str(c) not in set(datetime_cols)
    ]

    col_infos: list[dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        col_infos.append(
            {
                "name": str(col),
                "dtype": str(s.dtype),
                "non_null": int(s.notna().sum()),
                "unique": int(s.nunique(dropna=True)),
                "sample_values": _safe_sample_values(s),
            }
        )

    return DataProfile(
        sheet_name=target_sheet,
        df=df,
        column_infos=col_infos,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        datetime_cols=datetime_cols,
    )


def new_id() -> str:
    return uuid.uuid4().hex

