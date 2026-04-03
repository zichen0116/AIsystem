"""
PPT生成模块 - AI Providers
将 banana-slides 的 AI provider 体系适配到 AIsystem (FastAPI + asyncio)

支持的 Provider：
  gemini   — Google AI Studio / Vertex AI (GenAI SDK)
  openai   — OpenAI 兼容接口（含代理）
  anthropic — Anthropic Claude API

配置来源：app/core/config.py (Settings)
"""
import io
import re
import logging
import asyncio
import urllib.request
import base64
from abc import ABC, abstractmethod
from typing import Optional, List, Generator, AsyncGenerator

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def strip_think_tags(text: str) -> str:
    """移除 <think>...</think> 块"""
    if not text:
        return text
    return re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL).strip()


def _decode_data_uri_image(data_uri: str) -> Optional[bytes]:
    """Decode data:image/...;base64,... URI into bytes."""
    if not data_uri or not data_uri.startswith("data:image/"):
        return None
    try:
        _, b64_data = data_uri.split(",", 1)
        return base64.b64decode(b64_data)
    except Exception:
        return None


def _download_http_bytes(url: str) -> Optional[bytes]:
    """Download bytes from a HTTP/HTTPS URL."""
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return None
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except Exception:
        return None


def _extract_image_url_from_text(text: str) -> Optional[str]:
    """Extract image URL or data URI from text/markdown."""
    if not text:
        return None

    md_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", text)
    if md_match:
        return md_match.group(1).strip()

    data_uri_match = re.search(r"(data:image/[^;]+;base64,[A-Za-z0-9+/=]+)", text)
    if data_uri_match:
        return data_uri_match.group(1).strip()

    url_match = re.search(r"(https?://[^\s)\"']+)", text)
    if url_match:
        return url_match.group(1).strip()
    return None


# ─────────────────────────────────────────────
# 抽象基类
# ─────────────────────────────────────────────

class TextProvider(ABC):
    """文本生成 Provider 抽象基类"""

    @abstractmethod
    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        pass

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        """默认实现：退化为非流式"""
        yield self.generate_text(prompt, thinking_budget=thinking_budget)

    async def agenerate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        """异步包装，在线程池中运行同步方法"""
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.generate_text(prompt, thinking_budget=thinking_budget)
        )

    async def agenerate_text_stream(self, prompt: str, thinking_budget: int = 0) -> AsyncGenerator[str, None]:
        """异步流式包装"""
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        def _stream():
            try:
                for chunk in self.generate_text_stream(prompt, thinking_budget=thinking_budget):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        loop.run_in_executor(None, _stream)
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            yield item


class ImageProvider(ABC):
    """图片生成 Provider 抽象基类"""

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        ref_images: Optional[List[bytes]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = False,
        thinking_budget: int = 0,
    ) -> bytes:
        """
        生成图片并返回 PNG 字节数据。

        Args:
            prompt: 图片生成提示词
            ref_images: 参考图片字节列表（PIL 可读的格式）
            aspect_ratio: 宽高比，如 "16:9" / "4:3" / "1:1"
            resolution: 分辨率 "1K" / "2K" / "4K"
            enable_thinking: 是否启用思维链（GenAI 专用）
            thinking_budget: 思维链 token 预算（GenAI 专用）

        Returns:
            图片 PNG 字节数据
        """
        pass

    async def agenerate_image(
        self,
        prompt: str,
        ref_images: Optional[List[bytes]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = False,
        thinking_budget: int = 0,
    ) -> bytes:
        """异步包装，在线程池中运行同步方法"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.generate_image(
                prompt,
                ref_images=ref_images,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                enable_thinking=enable_thinking,
                thinking_budget=thinking_budget,
            ),
        )


# ─────────────────────────────────────────────
# GenAI (Google Gemini) Text Provider
# ─────────────────────────────────────────────

class GenAITextProvider(TextProvider):
    """Google GenAI SDK 文本生成"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "gemini-2.0-flash-preview-image-generation"):
        from google import genai
        self.model = model
        client_kwargs = {"api_key": api_key}
        if api_base:
            client_kwargs["http_options"] = {"base_url": api_base}
        self.client = genai.Client(**client_kwargs)

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        from google.genai import types
        config_params = {}
        if thinking_budget > 0:
            config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_params) if config_params else None,
        )
        if response.text is None:
            raise ValueError("GenAI 返回空响应")
        return strip_think_tags(response.text)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        from google.genai import types
        config_params = {}
        if thinking_budget > 0:
            config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_params) if config_params else None,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text


