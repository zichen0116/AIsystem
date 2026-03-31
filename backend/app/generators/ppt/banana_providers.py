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
        config_params["image_generation_config"] = types.ImageGenerationConfig(
            aspect_ratio=ar,
            number_of_images=1,
        )
        if enable_thinking and thinking_budget > 0:
            config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(**config_params),
        )

        last_image: Optional[PILImage.Image] = None
        for part in (response.parts or []):
            try:
                if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                    img = PILImage.open(io.BytesIO(part.inline_data.data))
                    last_image = img
                elif hasattr(part, 'file_data') and part.file_data:
                    import base64
                    raw = base64.b64decode(part.file_data.file_uri)
                    img = PILImage.open(io.BytesIO(raw))
                    last_image = img
            except Exception as e:
                logger.warning(f"GenAI 图片解析失败: {e}")

        if last_image is None:
            raise ValueError("GenAI 响应中未找到图片")

        buf = io.BytesIO()
        last_image.save(buf, format="PNG")
        return buf.getvalue()


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
