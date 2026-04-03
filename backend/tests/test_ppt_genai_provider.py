import io

from PIL import Image

from app.generators.ppt.banana_providers import GenAIImageProvider


def _png_bytes(color: str) -> bytes:
    image = Image.new("RGB", (2, 2), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeProxyImage:
    def __init__(self, image_bytes: bytes):
        self.image_bytes = image_bytes


class _FakePart:
    def __init__(self, image=None):
        self._image = image
        self.text = None

    def as_image(self):
        return self._image


class _FakeResponse:
    def __init__(self, parts):
        self.parts = parts
        self.candidates = []
        self.text = None


def test_extract_image_from_part_supports_proxy_image_bytes():
    provider = object.__new__(GenAIImageProvider)
    expected = _png_bytes("red")
    part = _FakePart(_FakeProxyImage(expected))

    result = provider._extract_image_from_part(part)

    assert result == expected


def test_extract_image_from_generate_content_response_prefers_last_image():
    provider = object.__new__(GenAIImageProvider)
    first = _FakePart(Image.new("RGB", (2, 2), color="red"))
    last = _FakePart(Image.new("RGB", (2, 2), color="blue"))
    response = _FakeResponse([first, last])

    result = provider._extract_image_from_generate_content_response(response)

    assert Image.open(io.BytesIO(result)).getpixel((0, 0)) == (0, 0, 255)
