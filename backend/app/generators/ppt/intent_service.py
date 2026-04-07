from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


INTENT_STATUS_CLARIFYING = "CLARIFYING"
INTENT_STATUS_READY = "READY"
INTENT_STATUS_CONFIRMED = "CONFIRMED"

DEFAULT_INTENT_PENDING = [
    "受众基础层次",
    "核心教学目标",
    "章节重点和节奏",
    "互动形式与限制条件",
]

DEFAULT_INTENT_SCORES = {
    "goal": 35,
    "audience": 35,
    "structure": 35,
    "interaction": 35,
}

INTENT_DIMENSIONS = {
    "audience": DEFAULT_INTENT_PENDING[0],
    "goal": DEFAULT_INTENT_PENDING[1],
    "structure": DEFAULT_INTENT_PENDING[2],
    "interaction": DEFAULT_INTENT_PENDING[3],
}

INTENT_SUMMARY_FIELDS = [
    "topic",
    "audience",
    "goal",
    "duration",
    "constraints",
    "style",
    "interaction",
    "extra",
]


def clamp_score(value: Any, default: int) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = default
    return max(0, min(100, score))


def safe_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def safe_list_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = safe_text(item)
        if text:
            result.append(text)
    return result


def ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = safe_text(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def build_empty_summary(initial_topic: str | None = None) -> dict[str, str]:
    summary = {field: "" for field in INTENT_SUMMARY_FIELDS}
    if initial_topic:
        summary["topic"] = initial_topic
    return summary


def normalize_intent_summary(raw: Any, fallback_topic: str | None = None) -> dict[str, str]:
    summary = build_empty_summary(fallback_topic)
    if isinstance(raw, dict):
        for field in INTENT_SUMMARY_FIELDS:
            summary[field] = safe_text(raw.get(field)) or summary[field]
    return summary


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def infer_intent_coverage(confirmed: list[str], summary: dict[str, str]) -> dict[str, bool]:
    merged_text = "\n".join(ordered_unique(confirmed))
    structure_text = "\n".join(
        text for text in [summary.get("duration", ""), summary.get("constraints", ""), merged_text] if text
    )
    interaction_text = "\n".join(
        text for text in [summary.get("interaction", ""), summary.get("constraints", ""), merged_text] if text
    )

    return {
        "audience": bool(summary.get("audience")) or contains_any(merged_text, ["受众", "年级", "学生", "基础", "零基础"]),
        "goal": bool(summary.get("goal")) or contains_any(merged_text, ["目标", "学习目标", "达成", "掌握", "学会", "理解"]),
        "structure": (
            bool(summary.get("duration"))
            or bool(summary.get("constraints"))
            or contains_any(structure_text, ["结构", "章节", "节奏", "课时", "时长", "页数", "页", "分钟", "节课", "时间"])
            or bool(re.search(r"\d+\s*页", structure_text))
            or bool(re.search(r"\d+\s*分钟", structure_text))
        ),
        "interaction": bool(summary.get("interaction")) or contains_any(interaction_text, ["互动", "提问", "讨论", "分享", "练习", "活动", "限制", "约束", "形式"]),
    }


def infer_pending_items(confirmed: list[str], summary: dict[str, str]) -> list[str]:
    coverage = infer_intent_coverage(confirmed, summary)
    return [label for key, label in INTENT_DIMENSIONS.items() if not coverage[key]]


def normalize_scores(raw: Any) -> dict[str, int]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "goal": clamp_score(source.get("goal"), DEFAULT_INTENT_SCORES["goal"]),
        "audience": clamp_score(source.get("audience"), DEFAULT_INTENT_SCORES["audience"]),
        "structure": clamp_score(source.get("structure"), DEFAULT_INTENT_SCORES["structure"]),
        "interaction": clamp_score(source.get("interaction"), DEFAULT_INTENT_SCORES["interaction"]),
    }


def is_summary_complete(summary: dict[str, str]) -> bool:
    required_fields = ["topic", "audience", "goal", "duration", "constraints", "style", "interaction"]
    return all(bool(summary.get(field)) for field in required_fields)


def create_intent_state(initial_topic: str | None = None) -> dict[str, Any]:
    summary = build_empty_summary(initial_topic)
    pending = infer_pending_items([], summary)
    return {
        "status": INTENT_STATUS_CLARIFYING,
        "confirmed": [],
        "pending": pending or DEFAULT_INTENT_PENDING.copy(),
        "scores": DEFAULT_INTENT_SCORES.copy(),
        "confidence": 35,
        "ready_for_confirmation": False,
        "summary": "继续澄清中",
        "intent_summary": summary,
        "round": 0,
        "confirmed_at": None,
    }