# ─────────────────────────────────────────────
# GenAI (Google Gemini) Image Provider
# ─────────────────────────────────────────────

_ASPECT_RATIO_MAP = {
    "16:9": "16:9",
    "4:3": "4:3",
    "1:1": "1:1",
    "9:16": "9:16",
    "3:4": "3:4",
}

_RESOLUTION_MAP = {
    "1K": 1024,
    "2K": 2048,
    "4K": 4096,
}


class GenAIImageProvider(ImageProvider):
    """Google GenAI SDK 图片生成"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "gemini-2.0-flash-preview-image-generation"):
        from google import genai
        self.model = model
        client_kwargs = {"api_key": api_key}
        if api_base:
            client_kwargs["http_options"] = {"base_url": api_base}
        self.client = genai.Client(**client_kwargs)

    def generate_image(
        self,
        prompt: str,
        ref_images: Optional[List[bytes]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = False,
        thinking_budget: int = 1024,
    ) -> bytes:
        from google.genai import types
        from PIL import Image as PILImage

        contents = []

        # 加入参考图片
        if ref_images:
            for img_bytes in ref_images:
                pil_img = PILImage.open(io.BytesIO(img_bytes))
                contents.append(pil_img)

        contents.append(prompt)

        config_params: dict = {
            "response_modalities": ["IMAGE", "TEXT"],
        }
        ar = _ASPECT_RATIO_MAP.get(aspect_ratio, "16:9")
        image_size = resolution if resolution in _RESOLUTION_MAP else "2K"
        config_params["image_config"] = types.ImageConfig(
            aspect_ratio=ar,
            image_size=image_size,
        )
        if enable_thinking and thinking_budget > 0:
            config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(**config_params),
        )

        image_bytes = self._extract_image_from_generate_content_response(response)
        if image_bytes:
            return image_bytes

        # 某些模型/中转会通过 generate_images 返回结构，作为兼容回退
        # 注意：该接口不支持参考图，因此仅在纯文生图时回退。
        if not ref_images:
            try:
                gen_images_resp = self.client.models.generate_images(
                    model=self.model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        aspect_ratio=ar,
                        image_size=image_size,
                        number_of_images=1,
                    ),
                )
                image_bytes = self._extract_image_from_generate_images_response(gen_images_resp)
                if image_bytes:
                    return image_bytes
            except Exception as e:
                logger.warning("GenAI generate_images 回退失败 model=%s: %s", self.model, e)

        text_preview = ((getattr(response, "text", None) or "")[:240]).replace("\n", " ")
        raise ValueError(f"GenAI响应中未找到图片（model={self.model}，text={text_preview}）")

    def _extract_image_from_generate_content_response(self, response) -> Optional[bytes]:
        # 1) response.parts
        response_parts = list(response.parts or [])
        # 2) response.candidates[].content.parts
        if not response_parts:
            for candidate in (response.candidates or []):
                candidate_content = getattr(candidate, "content", None)
                response_parts.extend(getattr(candidate_content, "parts", None) or [])

        last_image_bytes = None
        for part in response_parts:
            image_bytes = self._extract_image_from_part(part)
            if image_bytes:
                last_image_bytes = image_bytes

        if last_image_bytes:
            return last_image_bytes

        # 3) 从文本中提取 url/data-uri
        text = getattr(response, "text", None) or ""
        text_image_url = _extract_image_url_from_text(text)
        if text_image_url:
            return _decode_data_uri_image(text_image_url) or _download_http_bytes(text_image_url)

        return None

    def _extract_image_from_part(self, part) -> Optional[bytes]:
        from PIL import Image as PILImage

        # as_image() 在新版 SDK 中可直接取图
        if hasattr(part, "as_image"):
            try:
                maybe_image = part.as_image()
                if maybe_image is not None:
                    if isinstance(maybe_image, PILImage.Image):
                        buf = io.BytesIO()
                        maybe_image.save(buf, format="PNG")
                        return buf.getvalue()
                    image_bytes = getattr(maybe_image, "image_bytes", None)
                    if image_bytes:
                        return bytes(image_bytes)
                    pil_image = getattr(maybe_image, "_pil_image", None)
                    if isinstance(pil_image, PILImage.Image):
                        buf = io.BytesIO()
                        pil_image.save(buf, format="PNG")
                        return buf.getvalue()
            except Exception:
                pass

        inline_data = getattr(part, "inline_data", None)
        if inline_data and getattr(inline_data, "data", None):
            try:
                raw = bytes(inline_data.data)
                # 尝试验证可读图像
                PILImage.open(io.BytesIO(raw))
                return raw
            except Exception:
                return None

        file_data = getattr(part, "file_data", None)
        if file_data:
            uri = str(getattr(file_data, "file_uri", "") or "")
            if uri:
                return _decode_data_uri_image(uri) or _download_http_bytes(uri)
        return None

    def _extract_image_from_generate_images_response(self, response) -> Optional[bytes]:
        generated_images = getattr(response, "generated_images", None) or []
        for item in generated_images:
            image_obj = getattr(item, "image", None)
            if not image_obj:
                continue
            image_bytes = getattr(image_obj, "image_bytes", None)
            if image_bytes:
                return bytes(image_bytes)
            gcs_uri = str(getattr(image_obj, "gcs_uri", "") or "")
            if gcs_uri:
                downloaded = _download_http_bytes(gcs_uri)
                if downloaded:
                    return downloaded
        return None


# ─────────────────────────────────────────────
# OpenAI-compatible Text Provider
# ─────────────────────────────────────────────

class OpenAITextProvider(TextProvider):
    """OpenAI SDK 文本生成（兼容代理接口）"""

    def __init__(self, api_key: str, api_base: str = None, model: str = "gpt-4o"):
        from openai import OpenAI
        settings = get_settings()
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=settings.GENAI_TIMEOUT,
            max_retries=settings.GENAI_MAX_RETRIES,
        )
        self.model = model

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return strip_think_tags(response.choices[0].message.content)

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


# ─────────────────────────────────────────────
# OpenAI-compatible Image Provider
# ─────────────────────────────────────────────

class OpenAIImageProvider(ImageProvider):
    """
    OpenAI SDK 图片生成（兼容 Gemini 代理等多模态接口）

    通过 chat.completions 发送图文请求，从响应中提取内嵌图片。
    """

    def __init__(self, api_key: str, api_base: str = None, model: str = "gemini-2.0-flash-preview-image-generation"):
        from openai import OpenAI
        settings = get_settings()
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=settings.GENAI_TIMEOUT,
            max_retries=settings.GENAI_MAX_RETRIES,
        )
        self.model = model

    def generate_image(
        self,
        prompt: str,
        ref_images: Optional[List[bytes]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = False,
        thinking_budget: int = 0,
    ) -> bytes:
        import base64
        from PIL import Image as PILImage

        content: list = [{"type": "text", "text": prompt}]

        if ref_images:
            for img_bytes in ref_images:
                b64 = base64.b64encode(img_bytes).decode("ascii")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })

        extra_body: dict = {
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        }

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            extra_body=extra_body,
        )

        message = response.choices[0].message
        msg_content = message.content

        # 尝试从多模态响应中提取图片
        if isinstance(msg_content, list):
            for item in msg_content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    url = item["image_url"]["url"]
                    if url.startswith("data:"):
                        b64_data = url.split(",", 1)[1]
                        return base64.b64decode(b64_data)

        # 尝试从字符串中提取 base64 图片
        if isinstance(msg_content, str):
            match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', msg_content)
            if match:
                return base64.b64decode(match.group(1))

        raise ValueError("OpenAI 响应中未找到图片数据")


# ─────────────────────────────────────────────
# Anthropic Text Provider
# ─────────────────────────────────────────────

class AnthropicTextProvider(TextProvider):
    """Anthropic Claude API 文本生成"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        if thinking_budget > 0:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        message = self.client.messages.create(**kwargs)
        parts = [block.text for block in message.content if hasattr(block, 'text')]
        return strip_think_tags("\n".join(parts))

    def generate_text_stream(self, prompt: str, thinking_budget: int = 0) -> Generator[str, None, None]:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text


