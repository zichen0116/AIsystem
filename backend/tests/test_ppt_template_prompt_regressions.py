from types import SimpleNamespace

from app.generators.ppt.page_utils import build_page_image_prompt


def test_build_page_image_prompt_adds_template_constraints_and_style_description():
    page = SimpleNamespace(
        title="人工智能发展脉络",
        image_prompt=None,
        description="页面标题：人工智能发展脉络\n页面文字：概述符号主义、统计学习和深度学习的重要阶段",
        config={"extra_fields": {}},
    )

    prompt = build_page_image_prompt(
        page,
        [],
        {
            "template_image_url": "/templates/template_glass.png",
            "template_style": "整体采用玻璃拟态卡片和冷色渐变，强调科技感与留白。",
            "aspect_ratio": "16:9",
        },
    )

    assert "如果提供了模板参考图" in prompt
    assert "严格参考模板图的配色、版式、设计语言与整体氛围" in prompt
    assert "不要直接复用模板图中的文字" in prompt
    assert "补充风格要求" in prompt
    assert "整体采用玻璃拟态卡片和冷色渐变" in prompt
