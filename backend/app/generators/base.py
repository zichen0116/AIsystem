"""
文件生成器抽象基类
"""
from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path


class BaseGenerator(ABC):
    """
    文件生成器抽象基类

    所有文件生成器必须继承此类并实现 generate() 方法。
    支持的文件类型：PPT, DOCX, GAME
    """

    @property
    @abstractmethod
    def file_type(self) -> str:
        """返回生成器的文件类型标识"""
        pass

    @abstractmethod
    async def generate(self, content: dict[str, Any], output_path: Path) -> Path:
        """
        生成文件

        Args:
            content: Master Lesson JSON 结构化内容
            output_path: 输出文件路径

        Returns:
            生成文件的路径
        """
        pass

    async def validate_content(self, content: dict[str, Any]) -> bool:
        """
        验证内容是否符合生成要求

        Args:
            content: Master Lesson JSON 内容

        Returns:
            是否有效
        """
        required_fields = ["title", "slides", "lesson_plan_details"]
        return all(field in content for field in required_fields)

    def prepare_output_dir(self, output_path: Path) -> None:
        """准备输出目录"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
