"""
LangGraph 工作流编排

构建完整的 ReAct + Self-RAG 闭环：
- ReAct 循环：Agent 决策 -> 工具执行 -> Agent 决策
- Self-RAG 循环：生成答案 -> Grader 评估 -> 通过或重试
- Human-in-the-loop：大纲确认 -> 用户反馈 -> 最终确认
"""
import logging
from typing import List, Literal, Optional, Dict, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from app.services.ai.graph.state import AgentState
from app.services.ai.graph.nodes import (
    create_agent_node,
    create_tools_node,
    create_grader_node,
    create_outline_approval_node,
    create_finalize_node,
    should_continue,
    should_retry
)

logger = logging.getLogger(__name__)


def create_agent_graph(max_retries: int = 3) -> StateGraph:
    """
    创建 Agent 图

    流程：
    1. agent_node: LLM 决策（调用工具 or 生成答案）
    2. tools_node: 执行工具检索
    3. grader_node: Self-RAG 质量评估
    4. outline_approval_node: 大纲确认节点（Human-in-the-loop）
    5. finalize_node: 最终确认节点

    Args:
        max_retries: Self-RAG 最大重试次数

    Returns:
        编译后的 StateGraph
    """

    # 创建图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("agent", create_agent_node())
    workflow.add_node("tools", create_tools_node())
    workflow.add_node("grader", create_grader_node(max_retries=max_retries))
    workflow.add_node("outline_approval", create_outline_approval_node())
    workflow.add_node("finalize", create_finalize_node())

    # 设置入口点
    workflow.set_entry_point("agent")

    # 添加边
    # agent -> tools (需要调用工具)
    # agent -> grader (生成答案后评估)
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "grade": "grader"
        }
    )

    # tools -> agent (工具执行完，继续决策)
    workflow.add_edge("tools", "agent")

    # grader -> agent (评估不通过，重试)
    # grader -> outline_approval (评估通过，进入大纲确认)
    workflow.add_conditional_edges(
        "grader",
        should_retry,
        {
            "agent": "agent",
            "outline_approval": "outline_approval"  # 修改：评估通过后进入大纲确认
        }
    )

    # outline_approval -> finalize (等待用户确认后进入最终节点)
    workflow.add_edge("outline_approval", "finalize")

    # finalize -> END (流程结束)
    workflow.add_edge("finalize", END)

    # 创建 MemorySaver 用于保存检查点
    memory = MemorySaver()

    # 编译，添加中断点
    # 在 outline_approval 节点后中断，等待用户确认
    return workflow.compile(checkpointer=memory, interrupt_after=["outline_approval"])


# 全局图实例（单例）
_agent_graph = None


def get_agent_graph(max_retries: int = 3) -> StateGraph:
    """
    获取 Agent 图实例（带缓存）

    Args:
        max_retries: Self-RAG 最大重试次数

    Returns:
        编译后的 StateGraph
    """
    global _agent_graph

    if _agent_graph is None:
        _agent_graph = create_agent_graph(max_retries=max_retries)
        logger.info(f"Agent 图初始化完成，max_retries={max_retries}")

    return _agent_graph


async def run_agent(
    query: str,
    user_id: int,
    chat_history: List = None,
    system_library_ids: List[int] = None,
    max_retries: int = 3
) -> dict:
    """
    运行 Agent

    Args:
        query: 用户问题
        user_id: 用户ID
        chat_history: 历史消息（可选）
        max_retries: Self-RAG 最大重试次数

    Returns:
        {
            "answer": str,  # 最终答案
            "sources": List[dict],  # 引用的来源
            "retry_count": int,  # 重试次数
            "tool_calls": List[str]  # 使用的工具
        }
    """
    # 初始化消息
    messages = []

    # 添加历史消息
    if chat_history:
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(HumanMessage(content=msg["content"]))

    # 添加当前问题
    messages.append(HumanMessage(content=query))

    # 初始化状态
    initial_state = {
        "messages": messages,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "web_search_needed": False,
        "user_id": user_id,
        "tool_calls": [],
        "current_query": query,
        "system_library_ids": system_library_ids,
    }

    # 获取图并执行
    graph = get_agent_graph(max_retries=max_retries)

    logger.info(f"开始执行 Agent: query={query[:50]}..., user_id={user_id}")

    result = await graph.ainvoke(initial_state)

    # 提取结果
    answer = result.get("generation", "")

    # 如果 generation 为空，尝试从最后一条消息获取
    if not answer and result.get("messages"):
        last_msg = result["messages"][-1]
        if hasattr(last_msg, "content"):
            answer = last_msg.content

    # 提取来源
    sources = []
    for doc in result.get("documents", []):
        sources.append({
            "source": doc.metadata.get("source", "未知"),
            "page": doc.metadata.get("page"),
            "content_preview": doc.page_content[:200]
        })

    return {
        "answer": answer,
        "sources": sources,
        "retry_count": result.get("retry_count", 0),
        "tool_calls": result.get("tool_calls", [])
    }


