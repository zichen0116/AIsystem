from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
import aiofiles
from app.core.config import settings
from app.services.html_extract import extract_text_from_file

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt"}


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    file_id = str(uuid.uuid4())
    ext = suffix
    upload_dir = Path(settings.HTML_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / f"{file_id}{ext}"
    try:
        # 使用 str(path) 避免 Windows 下 aiofiles 对 Path 的兼容问题
        async with aiofiles.open(str(save_path), "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
    except Exception as e:
        raise HTTPException(500, detail=f"保存文件失败: {str(e)}")

    # 提取文本用于后续生成（提取失败不影响上传成功，仅预览为空）
    extract_engine = "unknown"
    try:
        text_content = extract_text_from_file(save_path)
    except Exception as e:
        text_content = ""
    # 简单推断引擎（便于前端排查）：PDF 优先 PyMuPDF，其它按后缀
    try:
        if suffix == ".pdf":
            extract_engine = "pymupdf_then_pypdf2"
        elif suffix == ".txt":
            extract_engine = "txt"
        elif suffix in (".doc", ".docx"):
            extract_engine = "docx"
        elif suffix in (".ppt", ".pptx"):
            extract_engine = "pptx"
    except Exception:
        extract_engine = "unknown"

    return {
        "file_id": file_id,
        "filename": file.filename,
        "size": save_path.stat().st_size,
        "extracted_length": len(text_content),
        "extract_engine": extract_engine,
        "preview": text_content[:500] + "..." if len(text_content) > 500 else text_content,
    }
