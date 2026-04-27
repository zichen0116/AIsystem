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

        prompt = f"""请将以下内容整理为结构化 PPT 大纲 JSON：

内容：
{outline_text}
{theme_hint}
{planning_context_block}
{materials_block}
{knowledge_block}
语言：{language}

    请返回标准JSON格式，包含以下字段：
    - pages: 页面列表，每个页面包含 title（标题）和 points（要点列表）

    硬性要求（必须遵守）：
    1. 文档优先：优先依据输入内容提炼要点，不要凭空编造与文档毫无关系的信息。
    2. 允许补充：当用户需求中有明确教学目标或风格要求且文档未覆盖时，可做合理补充，但必须具体可讲，不可空泛。
    3. points 质量：每页 2-3 条为宜，每条必须是完整可读的中文短句，长度建议 8-30 字。
    4. 禁止占位符：严禁输出“...”、“待补充”、“TBD”、“[核心概念一]”、“[关键技能]”、“[实际应用]”等模板或占位文本。
    5. 禁止嵌套结构：points 必须严格是纯字符串数组，不能是对象或数组嵌套。
    6. 若输入信息不足，也必须输出具体可执行表达，不得使用省略号或括号占位。

    仅返回 JSON，不要包含 markdown 代码块或解释说明。"""

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
        detail_level: str,
        extra_fields_config: Optional[list[dict]] = None,
        planning_context_text: Optional[str] = None,
        materials_context: Optional[str] = None,
        knowledge_context: Optional[str] = None,
    ) -> str:
        """构建描述生成提示词"""
        title = page.get("title", "")
        points = page.get("points", [])
        points_text = "\n".join(f"- {p}" for p in points)
        extra_fields_config = extra_fields_config or []
        extra_field_lines = []
        extra_output_lines = []
        for field in extra_fields_config:
            label = str(field.get("label") or "").strip()
            key = str(field.get("key") or "").strip()
            if not label or not key:
                continue
            if key == "notes":
                extra_field_lines.append(f"- {label}：补充给老师看的讲解提醒或表达建议，控制在1句。")
            else:
                extra_field_lines.append(f"- {label}：只写该页最关键的1条信息，不要展开。")
            extra_output_lines.append(f"{label}：...")

        theme_hint = f"\n风格主题：{theme}" if theme else ""

        planning_context_block = (
            f"\nPlanning Context 摘要：\n{planning_context_text.strip()}"
            if planning_context_text and planning_context_text.strip()
            else ""
        )
        materials_block = (
            f"\n项目资料参考：\n{materials_context.strip()}"
            if materials_context and materials_context.strip()
            else ""
        )
        knowledge_block = (
            f"\n知识库补充：\n{knowledge_context.strip()}"
            if knowledge_context and knowledge_context.strip()
            else ""
        )

        detail_instruction = {
            "concise": "尽量短，每个字段只保留核心信息。",
            "default": "保持简洁和结构化，每个字段只写1到3条关键信息。",
            "detailed": "在保持结构化的前提下补充必要信息，每个字段不要超过4条。"
        }.get(detail_level, "保持简洁和结构化。")

        prompt = f"""请为这个 PPT 页面生成简洁、结构化的中文页面描述。

页面标题：{title}
页面要点：
{points_text or "- 无"}
{theme_hint}
输出语言：{language}
详细程度：{detail_instruction}

要求：
1. 输出必须简洁、结构化，方便逐页阅读和人工编辑。
2. 不要写成长段，不要堆砌镜头、材质、光影、配色等冗长提示词。
3. 优先围绕当前页真正要展示的内容，而不是泛泛描述设计感。
4. 如果是封面页，可以突出标题、副标题和整体气质；普通内容页突出核心知识点与讲解顺序。
5. 不要返回 JSON，不要加解释开头或结尾。
6. 每个字段必须独立成段，字段名和冒号必须单独出现，不能把多个字段写到同一行。

请严格按下面格式输出：
页面主题内容：
- 要点1
- 要点2
- 要点3
"""

        if extra_field_lines:
            prompt += "\n\n额外字段要求：\n" + "\n".join(extra_field_lines)
            prompt += "\n请在“页面主题内容”后继续输出以下字段（字段名必须完全一致）：\n"
            prompt += "\n".join(extra_output_lines)

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
        detail_level: str = "default",
        extra_fields_config: Optional[list[dict]] = None,
        planning_context_text: Optional[str] = None,
        materials_context: Optional[str] = None,
        knowledge_context: Optional[str] = None,
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
        prompt = self._build_description_prompt(
            page,
            theme,
            language,
            detail_level,
            extra_fields_config=extra_fields_config,
            planning_context_text=planning_context_text,
            materials_context=materials_context,
            knowledge_context=knowledge_context,
        )
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
