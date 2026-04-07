from app.generators.ppt.intent_service import (
    INTENT_STATUS_CONFIRMED,
    INTENT_STATUS_READY,
    confirm_intent_state,
    create_intent_state,
    merge_intent_state,
    parse_intent_response,
)


def test_parse_intent_response_prefers_summary_to_infer_pending():
    raw = """
    {
      "reply": "请点击右侧按钮「确认意图，进入大纲页」，进一步生成大纲。",
      "intent_state": {
        "confirmed": ["主题是保护地球，人人有责"],
        "pending": ["核心教学目标", "章节重点和节奏"],
        "scores": {"goal": 90, "audience": 88, "structure": 86, "interaction": 85},
        "confidence": 91,
        "ready_for_confirmation": true,
        "summary": "本轮摘要"
      },
      "intent_summary": {
        "topic": "保护地球，人人有责",
        "audience": "八年级零基础学生",
        "goal": "理解保护地球的具体内涵，并掌握节约用水等行为指导",
        "duration": "20分钟",
        "constraints": "8页，风格轻松亲切",
        "style": "轻松亲切",
        "interaction": "一次提问互动和一次1分钟微分享",
        "extra": "围绕节约用水展开"
      }
    }
    """

    reply, state = parse_intent_response(raw)

    assert "确认意图" in reply
    assert state["pending"] == []
    assert state["ready_for_confirmation"] is True
    assert state["status"] == INTENT_STATUS_READY


def test_merge_intent_state_preserves_existing_confirmed_points():
    existing = create_intent_state("人工智能发展")
    existing["confirmed"] = ["受众是高一学生", "时长20分钟"]
    existing["intent_summary"]["audience"] = "高一学生"
    existing["intent_summary"]["duration"] = "20分钟"

    incoming = {
        "confirmed": ["核心目标是理解大模型的基本概念"],
        "intent_summary": {
            "goal": "理解大模型的基本概念",
            "constraints": "8页内",
            "style": "轻松清晰",
            "interaction": "1次提问互动",
        },
        "scores": {"goal": 88, "audience": 76, "structure": 78, "interaction": 80},
        "confidence": 82,
        "summary": "本轮摘要",
    }

    merged = merge_intent_state(existing, incoming, fallback_topic="人工智能发展")

    assert "受众是高一学生" in merged["confirmed"]
    assert "核心目标是理解大模型的基本概念" in merged["confirmed"]
    assert merged["intent_summary"]["topic"] == "人工智能发展"
    assert merged["intent_summary"]["goal"] == "理解大模型的基本概念"


def test_confirm_intent_state_marks_confirmed():
    state = create_intent_state("人工智能发展")
    state["confirmed"] = ["受众是高一学生", "目标是理解大模型", "课时20分钟", "有一次提问互动"]
    state["intent_summary"] = {
        "topic": "人工智能发展",
        "audience": "高一学生",
        "goal": "理解大模型",
        "duration": "20分钟",
        "constraints": "8页内",
        "style": "轻松清晰",
        "interaction": "一次提问互动",
        "extra": "",
    }
    state["pending"] = []

    confirmed = confirm_intent_state(state)

    assert confirmed["status"] == INTENT_STATUS_CONFIRMED
    assert confirmed["ready_for_confirmation"] is True
    assert confirmed["confirmed_at"] is not None
