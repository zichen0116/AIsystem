from io import BytesIO

import pytest
from starlette.datastructures import Headers, UploadFile

from app.generators.ppt.banana_routes import _parse_bool_field, _parse_string_list_field
from app.generators.ppt.celery_tasks import (
    _crop_image_by_selection_bbox,
    _generate_image_with_retry,
    _normalize_selection_bbox,
    _read_uploaded_context_images,
)


def test_parse_string_list_field_accepts_json_string():
    assert _parse_string_list_field('["a", "b", 3]') == ["a", "b", "3"]


def test_parse_string_list_field_accepts_repeated_values():
    assert _parse_string_list_field(["x", " ", 2, None]) == ["x", "2"]


def test_parse_bool_field_accepts_common_truthy_values():
    assert _parse_bool_field(True) is True
    assert _parse_bool_field("true") is True
    assert _parse_bool_field("1") is True
    assert _parse_bool_field("on") is True


def test_normalize_selection_bbox_clamps_to_image_bounds():
    assert _normalize_selection_bbox(
        {"x": 2.2, "y": -4, "width": 20.6, "height": 14.2},
        image_width=12,
        image_height=10,
    ) == (2, 0, 12, 10)


def test_crop_image_by_selection_bbox_returns_png_crop():
    from PIL import Image

    source = Image.new("RGB", (20, 20), color="white")
    for x in range(5, 15):
        for y in range(2, 14):
            source.putpixel((x, y), (255, 0, 0))

    raw = BytesIO()
    source.save(raw, format="PNG")

    cropped = _crop_image_by_selection_bbox(
        raw.getvalue(),
        {"x": 5, "y": 2, "width": 10, "height": 12},
    )

    assert cropped is not None
    with Image.open(BytesIO(cropped)) as cropped_image:
        assert cropped_image.size == (10, 12)


@pytest.mark.asyncio
async def test_read_uploaded_context_images_keeps_only_image_files():
    image_upload = UploadFile(
        file=BytesIO(b"img-bytes"),
        filename="crop.png",
        headers=Headers({"content-type": "image/png"}),
    )
    text_upload = UploadFile(
        file=BytesIO(b"text"),
        filename="notes.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    result = await _read_uploaded_context_images([image_upload, text_upload])

    assert result == [b"img-bytes"]


class _FlakyProvider:
    def __init__(self, failures_before_success: int):
        self.failures_before_success = failures_before_success
        self.calls = 0

    async def agenerate_image(self, **kwargs):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise RuntimeError("Server disconnected without sending a response.")
        return b"ok"


@pytest.mark.asyncio
async def test_generate_image_with_retry_retries_until_success():
    provider = _FlakyProvider(failures_before_success=1)

    result = await _generate_image_with_retry(
        provider,
        prompt="demo",
        ref_images=None,
        aspect_ratio="16:9",
        resolution="2K",
        max_attempts=2,
        retry_delay=0,
    )

    assert result == b"ok"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_generate_image_with_retry_raises_after_last_attempt():
    provider = _FlakyProvider(failures_before_success=3)

    with pytest.raises(RuntimeError, match="Server disconnected"):
        await _generate_image_with_retry(
            provider,
            prompt="demo",
            ref_images=None,
            aspect_ratio="16:9",
            resolution="2K",
            max_attempts=2,
            retry_delay=0,
        )

    assert provider.calls == 2
