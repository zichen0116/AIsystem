"""
图片解析器
使用阿里云视觉模型分析图片内容
"""
import os
import logging
from pathlib import Path
from typing import Optional

from app.services.parsers.base import BaseParser, ParseResult, ParsedChunk
from app.services.ai.vision_service import VisionService, get_vision_service

logger = logging.getLogger(__name__)


class ImageParser(BaseParser):
    """
    图片解析器

    核心功能：
    1. 接收图片文件（.jpg/.jpeg/.png）
    2. 调用阿里云 qwen-vl-plus 视觉模型分析图片
    3. 返回图片描述文本
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")

        # 初始化视觉服务
        if self.api_key:
            self.vision_service = VisionService(api_key=self.api_key)
        else:
            self.vision_service = None

    @property
    def supported_extensions(self) -> list[str]:
        return [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

    async def parse(self, file_path: Path) -> ParseResult:
        """
        解析图片文件

        Args:
            file_path: 图片文件路径

        Returns:
            ParseResult: 包含图片描述文本块
        """
        chunks = []
        images = []

        file_name = file_path.name

        # 检查文件是否存在
        if not file_path.exists():
            logger.error(f"图片文件不存在: {file_path}")
            return ParseResult(chunks=[], images=[])

        # 检查是否配置了 API Key
        if not self.vision_service:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过图片解析")
            # 返回一个基本信息块
            chunks.append(ParsedChunk(
                content=f"[图片文件] {file_name}",
                metadata={
                    "source": file_name,
                    "type": "image_upload",
                    "status": "no_api_key",
                    "image_count": 0,
                    "image_descriptions": []
                }
            ))
            return ParseResult(chunks=chunks, images=[])

        try:
            # 调用视觉模型分析图片
            logger.info(f"开始分析图片: {file_name}")

            description = await self.vision_service.describe_image(
                image_path=str(file_path)
            )

            if description and not description.startswith("错误:") and not description.startswith("API "):
                # 成功解析
                chunk = ParsedChunk(
                    content=description,
                    metadata={
                        "source": file_name,
                        "type": "image_upload",
                        "image_count": 1,
                        "image_descriptions": [
                            {
                                "filename": file_name,
                                "description": description
                            }
                        ]
                    }
                )
                chunks.append(chunk)
                images.append(str(file_path))
                logger.info(f"图片解析成功: {file_name}, 描述长度: {len(description)}")
            else:
                # 解析失败，返回基本信息
                logger.warning(f"图片解析失败: {description}")
                chunk = ParsedChunk(
                    content=f"[图片文件] {file_name} (解析失败)",
                    metadata={
                        "source": file_name,
                        "type": "image_upload",
                        "status": "parse_failed",
                        "image_count": 0,
                        "image_descriptions": [],
                        "error": description
                    }
                )
                chunks.append(chunk)

        except Exception as e:
            logger.error(f"图片解析异常: {e}")
            chunk = ParsedChunk(
                content=f"[图片文件] {file_name} (解析异常)",
                metadata={
                    "source": file_name,
                    "type": "image_upload",
                    "status": "error",
                    "image_count": 0,
                    "image_descriptions": [],
                    "error": str(e)
                }
            )
            chunks.append(chunk)

        return ParseResult(chunks=chunks, images=images)
