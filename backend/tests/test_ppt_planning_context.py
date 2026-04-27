from app.generators.ppt.planning_context_service import (
    SECTION_TITLES,
    build_strategy_fallback,
    format_planning_context_text,
    score_material_chunk,
    select_relevant_material_snippets,
)


def test_format_planning_context_text_uses_fixed_four_section_order():
    text = format_planning_context_text(
        {
            "intent_summary": "主题：水循环",
            "materials_summary": "图片：水循环示意图",
            "knowledge_summary": "知识库：蒸发与凝结",
            "generation_strategy": "建议 8 页结构",
        }
    )

    intent_title = f"## {SECTION_TITLES['intent_summary']}"
    materials_title = f"## {SECTION_TITLES['materials_summary']}"
    knowledge_title = f"## {SECTION_TITLES['knowledge_summary']}"
    strategy_title = f"## {SECTION_TITLES['generation_strategy']}"

    assert intent_title in text
    assert materials_title in text
    assert knowledge_title in text
    assert strategy_title in text
    assert text.index(intent_title) < text.index(materials_title) < text.index(knowledge_title) < text.index(strategy_title)


def test_score_material_chunk_prefers_title_and_keyword_hits():
    score = score_material_chunk(
        "水循环 蒸发",
        {
            "title": "水循环示意图",
            "content": "本页说明蒸发、凝结、降水过程",
            "keywords": ["蒸发", "降水"],
        },
    )

    assert score > 0


def test_select_relevant_material_snippets_returns_best_matches_only():
    snippets = select_relevant_material_snippets(
        query="水循环 蒸发",
        chunks=[
            {"title": "水循环示意图", "content": "蒸发与凝结", "keywords": ["蒸发"]},
            {"title": "植物结构", "content": "根茎叶", "keywords": ["植物"]},
            {"title": "蒸发实验", "content": "加热后观察水面变化", "keywords": ["蒸发"]},
        ],
        limit=2,
    )

    assert len(snippets) == 2
    assert snippets[0]["title"] == "水循环示意图"


def test_build_strategy_fallback_uses_available_inputs():
    text = build_strategy_fallback(
        intent_summary={
            "topic": "水循环",
            "constraints": "8页以内",
            "style": "课堂讲解",
        },
        has_materials=True,
        has_knowledge=True,
    )

    assert "水循环" in text
    assert "8页以内" in text
    assert "课堂讲解" in text
    assert "参考资料" in text
    assert "知识库" in text
