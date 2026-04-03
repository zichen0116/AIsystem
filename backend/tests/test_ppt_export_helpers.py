from pathlib import Path

from PIL import Image

from app.generators.ppt.banana_routes import _build_export_download_urls
from app.generators.ppt.ppt_export_service import PptExportService


def test_build_export_download_urls_for_local_file():
    result = _build_export_download_urls(
        r"D:\exports\slides_62.zip",
        is_local=True,
        api_base="http://127.0.0.1:8000",
    )

    assert result == {
        "download_url": "/api/v1/ppt/exports/local/slides_62.zip",
        "download_url_absolute": "http://127.0.0.1:8000/api/v1/ppt/exports/local/slides_62.zip",
        "is_local": True,
    }


def test_build_export_download_urls_for_remote_url():
    result = _build_export_download_urls(
        "https://cdn.example.com/ppt/62/presentation_abc.pdf",
        is_local=False,
        api_base="http://127.0.0.1:8000",
    )

    assert result == {
        "download_url": "https://cdn.example.com/ppt/62/presentation_abc.pdf",
        "download_url_absolute": "https://cdn.example.com/ppt/62/presentation_abc.pdf",
    }


def test_create_pdf_from_images_falls_back_without_img2pdf(tmp_path: Path):
    image_path = tmp_path / "page.png"
    Image.new("RGB", (320, 180), color="white").save(image_path)

    pdf_bytes = PptExportService.create_pdf_from_images([str(image_path)], aspect_ratio="16:9")

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
