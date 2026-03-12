from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Form

from app.schemas.data_analysis import (
    UploadAndAnalyzeResponse,
    GenerateChartsRequest,
    GenerateChartsResponse,
    DataAnalysisChatResponse,
    ChartOption,
    DataColumnInfo,
)
from app.services.data_analysis.analyzer import load_excel_profile, new_id
from app.services.data_analysis.chart_suggester import suggest_charts
from app.services.data_analysis.chart_renderer import render_combined_figure
from app.services.data_analysis import storage
from app.services.data_analysis.llm_planner import plan_charts_with_llm
from app.services.data_analysis.llm_chat import chat_about_excel, _summarize_dataframe
from app.services.html_llm import _call_llm


router = APIRouter(prefix="/data-analysis", tags=["data-analysis"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB


@router.post(
    "/upload",
    response_model=UploadAndAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_analyze(
    file: UploadFile = File(...),
    requirement: str = Form(""),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，仅支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大（最大 15MB）")

    file_id = new_id()
    scope = "public"
    stored = storage.save_upload(file_id=file_id, filename=file.filename or f"{file_id}{suffix}", content_bytes=content, scope=scope)

    try:
        profile = load_excel_profile(str(stored.path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析 Excel 失败: {e}")

    # 优先用 DeepSeek(HTML_LLM_*) 生成“更像大模型”的摘要与图表建议；失败则回退到规则推荐
    llm_plan = await plan_charts_with_llm(
        filename=file.filename or "",
        sheet_name=profile.sheet_name,
        rows=int(profile.df.shape[0]),
        cols=int(profile.df.shape[1]),
        column_infos=profile.column_infos,
        user_requirement=requirement,
        max_options=12,
    )
    if llm_plan:
        options = []
        for o in llm_plan["suggested_charts"]:
            options.append(
                {
                    "id": f"{o['type']}_{new_id()[:6]}",
                    "type": o["type"],
                    "title": o["title"],
                    "description": o.get("description") or "",
                    "columns": o.get("columns") or [],
                }
            )
        analysis_summary = llm_plan.get("analysis_summary") or "已完成分析并生成图表建议。"
        assistant_reply = llm_plan.get("assistant_reply") or analysis_summary
    else:
        options = suggest_charts(profile)
        analysis_summary = "已读取 Excel，并生成可选图表建议；请选择需要生成的图表类型。"
        assistant_reply = analysis_summary

    # 将 upload 阶段的图表建议落盘，保证 generate 时 chart_id 可追溯且稳定
    storage.write_meta(
        file_id=file_id,
        scope=scope,
        data={
            "file_id": file_id,
            "filename": file.filename or "",
            "scope": scope,
            "requirement": (requirement or "").strip(),
            "sheet_name": profile.sheet_name,
            "rows": int(profile.df.shape[0]),
            "columns": int(profile.df.shape[1]),
            "analysis_summary": analysis_summary,
            "assistant_reply": assistant_reply,
            "suggested_charts": options,
        },
    )

    return UploadAndAnalyzeResponse(
        file_id=file_id,
        filename=file.filename or "",
        sheet_name=profile.sheet_name,
        rows=int(profile.df.shape[0]),
        columns=int(profile.df.shape[1]),
        column_infos=[DataColumnInfo(**ci) for ci in profile.column_infos],
        suggested_charts=[ChartOption(**o) for o in options],
        analysis_summary=analysis_summary,
        assistant_reply=assistant_reply,
    )


@router.post(
    "/generate",
    response_model=GenerateChartsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_charts(
    body: GenerateChartsRequest,
):
    scope = "public"
    try:
        upload_path = storage.get_upload_path(body.file_id, scope)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        profile = load_excel_profile(str(upload_path), sheet_name=body.sheet_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析 Excel 失败: {e}")

    # 从 upload 阶段落盘的 suggested_charts 反查，确保 id 稳定
    meta = storage.read_meta(body.file_id, scope)
    all_options = meta.get("suggested_charts") if isinstance(meta, dict) else None
    if not isinstance(all_options, list) or not all_options:
        # 兜底：如果 meta 丢失，则回退到规则推荐（此时前端需要重新 upload 才能获得正确 id）
        all_options = suggest_charts(profile, max_options=50)
    opt_map = {o.get("id"): o for o in all_options if isinstance(o, dict) and o.get("id")}

    selected: list[dict] = []
    for cid in body.chart_ids:
        if cid not in opt_map:
            raise HTTPException(status_code=400, detail=f"未知 chart_id: {cid}（请重新上传并选择图表后再生成）")
        selected.append(opt_map[cid])

    if len(selected) > 12:
        raise HTTPException(status_code=400, detail="一次最多生成 12 张图（请减少选择）")

    task_id = new_id()
    out_png = storage.output_file_path(task_id, scope, "combined.png")
    out_png.parent.mkdir(parents=True, exist_ok=True)

    try:
        render_combined_figure(profile.df, selected, str(out_png), fig_title="班级成绩综合分析报告")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图表失败: {e}")

    report = {
        "task_id": task_id,
        "file_id": body.file_id,
        "sheet_name": profile.sheet_name,
        "selected_charts": selected,
        "rows_used": int(profile.df.shape[0]),
        "font_config": {
            "DATA_ANALYSIS_FONT_PATH": (getattr(__import__("app.core.config", fromlist=["settings"]).settings, "DATA_ANALYSIS_FONT_PATH", "") or ""),
            "matplotlib_font_family": __import__("matplotlib.pyplot").pyplot.rcParams.get("font.family"),
            "matplotlib_sans_serif": __import__("matplotlib.pyplot").pyplot.rcParams.get("font.sans-serif"),
        },
    }
    report_rel = storage.write_output_text(task_id, scope, "report.json", json.dumps(report, ensure_ascii=False, indent=2))

    # StaticFiles 已挂载 /media -> backend/media
    # output_dir 默认是 media/data_analysis/outputs，因此可通过 /media/data_analysis/outputs/... 访问
    combined_url = f"/media/data_analysis/outputs/{scope}/{task_id}/combined.png"
    report_url = f"/media/data_analysis/outputs/{scope}/{task_id}/report.json"

    return GenerateChartsResponse(
        task_id=task_id,
        file_id=body.file_id,
        combined_image_url=combined_url,
        report_url=report_url,
    )


@router.post(
    "/chat",
    response_model=DataAnalysisChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_only(
    message: str = Form(...),
    file: UploadFile | None = File(None),
    file_id: str = Form(""),
):
    """
    纯对话模式：
    - 首次可带 file 上传（返回 file_id 供后续复用）
    - 后续只带 file_id + message
    """
    scope = "public"
    msg = (message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message 不能为空")

    effective_file_id = (file_id or "").strip()
    filename = ""

    if file is not None:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式，仅支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="文件过大（最大 15MB）")
        effective_file_id = new_id()
        filename = file.filename or ""
        storage.save_upload(
            file_id=effective_file_id,
            filename=file.filename or f"{effective_file_id}{suffix}",
            content_bytes=content,
            scope=scope,
        )

    # 未提供文件时允许纯对话（无表格上下文）
    if not effective_file_id:
        general_system = (
            "你是数据分析对话助手。用户可能还未上传 Excel。"
            "请直接回答用户问题，必要时提醒：如需结合具体数据分析，可上传 Excel。"
            "回答简洁、清晰、友好。"
        )
        reply = await _call_llm(general_system, msg, max_tokens=1200)
        reply = (reply or "").strip() or "我可以先回答你的问题；如果你上传 Excel，我还能结合数据做更具体的分析与出图。"
        return DataAnalysisChatResponse(file_id="", assistant_reply=reply)

    try:
        upload_path = storage.get_upload_path(effective_file_id, scope)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在，请重新上传")

    try:
        profile = load_excel_profile(str(upload_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析 Excel 失败: {e}")

    # 生成一个轻量 summary 给模型
    df_summary = _summarize_dataframe(profile.df)
    reply = await chat_about_excel(
        filename=filename or upload_path.name,
        sheet_name=profile.sheet_name,
        rows=int(profile.df.shape[0]),
        cols=int(profile.df.shape[1]),
        column_infos=profile.column_infos,
        df_preview_summary=df_summary,
        user_message=msg,
    )
    if not reply:
        reply = "我已经收到你的问题，但当前大模型没有返回内容。请稍后重试，或换一种说法。"

    return DataAnalysisChatResponse(file_id=effective_file_id, assistant_reply=reply)

