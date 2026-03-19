"""
PPT LangGraph 工作流

业务主链路：知识检索 -> 大纲生成 -> 自动配图 -> 审批中断 -> PPT生成
支持审批中断恢复和继续修改触发新版本。
"""
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.services.ppt.state import PptAgentState
from app.services.ppt.nodes import (
    retrieve_knowledge,
    generate_outline,
    auto_image_node,
    approval_node,
)

logger = logging.getLogger(__name__)


def _route_after_approval(state: PptAgentState) -> str:
    """审批后路由：已批准则结束，否则等待"""
    if state.get("outline_approved"):
        return "end"
    return "wait"


def create_ppt_graph():
    """
    创建PPT工作流图

    流程：
    1. retrieve  - 检索知识库
    2. outline   - 生成大纲
    3. image     - 自动配图
    4. approval  - 审批中断（等待用户确认）
    """
    workflow = StateGraph(PptAgentState)

    workflow.add_node("retrieve", retrieve_knowledge)
    workflow.add_node("outline", generate_outline)
    workflow.add_node("image", auto_image_node)
    workflow.add_node("approval", approval_node)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "outline")
    workflow.add_edge("outline", "image")
    workflow.add_edge("image", "approval")
    workflow.add_edge("approval", END)

    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_after=["approval"],
    )


# 全局单例
_ppt_graph = None


def get_ppt_graph():
    """获取PPT工作流图实例"""
    global _ppt_graph
    if _ppt_graph is None:
        _ppt_graph = create_ppt_graph()
        logger.info("PPT工作流图初始化完成")
    return _ppt_graph
