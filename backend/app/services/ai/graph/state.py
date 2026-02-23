"""
LangGraph Agent 状态定义

定义 AgentState，用于在 LangGraph 工作流中传递状态
"""
from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Agent 状态定义

    使用 add_messages reducer 确保新消息是 append 而不是覆盖
    """

    # 消息历史，使用 add_messages 自动合并
    messages: Annotated[List[BaseMessage], add_messages]

    # RAG 检索到的上下文文档
    documents: List[Document]

    # LLM 生成的最终答案
    generation: str

    # Self-RAG 重试次数，防止死循环
    retry_count: int

    # 是否需要调用网络搜索
    web_search_needed: bool

    # 用户ID（用于知识库隔离）
    user_id: int

    # 工具调用记录（可选，用于调试）
    tool_calls: Optional[List[str]]

    # 当前查询（用于追踪）
    current_query: Optional[str]

    # ====== Human-in-the-loop 相关字段 ======

    # 结构化大纲 JSON（用于 PPT 生成等场景）
    outline: Optional[Dict[str, Any]]

    # 用户对大纲的修改意见
    user_feedback: Optional[str]

    # 是否已通过用户确认
    approved: bool