def parse_intent_response(raw_response: str, fallback_topic: str | None = None) -> tuple[str, dict[str, Any]]:
    raw_text = (raw_response or "").strip()
    fallback_state = create_intent_state(fallback_topic)

    candidates: list[str] = []
    code_blocks = re.findall(r"```json\s*([\s\S]*?)```", raw_text, flags=re.IGNORECASE)
    candidates.extend(code_blocks)

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidates.append(raw_text[start : end + 1])

    parsed: dict[str, Any] | None = None
    for candidate in candidates:
        try:
            parsed_obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed_obj, dict):
            parsed = parsed_obj
            break

    if not parsed:
        return raw_text, fallback_state

    state_obj = parsed.get("intent_state") if isinstance(parsed.get("intent_state"), dict) else parsed
    reply = safe_text(parsed.get("reply") or parsed.get("message") or state_obj.get("reply")) or raw_text

    confirmed = safe_list_text(state_obj.get("confirmed"))
    summary = normalize_intent_summary(parsed.get("intent_summary"), fallback_topic)
    pending = infer_pending_items(confirmed, summary)
    scores = normalize_scores(state_obj.get("scores"))
    confidence = clamp_score(state_obj.get("confidence"), 50)
    summary_text = safe_text(state_obj.get("summary")) or "继续澄清中"

    ready_hint = any(text in f"{reply}\n{summary_text}" for text in ["确认意图", "确认无误", "可以确认", "请确认"])
    ready_for_confirmation = bool(
        state_obj.get("ready_for_confirmation")
        or (ready_hint and not pending)
        or (not pending and is_summary_complete(summary))
    )
    status = INTENT_STATUS_READY if ready_for_confirmation else INTENT_STATUS_CLARIFYING

    if pending:
        ready_for_confirmation = False
        status = INTENT_STATUS_CLARIFYING

    return reply, {
        "status": status,
        "confirmed": ordered_unique(confirmed),
        "pending": pending,
        "scores": scores,
        "confidence": confidence,
        "ready_for_confirmation": ready_for_confirmation,
        "summary": summary_text,
        "intent_summary": summary,
    }


def merge_intent_state(existing: dict[str, Any] | None, incoming: dict[str, Any], fallback_topic: str | None = None) -> dict[str, Any]:
    existing_state = existing or create_intent_state(fallback_topic)
    existing_summary = normalize_intent_summary(existing_state.get("intent_summary"), fallback_topic)
    incoming_summary = normalize_intent_summary(incoming.get("intent_summary"), fallback_topic)

    summary = {
        field: incoming_summary.get(field) or existing_summary.get(field) or ""
        for field in INTENT_SUMMARY_FIELDS
    }

    confirmed = ordered_unique(
        safe_list_text(existing_state.get("confirmed")) + safe_list_text(incoming.get("confirmed"))
    )
    pending = infer_pending_items(confirmed, summary)
    ready_for_confirmation = not pending and is_summary_complete(summary)

    if existing_state.get("status") == INTENT_STATUS_CONFIRMED:
        status = INTENT_STATUS_CONFIRMED
    elif incoming.get("status") == INTENT_STATUS_CONFIRMED:
        status = INTENT_STATUS_CONFIRMED
    else:
        status = INTENT_STATUS_READY if ready_for_confirmation else INTENT_STATUS_CLARIFYING

    confirmed_at = existing_state.get("confirmed_at") or incoming.get("confirmed_at")
    if status != INTENT_STATUS_CONFIRMED:
        confirmed_at = None

    return {
        "status": status,
        "confirmed": confirmed,
        "pending": pending,
        "scores": normalize_scores(incoming.get("scores") or existing_state.get("scores")),
        "confidence": clamp_score(incoming.get("confidence"), clamp_score(existing_state.get("confidence"), 35)),
        "ready_for_confirmation": status in {INTENT_STATUS_READY, INTENT_STATUS_CONFIRMED},
        "summary": safe_text(incoming.get("summary")) or safe_text(existing_state.get("summary")) or "继续澄清中",
        "intent_summary": summary,
        "round": max(int(existing_state.get("round") or 0), int(incoming.get("round") or 0)),
        "confirmed_at": confirmed_at,
    }


