"""
生成器工厂
"""
from pathlib import Path
from typing import Any
from app.generators.base import BaseGenerator
from app.generators.ppt_generator import PPTGenerator
from app.generators.docx_generator import DOCXGenerator
from app.generators.game_generator import GameGenerator


class GeneratorFactory:
    """文件生成器工厂"""

    _generators: dict[str, BaseGenerator] = {
        "PPT": PPTGenerator(),
        "DOCX": DOCXGenerator(),
        "GAME": GameGenerator(),
    }

    @classmethod
    def get_generator(cls, file_type: str) -> BaseGenerator:
        """获取指定类型的生成器"""
        generator = cls._generators.get(file_type.upper())
        if generator is None:
            raise ValueError(f"不支持的文件类型: {file_type}")
        return generator

    @classmethod
    async def generate_file(
        cls,
        file_type: str,
        content: dict[str, Any],
        output_path: Path
    ) -> Path:
        """生成文件"""
        generator = cls.get_generator(file_type)
        return await generator.generate(content, output_path)

    @classmethod
    def register_generator(cls, file_type: str, generator: BaseGenerator) -> None:
        """注册新的生成器"""
        cls._generators[file_type.upper()] = generator
