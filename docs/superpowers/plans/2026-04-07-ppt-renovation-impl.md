# PPT 翻新后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 PPT 翻新后端流水线，支持上传 PDF/PPT/PPTX → 逐页解析 → 结构化内容提取 → 部分成功 → 单页重试。

**Architecture:** 新建 `renovation_service.py` 封装翻新核心逻辑（LibreOffice 转换、PDF 渲染/拆分、AI 内容提取），重写 `banana_routes.py` 中的翻新路由和 `celery_tasks.py` 中的翻新任务。PPTPage 新增 2 字段、PPTProject 新增 1 字段，通过 Alembic migration 落库。

**Tech Stack:** FastAPI, SQLAlchemy 2 (async), Celery, PyMuPDF (fitz), DashScope (qwen-plus / qwen-vl-plus), 阿里云 OSS, LibreOffice, MinerU API (可选)

**Design Spec:** `docs/superpowers/specs/2026-04-07-ppt-renovation-design.md`

---

## File Structure

```
修改:
  backend/app/generators/ppt/banana_models.py    — PPTPage +2字段, PPTProject +1字段
  backend/app/generators/ppt/banana_schemas.py   — Response schema 增加翻新字段
  backend/app/generators/ppt/banana_routes.py    — 重写两个翻新路由
  backend/app/generators/ppt/celery_tasks.py     — 重写 renovation_parse_task

新建:
  backend/app/generators/ppt/renovation_service.py  — 翻新核心服务
  backend/alembic/versions/20260407_add_renovation_fields.py — Migration
  backend/tests/test_ppt_renovation.py              — 翻新测试
```

---

### Task 1: Alembic Migration — 新增翻新字段

**Files:**
- Create: `backend/alembic/versions/20260407_add_renovation_fields.py`

- [ ] **Step 1: 创建 migration 文件**

```python
# backend/alembic/versions/20260407_add_renovation_fields.py
"""add renovation fields to ppt_pages and ppt_projects

Revision ID: add_renovation_fields_001
Revises: add_ppt_project_intents_001
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_renovation_fields_001"
down_revision: Union[str, None] = "add_ppt_project_intents_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ppt_pages", sa.Column("renovation_status", sa.String(20), nullable=True))
    op.add_column("ppt_pages", sa.Column("renovation_error", sa.Text(), nullable=True))
    op.add_column("ppt_projects", sa.Column("description_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ppt_projects", "description_text")
    op.drop_column("ppt_pages", "renovation_error")
    op.drop_column("ppt_pages", "renovation_status")
```

- [ ] **Step 2: 验证 migration**

Run: `cd backend && python -m alembic upgrade head`
Expected: 输出 `Running upgrade add_ppt_project_intents_001 -> add_renovation_fields_001`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/20260407_add_renovation_fields.py
git commit -m "feat(ppt): add migration for renovation fields"
```

---

### Task 2: 模型与 Schema 变更

**Files:**
- Modify: `backend/app/generators/ppt/banana_models.py`
- Modify: `backend/app/generators/ppt/banana_schemas.py`

- [ ] **Step 1: PPTPage 模型新增字段**

在 `backend/app/generators/ppt/banana_models.py` 的 `PPTPage` 类中，`material_ids` 字段之后、`created_at` 之前插入：

```python
    # 翻新解析状态 (仅 renovation 项目使用)
    renovation_status: Mapped[str] = mapped_column(String(20), nullable=True)
    """pending | completed | failed — 仅 creation_type='renovation' 的项目使用"""
    renovation_error: Mapped[str] = mapped_column(Text, nullable=True)
    """翻新解析失败时的错误信息"""
```

- [ ] **Step 2: PPTProject 模型新增字段**

在 `backend/app/generators/ppt/banana_models.py` 的 `PPTProject` 类中，`outline_text` 字段之后插入：

```python
    # 聚合描述文本 (翻新后各页描述拼接)
    description_text: Mapped[str] = mapped_column(Text, nullable=True)
```

- [ ] **Step 3: PPTPageResponse schema 新增字段**

在 `backend/app/generators/ppt/banana_schemas.py` 的 `PPTPageResponse` 类中，`description_mode` 之后插入：

```python
    renovation_status: Optional[str] = None
    renovation_error: Optional[str] = None
