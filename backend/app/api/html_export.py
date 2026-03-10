from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.schemas.html_export import ExportGifRequest
from app.services.html_gif_export import export_html_to_gif, cleanup_export_dir


router = APIRouter(prefix="/export", tags=["export"])


@router.post("/gif")
async def export_gif(req: ExportGifRequest):
    """
    将 HTML 渲染并导出为 GIF。

    - **html**: 完整 HTML 源码（推荐为单文件可运行的 HTML）
    - **width/height**: 导出分辨率（默认 960x540）
    - **duration_sec**: 导出时长（默认 6 秒）
    - **fps**: 帧率（默认 12）
    """
    html = (req.html or "").strip()
    if not html:
        raise HTTPException(400, detail="html 不能为空")

    try:
        result = await export_html_to_gif(
            html=html,
            width=req.width,
            height=req.height,
            duration_sec=req.duration_sec,
            fps=req.fps,
            start_delay_ms=req.start_delay_ms,
            filename=req.filename or "demo.gif",
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    except NotImplementedError:
        raise HTTPException(
            500,
            detail=(
                "导出失败：Playwright 在当前 Windows asyncio 事件循环下无法创建子进程。"
                "请重启后端或使用 Docker 运行后端。"
            ),
        )
    except Exception as e:
        raise HTTPException(500, detail=f"导出失败：{str(e)}")

    return FileResponse(
        path=str(result.gif_path),
        media_type="image/gif",
        filename=result.gif_path.name,
        background=BackgroundTask(cleanup_export_dir, result.work_dir),
    )

