"""
PPT翻新模块 - 核心服务
LibreOffice 转换、PDF 渲染/拆分、AI 内容提取
"""
import asyncio
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt — 复用 banana-slides prompts.py
# ---------------------------------------------------------------------------

LANGUAGE_CONFIG = {
    "zh": "Please output all content in Chinese (中文).",
    "en": "Please output all content in English.",
    "ja": "Please output all content in Japanese (日本語).",
    "auto": "",
}


def _get_language_instruction(language: str = "zh") -> str:
    return LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["zh"])


def get_page_content_extraction_prompt(markdown_text: str, language: str = "zh") -> str:
    """复用 banana-slides get_ppt_page_content_extraction_prompt"""
    prompt = f"""\
You are a helpful assistant that extracts structured PPT page content from parsed document text.

The following markdown text was extracted from a single PPT slide:

<slide_content>
{markdown_text}
</slide_content>

Your task is to extract the following structured information from this slide:

1. **title**: The main title/heading of the slide
2. **points**: A list of key bullet points or content items on the slide
3. **description**: A complete page description suitable for regenerating this slide, following this format:

页面标题：[title]

页面文字：
- [point 1]
- [point 2]
...

其他页面素材（如果有图表、表格、公式等描述，保留原文中的markdown图片完整形式）

Rules:
- Extract the title faithfully from the first heading in the markdown. Do NOT invent or rephrase it
- Points must be extracted verbatim from the slide content, in their original order
- In the description, 页面标题 and 页面文字 must be copied verbatim from the original text (punctuation may be normalized, but wording must be identical)
- The description should capture ALL content on the slide including text, data, and visual element descriptions
- If there are tables, charts, or formulas, describe them in the description under "其他页面素材"
- Preserve the original language of the content

Return a JSON object with exactly these three fields: "title", "points" (array of strings), "description" (string).
Return only the JSON, no other text.
{_get_language_instruction(language)}
"""
    return prompt


def get_layout_caption_prompt() -> str:
    """复用 banana-slides get_layout_caption_prompt"""
    return """\
You are a professional PPT layout analyst. Describe the visual layout and composition of this PPT slide image in detail.

Focus on:
1. **Overall layout**: How elements are arranged (e.g., title at top, content in two columns, image on the right)
2. **Text placement**: Where text blocks are positioned, their relative sizes, alignment
3. **Visual elements**: Position and size of images, charts, icons, decorative elements
4. **Spacing and proportions**: How space is distributed between elements

Output a concise layout description in Chinese that can be used to recreate a similar layout. Format:

排版布局：
- 整体结构：[描述]
- 标题位置：[描述]
- 内容区域：[描述]
- 视觉元素：[描述]

Only describe the layout and spatial arrangement. Do not describe colors, text content, or style.
"""


# ---------------------------------------------------------------------------
# RenovationService
# ---------------------------------------------------------------------------

