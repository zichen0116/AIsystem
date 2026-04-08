"""
解析器工厂
根据文件类型选择合适的解析器
"""
from pathlib import Path
from typing import Optional
import logging

from app.services.parsers.base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class ParserFactory:
    """解析器工厂"""

    _parsers: dict[str, BaseParser] = {}

    @classmethod
    def get_parser(cls, file_path: str | Path) -> Optional[BaseParser]:
        """
        根据文件扩展名获取解析器

        Args:
            file_path: 文件路径

        Returns:
            解析器实例，或 None
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        # 缓存解析器实例
        if ext not in cls._parsers:
            parser = cls._create_parser(ext)
            if parser:
                cls._parsers[ext] = parser
            else:
                return None

        return cls._parsers.get(ext)

    @classmethod
    def _create_parser(cls, ext: str) -> Optional[BaseParser]:
        """根据扩展名创建解析器"""
        if ext == ".pdf":
            from app.services.parsers.pdf_parser import PDFParser
            return PDFParser()
        elif ext in [".docx", ".doc"]:
            from app.services.parsers.docx_parser import WordParser
            return WordParser()
        elif ext in [".mp4", ".avi", ".mov", ".mkv", ".flv"]:
            from app.services.parsers.video_parser import VideoParser
            return VideoParser()
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            from app.services.parsers.image_parser import ImageParser
            return ImageParser()
        else:
            logger.warning(f"不支持的文件类型: {ext}")
            return None

    @classmethod
    async def parse_file(cls, file_path: str | Path) -> Optional[ParseResult]:
        """
        解析文件

        Args:
            file_path: 文件路径

        Returns:
            ParseResult 或 None
        """
        parser = cls.get_parser(file_path)
        if parser is None:
            return None

        return await parser.parse(Path(file_path))
