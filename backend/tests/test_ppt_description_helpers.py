from types import SimpleNamespace

from app.generators.ppt.banana_service import BananaAIService
from app.generators.ppt.page_utils import (
    build_page_image_prompt,
    extract_page_points,
    get_active_extra_fields_config,
    split_generated_description,
)


def test_extract_page_points_prefers_config_points():
    page = SimpleNamespace(
        config={"points": ["要点 A", "要点 B"]},
        description='["旧要点"]',
    )

    assert extract_page_points(page) == ["要点 A", "要点 B"]


def test_extract_page_points_falls_back_to_legacy_description_json():
    page = SimpleNamespace(
        config={},
        description='["旧要点 A", "旧要点 B"]',
    )

    assert extract_page_points(page) == ["旧要点 A", "旧要点 B"]


def test_extract_page_points_ignores_plain_text_description():
    page = SimpleNamespace(
        config={},
        description="页面标题：人工智能导论\n页面文字：- 发展脉络",
    )

    assert extract_page_points(page) == []


def test_build_description_prompt_requests_concise_structured_output():
    service = BananaAIService()

    prompt = service._build_description_prompt(
        {
            "id": 1,
            "title": "人工智能导论",
            "points": ["AI 定义", "发展阶段", "应用案例"],
        },
        theme="科技蓝",
        language="zh",
        detail_level="default",
    )

    assert "简洁" in prompt
    assert "结构化" in prompt
    assert "不要写成长段" in prompt
    assert "页面主题内容" in prompt
    assert "字段名必须完全一致" in prompt


def test_get_active_extra_fields_config_normalizes_saved_settings():
    settings = {
        "extra_fields_config": [
            {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
            {"key": "visual_focus", "label": "视觉焦点", "active": False, "image_prompt": True},
            {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
        ]
    }

    assert get_active_extra_fields_config(settings) == [
        {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
        {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
    ]


def test_split_generated_description_extracts_extra_fields_and_notes():
    parsed = split_generated_description(
        """页面标题：人工智能导论：发展脉络、深度学习崛起与二进制基础
页面文字：
- 主标题：人工智能导论
- 核心模块：AI 历史回顾、深度学习突破、二进制逻辑
讲稿：本页用于快速建立课程全貌，先交代发展线索，再引出本课的技术主线。
视觉元素：时间轴、芯片纹理背景、神经网络连线
视觉焦点：标题区与时间轴交汇点
排版布局：上标题，下方双栏信息区
演讲者备注：封面页要语速放慢，先抛出课程问题。""",
        [
            {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
            {"key": "visual_focus", "label": "视觉焦点", "active": True, "image_prompt": True},
            {"key": "layout", "label": "排版布局", "active": True, "image_prompt": True},
            {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
        ],
    )

    assert "页面标题：" in parsed["description"]
    assert "页面文字：" in parsed["description"]
    assert "讲稿：" in parsed["description"]
    assert "视觉元素" not in parsed["description"]
    assert parsed["extra_fields"] == {
        "visual_element": "时间轴、芯片纹理背景、神经网络连线",
        "visual_focus": "标题区与时间轴交汇点",
        "layout": "上标题，下方双栏信息区",
    }
    assert parsed["notes"] == "封面页要语速放慢，先抛出课程问题。"


def test_build_description_prompt_includes_active_extra_fields():
    service = BananaAIService()

    prompt = service._build_description_prompt(
        {
            "id": 1,
            "title": "人工智能导论",
            "points": ["AI 定义", "发展阶段", "应用案例"],
        },
        theme="科技蓝",
        language="zh",
        detail_level="default",
        extra_fields_config=[
            {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
            {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
        ],
    )

    assert "视觉元素：" in prompt
    assert "演讲者备注：" in prompt


def test_split_generated_description_prefers_page_theme_content_block():
    parsed = split_generated_description(
        """页面主题内容：
- 从 AI 发展脉络切入课程结构
- 点明深度学习崛起的关键节点
视觉元素：时间轴
视觉焦点：时间轴中段节点
排版布局：左右分栏
演讲者备注：开场先提问再讲定义""",
        [
            {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
            {"key": "visual_focus", "label": "视觉焦点", "active": True, "image_prompt": True},
            {"key": "layout", "label": "排版布局", "active": True, "image_prompt": True},
            {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
        ],
    )

    assert parsed["description"] == "- 从 AI 发展脉络切入课程结构\n- 点明深度学习崛起的关键节点"
    assert parsed["extra_fields"] == {
        "visual_element": "时间轴",
        "visual_focus": "时间轴中段节点",
        "layout": "左右分栏",
    }
    assert parsed["notes"] == "开场先提问再讲定义"


def test_build_page_image_prompt_filters_script_and_notes_but_keeps_visual_fields():
    page = SimpleNamespace(
        title="人工智能发展脉络与深度学习崛起",
        image_prompt=None,
        description="""页面标题：人工智能发展脉络与深度学习崛起
页面文字：
- 主标题：人工智能导论
- 核心模块：AI 历史回顾、深度学习突破、二进制逻辑
讲稿：大家好，我是软件工程专业的[你的名字]。今天我的汇报主题是《人工智能发展脉络与深度学习崛起》。
演讲者备注：封面页要放慢语速，先抛出课程问题。""",
        config={
            "extra_fields": {
                "visual_element": "时间轴、芯片纹理背景、神经网络连线",
                "visual_focus": "标题区与时间轴交汇点",
                "layout": "上标题，下方双栏信息区",
            }
        },
    )

    prompt = build_page_image_prompt(
        page,
        [
            {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
            {"key": "visual_focus", "label": "视觉焦点", "active": True, "image_prompt": True},
            {"key": "layout", "label": "排版布局", "active": True, "image_prompt": True},
            {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
        ],
    )

    assert "只输出图片" in prompt
    assert "页面标题：人工智能发展脉络与深度学习崛起" in prompt
    assert "页面文字：" in prompt
    assert "视觉元素：时间轴、芯片纹理背景、神经网络连线" in prompt
    assert "视觉焦点：标题区与时间轴交汇点" in prompt
    assert "排版布局：上标题，下方双栏信息区" in prompt
    assert "讲稿：" not in prompt
    assert "大家好，我是软件工程专业的" not in prompt
    assert "演讲者备注" not in prompt


def test_build_page_image_prompt_wraps_explicit_image_prompt():
    page = SimpleNamespace(
        title="人工智能发展脉络与深度学习崛起",
        image_prompt="科技感蓝色封面，中心发光时间轴，适合 AI 导论课程",
        description="讲稿：这段讲稿不应该再进入生图 prompt",
        config={"extra_fields": {"visual_element": "时间轴"}},
    )

    prompt = build_page_image_prompt(page)

    assert "只输出图片" in prompt
    assert "科技感蓝色封面，中心发光时间轴，适合 AI 导论课程" in prompt
    assert "这段讲稿不应该再进入生图 prompt" not in prompt