async def run_agent_with_checkpoint(
    query: str,
    user_id: int,
    thread_id: str = None,
    chat_history: List = None,
    system_library_ids: List[int] = None,
    max_retries: int = 3
) -> dict:
    """
    运行 Agent（带检查点）

    返回结果包含 thread_id，可用于后续的 resume 操作

    Args:
        query: 用户问题
        user_id: 用户ID
        thread_id: 线程ID（用于 resume），如果不传则自动生成
        chat_history: 历史消息（可选）
        max_retries: Self-RAG 最大重试次数

    Returns:
        {
            "answer": str,  # 当前阶段的答案/大纲
            "outline": dict,  # 结构化大纲（如果有）
            "sources": List[dict],  # 引用的来源
            "thread_id": str,  # 线程ID，用于 resume
            "status": "awaiting_approval" 或 "completed"
        }
    """
    import uuid

    # 生成 thread_id
    if not thread_id:
        thread_id = str(uuid.uuid4())

    # 初始化消息
    messages = []

    # 添加历史消息
    if chat_history:
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(HumanMessage(content=msg["content"]))

    # 添加当前问题
    messages.append(HumanMessage(content=query))

    # 初始化状态
    initial_state = {
        "messages": messages,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "web_search_needed": False,
        "user_id": user_id,
        "tool_calls": [],
        "current_query": query,
        "outline": None,
        "user_feedback": None,
        "approved": False,
        "system_library_ids": system_library_ids,
    }

    # 获取图并执行
    graph = get_agent_graph(max_retries=max_retries)

    # 创建 config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id
        }
    }

    logger.info(f"开始执行 Agent (with checkpoint): query={query[:50]}..., thread_id={thread_id}")

    # 使用 stream 而非 invoke，以便获取中断前的状态
    final_result = None
    async for chunk in graph.astream(initial_state, config):
        final_result = chunk
        # 如果包含 outline_approval 或 finalize 节点，说明流程已暂停
        if "outline_approval" in chunk or "finalize" in chunk:
            logger.info(f"流程已暂停，等待用户确认")
            break

    # 提取结果
    result = final_result if final_result else {}

    # 获取 outline
    outline = result.get("outline_approval", {}).get("outline") or \
               result.get("finalize", {}).get("outline") or \
               result.get("generation", "")

    # 尝试解析 generation 为 outline
    answer = result.get("generation", "")

    # 检查是否已完成
    status = "awaiting_approval"
    if result.get("finalize") or result.get("approved"):
        status = "completed"
        # 如果已完成，answer 就是最终的 generation
        if not answer:
            for node_result in final_result.values() if final_result else []:
                if isinstance(node_result, dict) and node_result.get("generation"):
                    answer = node_result.get("generation")
                    break

    # 提取来源
    sources = []
    for doc in result.get("documents", []):
        if hasattr(doc, "metadata"):
            sources.append({
                "source": doc.metadata.get("source", "未知"),
                "page": doc.metadata.get("page"),
                "content_preview": doc.page_content[:200] if hasattr(doc, "page_content") else ""
            })

    return {
        "answer": answer,
        "outline": outline if isinstance(outline, dict) else None,
        "sources": sources,
        "thread_id": thread_id,
        "status": status,
        "config": config
    }


async def resume_agent(
    thread_id: str,
    user_id: int,
    new_outline: Dict[str, Any] = None,
    user_feedback: str = None,
    max_retries: int = 3
) -> dict:
    """
    恢复 Agent 执行

    当用户确认或修改大纲后调用

    Args:
        thread_id: 线程ID（来自 run_agent_with_checkpoint）
        user_id: 用户ID
        new_outline: 用户修改后的新大纲（可选）
        user_feedback: 用户的修改意见（可选）
        max_retries: 最大重试次数

    Returns:
        {
            "answer": str,  # 最终答案
            "outline": dict,  # 最终大纲
            "status": "completed"
        }
    """
    graph = get_agent_graph(max_retries=max_retries)

    # 创建 config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id
        }
    }

    # 更新状态
    update_values = {}
    if new_outline:
        update_values["outline"] = new_outline
    if user_feedback:
        update_values["user_feedback"] = user_feedback
    update_values["approved"] = True

    logger.info(f"恢复 Agent 执行: thread_id={thread_id}, user_feedback={user_feedback}")

    # 更新状态并继续执行
    if update_values:
        graph.update_state(config, update_values)

    # 继续执行到结束
    final_result = None
    async for chunk in graph.astream(None, config):
        final_result = chunk
        logger.debug(f"Chunk: {chunk.keys()}")

    result = final_result if final_result else {}

    # 提取最终结果
    answer = ""
    outline = None

    for node_result in result.values():
        if isinstance(node_result, dict):
            if node_result.get("generation"):
                answer = node_result.get("generation")
            if node_result.get("outline"):
                outline = node_result.get("outline")

    return {
        "answer": answer,
        "outline": outline,
        "status": "completed"
    }
