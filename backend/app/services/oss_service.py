"""
阿里云 OSS 文件存储服务
"""
import logging
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import oss2
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# 扩展名 → FileType 枚举值映射
EXT_TO_FILE_TYPE = {
    "pdf": "pdf",
    "ppt": "ppt",
    "pptx": "ppt",
    "doc": "word",
    "docx": "word",
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "mp4": "video",
}

# 允许的 MIME 类型
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "video/mp4",
    "image/jpeg",
    "image/png",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB



def _get_bucket() -> oss2.Bucket:
    """获取 OSS Bucket 实例"""
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET)



def _url_to_key(url: str) -> str:
    """从 OSS URL 中提取 object key"""
    parsed = urlparse(url)
    return parsed.path.lstrip("/")



def get_file_type(filename: str) -> str | None:
    """从文件名获取 FileType 枚举值，不支持的返回 None"""
    ext = Path(filename).suffix.lstrip(".").lower()
    return EXT_TO_FILE_TYPE.get(ext)


async def upload_file(file: UploadFile, user_id: int, prefix: str = "knowledge") -> dict:
    """
    上传文件到 OSS

    Returns:
        {"url": "https://...", "file_name": "原始名.pdf", "file_type": "pdf"}
    """
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"不支持的文件类型: {content_type}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件大小超过限制（最大 50MB）")

    original_name = file.filename or "unnamed"
    ext = Path(original_name).suffix.lstrip(".").lower()
    file_type = EXT_TO_FILE_TYPE.get(ext)
    if not file_type:
        raise ValueError(f"不支持的文件扩展名: .{ext}")

    object_key = f"{prefix}/{user_id}/{uuid.uuid4().hex}.{ext}"

    bucket = _get_bucket()
    bucket.put_object(object_key, content)

    endpoint_host = settings.OSS_ENDPOINT.replace("https://", "").replace("http://", "")
    url = f"https://{settings.OSS_BUCKET}.{endpoint_host}/{object_key}"

    logger.info("文件上传成功: %s -> %s", original_name, url)

    return {
        "url": url,
        "file_name": original_name,
        "file_type": file_type,
    }



def delete_file(url: str) -> None:
    """删除 OSS 文件，URL 不是 OSS 链接时静默跳过"""
    if not url or settings.OSS_BUCKET not in url:
        return
    try:
        key = _url_to_key(url)
        bucket = _get_bucket()
        bucket.delete_object(key)
        logger.info("OSS 文件已删除: %s", key)
    except Exception as e:
        logger.warning("OSS 文件删除失败: %s, %s", url, e)



def download_to_temp(url: str) -> str:
    """
    从 OSS 下载文件到临时目录

    Returns:
        本地临时文件路径
    """
    key = _url_to_key(url)
    ext = Path(key).suffix
    temp_dir = Path(tempfile.gettempdir()) / "oss_downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    local_path = str(temp_dir / f"{uuid.uuid4().hex}{ext}")

    bucket = _get_bucket()
    bucket.get_object_to_file(key, local_path)
    logger.info("OSS 文件下载到: %s", local_path)

    return local_path


async def upload_bytes(
    content: bytes,
    ext: str,
    user_id: int,
    prefix: str = "rehearsal-audio",
) -> str:
    """
    上传程序生成的字节内容到 OSS（用于 TTS 音频等非用户上传场景）。
    Returns: 公开访问 URL
    """
    object_key = f"{prefix}/{user_id}/{uuid.uuid4().hex}.{ext}"
    bucket = _get_bucket()
    bucket.put_object(object_key, content)

    endpoint_host = settings.OSS_ENDPOINT.replace("https://", "").replace("http://", "")
    url = f"https://{settings.OSS_BUCKET}.{endpoint_host}/{object_key}"
    logger.info("Bytes uploaded: %s bytes -> %s", len(content), url)
    return url
