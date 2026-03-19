"""
PPT LangGraph 状态定义
"""
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class PptAgentState(TypedDict):
    """PPT工作流状态"""
    # 会话信息
    session_id: int
    user_id: int

    # 消息历史
    messages: Annotated[list[BaseMessage], add_messages]

    # 用户输入
    user_input: str

    # 知识库
    selected_library_ids: list[int]
    retrieved_context: str

    # 模板
    template_id: str | None

    # 大纲
    outline_markdown: str
    outline_id: int | None
    outline_approved: bool

    # 配图
    image_urls: dict

    # PPT结果
    result_id: int | None
    docmee_task_id: str | None

    # 流程控制
    next_action: str  # generate_outline / approve / generate_ppt / modify / done / error
    error_message: str
