"""
PPT生成模块 - AI服务层
banana-slides 核心服务适配（文本生成使用 Gemini text provider）
"""
import json
import re
from typing import Optional, AsyncGenerator
from app.generators.ppt.banana_providers import get_text_provider_singleton


class BananaAIService:
    """banana-slides AI服务适配"""

    def __init__(self):
        pass

    @property
    def _text(self):
        """懒加载文本 provider（Gemini/OpenAI/Anthropic，取决于 AI_PROVIDER_FORMAT）"""
        return get_text_provider_singleton()

    async def _chat(self, prompt: str) -> str:
        """统一文本调用入口"""
        return await self._text.agenerate_text(prompt)

    async def parse_outline_text(
        self,
        outline_text: str,
        theme: Optional[str] = None,
        language: str = "zh"
    ) -> dict:
        """
        解析大纲文本为结构化JSON

        Args:
            outline_text: 大纲文本内容
            theme: 主题/风格
            language: 输出语言

        Returns:
            解析后的结构化大纲字典
        """
        prompt = self._build_outline_parsing_prompt(outline_text, theme, language)

        try:
            response = await self._chat(prompt)
            return self._parse_json_response(response)
        except Exception as e:
            # 解析失败时返回原始文本
            return {"error": str(e), "raw_text": outline_text}

    def _build_outline_parsing_prompt(
        self,
        outline_text: str,
        theme: Optional[str],
        language: str
    ) -> str:
        """构建大纲解析提示词"""
        theme_hint = f"\n主题风格：{theme}" if theme else ""

        prompt = f"""请将以下大纲文本解析为结构化JSON格式：

内容：
{outline_text}
{theme_hint}
语言：{language}

请返回标准JSON格式，包含以下字段：
- pages: 页面列表，每个页面包含 title（标题）和 points（要点列表）

直接返回JSON，不要包含markdown代码块标记。"""

        return prompt

    def _parse_json_response(self, response: str):
        """解析JSON响应，处理可能的markdown包裹，支持对象或数组"""
        # 去除可能的 markdown 代码块
        cleaned = re.sub(r'^```json\s*', '', response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'```\s*$', '', cleaned.strip())
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试提取 JSON 数组或对象
            match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', cleaned)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise

    async def generate_descriptions_stream(
        self,
        pages: list[dict],
        theme: Optional[str] = None,
        language: str = "zh",
        detail_level: str = "default"
    ) -> AsyncGenerator[dict, None]:
        """
        流式生成页面描述

        Args:
            pages: 页面列表，每个包含 title 和 points
            theme: 主题/风格
            language: 输出语言
            detail_level: 详细程度 (concise/default/detailed)

        Yields:
            SSE 事件字典
        """
        total = len(pages)

        for idx, page in enumerate(pages):
            prompt = self._build_description_prompt(
                page, theme, language, detail_level
            )

            try:
                response = await self._chat(prompt)
                description = self._extract_description(response)

                yield {
                    "type": "page",
                    "page_id": page.get("id", idx),
                    "content": description,
                    "progress": idx + 1,
                    "total": total
                }
            except Exception as e:
                yield {
                    "type": "error",
                    "page_id": page.get("id", idx),
                    "message": str(e)
                }

        yield {"type": "done"}

    def _build_description_prompt(
        self,
        page: dict,
        theme: Optional[str],
        language: str,
        detail_level: str
    ) -> str:
        """构建描述生成提示词"""
        title = page.get("title", "")
        points = page.get("points", [])
        points_text = "\n".join(f"- {p}" for p in points)

        theme_hint = f"\n风格主题：{theme}" if theme else ""

        detail_instruction = {
            "concise": "简洁明了，突出核心信息",
            "default": "适中详细，包含关键细节",
            "detailed": "详尽全面，包含所有重要内容"
        }.get(detail_level, "")

        prompt = f"""为以下PPT页面生成描述内容：

页面标题：{title}
页面要点：
{points_text}
{theme_hint}
语言：{language}
详细程度：{detail_instruction}

请生成一段适合用于AI生成PPT图片的描述文字，包含：
1. 页面整体布局建议
2. 视觉元素描述
3. 配色建议（如适用）

直接返回描述文字，不需要JSON格式。"""

        return prompt

    def _extract_description(self, response: str) -> str:
        """从响应中提取描述内容"""
        # 去除可能的 markdown
        cleaned = re.sub(r'^```\s*', '', response.strip())
        cleaned = re.sub(r'```\s*$', '', cleaned.strip())
        return cleaned.strip()

    async def generate_description(
        self,
        page: dict,
        theme: Optional[str] = None,
        language: str = "zh",
        detail_level: str = "default"
    ) -> str:
        """
        为单个页面生成描述

        Args:
            page: 页面数据，包含 title 和 points
            theme: 主题/风格
            language: 输出语言
            detail_level: 详细程度

        Returns:
            页面描述文字
        """
        prompt = self._build_description_prompt(page, theme, language, detail_level)
        try:
            response = await self._chat(prompt)
            return self._extract_description(response)
        except Exception as e:
            return f"描述生成失败: {str(e)}"

    async def refine_outline(
        self,
        outline_pages: list[dict],
        user_requirement: str,
        language: str = "zh"
    ) -> list[dict]:
        """
        自然语言修改大纲

        Args:
            outline_pages: 当前大纲页面列表
            user_requirement: 用户修改要求
            language: 输出语言

        Returns:
            修改后的大纲页面列表
        """
        prompt = f"""请根据用户要求修改以下大纲：

用户要求：{user_requirement}

当前大纲（JSON数组格式，每项含id/title/points）：
{json.dumps(outline_pages, ensure_ascii=False, indent=2)}

语言：{language}

要求：
- 保留每个页面的 id 字段不变
- 返回修改后的JSON数组，格式与输入一致
- 直接返回JSON数组，不要包含markdown代码块"""

        try:
            response = await self._chat(prompt)
            result = self._parse_json_response(response)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("pages", outline_pages)
            return outline_pages
        except Exception:
            return outline_pages

    async def refine_descriptions(
        self,
        descriptions: list[dict],
        user_requirement: str,
        language: str = "zh"
    ) -> list[dict]:
        """
        自然语言修改页面描述

        Args:
            descriptions: 当前页面描述列表
            user_requirement: 用户修改要求
            language: 输出语言

        Returns:
            修改后的页面描述列表
        """
        prompt = f"""请根据用户要求修改以下页面描述：

用户要求：{user_requirement}

当前描述（JSON数组格式，每项含id/title/description）：
{json.dumps(descriptions, ensure_ascii=False, indent=2)}

语言：{language}

要求：
- 保留每个页面的 id 字段不变
- 返回修改后的JSON数组，格式与输入一致
- 直接返回JSON数组，不要包含markdown代码块"""

        try:
            response = await self._chat(prompt)
            result = self._parse_json_response(response)
            return result if isinstance(result, list) else descriptions
        except Exception:
            return descriptions


# 单例
_banana_service: Optional[BananaAIService] = None


def get_banana_service() -> BananaAIService:
    """获取 BananaAIService 单例"""
    global _banana_service
    if _banana_service is None:
        _banana_service = BananaAIService()
    return _banana_service
