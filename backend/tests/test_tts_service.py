import httpx
import pytest

from app.services import tts_service


class _FakeResponse:
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data
        self.text = str(data)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", tts_service.DASHSCOPE_TTS_URL)
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("bad request", request=request, response=response)

    def json(self):
        return self._data


class _FakeAudioResponse:
    def __init__(self):
        self.content = b"audio-bytes"

    def raise_for_status(self):
        return None


@pytest.mark.asyncio
async def test_synthesize_fallback_to_flash_model(monkeypatch):
    calls = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            calls.append((json["model"], json["input"]["voice"]))
            if json["model"] != "qwen3-tts-flash":
                return _FakeResponse(400, {"code": "InvalidParameter"})
            return _FakeResponse(200, {"output": {"audio": {"url": "https://audio.example/ok.wav"}}})

        async def get(self, url, timeout):
            return _FakeAudioResponse()

    monkeypatch.setattr(tts_service.httpx, "AsyncClient", lambda timeout: FakeClient())
    monkeypatch.setattr(tts_service.settings, "DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(tts_service.settings, "TTS_MODEL", "bad-model")
    monkeypatch.setattr(tts_service.settings, "TTS_VOICE", "Cherry")

    result = await tts_service.synthesize(
        text="测试文本",
        voice="Cherry",
        speed=1.0,
        user_id=0,
        persist=False,
    )

    assert result["audio_status"] == "temp_ready"
    assert result["temp_audio_url"] == "https://audio.example/ok.wav"
    assert any(model == "qwen3-tts-flash" for model, _ in calls)


@pytest.mark.asyncio
async def test_synthesize_fallback_to_default_voice(monkeypatch):
    calls = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            calls.append((json["model"], json["input"]["voice"]))
            if json["input"]["voice"] != "Cherry":
                return _FakeResponse(400, {"code": "InvalidParameter"})
            return _FakeResponse(200, {"output": {"audio": {"url": "https://audio.example/cherry.wav"}}})

        async def get(self, url, timeout):
            return _FakeAudioResponse()

    monkeypatch.setattr(tts_service.httpx, "AsyncClient", lambda timeout: FakeClient())
    monkeypatch.setattr(tts_service.settings, "DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(tts_service.settings, "TTS_MODEL", "qwen3-tts-flash")
    monkeypatch.setattr(tts_service.settings, "TTS_VOICE", "Cherry")

    result = await tts_service.synthesize(
        text="测试文本",
        voice="not-exists-voice",
        speed=1.0,
        user_id=0,
        persist=False,
    )

    assert result["audio_status"] == "temp_ready"
    assert result["temp_audio_url"] == "https://audio.example/cherry.wav"
    assert calls[0][1] == "not-exists-voice"
    assert any(voice == "Cherry" for _, voice in calls)
