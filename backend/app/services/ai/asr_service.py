"""
阿里云百炼 qwen3-asr-flash 语音识别服务
视频提出来的音频进行语音识别转文字
使用 OpenAI 兼容接口调用
"""
import json
import logging
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# OpenAI 兼容接口地址
OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenASRService:
    """
    qwen3-asr-flash 语音识别服务
    
    支持功能：
    - 音频文件转写（支持本地文件和 URL）
    - 多语言识别（中文、英文等）
    - 时间戳输出
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.base_url = OPENAI_BASE_URL
        self.model = settings.ASR_MODEL or "qwen3-asr-flash"
        
        # OSS 配置（可选，用于文件上传）
        self.oss_endpoint = settings.OSS_ENDPOINT or "https://oss-cn-hangzhou.aliyuncs.com"
        self.oss_bucket = settings.OSS_BUCKET
        self.oss_access_key_id = settings.OSS_ACCESS_KEY_ID
        self.oss_access_key_secret = settings.OSS_ACCESS_KEY_SECRET
        
        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY")

    async def recognize(
        self,
        audio_path: Optional[str] = None,
        audio_url: Optional[str] = None,
        language: str = "zh",
        enable_itn: bool = True,
        enable_timestamp: bool = False,
        format: str = "mp3"
    ) -> dict:
        """
        调用 qwen3-asr-flash 进行语音识别
        
        Args:
            audio_path: 本地音频文件路径
            audio_url: 音频文件 URL（二选一）
            language: 语言，支持 "zh" / "en" / "yue" / "ja" / "ko" 等
            enable_itn: 是否启用逆文本规范化（标点符号还原）
            enable_timestamp: 是否输出时间戳
            format: 音频格式，支持 "mp3", "wav", "aac", "flac", "m4a", "ogg"
            
        Returns:
            dict: 包含转写文本和时间戳的结果
        """
        if not self.api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")
        
        if not audio_path and not audio_url:
            raise ValueError("需要提供 audio_path 或 audio_url")

        # 获取音频文件 URL
        file_url = audio_url
        
        if audio_path and not file_url:
            # 上传到 OSS 获取 URL
            file_url = await self._upload_to_oss(audio_path)
            if not file_url:
                logger.error("无法获取音频文件 URL")
                return {"text": "", "sentences": [], "error": "文件上传失败"}

        if not file_url:
            raise ValueError("无法获取音频文件 URL")

        # 使用 OpenAI 兼容接口调用 ASR
        return await self._call_asr_api(
            file_url=file_url,
            language=language,
            enable_itn=enable_itn,
            enable_timestamp=enable_timestamp
        )

    async def _call_asr_api(
        self,
        file_url: str,
        language: str,
        enable_itn: bool,
        enable_timestamp: bool
    ) -> dict:
        """
        使用 OpenAI 兼容接口调用 ASR
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体 - 使用 OpenAI 兼容格式
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": file_url
                        }
                    }
                ]
            }],
            "extra_body": {
                "asr_options": {
                    "language": language,
                    "enable_itn": enable_itn,
                    "enable_timestamp": enable_timestamp
                }
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
                if response.status_code != 200:
                    logger.error(f"ASR API 错误: {response.status_code} - {response.text}")
                    return {"text": "", "sentences": [], "error": f"API error: {response.status_code}"}
                
                result = response.json()
                
                # 解析响应
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    
                    # 尝试解析 JSON 响应
                    try:
                        if isinstance(content, str):
                            # 尝试解析 JSON 字符串
                            content_data = json.loads(content)
                        else:
                            content_data = content
                        
                        # 提取文本
                        text = content_data.get("text", "")
                        
                        # 提取句子（含时间戳）
                        sentences = content_data.get("sentences", [])
                        
                        return {
                            "text": text,
                            "sentences": sentences
                        }
                    except json.JSONDecodeError:
                        # 如果不是 JSON，直接返回文本
                        return {
                            "text": str(content),
                            "sentences": []
                        }
                else:
                    logger.error(f"ASR 响应格式异常: {result}")
                    return {"text": "", "sentences": [], "error": "响应格式异常"}
                    
        except Exception as e:
            logger.error(f"ASR 调用异常: {e}")
            return {"text": "", "sentences": [], "error": str(e)}

    async def _upload_to_oss(self, file_path: str) -> Optional[str]:
        """
        上传音频文件到 OSS
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            OSS URL 或 None
        """
        if not all([self.oss_bucket, self.oss_access_key_id, self.oss_access_key_secret]):
            logger.warning("OSS 配置不完整，跳过上传")
            return None
        
        try:
            import oss2
            
            # 读取文件
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 生成 OSS 对象名
            object_name = f"asr/{uuid.uuid4().hex}_{file_path_obj.name}"
            
            # 使用 oss2 上传文件
            auth = oss2.Auth(self.oss_access_key_id, self.oss_access_key_secret)
            bucket = oss2.Bucket(auth, self.oss_endpoint, self.oss_bucket)
            
            # 上传文件
            result = bucket.put_object_from_file(object_name, file_path)
            
            if result.status == 200:
                # 使用 oss2 正确生成访问 URL
                endpoint = self.oss_endpoint.replace("https://", "").replace("http://", "")
                file_url = f"https://{self.oss_bucket}.{endpoint}/{object_name}"
                logger.info(f"OSS 上传成功: {file_url}")
                return file_url
            else:
                logger.error(f"OSS 上传失败: {result.status}")
                return None
            
        except Exception as e:
            logger.error(f"OSS 上传失败: {e}")
            return None


# 全局单例
_asr_service: Optional[QwenASRService] = None


def get_asr_service() -> QwenASRService:
    """获取 ASR 服务单例"""
    global _asr_service
    if _asr_service is None:
        from app.core.config import settings
        _asr_service = QwenASRService(api_key=settings.DASHSCOPE_API_KEY)
    return _asr_service