# ─────────────────────────────────────────────
# Provider 工厂函数
# ─────────────────────────────────────────────

def get_text_provider() -> TextProvider:
    """
    根据 Settings.AI_PROVIDER_FORMAT 返回对应的文本生成 Provider。

    支持：gemini / openai / anthropic
    """
    settings = get_settings()
    fmt = (settings.AI_PROVIDER_FORMAT or "gemini").lower()
    model = settings.TEXT_MODEL

    if fmt == "openai":
        api_key = settings.OPENAI_API_KEY
        model = model or "gpt-4o"
        logger.info("TextProvider: OpenAI, model=%s", model)
        return OpenAITextProvider(api_key=api_key, model=model)

    if fmt == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY
        model = model or "claude-sonnet-4-6"
        logger.info("TextProvider: Anthropic, model=%s", model)
        return AnthropicTextProvider(api_key=api_key, model=model)

    # 默认 gemini
    api_key = settings.GOOGLE_API_KEY
    api_base = settings.GOOGLE_API_BASE or None
    model = model or "gemini-2.0-flash"
    logger.info("TextProvider: GenAI (Gemini), model=%s", model)
    return GenAITextProvider(api_key=api_key, api_base=api_base, model=model)


def get_image_provider() -> ImageProvider:
    """
    根据 Settings.AI_PROVIDER_FORMAT 返回对应的图片生成 Provider。

    支持：gemini / openai
    注意：Anthropic 目前不支持直接生成 PPT 页面图片，回退到 GenAI。
    """
    settings = get_settings()
    fmt = (settings.AI_PROVIDER_FORMAT or "gemini").lower()
    model = settings.IMAGE_MODEL

    if fmt == "openai":
        api_key = settings.OPENAI_API_KEY
        model = model or "gemini-2.0-flash-preview-image-generation"
        logger.info("ImageProvider: OpenAI-compat, model=%s", model)
        return OpenAIImageProvider(api_key=api_key, model=model)

    # 默认 gemini（anthropic 也回退到 gemini）
    api_key = settings.GOOGLE_API_KEY
    api_base = settings.GOOGLE_API_BASE or None
    model = model or "gemini-2.0-flash-preview-image-generation"
    logger.info("ImageProvider: GenAI (Gemini), model=%s", model)
    return GenAIImageProvider(api_key=api_key, api_base=api_base, model=model)


# ─────────────────────────────────────────────
# 单例缓存
# ─────────────────────────────────────────────

_text_provider: Optional[TextProvider] = None
_image_provider: Optional[ImageProvider] = None


def get_text_provider_singleton() -> TextProvider:
    """获取 TextProvider 单例（进程级，懒加载）"""
    global _text_provider
    if _text_provider is None:
        _text_provider = get_text_provider()
    return _text_provider


def get_image_provider_singleton() -> ImageProvider:
    """获取 ImageProvider 单例（进程级，懒加载）"""
    global _image_provider
    if _image_provider is None:
        _image_provider = get_image_provider()
    return _image_provider
