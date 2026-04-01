from pathlib import Path

from app.generators.ppt.celery_tasks import (
    _load_project_template_bytes,
    _resolve_frontend_public_asset_path,
)


def test_resolve_frontend_public_asset_path_for_template_image():
    path = _resolve_frontend_public_asset_path("/templates/template_b.png")

    assert isinstance(path, Path)
    assert path.is_file()
    assert path.name == "template_b.png"


def test_load_project_template_bytes_reads_frontend_public_asset():
    result = _load_project_template_bytes({"template_image_url": "/templates/template_b.png"})

    assert result is not None
    assert len(result) > 0


def test_load_project_template_bytes_prefers_oss_key():
    expected = b"template-from-oss"

    class FakeOSS:
        def download_file(self, oss_key, local_path):
            assert oss_key == "ppt/templates/demo/example.png"
            Path(local_path).write_bytes(expected)

    result = _load_project_template_bytes(
        {
            "template_oss_key": "ppt/templates/demo/example.png",
            "template_image_url": "/templates/template_b.png",
        },
        FakeOSS(),
    )

    assert result == expected
