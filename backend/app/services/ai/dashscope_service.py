"""
阿里云百炼 AI 服务
支持通义千问 LLM 和 Embedding
"""
import os
import json
import logging
from typing import Optional, Any, List, Dict
from dataclasses import dataclass

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun

from app.core.config import settings

logger = logging.getLogger(__name__)

# 阿里云百炼 API 地址
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"


# ==================== LangChain 兼容 LLM ====================

@dataclass
class DashScopeChatMessage:
    """DashScope 消息格式"""
    role: str
    content: str


class ChatDashScope(BaseChatModel):
    """
    阿里云百炼 LangChain 兼容 LLM

    支持通义千问系列模型
    """

    model_name: str = "qwen-plus"
    temperature: float = 0.7
    max_tokens: int = 2000
    api_key: str = ""
    base_url: str = DASHSCOPE_BASE_URL

    @property
    def _llm_type(self) -> str:
        return "dashscope"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """生成回复"""
        # 转换消息格式
        dashscope_messages = self._convert_messages(messages)

        # 调用 API
        response = self._call_api(dashscope_messages, stop=stop)

        # 解析响应
        ai_message = AIMessage(content=response)
        generation = ChatGeneration(message=ai_message)

        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """异步生成回复"""
        # 转换消息格式
        dashscope_messages = self._convert_messages(messages)

        # 调用 API
        response = await self._acall_api(dashscope_messages, stop=stop)

        # 解析响应
        ai_message = AIMessage(content=response)
        generation = ChatGeneration(message=ai_message)

        return ChatResult(generations=[generation])

    def _convert_messages(self, messages: List[BaseMessage]) -> List[DashScopeChatMessage]:
        """转换 LangChain 消息为 DashScope 格式"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                role = "user"  # 默认

            result.append(DashScopeChatMessage(role=role, content=msg.content))

        return result

    def _call_api(
        self,
        messages: List[DashScopeChatMessage],
        stop: Optional[List[str]] = None
    ) -> str:
        """同步调用 API"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 已在事件循环中，使用线程池
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._acall_api(messages, stop)
                    )
                    return future.result()
            else:
                return asyncio.run(self._acall_api(messages, stop))
        except RuntimeError:
            return asyncio.run(self._acall_api(messages, stop))

    async def _acall_api(
        self,
        messages: List[DashScopeChatMessage],
        stop: Optional[List[str]] = None
    ) -> str:
        """异步调用 API"""
        url = f"{self.base_url}/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {"role": m.role, "content": m.content}
                    for m in messages
                ]
            },
            "parameters": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "result_format": "message",
                "stop": stop or []
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
                response.raise_for_status()

                result = response.json()

                if "output" in result and "choices" in result["output"]:
                    return result["output"]["choices"][0]["message"]["content"]
                else:
                    logger.error(f"DashScope 响应格式异常: {result}")
                    return f"响应格式异常: {result}"

        except Exception as e:
            logger.error(f"DashScope API 调用失败: {e}")
            return f"API 调用失败: {str(e)}"


