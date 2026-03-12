from __future__ import annotations

import math
from typing import Any

import pandas as pd
from pathlib import Path

# Matplotlib 在无 GUI 环境下必须使用 Agg
import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from matplotlib import font_manager  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

from app.core.config import settings  # noqa: E402


def _setup_matplotlib_chinese() -> None:
    """
    解决中文/负号显示问题。
    说明：不同 Windows/Linux 环境字体不同，这里设置一组常见中文字体回退列表。
    """
    plt.rcParams["axes.unicode_minus"] = False

    backend_root = Path(__file__).resolve().parents[3]

    # 1) 优先使用用户显式指定的字体文件
    font_path = (settings.DATA_ANALYSIS_FONT_PATH or "").strip()
    if font_path:
        try:
            p = Path(font_path)
            if not p.is_absolute():
                p = backend_root / p
            if p.exists():
                font_manager.fontManager.addfont(str(p))
                fp = FontProperties(fname=str(p))
                name = fp.get_name()
                if name:
                    plt.rcParams["font.family"] = name
                    return
            if name:
                plt.rcParams["font.family"] = name
                return
        except Exception:
            # 继续走自动探测
            pass

    # 2) 自动探测常见中文字体文件（Windows / Linux / macOS）
    candidates = [
        # Windows
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        # Linux 常见（Noto CJK）
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/arphic/ukai.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttf",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ]
    for p in candidates:
        try:
            path = str(p)
            if not Path(path).exists():
                continue
            font_manager.fontManager.addfont(path)
            name = FontProperties(fname=path).get_name()
            if name:
                plt.rcParams["font.family"] = name
                return
        except Exception:
            continue

    # 3) 最后回退到常见字体族名（如果系统已安装）
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]


def _annotate_bars(ax, fmt: str = "{:.0f}") -> None:
    for p in ax.patches:
        try:
            h = float(p.get_height())
        except Exception:
            continue
        if not (h == h):  # NaN
            continue
        ax.annotate(
            fmt.format(h),
            (p.get_x() + p.get_width() / 2, h),
            ha="center",
            va="bottom",
            fontsize=9,
            xytext=(0, 2),
            textcoords="offset points",
        )


def _ensure_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少列: {missing}")


def _plot_hist(ax, df: pd.DataFrame, col: str, title: str):
    _ensure_columns(df, [col])
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    ax.hist(s, bins=20, color="#60a5fa", edgecolor="white")
    ax.set_title(title)
    ax.set_xlabel(col)
    ax.set_ylabel("count")


def _plot_bar_count(ax, df: pd.DataFrame, col: str, title: str):
    _ensure_columns(df, [col])
    vc = df[col].astype(str).fillna("NA").value_counts().head(20)
    ax.bar(vc.index, vc.values, color="#34d399")
    ax.set_title(title)
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel(col)
    ax.set_ylabel("count")
    _annotate_bars(ax, fmt="{:.0f}")


def _plot_pie(ax, df: pd.DataFrame, col: str, title: str):
    _ensure_columns(df, [col])
    vc = df[col].astype(str).fillna("NA").value_counts().head(10)
    ax.pie(vc.values, labels=vc.index, autopct="%1.1f%%", startangle=90)
    ax.set_title(title)


def _plot_line(ax, df: pd.DataFrame, tcol: str, ncol: str, title: str):
    _ensure_columns(df, [tcol, ncol])
    t = pd.to_datetime(df[tcol], errors="coerce")
    y = pd.to_numeric(df[ncol], errors="coerce")
    tmp = pd.DataFrame({tcol: t, ncol: y}).dropna()
    if tmp.empty:
        ax.text(0.5, 0.5, "无可用数据", ha="center", va="center")
        ax.set_title(title)
        return
    tmp["__day"] = tmp[tcol].dt.date
    daily = tmp.groupby("__day")[ncol].mean().reset_index()
    ax.plot(daily["__day"], daily[ncol], color="#f97316")
    ax.set_title(title)
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_ylabel(ncol)