def confirm_intent_state(intent_state: dict[str, Any]) -> dict[str, Any]:
    merged = merge_intent_state(intent_state, intent_state, fallback_topic=intent_state.get("intent_summary", {}).get("topic"))
    if merged.get("pending"):
        raise ValueError("意图仍有待确认要点，暂时不能确认")
    merged["status"] = INTENT_STATUS_CONFIRMED
    merged["ready_for_confirmation"] = True
    merged["confirmed_at"] = datetime.now(timezone.utc)
    return merged


def serialize_intent_record(intent: Any) -> dict[str, Any]:
    summary = normalize_intent_summary(
        {
            "topic": intent.topic,
            "audience": intent.audience,
            "goal": intent.goal,
            "duration": intent.duration,
            "constraints": intent.constraints,
            "style": intent.style,
            "interaction": intent.interaction,
            "extra": intent.extra,
        }
    )
    scores = {
        "goal": clamp_score(intent.score_goal, DEFAULT_INTENT_SCORES["goal"]),
        "audience": clamp_score(intent.score_audience, DEFAULT_INTENT_SCORES["audience"]),
        "structure": clamp_score(intent.score_structure, DEFAULT_INTENT_SCORES["structure"]),
        "interaction": clamp_score(intent.score_interaction, DEFAULT_INTENT_SCORES["interaction"]),
    }
    status = safe_text(intent.status) or INTENT_STATUS_CLARIFYING
    pending = safe_list_text(intent.pending_items)
    confirmed = ordered_unique(safe_list_text(intent.confirmed_points))
    if not pending:
        pending = infer_pending_items(confirmed, summary)
        if status != INTENT_STATUS_CONFIRMED:
            status = INTENT_STATUS_READY if not pending and is_summary_complete(summary) else INTENT_STATUS_CLARIFYING

    return {
        "status": status,
        "confirmed": confirmed,
        "pending": pending,
        "scores": scores,
        "confidence": clamp_score(intent.confidence, 35),
        "ready_for_confirmation": status in {INTENT_STATUS_READY, INTENT_STATUS_CONFIRMED},
        "summary": safe_text(intent.summary_text) or "继续澄清中",
        "intent_summary": summary,
        "round": int(intent.clarification_round or 0),
        "confirmed_at": intent.confirmed_at.isoformat() if getattr(intent, "confirmed_at", None) else None,
    }


def apply_intent_state_to_record(intent: Any, intent_state: dict[str, Any], *, round_number: int, source_session_id: int | None = None) -> Any:
    summary = normalize_intent_summary(intent_state.get("intent_summary"))
    scores = normalize_scores(intent_state.get("scores"))

    intent.topic = summary["topic"] or None
    intent.audience = summary["audience"] or None
    intent.goal = summary["goal"] or None
    intent.duration = summary["duration"] or None
    intent.constraints = summary["constraints"] or None
    intent.style = summary["style"] or None
    intent.interaction = summary["interaction"] or None
    intent.extra = summary["extra"] or None

    intent.confirmed_points = ordered_unique(safe_list_text(intent_state.get("confirmed")))
    intent.pending_items = safe_list_text(intent_state.get("pending"))
    intent.score_goal = scores["goal"]
    intent.score_audience = scores["audience"]
    intent.score_structure = scores["structure"]
    intent.score_interaction = scores["interaction"]
    intent.confidence = clamp_score(intent_state.get("confidence"), 35)
    intent.summary_text = safe_text(intent_state.get("summary"))
    intent.status = safe_text(intent_state.get("status")) or INTENT_STATUS_CLARIFYING
    intent.clarification_round = int(round_number)
    intent.last_source_session_id = source_session_id
    intent.confirmed_at = intent_state.get("confirmed_at")
    return intent


def build_session_intent_metadata(intent_state: dict[str, Any]) -> dict[str, Any]:
    confirmed_at = intent_state.get("confirmed_at")
    if isinstance(confirmed_at, datetime):
        confirmed_at = confirmed_at.isoformat()
    return {
        "intent_state": {
            "status": intent_state.get("status"),
            "confirmed": ordered_unique(safe_list_text(intent_state.get("confirmed"))),
            "pending": safe_list_text(intent_state.get("pending")),
            "scores": normalize_scores(intent_state.get("scores")),
            "confidence": clamp_score(intent_state.get("confidence"), 35),
            "ready_for_confirmation": bool(intent_state.get("ready_for_confirmation")),
            "summary": safe_text(intent_state.get("summary")) or "继续澄清中",
            "intent_summary": normalize_intent_summary(intent_state.get("intent_summary")),
            "round": int(intent_state.get("round") or 0),
            "confirmed_at": confirmed_at,
        }
    }
