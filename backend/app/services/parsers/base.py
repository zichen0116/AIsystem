"""
文件解析器基类
支持 PDF、Word、Video 等多模态文件解析
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ParsedChunk:
    """解析后的文本块"""
    content: str  # 包含图片描述标记的文本
    metadata: dict[str, Any]  # 元数据：source, page, has_image, timestamp 等


@dataclass
class ParseResult:
    """解析结果"""
    chunks: list[ParsedChunk]
    images: list[str]  # 提取的图片路径列表


class BaseParser(ABC):
    """
    解析器抽象基类
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """支持的扩展名"""
        pass

    @abstractmethod
    async def parse(self, file_path: Path) -> ParseResult:
        """
        解析文件

        Args:
            file_path: 文件路径

        Returns:
            ParseResult: 包含文本块和图片路径
        """
        pass

    def _should_extract_image(self, width: int, height: int, min_size: int = 100) -> bool:
        """判断图片是否应该提取（过滤小图片）"""
        return width >= min_size and height >= min_size
