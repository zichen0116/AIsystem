"""
阿里云百炼视觉理解服务
用于分析图片内容，生成描述文本
"""
import os
import base64
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 阿里云百炼 API 地址
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"


class VisionService:
    """
    视觉理解服务

    使用 qwen-vl-plus 模型分析图片内容
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = os.getenv("VISION_MODEL", "qwen-vl-plus")
        self.base_url = DASHSCOPE_BASE_URL

        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY")

    async def describe_image(
        self,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """
        分析图片内容并生成描述

        Args:
            image_path: 本地图片路径
            image_url: 图片 URL（二选一）
            prompt: 自定义提示词

        Returns:
            str: 图片描述文本
        """
        if not self.api_key:
            return "错误: 未配置 DASHSCOPE_API_KEY"

        if not image_path and not image_url:
            raise ValueError("需要提供 image_path 或 image_url")

        # 构建提示词
        if prompt is None:
            prompt = (
                "请详细分析并描述这张图片的内容。"
                "如果是教学幻灯片、板书或教材，请完整提取其中的文字、数学公式、图表标题及其核心知识点。"
            )

        # 准备图片数据
        image_data = None
        if image_url:
            image_data = image_url
        elif image_path:
            image_data = await self._encode_image_to_base64(image_path)
            if not image_data:
                logger.error(f"图片编码失败: {image_path}")
                return "图片编码失败"

        # 调用视觉模型
        return await self._call_vision_api(image_data, prompt)

    async def describe_video_frame(
        self,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        timestamp: float = 0.0
    ) -> str:
        """
        分析视频关键帧内容

        Args:
            image_path: 本地图片路径
            image_url: 图片 URL（二选一）
            timestamp: 视频时间戳（秒）

        Returns:
            str: 画面描述文本
        """
        prompt = (
            f"这是教学视频在 {timestamp:.1f} 秒处的截图。"
            "请提取画面中的文字信息、公式和当前展示的知识点。"
        )

        return await self.describe_image(
            image_path=image_path,
            image_url=image_url,
            prompt=prompt
        )

    async def _call_vision_api(self, image_data: str, prompt: str) -> str:
        """
        调用视觉理解 API

        Args:
            image_data: 图片数据（base64 或 URL）
            prompt: 提示词

        Returns:
            str: 描述文本
        """
        url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 判断是 URL 还是 base64
        if image_data.startswith("http"):
            image_content = {"image": image_data}
        else:
            image_content = {"image": f"data:image/jpeg;base64,{image_data}"}

        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            image_content,
                            {"text": prompt}
                        ]
                    }
                ]
            },
            "parameters": {
                "max_tokens": 1000,
                "result_format": "message"
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )

                if response.status_code != 200:
                    logger.error(f"视觉 API 错误: {response.status_code} - {response.text}")
                    return f"API 错误: {response.status_code}"

                result = response.json()

                # 解析响应
                if "output" in result and "choices" in result["output"]:
                    content = result["output"]["choices"][0]["message"]["content"]
                    # 提取文本内容
                    if isinstance(content, list):
                        for item in content:
                            if item.get("text"):
                                return item["text"]
                    return str(content)
                else:
                    logger.error(f"视觉理解响应格式异常: {result}")
                    return "响应格式异常"

        except Exception as e:
            logger.error(f"调用视觉理解 API 失败: {e}")
            return f"API 调用失败: {str(e)}"

    async def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        将图片编码为 base64

        Args:
            image_path: 图片路径

        Returns:
            base64 编码字符串，或 None
        """
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            return None


# 全局服务实例
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """获取视觉理解服务实例"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