class DashScopeService:
    """阿里云百炼 AI 服务"""

    def __init__(self):
        # 优先读取 settings，确保与 .env 配置保持一致
        self.api_key = settings.DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY", "")
        raw_model = settings.LLM_MODEL or os.getenv("LLM_MODEL", "qwen-plus")
        self.llm_model = self._normalize_model_name(raw_model)
        self.base_url = DASHSCOPE_BASE_URL

        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY")

        if raw_model != self.llm_model:
            logger.warning("LLM_MODEL=%s 在当前端点不可用，自动使用 %s", raw_model, self.llm_model)

    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        """将不兼容别名映射到当前端点可用模型。"""
        if not model_name:
            return "qwen-plus"

        aliases = {
            "qwen3.5-plus": "qwen-plus",
            "qwen3.5-turbo": "qwen-turbo",
            "qwen3.5-max": "qwen-max",
        }
        return aliases.get(model_name, model_name)

    @staticmethod
    def _normalize_role(role: str) -> str:
        """将历史会话中的非标准角色映射为 DashScope 支持的角色。"""
        role_value = (role or "user").strip().lower()
        mapping = {
            "ai": "assistant",
            "bot": "assistant",
            "human": "user",
        }
        role_value = mapping.get(role_value, role_value)
        if role_value in {"system", "user", "assistant"}:
            return role_value
        return "user"

    async def _call_generation_api(self, payload: dict) -> dict:
        """调用 text-generation 接口，并在模型不兼容时自动回退。"""
        url = f"{self.base_url}/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )

            # 某些模型别名在该端点会返回 400，自动回退到 qwen-plus
            if response.status_code == 400 and payload.get("model") != "qwen-plus":
                fallback_payload = {**payload, "model": "qwen-plus"}
                logger.warning(
                    "DashScope 400，模型 %s 自动回退为 qwen-plus。原始响应: %s",
                    payload.get("model"),
                    response.text
                )
                response = await client.post(
                    url,
                    headers=headers,
                    json=fallback_payload,
                    timeout=60.0
                )

            response.raise_for_status()
            return response.json()

    async def chat(
        self,
        prompt: str,
        system_prompt: str = "你是一个专业的教学助手，擅长根据用户需求生成教学内容。",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        调用通义千问 API

        Args:
            prompt: 用户输入
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            AI 回复内容
        """
        if not self.api_key:
            return "错误: 未配置 DASHSCOPE_API_KEY"

        payload = {
            "model": self.llm_model,
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "result_format": "message"
            }
        }

        try:
            result = await self._call_generation_api(payload)

            # 解析响应
            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["message"]["content"]
            elif "usage" in result:
                # 返回 usage 信息用于调试
                return f"请求成功，但响应格式异常: {result}"
            else:
                return f"响应格式异常: {result}"

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            return f"API 调用失败: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            logger.error(f"调用通义千问 API 失败: {e}")
            return f"API 调用失败: {str(e)}"

    async def chat_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "你是一个专业的教学助手，擅长根据用户需求生成教学内容。",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        带历史记录的对话

        Args:
            messages: 历史消息 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            AI 回复内容
        """
        if not self.api_key:
            return "错误: 未配置 DASHSCOPE_API_KEY"

        # 构建消息列表
        normalized_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            normalized_messages.append({
                "role": self._normalize_role(msg.get("role", "user")),
                "content": content
            })

        all_messages = [{"role": "system", "content": system_prompt}] + normalized_messages

        payload = {
            "model": self.llm_model,
            "input": {
                "messages": all_messages
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "result_format": "message"
            }
        }

        try:
            result = await self._call_generation_api(payload)

            if "output" in result and "choices" in result["output"]:
                return result["output"]["choices"][0]["message"]["content"]
            else:
                return f"响应格式异常: {result}"

        except httpx.HTTPStatusError as e:
            logger.error(f"调用通义千问 API 失败: {e.response.status_code} - {e.response.text}")
            return f"API 调用失败: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            logger.error(f"调用通义千问 API 失败: {e}")
            return f"API 调用失败: {str(e)}"


class EmbeddingService:
    """阿里云百炼 Embedding 服务"""

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "tongyi-embedding-vision-flash")
        self.base_url = DASHSCOPE_BASE_URL

        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY")

    async def embed_text(self, text: str) -> list[float]:
        """
        获取文本的 Embedding 向量

        Args:
            text: 输入文本

        Returns:
            embedding 向量
        """
        if not self.api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")

        # 多模态模型使用多模态端点
        if self.embedding_model.startswith("tongyi-embedding-vision") or \
           self.embedding_model in ["multimodal-embedding-v1", "qwen2.5-vl-embedding", "qwen3-vl-embedding"]:
            embeddings = await self._embed_multimodal([text])
            return embeddings[0]

        # 标准文本嵌入模型
        url = f"{self.base_url}/services/embeddings/text-embedding/text-embedding"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.embedding_model,
            "input": {"texts": [text]}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

                result = response.json()

                if "output" in result and "embeddings" in result["output"]:
                    return result["output"]["embeddings"][0]["embedding"]
                else:
                    raise ValueError(f"响应格式异常: {result}")

        except Exception as e:
            logger.error(f"获取 Embedding 失败: {e}")
            raise

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        批量获取文本的 Embedding 向量

        Args:
            texts: 输入文本列表

        Returns:
            embedding 向量列表
        """
        if not self.api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")

        # 多模态模型使用不同的端点和格式
        if self.embedding_model.startswith("tongyi-embedding-vision") or \
           self.embedding_model in ["multimodal-embedding-v1", "qwen2.5-vl-embedding", "qwen3-vl-embedding"]:
            return await self._embed_multimodal(texts)

        # 标准文本嵌入模型
        url = f"{self.base_url}/services/embeddings/text-embedding/text-embedding"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.embedding_model,
            "input": {"texts": texts}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()

                result = response.json()

                if "output" in result and "embeddings" in result["output"]:
                    return [item["embedding"] for item in result["output"]["embeddings"]]
                else:
                    raise ValueError(f"响应格式异常: {result}")

        except Exception as e:
            logger.error(f"批量获取 Embedding 失败: {e}")
            raise

    async def _embed_multimodal(self, texts: list[str]) -> list[list[float]]:
        """
        多模态模型嵌入（支持 tongyi-embedding-vision 系列）
        
        API 端点: /services/embeddings/multimodal-embedding/multimodal-embedding
        请求格式: {"input": {"contents": [{"text": "..."}, {"image": "..."}]}}
        """
        url = f"{self.base_url}/services/embeddings/multimodal-embedding/multimodal-embedding"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 多模态格式：每个文本作为一个 content 对象
        contents = [{"text": t} for t in texts]
        
        payload = {
            "model": self.embedding_model,
            "input": {"contents": contents}
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
                    logger.error(f"多模态 API 错误: {response.status_code} - {response.text}")
                    
                response.raise_for_status()

                result = response.json()

                if "output" in result and "embeddings" in result["output"]:
                    return [item["embedding"] for item in result["output"]["embeddings"]]
                else:
                    raise ValueError(f"响应格式异常: {result}")

        except Exception as e:
            logger.error(f"多模态 Embedding 失败: {e}")
            raise


# 全局服务实例
_dashscope_service: Optional[DashScopeService] = None
_embedding_service: Optional[EmbeddingService] = None


def get_dashscope_service() -> DashScopeService:
    """获取通义千问服务实例"""
    global _dashscope_service
    if _dashscope_service is None:
        _dashscope_service = DashScopeService()
    return _dashscope_service


def get_embedding_service() -> EmbeddingService:
    """获取 Embedding 服务实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


# ==================== LangChain LLM 服务 ====================

_llm_instance: Optional[ChatDashScope] = None


class LLMService:
    """LLM 服务封装（LangChain 兼容）"""

    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL", "qwen-plus")
        self.temperature = 0.7
        self.max_tokens = 2000

        if not self.api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY")

    @property
    def llm(self) -> ChatDashScope:
        """获取 LangChain 兼容的 LLM 实例"""
        global _llm_instance
        if _llm_instance is None:
            _llm_instance = ChatDashScope(
                model_name=self.llm_model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=self.api_key
            )
        return _llm_instance

    async def ainvoke(self, messages: List[Dict]) -> AIMessage:
        """
        异步调用 LLM

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]

        Returns:
            AIMessage
        """
        # 转换格式
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))

        # 调用
        result = await self.llm.agenerate([langchain_messages])

        return result.generations[0][0].message


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例（LangChain 兼容）"""
    global _llm_instance
    if not hasattr(get_llm_service, '_instance'):
        get_llm_service._instance = LLMService()
    return get_llm_service._instance
