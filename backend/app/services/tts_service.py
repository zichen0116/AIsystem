"""
Qwen TTS 轻量封装 — 单 provider，不做多 provider 架构。
调用阿里云百炼 DashScope multimodal-generation 接口。
TTS 失败时返回 None，调用方降级为计时播放。
音频持久化到 OSS，返回持久 URL。
"""
import logging
import httpx

from app.core.config import get_settings
from app.services.oss_service import upload_bytes

logger = logging.getLogger(__name__)
settings = get_settings()

DASHSCOPE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
FALLBACK_MODEL = "qwen3-tts-flash"
FALLBACK_VOICE = "Cherry"
DEFAULT_MODEL = settings.TTS_MODEL or FALLBACK_MODEL
DEFAULT_VOICE = settings.TTS_VOICE or FALLBACK_VOICE


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _build_tts_candidates(voice: str) -> list[tuple[str, str]]:
    model_candidates = _dedupe_keep_order([
        settings.TTS_MODEL,
        DEFAULT_MODEL,
        FALLBACK_MODEL,
    ])
    voice_candidates = _dedupe_keep_order([
        voice,
        settings.TTS_VOICE,
        DEFAULT_VOICE,
        FALLBACK_VOICE,
    ])

    pairs: list[tuple[str, str]] = []
    seen_pairs = set()
    for model in model_candidates:
        for candidate_voice in voice_candidates:
            pair = (model, candidate_voice)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            pairs.append(pair)
    return pairs


def _speed_to_rate(speed: float) -> int:
    """将播放速度 (0.5-2.0) 转换为 DashScope rate 参数 (-500 to 500)。"""
    return round((speed - 1.0) * 500)


async def synthesize(
    text: str,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    user_id: int = 0,
    persist: bool = True,
) -> dict:
    """
    合成语音。返回:
    {
        "temp_audio_url": str | None,      # DashScope 返回的临时 URL（约24h有效）
        "persistent_audio_url": str | None, # OSS 持久 URL
        "audio_status": "temp_ready" | "ready" | "failed",
        "duration": int,                    # 预估时长 ms
    }
    """
    duration = estimate_duration_ms(text, speed)
    result = {
        "temp_audio_url": None,
        "persistent_audio_url": None,
        "audio_status": "failed",
        "duration": duration,
    }

    if not settings.DASHSCOPE_API_KEY:
        logger.warning("DASHSCOPE_API_KEY not set, skipping TTS")
        return result

    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    candidates = _build_tts_candidates(voice)

    async with httpx.AsyncClient(timeout=60.0) as client:
        last_error: Exception | None = None
        for idx, (candidate_model, candidate_voice) in enumerate(candidates, start=1):
            payload = {
                "model": candidate_model,
                "input": {
                    "text": text,
                    "voice": candidate_voice,
                    "language_type": "Chinese",
                },
                "parameters": {
                    "rate": _speed_to_rate(speed),
                },
            }
            try:
                resp = await client.post(DASHSCOPE_TTS_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                temp_url = data.get("output", {}).get("audio", {}).get("url")

                if not temp_url:
                    logger.warning(
                        "TTS response missing audio URL model=%s voice=%s: %s",
                        candidate_model,
                        candidate_voice,
                        data,
                    )
                    continue

                result["temp_audio_url"] = temp_url
                result["audio_status"] = "temp_ready"
                logger.info(
                    "TTS temporary audio ready: model=%s voice=%s temp_audio_url=%s",
                    candidate_model,
                    candidate_voice,
                    temp_url,
                )

                # 2. 下载音频并持久化到 OSS
                if persist and user_id:
                    try:
                        audio_resp = await client.get(temp_url, timeout=30.0)
                        audio_resp.raise_for_status()
                        audio_bytes = audio_resp.content
                        persistent_url = await upload_bytes(audio_bytes, "wav", user_id, "rehearsal-audio")
                        result["persistent_audio_url"] = persistent_url
                        result["audio_status"] = "ready"
                        logger.info(
                            "TTS persisted: model=%s voice=%s persistent_audio_url=%s temp_audio_url=%s",
                            candidate_model,
                            candidate_voice,
                            persistent_url,
                            temp_url,
                        )
                    except Exception as e:
                        logger.warning(
                            "TTS audio persist failed (temp URL still usable): model=%s voice=%s err=%s temp_audio_url=%s",
                            candidate_model,
                            candidate_voice,
                            e,
                            temp_url,
                        )
                        # 保持 temp_ready 状态

                if idx > 1:
                    logger.info(
                        "TTS fallback succeeded after retries: attempts=%s final_model=%s final_voice=%s",
                        idx,
                        candidate_model,
                        candidate_voice,
                    )
                return result

            except Exception as e:
                last_error = e
                if isinstance(e, httpx.HTTPStatusError):
                    body_preview = e.response.text[:300] if e.response is not None else ""
                    logger.warning(
                        "TTS attempt failed: model=%s voice=%s status=%s body=%s",
                        candidate_model,
                        candidate_voice,
                        e.response.status_code if e.response is not None else "unknown",
                        body_preview,
                    )
                else:
                    logger.warning(
                        "TTS attempt failed: model=%s voice=%s err=%s",
                        candidate_model,
                        candidate_voice,
                        e,
                    )
                continue

        logger.error("TTS synthesis failed after %s attempts: %s", len(candidates), last_error)
        return result


def estimate_duration_ms(text: str, speed: float = 1.0) -> int:
    """估算文本阅读时长（毫秒），用于无音频时的计时播放。"""
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    non_cjk_text = ''.join(c for c in text if not ('\u4e00' <= c <= '\u9fff'))
    word_count = len(non_cjk_text.split())
    duration = max(cjk_count * 150 + word_count * 240, 2000)
    return int(duration / speed)
