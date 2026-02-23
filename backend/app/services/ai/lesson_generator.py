"""
AI 核心服务：生成 Master Lesson JSON
"""
from typing import Any
import json


class AILessonService:
    """
    AI 课程生成服务

    负责调用 AI 模型生成标准化的 Master Lesson JSON 结构。
    """

    async def generate_lesson_json(
        self,
        user_request: str,
        knowledge_context: list[dict] | None = None
    ) -> dict[str, Any]:
        """
        生成 Master Lesson JSON

        Args:
            user_request: 用户需求描述
            knowledge_context: 知识库上下文

        Returns:
            Master Lesson JSON 结构
        """
        # TODO: 实现实际 AI 调用逻辑
        # 1. 构建 prompt
        # 2. 调用 OpenAI/Anthropic API
        # 3. 解析响应为标准 JSON 格式

        # 返回示例数据
        master_lesson = {
            "title": "示例课件标题",
            "slides": [
                {
                    "title": "封面页",
                    "content": "这是课件的封面内容",
                    "image_prompt": "一个温馨的教室场景",
                    "notes": "授课教师介绍"
                },
                {
                    "title": "课程目标",
                    "content": "1. 理解基本概念\\n2. 掌握核心技能\\n3. 能够实际应用",
                    "image_prompt": "学生学习的插图",
                    "notes": "引导学生明确学习目标"
                }
            ],
            "lesson_plan_details": {
                "objectives": ["理解概念", "掌握技能", "实际应用"],
                "duration": "45分钟",
                "materials": ["PPT", "练习册"],
                "assessment": "课堂测验"
            },
            "interactive_elements": [
                {
                    "type": "quiz",
                    "question": "本节课的核心知识点是？",
                    "options": ["A. 选项1", "B. 选项2", "C. 选项3"],
                    "correct_answer": "A"
                }
            ]
        }

        return master_lesson

    async def chat_with_ai(
        self,
        message: str,
        conversation_history: list[dict]
    ) -> str:
        """
        与 AI 对话

        Args:
            message: 用户消息
            conversation_history: 对话历史

        Returns:
            AI 回复
        """
        # TODO: 实现实际 AI 对话逻辑
        return "感谢您的提问！请告诉我更多关于您想要创建的课件信息，比如主题、受众、时长等。"
