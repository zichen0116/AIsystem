from pydantic import BaseModel, Field


class ExportGifRequest(BaseModel):
    html: str = Field(..., description="完整 HTML 源码（单文件可运行）")
    width: int = Field(960, ge=200, le=1920, description="导出宽度")
    height: int = Field(540, ge=200, le=1080, description="导出高度")
    duration_sec: float = Field(6.0, gt=0, le=30, description="导出时长（秒）")
    fps: int = Field(12, ge=1, le=30, description="帧率")
    start_delay_ms: int = Field(300, ge=0, le=5000, description="开始录制前等待（毫秒）")
    filename: str | None = Field(None, description="下载文件名（可选）")

