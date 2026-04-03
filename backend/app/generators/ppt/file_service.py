"""
PPT生成模块 - OSS文件服务
阿里云OSS存储封装
"""
import os
from typing import Optional
import oss2

from app.core.config import settings


class OSSFileService:
    """OSS文件服务"""

    def __init__(self):
        self.bucket = oss2.Bucket(
            oss2.Auth(
                settings.OSS_ACCESS_KEY_ID,
                settings.OSS_ACCESS_KEY_SECRET
            ),
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET
        )
        self.bucket_name = settings.OSS_BUCKET

    def upload_file(self, local_path: str, oss_key: str) -> str:
        """
        上传本地文件到OSS

        Args:
            local_path: 本地文件路径
            oss_key: OSS存储路径

        Returns:
            公网访问URL
        """
        self.bucket.put_object_from_file(oss_key, local_path)
        return self._build_url(oss_key)

    def upload_bytes(self, data: bytes, oss_key: str) -> str:
        """
        上传字节数据到OSS

        Args:
            data: 字节数据
            oss_key: OSS存储路径

        Returns:
            访问URL（永久公网URL）
        """
        self.bucket.put_object(oss_key, data)
        return self._build_url(oss_key)

    def get_signed_url(self, oss_key: str, expires: int = 3600) -> str:
        """
        获取带签名的访问URL

        Args:
            oss_key: OSS存储路径
            expires: 签名过期时间（秒）

        Returns:
            签名URL
        """
        return self.bucket.sign_url("GET", oss_key, expires)

    def download_file(self, oss_key: str, local_path: str) -> None:
        """
        从OSS下载文件到本地

        Args:
            oss_key: OSS存储路径
            local_path: 本地保存路径
        """
        self.bucket.get_object_to_file(oss_key, local_path)

    def delete_file(self, oss_key: str) -> None:
        """
        删除OSS文件

        Args:
            oss_key: OSS存储路径
        """
        self.bucket.delete_object(oss_key)

    def file_exists(self, oss_key: str) -> bool:
        """
        检查文件是否存在

        Args:
            oss_key: OSS存储路径

        Returns:
            是否存在
        """
        return self.bucket.object_exists(oss_key)

    def _build_url(self, oss_key: str) -> str:
        """构建公网访问URL"""
        endpoint = settings.OSS_ENDPOINT
        # 去掉协议头，避免拼接出 https://bucket.https://endpoint/... 的畸形URL
        if endpoint.startswith('https://'):
            endpoint = endpoint[8:]
        elif endpoint.startswith('http://'):
            endpoint = endpoint[7:]
        return f"https://{self.bucket_name}.{endpoint}/{oss_key}"


# 单例
_oss_service: Optional[OSSFileService] = None


def get_oss_service() -> OSSFileService:
    """获取 OSSFileService 单例"""
    global _oss_service
    if _oss_service is None:
        _oss_service = OSSFileService()
    return _oss_service
