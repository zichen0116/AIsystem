"""
PPT生成模块 - 导出服务
基于 banana-slides 的 ExportService 实现
"""
import io
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_page_size_inches(aspect_ratio: str) -> tuple:
    """根据比例获取页面尺寸（英寸）"""
    sizes = {
        '16:9': (13.333, 7.5),   # 标准的 16:9
        '4:3': (10, 7.5),          # 标准的 4:3
        '1:1': (7.5, 7.5),         # 正方形
    }
    return sizes.get(aspect_ratio, (13.333, 7.5))


class PptExportService:
    """PPT导出服务"""

    @staticmethod
    def create_pptx_from_images(image_paths: list[str], output_file: str = None, aspect_ratio: str = '16:9') -> Optional[bytes]:
        """
        从图片创建 PPTX 文件

        Args:
            image_paths: 图片路径列表
            output_file: 输出文件路径（如果为 None，则返回 bytes）
            aspect_ratio: 页面比例，如 '16:9', '4:3', '1:1'

        Returns:
            如果 output_file 为 None，返回 PPTX 文件的字节数据
        """
        from pptx import Presentation
        from pptx.util import Inches

        prs = Presentation()

        # 设置幻灯片尺寸
        page_w, page_h = get_page_size_inches(aspect_ratio)
        prs.slide_width = Inches(page_w)
        prs.slide_height = Inches(page_h)

        # 添加每张图片作为一页
        for image_path in image_paths:
            import os
            if not os.path.exists(image_path):
                logger.warning(f"图片不存在: {image_path}")
                continue

            # 添加空白幻灯片
            blank_slide_layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(blank_slide_layout)

            # 添加图片填满整个幻灯片
            slide.shapes.add_picture(
                image_path,
                left=0,
                top=0,
                width=prs.slide_width,
                height=prs.slide_height
            )

        # 保存或返回字节
        if output_file:
            prs.save(output_file)
            return None
        else:
            pptx_bytes = io.BytesIO()
            prs.save(pptx_bytes)
            pptx_bytes.seek(0)
            return pptx_bytes.getvalue()

    @staticmethod
    def create_pdf_from_images(image_paths: list[str], output_file: str = None, aspect_ratio: str = '16:9') -> Optional[bytes]:
        """
        从图片创建 PDF 文件（使用 img2pdf，低内存）

        Args:
            image_paths: 图片路径列表
            output_file: 输出文件路径（如果为 None，则返回 bytes）
            aspect_ratio: 页面比例

        Returns:
            如果 output_file 为 None，返回 PDF 文件的字节数据
        """
        import os
        import img2pdf

        # 验证图片并记录警告
        valid_paths = []
        for p in image_paths:
            if os.path.exists(p):
                valid_paths.append(p)
            else:
                logger.warning(f"PDF 导出时跳过不存在的图片: {p}")

        if not valid_paths:
            raise ValueError("没有找到有效的图片用于 PDF 导出")

        try:
            page_w, page_h = get_page_size_inches(aspect_ratio)
            layout_fun = img2pdf.get_layout_fun(
                pagesize=(img2pdf.in_to_pt(page_w), img2pdf.in_to_pt(page_h)),
                fit=img2pdf.FitMode.fill,
            )

            pdf_bytes = img2pdf.convert(valid_paths, layout_fun=layout_fun)

            if output_file:
                with open(output_file, "wb") as f:
                    f.write(pdf_bytes)
                return None
            else:
                return pdf_bytes
        except Exception as e:
            logger.warning(f"img2pdf 转换失败: {e}，回退到 Pillow 方法")
            return PptExportService.create_pdf_from_images_pillow(valid_paths, output_file, aspect_ratio)

    @staticmethod
    def create_pdf_from_images_pillow(image_paths: list[str], output_file: str = None, aspect_ratio: str = '16:9') -> Optional[bytes]:
        """
        从图片创建 PDF 文件（使用 Pillow，高内存占用）

        Args:
            image_paths: 图片路径列表
            output_file: 输出文件路径
            aspect_ratio: 页面比例

        Returns:
            PDF 字节数据或 None
        """
        from PIL import Image

        page_w, page_h = get_page_size_inches(aspect_ratio)

        # 转换为像素 (72 DPI)
        width_px = int(page_w * 72)
        height_px = int(page_h * 72)

        images = []
        for path in image_paths:
            img = Image.open(path)
            img = img.convert('RGB')
            # 调整大小
            img = img.resize((width_px, height_px), Image.Resampling.LANCZOS)
            images.append(img)

        if not images:
            raise ValueError("没有有效的图片")

        # 保存到字节
        pdf_bytes = io.BytesIO()
        images[0].save(
            pdf_bytes,
            format='PDF',
            save_all=True,
            append_images=images[1:],
            resolution=72.0
        )
        pdf_bytes.seek(0)

        if output_file:
            with open(output_file, "wb") as f:
                f.write(pdf_bytes.getvalue())
            return None
        else:
            return pdf_bytes.getvalue()


# 单例
_export_service: Optional[PptExportService] = None


def get_ppt_export_service() -> PptExportService:
    """获取导出服务单例"""
    global _export_service
    if _export_service is None:
        _export_service = PptExportService()
    return _export_service
