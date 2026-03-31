"""
PPT生成模块 - Celery异步任务
"""
import asyncio
import logging
import os
import tempfile
import uuid
from typing import Optional

from celery import Task
from app.celery import celery_app
from app.generators.ppt.banana_service import get_banana_service
from app.generators.ppt.file_service import get_oss_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

async def _update_task_status(db, task_id_str: str, status: str, progress: int, result: dict = None):
    """更新 PPTTask 记录状态"""
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTTask
    from datetime import datetime, timezone

    res = await db.execute(select(PPTTask).where(PPTTask.task_id == task_id_str))
    task = res.scalar_one_or_none()
    if task:
        task.status = status
        task.progress = progress
        if result is not None:
            task.result = result
        if status in ("COMPLETED", "FAILED"):
            task.completed_at = datetime.now(timezone.utc)
    await db.commit()


def _extract_oss_key(url: str) -> Optional[str]:
    """从 OSS URL 或签名 URL 提取 oss_key"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        if path:
            return path
    except Exception:
        pass
    return None


def _normalize_extension(file_type: Optional[str], filename: Optional[str] = None) -> str:
    """将 file_type/MIME/文件名统一为扩展名（不带点）。"""
    mime_to_ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "application/pdf": "pdf",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "text/markdown": "md",
        "text/csv": "csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    }

    value = (file_type or "").strip().lower()
    if value in mime_to_ext:
        return mime_to_ext[value]

    if "/" in value and value in mime_to_ext:
        return mime_to_ext[value]

    if value.startswith("."):
        return value.lstrip(".")

    if value and "/" not in value:
        return value

    if filename:
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext:
            return ext

    return "bin"


def _download_image_bytes(page, oss_svc) -> Optional[bytes]:
    """同步下载页面图片，返回 bytes；失败返回 None"""
    if not page.image_url:
        return None
    tmp_path = None
    try:
        oss_key = _extract_oss_key(page.image_url)
        if oss_key:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            oss_svc.download_file(oss_key, tmp_path)
            with open(tmp_path, "rb") as f:
                return f.read()
        else:
            import urllib.request
            with urllib.request.urlopen(page.image_url, timeout=30) as resp:
                return resp.read()
    except Exception as e:
        logger.warning("下载页面图片失败 page_id=%s: %s", page.id, e)
        return None
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# 任务：批量生成描述
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.generate_descriptions")
def generate_descriptions_task(self: Task, project_id: int, task_id_str: str = None, language: str = "zh"):
    """
    批量生成页面描述。

    Args:
        project_id: 项目ID
        task_id_str: PPTTask.task_id，用于更新进度
        language: 输出语言
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject, PPTPage

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 0)

            res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = res.scalar_one_or_none()
            if not project:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Project not found"})
                return {"error": "Project not found"}

            res = await db.execute(
                select(PPTPage)
                .where(PPTPage.project_id == project_id)
                .order_by(PPTPage.page_number)
            )
            pages = list(res.scalars().all())
            total = len(pages)

            if total == 0:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "COMPLETED", 100, {"count": 0})
                return {"status": "completed", "count": 0}

            for p in pages:
                p.is_description_generating = True
            await db.commit()

        banana_svc = get_banana_service()
        theme = project.theme
        completed = 0

        for page in pages:
            cfg = page.config or {}
            points = cfg.get("points") or []
            page_dict = {"id": page.id, "title": page.title or "", "points": points}

            try:
                description = await banana_svc.generate_description(
                    page_dict, theme=theme, language=language
                )
                async with AsyncSessionLocal() as db2:
                    res2 = await db2.execute(select(PPTPage).where(PPTPage.id == page.id))
                    db_page = res2.scalar_one_or_none()
                    if db_page:
                        db_page.description = description
                        db_page.is_description_generating = False
                    await db2.commit()
            except Exception as e:
                logger.error("描述生成失败 page_id=%s: %s", page.id, e)
                async with AsyncSessionLocal() as db2:
                    res2 = await db2.execute(select(PPTPage).where(PPTPage.id == page.id))
                    db_page = res2.scalar_one_or_none()
                    if db_page:
                        db_page.is_description_generating = False
                    await db2.commit()

            completed += 1
            if task_id_str:
                progress = int(completed / total * 100)
                async with AsyncSessionLocal() as db3:
                    await _update_task_status(db3, task_id_str, "PROCESSING", progress)

        if task_id_str:
            async with AsyncSessionLocal() as db4:
                await _update_task_status(db4, task_id_str, "COMPLETED", 100, {"count": completed})
        return {"status": "completed", "project_id": project_id, "count": completed}

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 任务：批量生成图片
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.generate_images")
def generate_images_task(self: Task, project_id: int, page_ids: list = None, task_id_str: str = None):
    """
    批量生成页面图片。

    Args:
        project_id: 项目ID
        page_ids: 页面ID列表，None 表示全部
        task_id_str: PPTTask.task_id
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, update as sa_update
    from app.generators.ppt.banana_models import PPTProject, PPTPage, PPTMaterial, PageImageVersion
    from app.generators.ppt.banana_providers import get_image_provider_singleton

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 0)

            res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = res.scalar_one_or_none()
            if not project:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Project not found"})
                return {"error": "Project not found"}

            q = select(PPTPage).where(PPTPage.project_id == project_id)
            if page_ids:
                q = q.where(PPTPage.id.in_(page_ids))
            q = q.order_by(PPTPage.page_number)
            res = await db.execute(q)
            pages = list(res.scalars().all())
            total = len(pages)

            if total == 0:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "COMPLETED", 100, {"count": 0})
                return {"status": "completed", "count": 0}

            for p in pages:
                p.is_image_generating = True
            await db.commit()

        aspect_ratio = (project.settings or {}).get("aspect_ratio", "16:9")
        oss_svc = get_oss_service()
        image_provider = get_image_provider_singleton()
        completed = 0

        for page in pages:
            try:
                prompt = page.image_prompt or page.description or page.title or "Professional PPT slide"

                # 素材参考图（同步下载）
                ref_images = []
                if page.material_ids:
                    async with AsyncSessionLocal() as db_mat:
                        mat_res = await db_mat.execute(
                            select(PPTMaterial).where(PPTMaterial.id.in_(page.material_ids))
                        )
                        materials = list(mat_res.scalars().all())
                    for mat in materials:
                        mat_ext = _normalize_extension(mat.file_type, mat.filename)
                        if mat_ext in ("png", "jpg", "jpeg", "webp"):
                            mat_key = _extract_oss_key(mat.url)
                            if mat_key:
                                try:
                                    with tempfile.NamedTemporaryFile(
                                        suffix="." + mat_ext, delete=False
                                    ) as tmp:
                                        tmp_path = tmp.name
                                    oss_svc.download_file(mat_key, tmp_path)
                                    with open(tmp_path, "rb") as f:
                                        ref_images.append(f.read())
                                    os.unlink(tmp_path)
                                except Exception as e:
                                    logger.warning("加载素材图片失败 material_id=%s: %s", mat.id, e)

                img_bytes = await image_provider.agenerate_image(
                    prompt=prompt,
                    ref_images=ref_images or None,
                    aspect_ratio=aspect_ratio,
                )

                oss_key = "ppt/{}/pages/{}/v{}_{}.png".format(
                    project_id, page.id, page.image_version + 1, uuid.uuid4().hex[:8]
                )
                image_url = oss_svc.upload_bytes(img_bytes, oss_key)

                async with AsyncSessionLocal() as db2:
                    res2 = await db2.execute(select(PPTPage).where(PPTPage.id == page.id))
                    db_page = res2.scalar_one_or_none()
                    if db_page:
                        new_version = db_page.image_version + 1
                        db_page.image_url = image_url
                        db_page.image_version = new_version
                        db_page.is_image_generating = False

                        await db2.execute(
                            sa_update(PageImageVersion)
                            .where(PageImageVersion.page_id == page.id)
                            .where(PageImageVersion.is_active.is_(True))
                            .values(is_active=False)
                        )
                        db2.add(PageImageVersion(
                            page_id=page.id,
                            user_id=project.user_id,
                            version=new_version,
                            image_url=image_url,
                            operation="generate",
                            is_active=True,
                        ))
                        await db2.commit()

            except Exception as e:
                logger.error("图片生成失败 page_id=%s: %s", page.id, e)
                async with AsyncSessionLocal() as db2:
                    res2 = await db2.execute(select(PPTPage).where(PPTPage.id == page.id))
                    db_page = res2.scalar_one_or_none()
                    if db_page:
                        db_page.is_image_generating = False
                    await db2.commit()

            completed += 1
            if task_id_str:
                progress = int(completed / total * 100)
                async with AsyncSessionLocal() as db3:
                    await _update_task_status(db3, task_id_str, "PROCESSING", progress)

        if task_id_str:
            async with AsyncSessionLocal() as db4:
                await _update_task_status(db4, task_id_str, "COMPLETED", 100, {"count": completed})
        return {"status": "completed", "project_id": project_id, "count": completed}

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 共用：下载所有页面图片到临时目录
# ---------------------------------------------------------------------------

def _download_pages_to_tmpdir(pages, oss_svc) -> tuple:
    """下载页面图片到临时目录，返回 (tmp_dir, image_paths)"""
    tmp_dir = tempfile.mkdtemp()
    image_paths = []
    for i, page in enumerate(pages):
        local_path = os.path.join(tmp_dir, "page_{:04d}.png".format(i))
        oss_key = _extract_oss_key(page.image_url)
        try:
            if oss_key:
                oss_svc.download_file(oss_key, local_path)
            else:
                import urllib.request
                urllib.request.urlretrieve(page.image_url, local_path)
            image_paths.append(local_path)
        except Exception as e:
            logger.warning("下载页面图片失败 page_id=%s: %s", page.id, e)
    return tmp_dir, image_paths


async def _update_project_export(project_id: int, export_url: str):
    """更新项目导出字段"""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
        proj = res.scalar_one_or_none()
        if proj:
            proj.exported_file_url = export_url
            proj.exported_at = datetime.now(timezone.utc)
        await db.commit()


# ---------------------------------------------------------------------------
# 任务：导出 PPTX
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.export_pptx")
def export_pptx_task(self: Task, project_id: int, task_id_str: str = None):
    """
    导出PPTX。

    Args:
        project_id: 项目ID
        task_id_str: PPTTask.task_id
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject, PPTPage
    from app.generators.ppt.ppt_export_service import get_ppt_export_service
    import shutil

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 10)

            res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = res.scalar_one_or_none()
            if not project:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Project not found"})
                return {"error": "Project not found"}

            res = await db.execute(
                select(PPTPage)
                .where(PPTPage.project_id == project_id)
                .where(PPTPage.image_url.isnot(None))
                .order_by(PPTPage.page_number)
            )
            pages = list(res.scalars().all())

        aspect_ratio = (project.settings or {}).get("aspect_ratio", "16:9")
        oss_svc = get_oss_service()
        export_svc = get_ppt_export_service()

        tmp_dir, image_paths = _download_pages_to_tmpdir(pages, oss_svc)
        try:
            if task_id_str:
                async with AsyncSessionLocal() as db2:
                    await _update_task_status(db2, task_id_str, "PROCESSING", 50)

            pptx_bytes = export_svc.create_pptx_from_images(image_paths, aspect_ratio=aspect_ratio)
            if not pptx_bytes:
                raise ValueError("PPTX生成失败")

            oss_key = "ppt/{}/exports/presentation_{}.pptx".format(
                project_id, uuid.uuid4().hex[:8]
            )
            export_url = oss_svc.upload_bytes(pptx_bytes, oss_key)
            await _update_project_export(project_id, export_url)

            if task_id_str:
                async with AsyncSessionLocal() as db3:
                    await _update_task_status(db3, task_id_str, "COMPLETED", 100, {"url": export_url})
            return {"status": "completed", "url": export_url}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 任务：导出 PDF
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.export_pdf")
def export_pdf_task(self: Task, project_id: int, task_id_str: str = None):
    """
    导出PDF。

    Args:
        project_id: 项目ID
        task_id_str: PPTTask.task_id
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject, PPTPage
    from app.generators.ppt.ppt_export_service import get_ppt_export_service
    import shutil

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 10)

            res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = res.scalar_one_or_none()
            if not project:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Project not found"})
                return {"error": "Project not found"}

            res = await db.execute(
                select(PPTPage)
                .where(PPTPage.project_id == project_id)
                .where(PPTPage.image_url.isnot(None))
                .order_by(PPTPage.page_number)
            )
            pages = list(res.scalars().all())

        aspect_ratio = (project.settings or {}).get("aspect_ratio", "16:9")
        oss_svc = get_oss_service()
        export_svc = get_ppt_export_service()

        tmp_dir, image_paths = _download_pages_to_tmpdir(pages, oss_svc)
        try:
            if task_id_str:
                async with AsyncSessionLocal() as db2:
                    await _update_task_status(db2, task_id_str, "PROCESSING", 50)

            pdf_bytes = export_svc.create_pdf_from_images(image_paths, aspect_ratio=aspect_ratio)
            if not pdf_bytes:
                raise ValueError("PDF生成失败")

            oss_key = "ppt/{}/exports/presentation_{}.pdf".format(
                project_id, uuid.uuid4().hex[:8]
            )
            export_url = oss_svc.upload_bytes(pdf_bytes, oss_key)
            await _update_project_export(project_id, export_url)

            if task_id_str:
                async with AsyncSessionLocal() as db3:
                    await _update_task_status(db3, task_id_str, "COMPLETED", 100, {"url": export_url})
            return {"status": "completed", "url": export_url}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 任务：导出图片集 (ZIP)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.export_images")
def export_images_task(self: Task, project_id: int, task_id_str: str = None):
    """
    将每页图片打包为 ZIP 导出。

    Args:
        project_id: 项目ID
        task_id_str: PPTTask.task_id
    """
    import io as _io
    import zipfile
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject, PPTPage

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 10)

            res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = res.scalar_one_or_none()
            if not project:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Project not found"})
                return {"error": "Project not found"}

            res = await db.execute(
                select(PPTPage)
                .where(PPTPage.project_id == project_id)
                .where(PPTPage.image_url.isnot(None))
                .order_by(PPTPage.page_number)
            )
            pages = list(res.scalars().all())

        oss_svc = get_oss_service()
        zip_buf = _io.BytesIO()
        total = len(pages)

        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, page in enumerate(pages):
                img_bytes = _download_image_bytes(page, oss_svc)
                if img_bytes:
                    zf.writestr("slide_{:03d}.png".format(i + 1), img_bytes)
                else:
                    logger.warning("跳过无图片页面 page_id=%s", page.id)

                if task_id_str:
                    progress = int((i + 1) / max(total, 1) * 80) + 10
                    async with AsyncSessionLocal() as db2:
                        await _update_task_status(db2, task_id_str, "PROCESSING", progress)

        zip_bytes = zip_buf.getvalue()
        oss_key = "ppt/{}/exports/images_{}.zip".format(project_id, uuid.uuid4().hex[:8])
        export_url = oss_svc.upload_bytes(zip_bytes, oss_key)

        if task_id_str:
            async with AsyncSessionLocal() as db3:
                await _update_task_status(db3, task_id_str, "COMPLETED", 100, {"url": export_url})
        return {"status": "completed", "url": export_url}

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 任务：导出可编辑 PPTX（委托给 export_pptx_task）
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.export_editable_pptx")
def export_editable_pptx_task(self: Task, project_id: int, task_id_str: str = None):
    """
    导出可编辑PPTX（当前实现与 export_pptx 相同）。

    Args:
        project_id: 项目ID
        task_id_str: PPTTask.task_id
    """
    return export_pptx_task(project_id, task_id_str=task_id_str)


# ---------------------------------------------------------------------------
# 任务：翻新解析旧PPT/PDF
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.renovation_parse")
def renovation_parse_task(self: Task, project_id: int, file_id: int, task_id_str: str = None):
    """
    解析旧 PPT/PDF 提取大纲。

    Args:
        project_id: 项目ID
        file_id: PPTReferenceFile.id
        task_id_str: PPTTask.task_id
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTReferenceFile

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 0)

            res = await db.execute(select(PPTReferenceFile).where(PPTReferenceFile.id == file_id))
            ref_file = res.scalar_one_or_none()
            if not ref_file:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "File not found"})
                return {"error": "File not found"}

            ref_file.parse_status = "processing"
            await db.commit()

        oss_svc = get_oss_service()
        banana_svc = get_banana_service()
        tmp_path = None

        try:
            ref_ext = _normalize_extension(ref_file.file_type, ref_file.filename)
            with tempfile.NamedTemporaryFile(suffix="." + ref_ext, delete=False) as tmp:
                tmp_path = tmp.name
            oss_key = _extract_oss_key(ref_file.url)
            if oss_key:
                oss_svc.download_file(oss_key, tmp_path)
            else:
                import urllib.request
                urllib.request.urlretrieve(ref_file.url, tmp_path)

            text_content = ""
            if ref_ext == "pdf":
                try:
                    import fitz
                    doc = fitz.open(tmp_path)
                    text_content = "\n".join((page.get_text() or "") for page in doc)
                    doc.close()
                except Exception as e:
                    logger.warning("PDF文本提取失败: %s", e)
            elif ref_ext in ("pptx", "ppt"):
                try:
                    from pptx import Presentation
                    prs = Presentation(tmp_path)
                    lines = []
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if shape.has_text_frame:
                                lines.append(shape.text_frame.text)
                    text_content = "\n".join(lines)
                except Exception as e:
                    logger.warning("PPTX文本提取失败: %s", e)

            if task_id_str:
                async with AsyncSessionLocal() as db2:
                    await _update_task_status(db2, task_id_str, "PROCESSING", 50)

            parsed = await banana_svc.parse_outline_text(
                text_content or ref_file.filename, language="zh"
            )

            async with AsyncSessionLocal() as db3:
                res3 = await db3.execute(
                    select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                )
                db_file = res3.scalar_one_or_none()
                if db_file:
                    db_file.parse_status = "completed"
                    db_file.parsed_outline = parsed
                await db3.commit()

            if task_id_str:
                async with AsyncSessionLocal() as db4:
                    await _update_task_status(db4, task_id_str, "COMPLETED", 100, {"parsed": True})
            return {"status": "completed", "file_id": file_id}

        except Exception as e:
            logger.error("翻新解析失败 file_id=%s: %s", file_id, e)
            async with AsyncSessionLocal() as db2:
                res2 = await db2.execute(
                    select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                )
                db_file = res2.scalar_one_or_none()
                if db_file:
                    db_file.parse_status = "failed"
                    db_file.parse_error = str(e)
                await db2.commit()
            if task_id_str:
                async with AsyncSessionLocal() as db3:
                    await _update_task_status(db3, task_id_str, "FAILED", 0, {"error": str(e)})
            raise
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 任务：编辑单页图片
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.edit_page_image")
def edit_page_image_task(
    self: Task,
    project_id: int,
    page_id: int,
    edit_instruction: str,
    task_id_str: str = None,
    context_images: dict = None,
):
    """
    对单页图片执行自然语言编辑。

    Args:
        project_id: 项目ID
        page_id: 页面ID
        edit_instruction: 自然语言编辑指令
        task_id_str: PPTTask.task_id
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, update as sa_update
    from app.generators.ppt.banana_models import PPTProject, PPTPage, PageImageVersion
    from app.generators.ppt.banana_providers import get_image_provider_singleton

    async def _run():
        async with AsyncSessionLocal() as db:
            if task_id_str:
                await _update_task_status(db, task_id_str, "PROCESSING", 0)

            res = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = res.scalar_one_or_none()
            if not project:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Project not found"})
                return {"error": "Project not found"}

            res = await db.execute(select(PPTPage).where(PPTPage.id == page_id))
            page = res.scalar_one_or_none()
            if not page:
                if task_id_str:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": "Page not found"})
                return {"error": "Page not found"}

        aspect_ratio = (project.settings or {}).get("aspect_ratio", "16:9")
        oss_svc = get_oss_service()
        image_provider = get_image_provider_singleton()

        ref_images = []

        # 1. 当前页面图作为基础参考
        if page.image_url:
            img = _download_image_bytes(page, oss_svc)
            if img:
                ref_images.append(img)

        # 2. 消费 context_images
        if context_images:
            # 2a. 模板图：从项目 settings.template_image_url 获取
            if context_images.get("use_template"):
                template_url = (project.settings or {}).get("template_image_url")
                if template_url:
                    try:
                        import urllib.request as _ureq
                        with _ureq.urlopen(template_url, timeout=20) as resp:
                            ref_images.append(resp.read())
                    except Exception as e:
                        logger.warning("加载模板图片失败: %s", e)

            # 2b. 描述中的图片URL列表
            for url in (context_images.get("desc_image_urls") or []):
                try:
                    import urllib.request as _ureq
                    with _ureq.urlopen(url, timeout=20) as resp:
                        ref_images.append(resp.read())
                except Exception as e:
                    logger.warning("加载描述图片失败 url=%s: %s", url, e)

            # 2c. 上传的图片ID：从 PPTMaterial 查找，通过 url 字段下载
            uploaded_ids = context_images.get("uploaded_image_ids") or []
            if uploaded_ids:
                from app.generators.ppt.banana_models import PPTMaterial
                async with AsyncSessionLocal() as db_mat:
                    mat_res = await db_mat.execute(
                        select(PPTMaterial).where(PPTMaterial.id.in_([
                            int(i) for i in uploaded_ids if str(i).isdigit()
                        ]))
                    )
                    for mat in mat_res.scalars().all():
                        if not mat.url:
                            continue
                        mat_ext = _normalize_extension(mat.file_type, mat.filename)
                        if mat_ext not in ("png", "jpg", "jpeg", "webp"):
                            continue
                        try:
                            mat_key = _extract_oss_key(mat.url)
                            if mat_key:
                                with tempfile.NamedTemporaryFile(suffix="." + mat_ext, delete=False) as tmp:
                                    tmp_mat_path = tmp.name
                                oss_svc.download_file(mat_key, tmp_mat_path)
                                with open(tmp_mat_path, "rb") as f:
                                    ref_images.append(f.read())
                                os.unlink(tmp_mat_path)
                            else:
                                import urllib.request as _ureq2
                                with _ureq2.urlopen(mat.url, timeout=20) as resp:
                                    ref_images.append(resp.read())
                        except Exception as e:
                            logger.warning("加载上传图片失败 material_id=%s: %s", mat.id, e)

        base_desc = page.description or page.title or ""
        prompt = "{0}\n\n编辑要求：{1}".format(base_desc, edit_instruction) if base_desc else edit_instruction

        if task_id_str:
            async with AsyncSessionLocal() as db2:
                await _update_task_status(db2, task_id_str, "PROCESSING", 30)

        img_bytes = await image_provider.agenerate_image(
            prompt=prompt,
            ref_images=ref_images or None,
            aspect_ratio=aspect_ratio,
        )

        oss_key = "ppt/{}/pages/{}/edit_{}.png".format(project_id, page_id, uuid.uuid4().hex[:8])
        image_url = oss_svc.upload_bytes(img_bytes, oss_key)

        async with AsyncSessionLocal() as db3:
            res3 = await db3.execute(select(PPTPage).where(PPTPage.id == page_id))
            db_page = res3.scalar_one_or_none()
            if db_page:
                new_version = db_page.image_version + 1
                db_page.image_url = image_url
                db_page.image_version = new_version
                db_page.is_image_generating = False

                await db3.execute(
                    sa_update(PageImageVersion)
                    .where(PageImageVersion.page_id == page_id)
                    .where(PageImageVersion.is_active.is_(True))
                    .values(is_active=False)
                )
                db3.add(PageImageVersion(
                    page_id=page_id,
                    user_id=project.user_id,
                    version=new_version,
                    image_url=image_url,
                    operation="edit",
                    prompt=edit_instruction,
                    is_active=True,
                ))
                await db3.commit()

        if task_id_str:
            async with AsyncSessionLocal() as db4:
                await _update_task_status(db4, task_id_str, "COMPLETED", 100, {"url": image_url})
        return {"status": "completed", "url": image_url}

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# 任务：AI 生成素材图片
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.generate_material")
def generate_material_task(
    self: Task,
    project_id: int,
    user_id: int,
    prompt: str,
    aspect_ratio: str = "1:1",
    task_id_str: str = None,
):
    """
    AI 生成素材图片，结果写入 PPTMaterial 表。

    Args:
        project_id: 项目ID
        user_id: 用户ID
        prompt: 生成提示词
        aspect_ratio: 图片比例
        task_id_str: PPTTask.task_id
    """
    from app.core.database import AsyncSessionLocal
    from app.generators.ppt.banana_models import PPTMaterial
    from app.generators.ppt.banana_providers import get_image_provider_singleton

    async def _run():
        if task_id_str:
            async with AsyncSessionLocal() as db:
                await _update_task_status(db, task_id_str, "PROCESSING", 10)

        try:
            image_provider = get_image_provider_singleton()
            oss_svc = get_oss_service()

            if task_id_str:
                async with AsyncSessionLocal() as db:
                    await _update_task_status(db, task_id_str, "PROCESSING", 30)

            img_bytes = await image_provider.agenerate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )

            oss_key = "ppt/{}/materials/ai_{}.png".format(project_id, uuid.uuid4().hex[:10])
            image_url = oss_svc.upload_bytes(img_bytes, oss_key)

            if task_id_str:
                async with AsyncSessionLocal() as db:
                    await _update_task_status(db, task_id_str, "PROCESSING", 80)

            # 写入 PPTMaterial
            async with AsyncSessionLocal() as db:
                material = PPTMaterial(
                    user_id=user_id,
                    project_id=project_id,
                    filename="ai_material_{}.png".format(uuid.uuid4().hex[:6]),
                    oss_path=oss_key,
                    url=image_url,
                    file_type="png",
                    material_type="image",
                )
                db.add(material)
                await db.commit()
                await db.refresh(material)
                material_id = material.id

            if task_id_str:
                async with AsyncSessionLocal() as db:
                    await _update_task_status(
                        db, task_id_str, "COMPLETED", 100,
                        {"url": image_url, "material_id": material_id}
                    )
            return {"status": "completed", "url": image_url, "material_id": material_id}

        except Exception as e:
            logger.error("素材生成失败 project_id=%s: %s", project_id, e)
            if task_id_str:
                async with AsyncSessionLocal() as db:
                    await _update_task_status(db, task_id_str, "FAILED", 0, {"error": str(e)})
            raise

    return asyncio.run(_run())