class RenovationService:
    """PPT 翻新核心服务"""

    def __init__(self):
        from app.core.config import get_settings
        s = get_settings()
        self.dashscope_api_key = s.DASHSCOPE_API_KEY
        self.llm_model = s.LLM_MODEL or "qwen-plus"
        self.vision_model = s.VISION_MODEL or "qwen-vl-plus"
        self.dashscope_base_url = "https://dashscope.aliyuncs.com/api/v1"

    # ----- LibreOffice 转换 -----

    def convert_to_pdf(self, file_path: str, file_ext: str) -> str:
        """
        PPT/PPTX → PDF (LibreOffice headless)

        Args:
            file_path: 输入文件路径
            file_ext: 文件扩展名 (ppt/pptx)

        Returns:
            转换后的 PDF 文件路径

        Raises:
            FileNotFoundError: LibreOffice 未安装
            RuntimeError: 转换失败或超时
        """
        if file_ext not in ("ppt", "pptx"):
            raise ValueError(f"不支持的文件类型: {file_ext}")

        soffice = self._find_soffice()
        output_dir = os.path.dirname(file_path)

        try:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", output_dir, file_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice 转换超时（120秒），请检查文件是否过大")
        except FileNotFoundError:
            raise FileNotFoundError(
                "未找到 LibreOffice，请安装 LibreOffice 并确保 soffice 在 PATH 中。"
                "注意：服务端字体可能与本地不同，可能影响排版效果。"
            )

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice 转换失败: {result.stderr or result.stdout}")

        # 找到输出文件
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        if not os.path.exists(pdf_path):
            raise RuntimeError(f"LibreOffice 转换后未找到 PDF 文件: {pdf_path}")

        return pdf_path

    def _find_soffice(self) -> str:
        """查找 soffice 可执行文件路径"""
        if shutil.which("soffice"):
            return "soffice"

        if platform.system() == "Windows":
            candidates = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c

        raise FileNotFoundError(
            "未找到 LibreOffice，请安装 LibreOffice 并确保 soffice 在 PATH 中。"
        )

    # ----- PDF 渲染 -----

    def render_pdf_to_images(self, pdf_path: str, output_dir: str) -> list[str | None]:
        """
        PDF → 逐页 PNG (PyMuPDF, 2x 缩放)

        Returns:
            图片路径列表，渲染失败的页面为 None
        """
        import fitz

        doc = fitz.open(pdf_path)
        results: list[str | None] = []

        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
                pix.save(img_path)
                results.append(img_path)
            except Exception as e:
                logger.warning("PDF 页面 %d 渲染失败: %s", page_num + 1, e)
                results.append(None)

        doc.close()
        return results

    def get_pdf_aspect_ratio(self, pdf_path: str) -> str:
        """从 PDF 首页提取宽高比，归一化为标准比例"""
        import fitz

        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return "16:9"

        page = doc[0]
        rect = page.rect
        w, h = rect.width, rect.height
        doc.close()

        ratio = w / h if h > 0 else 1.78
        if ratio > 1.6:
            return "16:9"
        elif ratio > 1.2:
            return "4:3"
        elif ratio > 0.9:
            return "1:1"
        elif ratio > 0.7:
            return "3:4"
        else:
            return "9:16"

    # ----- PDF 拆分 / 解析 — 委托 ppt_parse_service -----

    async def split_pdf_to_pages(self, pdf_path: str, output_dir: str) -> list[str]:
        """PDF → 逐页 PDF，委托 ppt_parse_service"""
        from app.generators.ppt.ppt_parse_service import get_ppt_parse_service
        svc = get_ppt_parse_service()
        return await svc.split_pdf_to_pages(pdf_path, output_dir)

    async def parse_page_markdown(self, page_pdf_path: str, filename: str) -> tuple[str | None, str | None]:
        """
        单页 PDF → markdown，委托 ppt_parse_service.parse_file()

        ppt_parse_service 已经内置 MinerU 优先 + fitz fallback 逻辑。
        Returns: (markdown_content, error_message)
        """
        from app.generators.ppt.ppt_parse_service import get_ppt_parse_service
        svc = get_ppt_parse_service()
        return await svc.parse_file(page_pdf_path, filename)

    # ----- AI 内容提取 -----

    async def extract_page_content(self, markdown_text: str, language: str = "zh") -> dict:
        """
        markdown → {title, points, description}
        使用 DashScope qwen 模型
        """
        prompt = get_page_content_extraction_prompt(markdown_text, language)
        response_text = await self._call_dashscope_text(prompt)

        try:
            result = self._parse_json_from_text(response_text)
            result.setdefault("title", "")
            result.setdefault("points", [])
            result.setdefault("description", "")
            return result
        except Exception as e:
            logger.error("AI 提取结果解析失败: %s, 原始响应: %s", e, response_text[:200])
            raise RuntimeError(f"AI 内容提取结果解析失败: {e}")

    async def generate_layout_caption(self, image_path: str) -> str:
        """
        页面图片 → 布局描述
        使用 DashScope qwen-vl 视觉模型
        """
        prompt = get_layout_caption_prompt()
        return await self._call_dashscope_vision(image_path, prompt)

    # ----- 单页完整流水线 -----

    async def process_single_page(
        self,
        page_pdf_path: str,
        page_image_url: str | None,
        keep_layout: bool,
        language: str,
    ) -> dict:
        """
        单页完整处理：parse → extract → 可选 caption

        Returns: {title, points, description}
        Raises: RuntimeError on failure
        """
        filename = os.path.basename(page_pdf_path)
        md_text, err = await self.parse_page_markdown(page_pdf_path, filename)
        if not md_text:
            raise RuntimeError(f"markdown 解析失败: {err}")

        content = await self.extract_page_content(md_text, language)

        if keep_layout and page_image_url:
            try:
                # 下载图片到临时文件后调用视觉模型
                img_path = await self._download_to_temp(page_image_url)
                if img_path:
                    caption = await self.generate_layout_caption(img_path)
                    if caption:
                        content["description"] += f"\n\n{caption}"
                    try:
                        os.unlink(img_path)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("layout caption 生成失败，跳过: %s", e)

        return content

    # ----- DashScope 调用 -----

    async def _call_dashscope_text(self, prompt: str) -> str:
        """调用 DashScope 文本生成"""
        url = f"{self.dashscope_base_url}/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.llm_model,
            "input": {
                "messages": [{"role": "user", "content": prompt}]
            },
            "parameters": {
                "temperature": 0.1,
                "max_tokens": 2000,
                "result_format": "message",
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            result = resp.json()

            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["message"]["content"]
            raise RuntimeError(f"DashScope 响应格式异常: {result}")

    async def _call_dashscope_vision(self, image_path: str, prompt: str) -> str:
        """调用 DashScope 视觉模型"""
        import base64

        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        url = f"{self.dashscope_base_url}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.vision_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": f"data:image/png;base64,{b64}"},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {"max_tokens": 1000, "result_format": "message"},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            result = resp.json()

            if "output" in result and "choices" in result["output"]:
                content = result["output"]["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    for item in content:
                        if item.get("text"):
                            return item["text"]
                return str(content)
            return ""

    # ----- 工具方法 -----

    def _parse_json_from_text(self, text: str) -> dict:
        """从可能包含 markdown 代码块的文本中提取 JSON"""
        text = text.strip()
        # 去除 markdown 代码块
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        return json.loads(text)

    async def _download_to_temp(self, url: str) -> str | None:
        """下载 URL 到临时文件"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30)
                if resp.status_code == 200:
                    suffix = ".png"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                        f.write(resp.content)
                        return f.name
        except Exception as e:
            logger.warning("下载文件失败 %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------
_renovation_service: RenovationService | None = None


def get_renovation_service() -> RenovationService:
    global _renovation_service
    if _renovation_service is None:
        _renovation_service = RenovationService()
    return _renovation_service
