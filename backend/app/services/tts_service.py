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
DEFAULT_MODEL = "qwen3-tts-flash"
DEFAULT_VOICE = "Cherry"


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
    payload = {
        "model": DEFAULT_MODEL,
        "input": {
            "text": text,
            "voice": voice,
            "language_type": "Chinese",
        },
        "parameters": {
            "rate": _speed_to_rate(speed),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. 调用 TTS API
            resp = await client.post(DASHSCOPE_TTS_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            temp_url = data.get("output", {}).get("audio", {}).get("url")

            if not temp_url:
                logger.warning(f"TTS response missing audio URL: {data}")
                return result

            result["temp_audio_url"] = temp_url
            result["audio_status"] = "temp_ready"

            # 2. 下载音频并持久化到 OSS
            if persist and user_id:
                try:
                    audio_resp = await client.get(temp_url, timeout=30.0)
                    audio_resp.raise_for_status()
                    audio_bytes = audio_resp.content
                    persistent_url = await upload_bytes(audio_bytes, "wav", user_id, "rehearsal-audio")
                    result["persistent_audio_url"] = persistent_url
                    result["audio_status"] = "ready"
                    logger.info(f"TTS persisted: {len(text)} chars -> {persistent_url[:80]}...")
                except Exception as e:
                    logger.warning(f"TTS audio persist failed (temp URL still usable): {e}")
                    # 保持 temp_ready 状态

            return result

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return result


def estimate_duration_ms(text: str, speed: float = 1.0) -> int:
    """估算文本阅读时长（毫秒），用于无音频时的计时播放。"""
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    non_cjk_text = ''.join(c for c in text if not ('\u4e00' <= c <= '\u9fff'))
    word_count = len(non_cjk_text.split())
    duration = max(cjk_count * 150 + word_count * 240, 2000)
    return int(duration / speed)