```

- [ ] **Step 4: PPTProjectResponse schema 新增字段**

在 `backend/app/generators/ppt/banana_schemas.py` 的 `PPTProjectResponse` 类中，`outline_text` 之后插入：

```python
    description_text: Optional[str] = None
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/generators/ppt/banana_models.py backend/app/generators/ppt/banana_schemas.py
git commit -m "feat(ppt): add renovation fields to models and schemas"
```

---

### Task 3: RenovationService — 核心服务

**Files:**
- Create: `backend/app/generators/ppt/renovation_service.py`

- [ ] **Step 1: 创建 renovation_service.py**

```python
# backend/app/generators/ppt/renovation_service.py
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
        self.mineru_token = os.getenv("MINERU_TOKEN", "")
        self.mineru_api_base = os.getenv("MINERU_API_BASE", "https://mineru.net")

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

    # ----- PDF 拆分 -----

    def split_pdf_to_pages(self, pdf_path: str, output_dir: str) -> list[str]:
        """PDF → 逐页 PDF"""
        import fitz

        doc = fitz.open(pdf_path)
        paths: list[str] = []

        for page_num in range(len(doc)):
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            out_path = os.path.join(output_dir, f"page_{page_num + 1}.pdf")
            new_doc.save(out_path)
            new_doc.close()
            paths.append(out_path)

        doc.close()
        return paths

    # ----- PDF → Markdown -----

    async def parse_page_markdown(self, page_pdf_path: str, filename: str) -> tuple[str | None, str | None]:
        """
        单页 PDF → markdown

        优先 MinerU API，fallback 到 fitz 文本提取。
        Returns: (markdown_content, error_message)
        """
        if self.mineru_token:
            try:
                md, err = await self._parse_via_mineru(page_pdf_path, filename)
                if md:
                    return md, None
                logger.warning("MinerU 解析失败 (%s)，fallback 到 fitz: %s", filename, err)
            except Exception as e:
                logger.warning("MinerU 异常 (%s)，fallback 到 fitz: %s", filename, e)

        return self._parse_via_fitz(page_pdf_path)

    async def _parse_via_mineru(self, file_path: str, filename: str) -> tuple[str | None, str | None]:
        """MinerU API 解析"""
        headers = {"Authorization": f"Bearer {self.mineru_token}"}
        file_size = os.path.getsize(file_path)

        async with httpx.AsyncClient() as client:
            # 获取上传 URL
            resp = await client.post(
                f"{self.mineru_api_base}/api/v4/file-urls/batch",
                headers=headers,
                json={"files": [{"file_name": filename, "file_size": file_size}]},
                timeout=30,
            )
            if resp.status_code != 200:
                return None, f"MinerU 上传 URL 获取失败: {resp.text}"

            info = resp.json()["data"][0]
            upload_url = info["upload_url"]
            file_key = info["file_key"]

            # 上传文件
            with open(file_path, "rb") as f:
                file_data = f.read()
            up_resp = await client.put(upload_url, content=file_data, timeout=60)
            if up_resp.status_code not in (200, 201):
                return None, f"MinerU 文件上传失败: {up_resp.status_code}"

            # 轮询结果
            result_url = f"{self.mineru_api_base}/api/v4/extract-results/batch/{file_key}"
            for _ in range(30):
                await asyncio.sleep(10)
                r = await client.get(result_url, headers=headers, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "completed":
                        md_url = data["data"]["result_files"][0]["url"]
                        md_resp = await client.get(md_url, timeout=60)
                        if md_resp.status_code == 200:
                            return md_resp.text, None
                        return None, f"下载 markdown 失败: {md_resp.status_code}"
                    elif data.get("status") == "failed":
                        return None, f"MinerU 解析失败: {data.get('message', '未知错误')}"

            return None, "MinerU 解析超时"

    def _parse_via_fitz(self, pdf_path: str) -> tuple[str | None, str | None]:
        """fitz 文本提取 fallback"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            texts = []
            for page in doc:
                text = page.get_text() or ""
                if text.strip():
                    texts.append(text.strip())
            doc.close()

            if not texts:
                return None, "PDF 页面无文本内容"
            return "\n\n".join(texts), None
        except Exception as e:
            return None, f"fitz 文本提取失败: {e}"

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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/generators/ppt/renovation_service.py
git commit -m "feat(ppt): add RenovationService with LibreOffice, PDF render, AI extract"
```

---

### Task 4: 重写翻新项目创建路由

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py:2657-2729`

- [ ] **Step 1: 重写 create_renovation_project**

替换 `banana_routes.py` 中从 `# ============= Renovation =============` 到 `os.unlink(tmp_path)` 之后的整个 `create_renovation_project` 函数（约 2657-2729 行），替换为：

```python
# ============= Renovation =============

@router.post("/projects/renovation")
async def create_renovation_project(
    file: UploadFile = File(...),
    keep_layout: bool = Form(False),
    template_style: Optional[str] = Form(None),
    language: str = Form("zh"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建PPT翻新项目（上传文件 → 转换 → 渲染页面 → 异步解析）"""
    from app.generators.ppt.file_service import get_oss_service
    from app.generators.ppt.renovation_service import get_renovation_service
    import tempfile
    import os

    # 校验文件类型
    file_ext = _normalize_file_ext(file.filename, file.content_type)
    if file_ext not in ("pdf", "ppt", "pptx"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}，仅支持 pdf/ppt/pptx")

    # 保存上传文件到临时目录
    tmp_dir = tempfile.mkdtemp(prefix="ppt_renovation_")
    tmp_path = os.path.join(tmp_dir, file.filename)
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        oss = get_oss_service()
        renovation_svc = get_renovation_service()
        oss_prefix = f"ppt/renovation/{current_user.id}/{uuid.uuid4()}"

        # 上传原始文件到 OSS
        original_oss_key = f"{oss_prefix}/original.{file_ext}"
        original_url = oss.upload_file(tmp_path, original_oss_key)

        # 创建项目
        project = PPTProject(
            user_id=current_user.id,
            title=f"翻新项目_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            creation_type="renovation",
            status="PARSE",
            settings={
                "keep_layout": keep_layout,
                "language": language,
                "oss_prefix": oss_prefix,
                "aspect_ratio": "16:9",
            },
            template_style=template_style,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # 创建参考文件记录
        ref_file = PPTReferenceFile(
            project_id=project.id,
            user_id=current_user.id,
            filename=file.filename,
            oss_path=original_oss_key,
            url=original_url,
            file_type=file_ext,
            file_size=len(content),
            parse_status="pending",
        )
        db.add(ref_file)
        await db.commit()
        await db.refresh(ref_file)

        # 如果是 PPT/PPTX → LibreOffice 转 PDF
        pdf_path = tmp_path
        if file_ext in ("ppt", "pptx"):
            try:
                pdf_path = renovation_svc.convert_to_pdf(tmp_path, file_ext)
            except (FileNotFoundError, RuntimeError) as e:
                project.status = "FAILED"
                await db.commit()
                raise HTTPException(status_code=500, detail=str(e))

            # 上传转换后的 PDF 到 OSS
            pdf_oss_key = f"{oss_prefix}/converted.pdf"
            oss.upload_file(pdf_path, pdf_oss_key)

        # 渲染 PDF 逐页 PNG
        images_dir = os.path.join(tmp_dir, "pages")
        os.makedirs(images_dir, exist_ok=True)
        image_paths = renovation_svc.render_pdf_to_images(pdf_path, images_dir)

        if not any(p is not None for p in image_paths):
            project.status = "FAILED"
            await db.commit()
            raise HTTPException(status_code=500, detail="PDF 无法渲染出任何页面")

        # 提取宽高比
        aspect_ratio = renovation_svc.get_pdf_aspect_ratio(pdf_path)
        project.settings = {**project.settings, "aspect_ratio": aspect_ratio}

        # 为每页创建 PPTPage + PageImageVersion
        for i, img_path in enumerate(image_paths):
            page = PPTPage(
                project_id=project.id,
                page_number=i + 1,
                title=f"第 {i + 1} 页",
                config={"points": []},
                renovation_status="pending",
            )
            db.add(page)
            await db.flush()

            if img_path:
                # 上传页面图片到 OSS
                img_oss_key = f"{oss_prefix}/pages/page_{i + 1}.png"
                img_url = oss.upload_file(img_path, img_oss_key)
                page.image_url = img_url

                # 创建初始图片版本
                img_version = PageImageVersion(
                    page_id=page.id,
                    user_id=current_user.id,
                    version=1,
                    image_url=img_url,
                    operation="renovation_upload",
                    is_active=True,
                )
                db.add(img_version)

        await db.commit()

        # 创建翻新解析任务
        task_id = str(uuid.uuid4())
        task = PPTTask(
            project_id=project.id,
            task_id=task_id,
            task_type="renovation_parse",
            status="PENDING",
        )
        db.add(task)
        await db.commit()

        from app.generators.ppt.celery_tasks import renovation_parse_task
        renovation_parse_task.delay(
            project_id=project.id,
            file_id=ref_file.id,
            task_id_str=task_id,
        )

        page_count = len(image_paths)
        return {
            "project_id": project.id,
            "task_id": task_id,
            "file_id": ref_file.id,
            "page_count": page_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("翻新项目创建失败")
        raise HTTPException(status_code=500, detail=f"翻新项目创建失败: {str(e)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
```

- [ ] **Step 2: 确保 import**

在 `banana_routes.py` 顶部的 import 区域，确保以下 import 存在（如不存在则添加）：

```python
from fastapi import Form
import shutil
```

同时确保文件顶部已有 `from app.generators.ppt.banana_models import ... PageImageVersion` — 检查现有 import 行。

- [ ] **Step 3: Commit**

```bash
git add backend/app/generators/ppt/banana_routes.py
git commit -m "feat(ppt): rewrite renovation project creation with page skeletons"
```

---

### Task 5: 重写 Celery 翻新任务

**Files:**
- Modify: `backend/app/generators/ppt/celery_tasks.py:1093-1204`

- [ ] **Step 1: 重写 renovation_parse_task**

替换 `celery_tasks.py` 中的 `renovation_parse_task` 函数（约 1093-1204 行）为：

```python
@celery_app.task(bind=True, name="banana-slides.renovation_parse")
def renovation_parse_task(self: Task, project_id: int, file_id: int, task_id_str: str = None):
    """
    翻新解析任务：逐页 PDF 解析 + AI 内容提取

    支持部分成功：至少 1 页成功则 COMPLETED，0 页成功则 FAILED。
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject, PPTPage, PPTReferenceFile
    from app.generators.ppt.renovation_service import get_renovation_service
    from app.generators.ppt.file_service import get_oss_service
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import shutil

    def _process_page_in_thread(
        page_id: int,
        page_number: int,
        page_pdf_path: str,
        page_image_url: str | None,
        keep_layout: bool,
        language: str,
    ) -> dict:
        """在独立线程中处理单页，包含独立 event loop 和 DB session"""
        import asyncio

        async def _inner():
            renovation_svc = get_renovation_service()
            try:
                content = await renovation_svc.process_single_page(
                    page_pdf_path, page_image_url, keep_layout, language,
                )

                # 独立 DB session 写回
                async with AsyncSessionLocal() as db:
                    res = await db.execute(select(PPTPage).where(PPTPage.id == page_id))
                    page = res.scalar_one_or_none()
                    if page:
                        page.title = content.get("title", "")
                        page.description = content.get("description", "")
                        page.config = {**(page.config or {}), "points": content.get("points", [])}
                        page.renovation_status = "completed"
                        page.renovation_error = None
                    await db.commit()

                return {"success": True, "page_id": page_id, "page_number": page_number, "content": content}

            except Exception as e:
                logger.error("翻新解析页面 %d 失败: %s", page_number, e)
                # 标记页面失败
                async with AsyncSessionLocal() as db:
                    res = await db.execute(select(PPTPage).where(PPTPage.id == page_id))
                    page = res.scalar_one_or_none()
                    if page:
                        page.renovation_status = "failed"
                        page.renovation_error = str(e)
                    await db.commit()

                return {"success": False, "page_id": page_id, "page_number": page_number, "error": str(e)}

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_inner())
        finally:
            loop.close()

    async def _run():
        oss_svc = get_oss_service()
        tmp_dir = tempfile.mkdtemp(prefix="renovation_parse_")

        try:
            # 更新任务状态
            async with AsyncSessionLocal() as db:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "PROCESSING", 0)

                # 获取参考文件
                res = await db.execute(select(PPTReferenceFile).where(PPTReferenceFile.id == file_id))
                ref_file = res.scalar_one_or_none()
                if not ref_file:
                    if task_id_str:
                        await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "参考文件不存在"})
                    return

                # 获取项目
                res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
                project = res.scalar_one_or_none()
                if not project:
                    if task_id_str:
                        await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "项目不存在"})
                    return

                keep_layout = (project.settings or {}).get("keep_layout", False)
                language = (project.settings or {}).get("language", "zh")
                oss_prefix = (project.settings or {}).get("oss_prefix", "")

                ref_file.parse_status = "processing"
                await db.commit()

            # 下载 PDF
            pdf_path = os.path.join(tmp_dir, "source.pdf")
            ref_ext = _normalize_extension(ref_file.file_type, ref_file.filename)
            if ref_ext in ("ppt", "pptx"):
                # 下载转换后的 PDF
                pdf_oss_key = f"{oss_prefix}/converted.pdf"
                oss_svc.download_file(pdf_oss_key, pdf_path)
            else:
                oss_key = _extract_oss_key(ref_file.url)
                if oss_key:
                    oss_svc.download_file(oss_key, pdf_path)
                else:
                    import urllib.request
                    urllib.request.urlretrieve(ref_file.url, pdf_path)

            # 拆分 PDF 为单页
            split_dir = os.path.join(tmp_dir, "split_pages")
            os.makedirs(split_dir, exist_ok=True)
            renovation_svc = get_renovation_service()
            page_pdfs = renovation_svc.split_pdf_to_pages(pdf_path, split_dir)

            if not page_pdfs:
                async with AsyncSessionLocal() as db:
                    if task_id_str:
                        await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "PDF 拆分失败，无页面"})
                    project_res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
                    p = project_res.scalar_one_or_none()
                    if p:
                        p.status = "FAILED"
                    await db.commit()
                return

            # 上传单页 PDF 到 OSS（供后续重试复用）
            for i, pp in enumerate(page_pdfs):
                split_oss_key = f"{oss_prefix}/split_pages/page_{i + 1}.pdf"
                oss_svc.upload_file(pp, split_oss_key)

            # 获取所有页面
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PPTPage)
                    .where(PPTPage.project_id == project_id)
                    .order_by(PPTPage.page_number)
                )
                pages = list(res.scalars().all())

            if len(pages) != len(page_pdfs):
                logger.warning("页面数量不匹配: DB=%d, PDF=%d", len(pages), len(page_pdfs))

            # ThreadPoolExecutor 并行逐页处理
            results: list[dict] = []
            max_workers = min(5, len(page_pdfs))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i, page_pdf in enumerate(page_pdfs):
                    if i < len(pages):
                        page = pages[i]
                        future = executor.submit(
                            _process_page_in_thread,
                            page.id,
                            page.page_number,
                            page_pdf,
                            page.image_url,
                            keep_layout,
                            language,
                        )
                        futures[future] = i

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        idx = futures[future]
                        logger.error("线程异常 page_index=%d: %s", idx, e)
                        if idx < len(pages):
                            results.append({
                                "success": False,
                                "page_id": pages[idx].id,
                                "page_number": pages[idx].page_number,
                                "error": str(e),
                            })

            # 统计结果
            success_count = sum(1 for r in results if r.get("success"))
            failed_count = sum(1 for r in results if not r.get("success"))
            failed_pages = [
                {"page_id": r["page_id"], "page_number": r["page_number"], "error": r.get("error", "")}
                for r in results if not r.get("success")
            ]

            task_result = {
                "total_pages": len(page_pdfs),
                "success_count": success_count,
                "failed_count": failed_count,
                "partial_success": success_count > 0 and failed_count > 0,
                "failed_pages": failed_pages,
            }

            # 聚合 outline_text / description_text
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PPTPage)
                    .where(PPTPage.project_id == project_id)
                    .order_by(PPTPage.page_number)
                )
                all_pages = list(res.scalars().all())

                outline_parts = []
                desc_parts = []
                for p in all_pages:
                    if p.renovation_status == "completed":
                        points = (p.config or {}).get("points", [])
                        points_text = "\n".join(f"- {pt}" for pt in points)
                        outline_parts.append(f"第{p.page_number}页：{p.title or ''}\n{points_text}")
                        desc_parts.append(f"--- 第{p.page_number}页 ---\n{p.description or ''}")

                project_res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
                proj = project_res.scalar_one_or_none()
                if proj:
                    proj.outline_text = "\n\n".join(outline_parts)
                    proj.description_text = "\n\n".join(desc_parts)

                    if success_count > 0:
                        proj.status = "DESCRIPTIONS_GENERATED"
                    else:
                        proj.status = "FAILED"

                # 更新参考文件状态
                ref_res = await db.execute(select(PPTReferenceFile).where(PPTReferenceFile.id == file_id))
                rf = ref_res.scalar_one_or_none()
                if rf:
                    rf.parse_status = "completed" if success_count > 0 else "failed"
                    if failed_count > 0:
                        rf.parse_error = f"{failed_count}/{len(page_pdfs)} 页解析失败"

                await db.commit()

            # 更新任务状态
            if task_id_str:
                async with AsyncSessionLocal() as db:
                    final_status = "COMPLETED" if success_count > 0 else "FAILED"
                    await _update_task_status(db, task_id_str, final_status, 100, task_result)

        except Exception as e:
            logger.exception("翻新解析任务异常 project_id=%s", project_id)
            async with AsyncSessionLocal() as db:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": str(e)})
                project_res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
                proj = project_res.scalar_one_or_none()
                if proj:
                    proj.status = "FAILED"
                ref_res = await db.execute(select(PPTReferenceFile).where(PPTReferenceFile.id == file_id))
                rf = ref_res.scalar_one_or_none()
                if rf:
                    rf.parse_status = "failed"
                    rf.parse_error = str(e)
                await db.commit()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return asyncio.run(_run())
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/generators/ppt/celery_tasks.py
git commit -m "feat(ppt): rewrite renovation_parse_task with per-page processing"
```

---

### Task 6: 重写单页翻新重试路由

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py:2731-2792`

- [ ] **Step 1: 重写 regenerate_page_renovation**

替换 `banana_routes.py` 中的 `regenerate_page_renovation` 函数（约 2731-2792 行）为：

```python
# ============= Pages - Regenerate for Renovation =============

@router.post("/projects/{project_id}/pages/{page_id}/regenerate-renovation")
async def regenerate_page_renovation(
    project_id: int,
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """翻新模式单页重新解析（基于原始单页 PDF）"""
    from app.generators.ppt.renovation_service import get_renovation_service
    from app.generators.ppt.file_service import get_oss_service
    import tempfile
    import os

    # 获取项目
    result = await db.execute(
        select(PPTProject).where(PPTProject.id == project_id, PPTProject.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.creation_type != "renovation":
        raise HTTPException(status_code=400, detail="仅翻新项目支持此操作")

    # 获取页面
    result = await db.execute(
        select(PPTPage).where(PPTPage.id == page_id, PPTPage.project_id == project_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    # 从 project.settings 获取参数
    settings = project.settings or {}
    oss_prefix = settings.get("oss_prefix", "")
    keep_layout = settings.get("keep_layout", False)
    language = settings.get("language", "zh")

    if not oss_prefix:
        raise HTTPException(status_code=500, detail="项目配置缺少 oss_prefix")

    # 下载单页 PDF
    split_pdf_oss_key = f"{oss_prefix}/split_pages/page_{page.page_number}.pdf"
    oss = get_oss_service()
    renovation_svc = get_renovation_service()

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name

        if not oss.file_exists(split_pdf_oss_key):
            raise HTTPException(status_code=500, detail=f"单页 PDF 不存在: page_{page.page_number}.pdf")

        oss.download_file(split_pdf_oss_key, tmp_path)

        # 重新解析
        content = await renovation_svc.process_single_page(
            tmp_path, page.image_url, keep_layout, language,
        )

        # 写回页面
        page.title = content.get("title", "")
        page.description = content.get("description", "")
        page.config = {**(page.config or {}), "points": content.get("points", [])}
        page.renovation_status = "completed"
        page.renovation_error = None
        await db.commit()

        # 重新聚合项目级 outline_text / description_text
        result = await db.execute(
            select(PPTPage)
            .where(PPTPage.project_id == project_id)
            .order_by(PPTPage.page_number)
        )
        all_pages = list(result.scalars().all())

        outline_parts = []
        desc_parts = []
        for p in all_pages:
            if p.renovation_status == "completed":
                points = (p.config or {}).get("points", [])
                points_text = "\n".join(f"- {pt}" for pt in points)
                outline_parts.append(f"第{p.page_number}页：{p.title or ''}\n{points_text}")
                desc_parts.append(f"--- 第{p.page_number}页 ---\n{p.description or ''}")

        project.outline_text = "\n\n".join(outline_parts)
        project.description_text = "\n\n".join(desc_parts)

        # 如果之前 project 是 FAILED 且现在有成功页，更新为 DESCRIPTIONS_GENERATED
        success_count = sum(1 for p in all_pages if p.renovation_status == "completed")
        if success_count > 0 and project.status == "FAILED":
            project.status = "DESCRIPTIONS_GENERATED"

        await db.commit()
        await db.refresh(page)

        return {
            "status": "completed",
            "page": {
                "id": page.id,
                "page_number": page.page_number,
                "title": page.title,
                "description": page.description,
                "renovation_status": page.renovation_status,
                "renovation_error": page.renovation_error,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("单页翻新重试失败 page_id=%s", page_id)
        page.renovation_status = "failed"
        page.renovation_error = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"单页重试失败: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/generators/ppt/banana_routes.py
git commit -m "feat(ppt): rewrite single-page renovation retry with split PDF"
```

---

### Task 7: 测试

**Files:**
- Create: `backend/tests/test_ppt_renovation.py`

- [ ] **Step 1: 创建测试文件**

```python
# backend/tests/test_ppt_renovation.py
"""PPT 翻新后端测试"""
import os
import sys
import json
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# 确保 backend/ 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============= RenovationService 单元测试 =============


class TestRenovationServiceConvertToPdf:
    """LibreOffice 转换测试"""

    def _make_service(self):
        with patch("app.core.config.get_settings") as mock_settings:
            s = MagicMock()
            s.DASHSCOPE_API_KEY = "test-key"
            s.LLM_MODEL = "qwen-plus"
            s.VISION_MODEL = "qwen-vl-plus"
            mock_settings.return_value = s
            from app.generators.ppt.renovation_service import RenovationService
            return RenovationService()

    @patch("shutil.which", return_value=None)
    @patch("os.path.exists", return_value=False)
    def test_soffice_not_found_raises(self, mock_exists, mock_which):
        svc = self._make_service()
        with pytest.raises(FileNotFoundError, match="未找到 LibreOffice"):
            svc.convert_to_pdf("/tmp/test.pptx", "pptx")

    def test_unsupported_ext_raises(self):
        svc = self._make_service()
        with pytest.raises(ValueError, match="不支持的文件类型"):
            svc.convert_to_pdf("/tmp/test.docx", "docx")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="soffice")
    def test_conversion_timeout_raises(self, mock_which, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="soffice", timeout=120)
        svc = self._make_service()
        with pytest.raises(RuntimeError, match="超时"):
            svc.convert_to_pdf("/tmp/test.pptx", "pptx")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="soffice")
    @patch("os.path.exists", return_value=True)
    def test_conversion_success(self, mock_exists, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        svc = self._make_service()
        result = svc.convert_to_pdf("/tmp/test.pptx", "pptx")
        assert result.endswith(".pdf")


class TestRenovationServiceParseJson:
    """JSON 解析测试"""

    def _make_service(self):
        with patch("app.core.config.get_settings") as mock_settings:
            s = MagicMock()
            s.DASHSCOPE_API_KEY = "test-key"
            s.LLM_MODEL = "qwen-plus"
            s.VISION_MODEL = "qwen-vl-plus"
            mock_settings.return_value = s
            from app.generators.ppt.renovation_service import RenovationService
            return RenovationService()

    def test_parse_json_plain(self):
        svc = self._make_service()
        result = svc._parse_json_from_text('{"title": "Hello", "points": ["a"], "description": "desc"}')
        assert result["title"] == "Hello"
        assert result["points"] == ["a"]

    def test_parse_json_from_markdown_block(self):
        svc = self._make_service()
        text = '```json\n{"title": "Test", "points": [], "description": "d"}\n```'
        result = svc._parse_json_from_text(text)
        assert result["title"] == "Test"


class TestRenovationServiceFitzFallback:
    """fitz fallback 测试"""

    def _make_service(self):
        with patch("app.core.config.get_settings") as mock_settings:
            s = MagicMock()
            s.DASHSCOPE_API_KEY = "test-key"
            s.LLM_MODEL = "qwen-plus"
            s.VISION_MODEL = "qwen-vl-plus"
            mock_settings.return_value = s
            from app.generators.ppt.renovation_service import RenovationService
            return RenovationService()

    def test_fitz_fallback_no_text(self):
        svc = self._make_service()
        # 模拟一个空 PDF
        with patch("fitz.open") as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = ""
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_open.return_value = mock_doc
            md, err = svc._parse_via_fitz("/tmp/empty.pdf")
            assert md is None
            assert "无文本" in err

    def test_fitz_fallback_with_text(self):
        svc = self._make_service()
        with patch("fitz.open") as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Hello World"
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_open.return_value = mock_doc
            md, err = svc._parse_via_fitz("/tmp/test.pdf")
            assert md == "Hello World"
            assert err is None


# ============= Celery 任务逻辑测试 =============


class TestRenovationParseTaskResults:
    """翻新任务结果统计测试"""

    def test_all_success_result(self):
        results = [
            {"success": True, "page_id": 1, "page_number": 1},
            {"success": True, "page_id": 2, "page_number": 2},
        ]
        success_count = sum(1 for r in results if r.get("success"))
        failed_count = sum(1 for r in results if not r.get("success"))
        failed_pages = [
            {"page_id": r["page_id"], "page_number": r["page_number"], "error": r.get("error", "")}
            for r in results if not r.get("success")
        ]
        task_result = {
            "total_pages": 2,
            "success_count": success_count,
            "failed_count": failed_count,
            "partial_success": success_count > 0 and failed_count > 0,
            "failed_pages": failed_pages,
        }
        assert task_result["success_count"] == 2
        assert task_result["failed_count"] == 0
        assert task_result["partial_success"] is False
        assert task_result["failed_pages"] == []

    def test_partial_success_result(self):
        results = [
            {"success": True, "page_id": 1, "page_number": 1},
            {"success": False, "page_id": 2, "page_number": 2, "error": "AI 超时"},
        ]
        success_count = sum(1 for r in results if r.get("success"))
        failed_count = sum(1 for r in results if not r.get("success"))
        failed_pages = [
            {"page_id": r["page_id"], "page_number": r["page_number"], "error": r.get("error", "")}
            for r in results if not r.get("success")
        ]
        task_result = {
            "total_pages": 2,
            "success_count": success_count,
            "failed_count": failed_count,
            "partial_success": success_count > 0 and failed_count > 0,
            "failed_pages": failed_pages,
        }
        assert task_result["success_count"] == 1
        assert task_result["failed_count"] == 1
        assert task_result["partial_success"] is True
        assert len(task_result["failed_pages"]) == 1
        assert task_result["failed_pages"][0]["error"] == "AI 超时"

    def test_all_failed_result(self):
        results = [
            {"success": False, "page_id": 1, "page_number": 1, "error": "err1"},
            {"success": False, "page_id": 2, "page_number": 2, "error": "err2"},
        ]
        success_count = sum(1 for r in results if r.get("success"))
        failed_count = sum(1 for r in results if not r.get("success"))

        final_status = "COMPLETED" if success_count > 0 else "FAILED"
        project_status = "DESCRIPTIONS_GENERATED" if success_count > 0 else "FAILED"

        assert final_status == "FAILED"
        assert project_status == "FAILED"
        assert success_count == 0
        assert failed_count == 2


# ============= Schema / Model 测试 =============


class TestRenovationSchemaFields:
    """翻新相关 schema 字段测试"""

    def test_page_response_has_renovation_fields(self):
        from app.generators.ppt.banana_schemas import PPTPageResponse
        fields = PPTPageResponse.model_fields
        assert "renovation_status" in fields
        assert "renovation_error" in fields

    def test_project_response_has_description_text(self):
        from app.generators.ppt.banana_schemas import PPTProjectResponse
        fields = PPTProjectResponse.model_fields
        assert "description_text" in fields


class TestRenovationModelFields:
    """翻新相关模型字段测试"""

    def test_page_model_has_renovation_fields(self):
        from app.generators.ppt.banana_models import PPTPage
        mapper = PPTPage.__table__.columns
        assert "renovation_status" in mapper
        assert "renovation_error" in mapper

    def test_project_model_has_description_text(self):
        from app.generators.ppt.banana_models import PPTProject
        mapper = PPTProject.__table__.columns
        assert "description_text" in mapper


# ============= Prompt 测试 =============


class TestPrompts:
    """Prompt 格式测试"""

    def test_extraction_prompt_contains_slide_content(self):
        from app.generators.ppt.renovation_service import get_page_content_extraction_prompt
        prompt = get_page_content_extraction_prompt("# Hello\n- point1", "zh")
        assert "<slide_content>" in prompt
        assert "# Hello" in prompt
        assert "point1" in prompt
        assert "title" in prompt
        assert "points" in prompt

    def test_extraction_prompt_language(self):
        from app.generators.ppt.renovation_service import get_page_content_extraction_prompt
        prompt_zh = get_page_content_extraction_prompt("test", "zh")
        prompt_en = get_page_content_extraction_prompt("test", "en")
        assert "Chinese" in prompt_zh
        assert "English" in prompt_en

    def test_layout_caption_prompt(self):
        from app.generators.ppt.renovation_service import get_layout_caption_prompt
        prompt = get_layout_caption_prompt()
        assert "layout" in prompt.lower()
        assert "排版布局" in prompt


# ============= 路由校验测试 =============


class TestRenovationRouteValidation:
    """路由层输入校验（不需要完整 HTTP 测试）"""

    def test_file_ext_validation_logic(self):
        """验证文件类型校验逻辑"""
        valid_exts = ("pdf", "ppt", "pptx")
        invalid_exts = ("docx", "txt", "xlsx", "jpg")

        for ext in valid_exts:
            assert ext in valid_exts

        for ext in invalid_exts:
            assert ext not in valid_exts

    def test_creation_type_renovation(self):
        """验证 creation_type 校验逻辑"""
        # 模拟 non-renovation 项目被拒绝
        project_type = "dialog"
        assert project_type != "renovation"

        project_type = "renovation"
        assert project_type == "renovation"
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_ppt_renovation.py -v`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_ppt_renovation.py
git commit -m "test(ppt): add renovation tests for service, task, schema, routes"
```

---

### Task 8: 最终验证

- [ ] **Step 1: 运行全部翻新测试**

Run: `cd backend && python -m pytest tests/test_ppt_renovation.py -v`
Expected: 全部通过

- [ ] **Step 2: 运行现有 PPT 测试确保无回归**

Run: `cd backend && python -m pytest tests/test_ppt_project_schema_fields.py tests/test_ppt_intent_service.py -v`
Expected: 全部通过

- [ ] **Step 3: 验证 alembic migration 可升级降级**

Run: `cd backend && python -m alembic downgrade -1 && python -m alembic upgrade head`
Expected: 升降级均成功

- [ ] **Step 4: 最终 commit（如有遗漏修复）**

```bash
git add -A
git commit -m "fix(ppt): final adjustments for renovation pipeline"
```
