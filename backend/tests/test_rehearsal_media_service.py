from copy import deepcopy

import pytest

from app.services.rehearsal_media_service import (
    build_rehearsal_image_prompt,
    populate_slide_media,
)


@pytest.mark.asyncio
async def test_populate_slide_media_replaces_placeholder_with_oss_url(monkeypatch):
    slide_content = {
        "id": "slide_1",
        "viewportSize": 1000,
        "viewportRatio": 0.5625,
        "background": {"type": "solid", "color": "#ffffff"},
        "elements": [
            {
                "id": "el_title",
                "type": "text",
                "content": "<p>牛顿第二定律</p>",
                "left": 60,
                "top": 40,
                "width": 400,
                "height": 50,
            },
            {
                "id": "el_image_1",
                "type": "image",
                "src": "placeholder",
                "left": 520,
                "top": 120,
                "width": 360,
                "height": 240,
            },
        ],
    }
    outline = {
        "title": "牛顿第二定律",
        "description": "通过生活中的受力现象理解加速度和合力的关系",
        "keyPoints": ["F=ma", "合力方向决定加速度方向"],
    }

    async def fake_generate(*, prompt, size):
        assert "牛顿第二定律" in prompt
        assert size == "1280*720"
        return "https://dashscope.example/generated.png"

    async def fake_download(url):
        assert url == "https://dashscope.example/generated.png"
        return b"image-bytes", "png"

    async def fake_upload(content, ext, user_id, prefix):
        assert content == b"image-bytes"
        assert ext == "png"
        assert user_id == 42
        assert prefix == "rehearsal-images"
        return "https://oss.example/rehearsal-images/42/generated.png"

    monkeypatch.setattr(
        "app.services.rehearsal_media_service.generate_qwen_image",
        fake_generate,
    )
    monkeypatch.setattr(
        "app.services.rehearsal_media_service.download_generated_media",
        fake_download,
    )
    monkeypatch.setattr(
        "app.services.rehearsal_media_service.upload_generated_media",
        fake_upload,
    )

    enriched = await populate_slide_media(
        deepcopy(slide_content),
        outline,
        user_id=42,
        session_id=7,
        scene_id=9,
    )

    image_element = enriched["elements"][1]
    assert image_element["type"] == "image"
    assert image_element["src"] == "https://oss.example/rehearsal-images/42/generated.png"


@pytest.mark.asyncio
async def test_populate_slide_media_degrades_failed_image_to_shape(monkeypatch):
    slide_content = {
        "id": "slide_1",
        "elements": [
            {
                "id": "el_image_1",
                "type": "image",
                "src": "placeholder",
                "left": 100,
                "top": 120,
                "width": 300,
                "height": 200,
            }
        ],
    }
    outline = {
        "title": "化学反应速率",
        "description": "观察温度变化对反应速率的影响",
        "keyPoints": ["温度升高，反应加快"],
    }

    async def fake_generate(*, prompt, size):
        raise RuntimeError("dashscope unavailable")

    monkeypatch.setattr(
        "app.services.rehearsal_media_service.generate_qwen_image",
        fake_generate,
    )

    enriched = await populate_slide_media(
        deepcopy(slide_content),
        outline,
        user_id=9,
        session_id=2,
        scene_id=3,
    )

    degraded = enriched["elements"][0]
    assert degraded["id"] == "el_image_1"
    assert degraded["type"] == "shape"
    assert degraded["shape"] == "roundRect"
    assert "src" not in degraded


def test_build_rehearsal_image_prompt_uses_nearby_text_as_slot_focus():
    slide_content = {
        "elements": [
            {
                "id": "img_ding",
                "type": "image",
                "src": "placeholder",
                "left": 80,
                "top": 120,
                "width": 180,
                "height": 180,
            },
            {
                "id": "txt_ding",
                "type": "text",
                "content": "<p>鼎</p>",
                "left": 80,
                "top": 320,
                "width": 180,
                "height": 40,
            },
            {
                "id": "img_ma",
                "type": "image",
                "src": "placeholder",
                "left": 380,
                "top": 120,
                "width": 180,
                "height": 180,
            },
            {
                "id": "txt_ma",
                "type": "text",
                "content": "<p>马</p>",
                "left": 380,
                "top": 320,
                "width": 180,
                "height": 40,
            },
            {
                "id": "img_tu",
                "type": "image",
                "src": "placeholder",
                "left": 680,
                "top": 120,
                "width": 180,
                "height": 180,
            },
            {
                "id": "txt_tu",
                "type": "text",
                "content": "<p>图</p>",
                "left": 680,
                "top": 320,
                "width": 180,
                "height": 40,
            },
        ]
    }
    outline = {
        "title": "青铜器与图腾",
        "description": "认识鼎、马、图三种文化符号",
        "keyPoints": ["鼎", "马", "图"],
    }

    prompt = build_rehearsal_image_prompt(outline, slide_content["elements"][0], slide_content)

    assert "鼎" in prompt
    assert "\n- 马" not in prompt
    assert "\n- 图" not in prompt
    assert "Do not include subjects from other image slots" in prompt
