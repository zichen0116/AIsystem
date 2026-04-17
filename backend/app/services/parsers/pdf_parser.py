"""
PDF 解析器
同时提取文本和图片，处理图文混排
支持调用视觉模型理解图片内容
"""
from pathlib import Path
from typing import Any, Optional
import os
import uuid
import logging

from app.services.parsers.base import BaseParser, ParsedChunk, ParseResult
from app.services.ai.vision_service import VisionService

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    PDF 解析器

    核心功能：
    1. 提取每页文本
    2. 提取图片，过滤小图片
    3. 调用视觉模型生成图片描述
    4. 在文本中插入图片描述
    """

    def __init__(self, output_dir: str = "media/extracted", api_key: Optional[str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")

        # 初始化视觉服务
        if self.api_key:
            self.vision_service = VisionService(api_key=self.api_key)
        else:
            self.vision_service = None
            logger.warning("未配置 DASHSCOPE_API_KEY，图片将使用基础描述")

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    async def parse(self, file_path: Path) -> ParseResult:
        """
        解析 PDF 文件

        Args:
            file_path: PDF 文件路径

        Returns:
            ParseResult: 包含文本块列表和图片路径列表
        """
        chunks: list[ParsedChunk] = []
        images: list[str] = []

        # 打开 PDF
        try:
            import fitz  # PyMuPDF
        except ModuleNotFoundError:
            logger.warning("PyMuPDF(fitz) unavailable, falling back to PyPDF2 text parsing")
            return await self._parse_with_pypdf(file_path)

        doc = fitz.open(str(file_path))
        file_name = file_path.name

        # 遍历每一页
        for page_num in range(len(doc)):
            page = doc[page_num]

            # ========== 1. 提取文本 ==========
            text = page.get_text()
            text = text.strip()

            # ========== 2. 提取图片 ==========
            image_refs = []
            image_descriptions = []  # 存储图片描述

            # 获取页面的图片列表
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # 获取图片尺寸
                    width = base_image["width"]
                    height = base_image["height"]

                    # 过滤小图片（如图标、页眉线条）
                    if not self._should_extract_image(width, height, min_size=100):
                        logger.info(f"跳过小图片: {width}x{height}")
                        continue

                    # 保存图片
                    img_ext = base_image["ext"]
                    img_name = f"{file_name}_p{page_num + 1}_img{img_index}_{uuid.uuid4().hex[:8]}.{img_ext}"
                    img_path = self.output_dir / img_name

                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    images.append(str(img_path))

                    # ========== 3. 生成图片描述（视觉理解）==========
                    description = await self._generate_image_description(
                        str(img_path), width, height, img_ext
                    )

                    # 简单图片引用放到文本中，详细描述存到 metadata
                    image_refs.append(f"\n[IMAGE: {img_name}]\n")
                    image_descriptions.append({
                        "filename": img_name,
                        "description": description
                    })

                    logger.info(f"提取图片: {img_name} ({width}x{height})")

                except Exception as e:
                    logger.error(f"提取图片失败: {e}")
                    continue

            # ========== 4. 构建文本块 ==========
            # 合并文本和图片引用
            final_content = text
            if image_refs:
                # 将图片引用插入到文本末尾
                final_content += "\n" + "".join(image_refs)

            if final_content.strip():
                chunk = ParsedChunk(
                    content=final_content,
                    metadata={
                        "source": file_name,
                        "page": page_num + 1,
                        "type": "text",
                        "has_image": len(image_refs) > 0,
                        "image_count": len(image_refs),
                        "image_descriptions": image_descriptions
                    }
                )
                chunks.append(chunk)

        doc.close()

        logger.info(f"PDF 解析完成: {file_name}, 共 {len(chunks)} 个文本块, {len(images)} 张图片")

        return ParseResult(chunks=chunks, images=images)

    async def _parse_with_pypdf(self, file_path: Path) -> ParseResult:
        """Fallback parser when PyMuPDF is unavailable."""
        from PyPDF2 import PdfReader

        chunks: list[ParsedChunk] = []
        file_name = file_path.name

        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    continue

                chunks.append(
                    ParsedChunk(
                        content=text,
                        metadata={
                            "source": file_name,
                            "page": page_num,
                            "type": "text",
                            "has_image": False,
                            "image_count": 0,
                            "image_descriptions": [],
                        },
                    )
                )

        logger.info(
            "PDF fallback parse completed: %s, chunks=%s, images=0",
            file_name,
            len(chunks),
        )
        return ParseResult(chunks=chunks, images=[])

    async def _generate_image_description(
        self, image_path: str, width: int, height: int, img_ext: str
    ) -> str:
        """
        生成图片描述（调用视觉模型或使用基础描述）

        Args:
            image_path: 图片路径
            width: 图片宽度
            height: 图片高度
            img_ext: 图片格式

        Returns:
            str: 图片描述
        """
        # 如果配置了视觉服务，调用视觉模型
        if self.vision_service:
            try:
                prompt = (
                    "请详细分析这张教学图片。提取其中的文字、公式、图表内容，"
                    "并总结画面所传达的知识点。\n\n"
                    "【重要】如果检测到表格，请务必以标准的 Markdown 表格格式提取内容，"
                    "例如：\n"
                    "| 列1 | 列2 | 列3 |\n"
                    "| --- | --- | --- |\n"
                    "| 内容 | 内容 | 内容 |\n\n"
                    "保持数据的结构性，便于后续分析和检索。"
                )
                description = await self.vision_service.describe_image(
                    image_path=image_path,
                    prompt=prompt
                )

                # 检查是否成功
                if description and not description.startswith("错误:") and not description.startswith("API "):
                    return description
                else:
                    logger.warning(f"视觉理解失败，使用基础描述: {description}")
            except Exception as e:
                logger.warning(f"调用视觉服务失败: {e}")

        # 回退到基础描述
        return self._generate_basic_description(width, height, img_ext)

    def _generate_basic_description(self, width: int, height: int, img_ext: str) -> str:
        """
        生成基础图片描述（未配置视觉服务时使用）

        Args:
            width: 图片宽度
            height: 图片高度
            img_ext: 图片格式

        Returns:
            str: 基础描述
        """
        aspect_ratio = width / height if height > 0 else 1

        if aspect_ratio > 1.5:
            desc = f"A wide image ({width}x{height}), possibly a chart or diagram"
        elif aspect_ratio < 0.7:
            desc = f"A tall image ({width}x{height}), possibly a portrait or long image"
        else:
            desc = f"An image ({width}x{height})"

        if img_ext.lower() in ["png"]:
            desc += ", PNG format with transparency"
        elif img_ext.lower() in ["jpg", "jpeg"]:
            desc += ", JPEG format"

        return desc

    def _should_extract_image(self, width: int, height: int, min_size: int = 100) -> bool:
        """判断图片是否应该提取"""
        # 过滤太小的图片
        return width >= min_size and height >= min_size
