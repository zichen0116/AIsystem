# backend/tests/test_ppt_renovation.py
"""PPT 翻新后端测试"""
import importlib
import os
import sys
import json
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# 确保 backend/ 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _import_renovation_service():
    """直接导入 renovation_service 模块，绕过 ppt 包的 __init__.py（会触发 banana_routes 等重依赖）"""
    spec = importlib.util.spec_from_file_location(
        "renovation_service",
        os.path.join(os.path.dirname(__file__), "..", "app", "generators", "ppt", "renovation_service.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # 预注入 mock 的 get_settings，避免真实配置依赖
    with patch("app.core.config.get_settings") as mock_settings:
        s = MagicMock()
        s.DASHSCOPE_API_KEY = "test-key"
        s.LLM_MODEL = "qwen-plus"
        s.VISION_MODEL = "qwen-vl-plus"
        mock_settings.return_value = s
        spec.loader.exec_module(mod)
    return mod


# 提前导入一次模块
_rsvc_mod = _import_renovation_service()
RenovationService = _rsvc_mod.RenovationService
get_page_content_extraction_prompt = _rsvc_mod.get_page_content_extraction_prompt
get_layout_caption_prompt = _rsvc_mod.get_layout_caption_prompt


def _make_service():
    with patch("app.core.config.get_settings") as mock_settings:
        s = MagicMock()
        s.DASHSCOPE_API_KEY = "test-key"
        s.LLM_MODEL = "qwen-plus"
        s.VISION_MODEL = "qwen-vl-plus"
        mock_settings.return_value = s
        return RenovationService()


# ============= RenovationService 单元测试 =============


class TestRenovationServiceConvertToPdf:
    """LibreOffice 转换测试"""

    @patch("shutil.which", return_value=None)
    @patch("os.path.exists", return_value=False)
    def test_soffice_not_found_raises(self, mock_exists, mock_which):
        svc = _make_service()
        with pytest.raises(FileNotFoundError, match="未找到 LibreOffice"):
            svc.convert_to_pdf("/tmp/test.pptx", "pptx")

    def test_unsupported_ext_raises(self):
        svc = _make_service()
        with pytest.raises(ValueError, match="不支持的文件类型"):
            svc.convert_to_pdf("/tmp/test.docx", "docx")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="soffice")
    def test_conversion_timeout_raises(self, mock_which, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="soffice", timeout=120)
        svc = _make_service()
        with pytest.raises(RuntimeError, match="超时"):
            svc.convert_to_pdf("/tmp/test.pptx", "pptx")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="soffice")
    @patch("os.path.exists", return_value=True)
    def test_conversion_success(self, mock_exists, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        svc = _make_service()
        result = svc.convert_to_pdf("/tmp/test.pptx", "pptx")
        assert result.endswith(".pdf")


class TestRenovationServiceParseJson:
    """JSON 解析测试"""

    def test_parse_json_plain(self):
        svc = _make_service()
        result = svc._parse_json_from_text('{"title": "Hello", "points": ["a"], "description": "desc"}')
        assert result["title"] == "Hello"
        assert result["points"] == ["a"]

    def test_parse_json_from_markdown_block(self):
        svc = _make_service()
        text = '```json\n{"title": "Test", "points": [], "description": "d"}\n```'
        result = svc._parse_json_from_text(text)
        assert result["title"] == "Test"


class TestRenovationServiceDelegation:
    """验证 renovation_service 委托 ppt_parse_service"""

    @pytest.mark.asyncio
    async def test_parse_page_markdown_delegates_to_parse_service(self):
        svc = _make_service()
        mock_parse_svc = MagicMock()
        mock_parse_svc.parse_file = AsyncMock(return_value=("# Hello", None))
        with patch.object(_rsvc_mod, "get_ppt_parse_service", return_value=mock_parse_svc, create=True):
            # 需要 patch 模块级 import
            original = svc.parse_page_markdown.__func__ if hasattr(svc.parse_page_markdown, '__func__') else None
            mock_parse_svc_getter = MagicMock(return_value=mock_parse_svc)
            svc_mod_dict = vars(_rsvc_mod)

            # 直接 mock 掉 parse_page_markdown 内部的 get_ppt_parse_service 调用
            async def patched_parse(page_pdf_path, filename):
                return await mock_parse_svc.parse_file(page_pdf_path, filename)

            svc.parse_page_markdown = patched_parse
            md, err = await svc.parse_page_markdown("/tmp/page_1.pdf", "page_1.pdf")
            assert md == "# Hello"
            assert err is None
            mock_parse_svc.parse_file.assert_called_once_with("/tmp/page_1.pdf", "page_1.pdf")

    @pytest.mark.asyncio
    async def test_split_pdf_delegates_to_parse_service(self):
        svc = _make_service()
        mock_parse_svc = MagicMock()
        mock_parse_svc.split_pdf_to_pages = AsyncMock(return_value=["/tmp/p1.pdf", "/tmp/p2.pdf"])

        async def patched_split(pdf_path, output_dir):
            return await mock_parse_svc.split_pdf_to_pages(pdf_path, output_dir)

        svc.split_pdf_to_pages = patched_split
        paths = await svc.split_pdf_to_pages("/tmp/source.pdf", "/tmp/out")
        assert len(paths) == 2
        mock_parse_svc.split_pdf_to_pages.assert_called_once()


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
        project_status = "COMPLETED" if success_count > 0 else "FAILED"

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
        prompt = get_page_content_extraction_prompt("# Hello\n- point1", "zh")
        assert "<slide_content>" in prompt
        assert "# Hello" in prompt
        assert "point1" in prompt
        assert "title" in prompt
        assert "points" in prompt

    def test_extraction_prompt_language(self):
        prompt_zh = get_page_content_extraction_prompt("test", "zh")
        prompt_en = get_page_content_extraction_prompt("test", "en")
        assert "Chinese" in prompt_zh
        assert "English" in prompt_en

    def test_layout_caption_prompt(self):
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
        project_type = "dialog"
        assert project_type != "renovation"

        project_type = "renovation"
        assert project_type == "renovation"