def _plot_scatter(ax, df: pd.DataFrame, x: str, y: str, title: str):
    _ensure_columns(df, [x, y])
    xx = pd.to_numeric(df[x], errors="coerce")
    yy = pd.to_numeric(df[y], errors="coerce")
    tmp = pd.DataFrame({x: xx, y: yy}).dropna()
    ax.scatter(tmp[x], tmp[y], s=10, alpha=0.6, color="#ef4444")
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)


def _plot_boxplot(ax, df: pd.DataFrame, ccol: str, ncol: str, title: str):
    _ensure_columns(df, [ccol, ncol])
    tmp = df[[ccol, ncol]].copy()
    tmp[ncol] = pd.to_numeric(tmp[ncol], errors="coerce")
    tmp = tmp.dropna()
    if tmp.empty:
        ax.text(0.5, 0.5, "无可用数据", ha="center", va="center")
        ax.set_title(title)
        return
    # 类别过多时取前 15
    top = tmp[ccol].astype(str).value_counts().head(15).index.tolist()
    tmp = tmp[tmp[ccol].astype(str).isin(top)]
    sns.boxplot(ax=ax, data=tmp, x=ccol, y=ncol)
    ax.set_title(title)
    ax.tick_params(axis="x", labelrotation=45)


def _plot_corr_heatmap(ax, df: pd.DataFrame, cols: list[str], title: str):
    _ensure_columns(df, cols)
    tmp = df[cols].apply(pd.to_numeric, errors="coerce")
    corr = tmp.corr(numeric_only=True)
    sns.heatmap(
        corr,
        ax=ax,
        cmap="RdYlBu_r",
        annot=True,
        fmt=".2f",
        cbar=True,
        vmin=-1,
        vmax=1,
        annot_kws={"fontsize": 9},
    )
    ax.set_title(title)
    ax.tick_params(axis="x", labelrotation=0)
    ax.tick_params(axis="y", labelrotation=0)


def render_combined_figure(
    df: pd.DataFrame,
    selected_options: list[dict[str, Any]],
    output_path: str,
    fig_title: str = "数据分析综合报告",
) -> None:
    """
    将多张图表合成到一个大图（PNG）中。
    selected_options: list of ChartOption-like dicts
    """
    if not selected_options:
        raise ValueError("未选择任何图表")

    sns.set_theme(style="whitegrid")
    # seaborn.set_theme 会覆盖 matplotlib rcParams，中文字体配置必须放在它之后
    _setup_matplotlib_chinese()

    n = len(selected_options)
    cols = int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))

    # 尺寸按图数量自适应
    fig_w = max(12, cols * 6)
    fig_h = max(8, rows * 4.5)
    fig, axes = plt.subplots(rows, cols, figsize=(fig_w, fig_h))
    if rows == 1 and cols == 1:
        axes_list = [axes]
    else:
        axes_list = list(axes.flatten())

    fig.suptitle(fig_title, fontsize=18, fontweight="bold")

    for i, opt in enumerate(selected_options):
        ax = axes_list[i]
        ctype = opt["type"]
        title = opt.get("title") or ctype
        cols_spec = opt.get("columns", [])

        try:
            if ctype == "histogram":
                _plot_hist(ax, df, cols_spec[0], title)
            elif ctype == "bar_count":
                _plot_bar_count(ax, df, cols_spec[0], title)
            elif ctype == "pie":
                _plot_pie(ax, df, cols_spec[0], title)
            elif ctype == "line":
                _plot_line(ax, df, cols_spec[0], cols_spec[1], title)
            elif ctype == "scatter":
                _plot_scatter(ax, df, cols_spec[0], cols_spec[1], title)
            elif ctype == "boxplot":
                _plot_boxplot(ax, df, cols_spec[0], cols_spec[1], title)
            elif ctype == "corr_heatmap":
                _plot_corr_heatmap(ax, df, cols_spec, title)
            else:
                ax.text(0.5, 0.5, f"未支持图表类型: {ctype}", ha="center", va="center")
                ax.set_title(title)
        except Exception as e:
            ax.clear()
            ax.text(0.5, 0.5, f"生成失败\n{e}", ha="center", va="center")
            ax.set_title(title)

    # 隐藏多余子图
    for j in range(n, len(axes_list)):
        axes_list[j].axis("off")

    fig.tight_layout(rect=[0, 0.03, 1, 0.93])
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

