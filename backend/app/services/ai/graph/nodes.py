"""
LangGraph 节点定义

实现核心节点：
1. agent_node - 绑定工具的 LLM，负责决策
2. tools_node - 执行工具检索
3. grader_node - Self-RAG 审查（ Relevance + Groundedness）
"""
import os
import logging
from typing import Literal

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig

from app.services.ai.graph.state import AgentState
from app.services.ai.tools import get_search_tools
from app.services.ai.dashscope_service import get_llm_service

logger = logging.getLogger(__name__)


# ==================== System Prompt ====================

AGENT_SYSTEM_PROMPT = """你是一个专业的教学智能体。

## 核心原则

1. **数据源融合**：如果同时使用了 Local（本地知识库）和 Web（网络搜索），请将 Local 的理论与 Web 的案例有机结合。

2. **权威性原则**：
   - 如果 Web 结果与 Local 资料冲突，以 Local 资料为准
   - 如果两者都没有相关信息，请明确告知用户

3. **引用标注规范**：
   - 引用本地资料：[Ref: 文件名, p.页码]
   - 引用网络资料：[Web: 来源网站名]
   - 多个来源用逗号分隔

4. **格式要求**：
   - 如果用户请求生成大纲，必须输出 JSON 格式
   - 代码示例请使用 Markdown 代码块

## 工具使用策略

- **具体细节查询**：涉及定义、公式、原文引用、具体步骤等，使用 search_local_knowledge
- **全局概述查询**：涉及总结、概述、知识脉络、关系梳理或对比分析，使用 search_knowledge_graph（仅当可用时）
- **复杂教学设计**：可同时调用 search_local_knowledge 和 search_knowledge_graph，先获取全局框架再补充具体细节
- **本地无结果时**：搜索网络补充最新信息或外部案例

回答问题要专业、准确、完整。"""


# ==================== 节点实现 ====================

def create_agent_node():
    """
    创建 Agent 节点

    工具列表根据 state 中 system_library_ids 动态绑定：
    - system_library_ids 非空 → 向量 + 图谱 + 网络搜索
    - system_library_ids 为空 → 向量 + 网络搜索

    Returns:
        agent_node 函数
    """
    from langchain_core.utils.function_calling import convert_to_openai_function

    # 获取 LLM
    llm_service = get_llm_service()

    async def agent_node(state: AgentState) -> AgentState:
        """
        Agent 节点

        根据当前状态决定：
        1. 调用工具
        2. 生成最终答案
        """
        messages = state["messages"]
        user_id = state.get("user_id", 0)
        current_query = state.get("current_query", "")
        system_library_ids = state.get("system_library_ids") or []

        # 如果是第一条消息，提取用户查询
        if not current_query and messages:
            last_msg = messages[-1]
            if isinstance(last_msg, HumanMessage):
                current_query = last_msg.content

        # 动态获取工具列表
        tools = get_search_tools(
            system_library_ids=system_library_ids if system_library_ids else None
        )

        # 动态绑定工具到 LLM（每次请求根据 state 决定工具列表）
        llm = llm_service.llm
        llm_with_tools = llm.bind(
            tools=[convert_to_openai_function(tool) for tool in tools],
            tool_choice="auto"
        )

        # 构造消息列表（SystemMessage 而非 dict，避免混入 BaseMessage 列表后类型不兼容）
        system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
        all_messages = [system_msg] + messages

        logger.info(
            f"Agent 节点执行: user_id={user_id}, 消息数={len(messages)}, "
            f"工具数={len(tools)}, 系统库={system_library_ids}"
        )

        # 调用 LLM（使用绑定了工具的版本）
        response = await llm_with_tools.ainvoke(all_messages)

        # 检查是否需要调用工具
        tool_calls = []
        if hasattr(response, "additional_kwargs") and response.additional_kwargs.get("tool_calls"):
            tool_calls = response.additional_kwargs["tool_calls"]

        if tool_calls:
            # 有工具调用，准备工具调用消息
            ai_msg = AIMessage(
                content=response.content,
                additional_kwargs={"tool_calls": tool_calls}
            )

            # 更新状态
            new_state = {
                "messages": [ai_msg],
                "tool_calls": [tc["function"]["name"] for tc in tool_calls],
                "current_query": current_query,
            }
        else:
            # 无工具调用，生成最终答案
            documents = state.get("documents", [])

            # 构建上下文
            context = ""
            if documents:
                context_parts = []
                for i, doc in enumerate(documents[:5], 1):
                    source = doc.metadata.get("source", "未知")
                    page = doc.metadata.get("page", "")
                    content = doc.page_content[:300]

                    ref = f"[Ref: {source}"
                    if page:
                        ref += f", p.{page}"
                    ref += "]"

                    context_parts.append(f"{i}. {ref}\n{content}")
                context = "\n\n".join(context_parts)

            # 生成最终回复
            final_response = _generate_final_response(
                query=current_query,
                context=context,
                generation=response.content,
                llm_service=llm_service
            )

            new_state = {
                "messages": [response],
                "generation": final_response,
                "documents": documents,
            }

        return new_state

    return agent_node


def _generate_final_response(
    query: str,
    context: str,
    generation: str,
    llm_service
) -> str:
    """
    生成最终回复

    如果有上下文，将上下文整合到回复中
    """
    if not context:
        return generation

    # 简单的上下文整合
    prompt = f"""基于以下参考资料回答用户问题。

参考资料：
{context}

用户问题：{query}

原始回答：
{generation}

请根据参考资料优化回答，确保引用准确。如果参考资料无法回答问题，请说明"当前知识库中无相关信息"。"""

    response = llm_service.ainvoke([{"role": "user", "content": prompt}])

    if hasattr(response, "content"):
        return response.content
    return generation


def create_tools_node():
    """
    创建工具执行节点

    使用 LangGraph 预置的 ToolNode 或自定义实现

    Returns:
        tools_node 函数
    """
    from langgraph.prebuilt import ToolNode

    # 注意：ToolNode 需要在调用时根据 state 动态构建
    # 因为工具列表可能包含图谱工具

    async def tools_node(state: AgentState) -> AgentState:
        """
        工具执行节点

        执行上一次 Agent 调用的工具，返回结果
        """
        messages = state["messages"]
        user_id = state.get("user_id", 0)
        system_library_ids = state.get("system_library_ids") or []

        # 获取最后一条消息（应该包含 tool_calls）
        last_msg = messages[-1]

        if not hasattr(last_msg, "additional_kwargs") or \
           "tool_calls" not in last_msg.additional_kwargs:
            return {"messages": []}

        # 动态构建 ToolNode
        tools = get_search_tools(
            system_library_ids=system_library_ids if system_library_ids else None
        )
        tool_node = ToolNode(tools)

        logger.info(f"Tools 节点执行: user_id={user_id}")

        tool_messages = await tool_node.ainvoke(last_msg)

        # 收集检索到的文档
        documents = []
        tool_call_results = []

        for msg in tool_messages:
            content = msg.content
            tool_call_results.append(content)

            if "【文档" in content:
                docs = _parse_retrieved_docs(content)
                documents.extend(docs)

        return {
            "messages": tool_messages,
            "documents": documents,
            "tool_calls": [tc.get("name", "") for tc in last_msg.additional_kwargs.get("tool_calls", [])]
        }

    return tools_node


def _parse_retrieved_docs(content: str) -> list[Document]:
    """
    简单解析检索结果为 Document 对象

    这是一个简化实现，实际可使用更复杂的解析逻辑
    """
    documents = []
    lines = content.split("\n")

    current_doc = None
    current_content = []

    for line in lines:
        if line.startswith("【文档"):
            # 保存上一个文档
            if current_doc is not None:
                current_doc.page_content = "\n".join(current_content)
                documents.append(current_doc)

            # 解析来源
            import re
            match = re.search(r"\[Ref: ([^\]]+)\]", line)
            source = match.group(1) if match else "未知来源"

            match = re.search(r"p\.(\d+)", line)
            page = int(match.group(1)) if match else None

            current_doc = Document(
                page_content="",
                metadata={"source": source, "page": page}
            )
            current_content = []
        elif current_doc is not None and line.startswith("内容:"):
            current_content.append(line[3:].strip())
        elif current_doc is not None and line.strip():
            current_content.append(line.strip())

    # 保存最后一个文档
    if current_doc is not None:
        current_doc.page_content = "\n".join(current_content)
        documents.append(current_doc)

    return documents


def create_grader_node(
    max_retries: int = 3,
    use_llm_judge: bool = True
):
    """
    创建 Grader 节点（Self-RAG 核心）

    作为"阅卷老师"，评估：
    1. Relevance: 检索到的文档是否能回答用户问题？
    2. Groundedness: 生成的答案是否基于文档（有无幻觉）？

    Args:
        max_retries: 最大重试次数
        use_llm_judge: 是否使用 LLM 判断（更准确但更慢）

    Returns:
        grader_node 函数
    """
    llm_service = get_llm_service()
    llm = llm_service.llm

    GRADER_PROMPT = """你是一个严格的评估老师。请评估以下回答的质量。

用户问题：{question}

检索到的相关资料：
{context}

待评估的回答：
{generation}

请从以下两个维度评估：

1. **Relevance（相关性）**：检索到的资料是否与问题相关？回答是否基于这些资料？
   - 如果相关：回答 "yes"
   - 如果不相关：回答 "no"

2. **Groundedness（准确性）**：回答是否基于提供的资料？是否存在幻觉（资料中找不到的内容）？
   - 如果 grounded：回答 "yes"
   - 如果有幻觉：回答 "no"

输出格式（JSON）：
{{
    "relevance": "yes" 或 "no",
    "groundedness": "yes" 或 "no",
    "reason": "简短解释原因"
}}"""

    async def grader_node(state: AgentState) -> AgentState:
        """
        Grader 节点

        评估回答质量，决定是否通过
        """
        generation = state.get("generation", "")
        documents = state.get("documents", [])
        query = state.get("current_query", "")
        retry_count = state.get("retry_count", 0)

        # 如果没有生成内容，直接返回
        if not generation:
            return {"retry_count": retry_count + 1}

        # 构建上下文
        context = ""
        for doc in documents:
            source = doc.metadata.get("source", "未知")
            page = doc.metadata.get("page", "")
            content = doc.page_content[:500]

            ref = f"[Ref: {source}"
            if page:
                ref += f", p.{page}"
            ref += "]"

            context += f"{ref}\n{content}\n\n"

        # 使用 LLM 评估
        if use_llm_judge and documents:
            prompt = GRADER_PROMPT.format(
                question=query,
                context=context,
                generation=generation
            )

            try:
                response = await llm_service.ainvoke([{"role": "user", "content": prompt}])

                # 解析响应
                import json
                import re

                response_text = response.content if hasattr(response, "content") else str(response)

                # 尝试提取 JSON
                match = re.search(r"\{[^}]+\}", response_text, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    relevance = result.get("relevance", "yes")
                    groundedness = result.get("groundedness", "yes")
                else:
                    # 简单解析
                    relevance = "yes" if "yes" in response_text.lower() else "no"
                    groundedness = "yes" if "yes" in response_text.lower() else "no"

            except Exception as e:
                logger.warning(f"LLM 评估失败: {e}，使用默认评估")
                relevance = "yes" if documents else "no"
                groundedness = "yes"
        else:
            # 简化评估：只要有文档就通过
            relevance = "yes" if documents else "no"
            groundedness = "yes"

        # 决定是否通过
        passed = (relevance == "yes" and groundedness == "yes")

        logger.info(
            f"Grader 评估: relevance={relevance}, groundedness={groundedness}, "
            f"passed={passed}, retry={retry_count}"
        )

        if passed:
            return {
                "retry_count": 0,  # 重置重试计数
            }
        elif retry_count >= max_retries:
            # 达到最大重试次数，强制返回当前结果
            logger.warning(f"达到最大重试次数 {max_retries}，强制返回")
            return {
                "retry_count": retry_count,
            }
        else:
            # 需要重试
            return {
                "retry_count": retry_count + 1,
                "generation": "",  # 清空生成，触发重新生成
                "documents": [],   # 清空文档，可能需要重新检索
            }

    return grader_node


# ==================== 辅助函数 ====================

def should_continue(state: AgentState) -> Literal["tools", "grade"]:
    """
    判断是否继续

    Returns:
        "tools": 继续执行工具
        "grade": 进入评估节点
    """
    messages = state["messages"]
    last_msg = messages[-1]

    # 检查是否有工具调用
    if hasattr(last_msg, "additional_kwargs") and \
       "tool_calls" in last_msg.additional_kwargs:
        return "tools"

    return "grade"


def should_retry(state: AgentState) -> Literal["agent", "outline_approval"]:
    """
    判断是否需要重试

    Returns:
        "agent": 重新执行 agent
        "outline_approval": 进入大纲确认环节
    """
    retry_count = state.get("retry_count", 0)
    max_retries = 3

    if retry_count >= max_retries:
        return "outline_approval"

    # 如果 generation 为空，说明需要重新生成
    if not state.get("generation"):
        return "agent"

    return "outline_approval"


# ==================== Human-in-the-loop 节点 ====================

def create_outline_approval_node():
    """
    大纲确认节点

    负责：
    1. 接收 Self-RAG 通过后的 generation
    2. 尝试解析为 JSON 存入 state["outline"]
    3. 设置 approved = False，等待用户确认

    此节点执行后会中断，等待用户调用 resume 接口
    """

    async def outline_approval_node(state: AgentState) -> AgentState:
        """
        大纲审批节点
        """
        generation = state.get("generation", "")

        if not generation:
            return {
                "outline": None,
                "approved": False,
                "messages": []
            }

        # 尝试解析 JSON
        outline = None
        parse_error = None

        try:
            import json
            import re

            # 尝试提取 JSON 块
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', generation)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个 generation
                json_str = generation

            outline = json.loads(json_str)

            logger.info(f"大纲解析成功: {type(outline)}")

        except json.JSONDecodeError as e:
            parse_error = str(e)
            logger.warning(f"JSON 解析失败: {parse_error}")
            outline = None

        except Exception as e:
            parse_error = str(e)
            logger.error(f"大纲处理异常: {parse_error}")
            outline = None

        # 更新状态，设置 approved = False 等待用户确认
        return {
            "outline": outline,
            "approved": False,
            "user_feedback": None,
            "messages": []
        }

    return outline_approval_node


def create_finalize_node():
    """
    最终确认节点

    当用户确认大纲后，执行最终处理：
    1. 遍历大纲的每一个章节
    2. 如果是用户新增的章节（只有标题），根据知识库扩写详细内容
    3. 输出完整的、可用于生成 PPT 的 JSON
    """

    EXPAND_PROMPT = """你是一个专业的教学课件生成助手。

用户已经确认并修改了大纲。请遍历大纲的每一个章节，进行内容扩写：

## 大纲结构
{outline_json}

## 要求
1. 如果该章节已有详细内容（content, notes），保留原内容
2. 如果该章节是**新增的**（只有标题 title，没有 content），请根据你的知识为该章节**扩写出详细的正文和演讲备注**
3. 演讲备注 (notes) 应该包含：
   - 要点提示
   - 讲解时长建议
   - 可能的提问点
4. 最终输出**完整的、可用于生成 PPT 的 JSON**

## 输出格式
```json
{{
    "title": "课程标题",
    "sections": [
        {{
            "title": "章节标题",
            "content": "章节正文内容（详细）",
            "notes": "演讲备注"
        }}
    ]
}}
```

请直接输出 JSON，不要有其他解释。"""

    async def finalize_node(state: AgentState) -> AgentState:
        """
        最终确认节点 - 内容扩写
        """
        from app.services.ai.dashscope_service import get_llm_service

        outline = state.get("outline")
        user_feedback = state.get("user_feedback")
        documents = state.get("documents", [])

        # 如果没有大纲，直接返回
        if not outline:
            logger.warning("finalize_node: 没有大纲内容")
            return {
                "approved": True,
                "generation": "抱歉，未找到有效的大纲内容。"
            }

        logger.info(f"finalize_node: 开始内容扩写，用户反馈={user_feedback}")

        # 构建上下文（如果有检索到的文档）
        context = ""
        if documents:
            for doc in documents[:3]:
                source = doc.metadata.get("source", "未知")
                page = doc.metadata.get("page", "")
                content = doc.page_content[:500]
                context += f"【{source} p.{page}】\n{content}\n\n"

        # 准备 prompt
        import json
        outline_json = json.dumps(outline, ensure_ascii=False, indent=2)

        prompt = EXPAND_PROMPT.format(outline_json=outline_json)

        # 如果有上下文，添加到 prompt
        if context:
            prompt += f"\n\n## 参考资料\n{context}\n\n请根据以上参考资料扩写内容。"

        # 调用 LLM 扩写
        llm_service = get_llm_service()

        try:
            response = await llm_service.ainvoke([
                {"role": "system", "content": "你是一个专业的教学课件生成助手，擅长生成结构清晰、内容丰富的教学大纲。"},
                {"role": "user", "content": prompt}
            ])

            # 提取 JSON
            generated_content = ""
            if hasattr(response, "content"):
                generated_content = response.content
            else:
                generated_content = str(response)

            # 尝试解析为 JSON
            final_outline = outline  # 默认使用原大纲
            try:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', generated_content)
                if json_match:
                    final_outline = json.loads(json_match.group(1))
                else:
                    final_outline = json.loads(generated_content)

                logger.info(f"finalize_node: 内容扩写成功")
            except json.JSONDecodeError:
                logger.warning(f"finalize_node: JSON 解析失败，使用原始大纲")
                # 如果解析失败，保留原始大纲

            return {
                "approved": True,
                "generation": generated_content,
                "outline": final_outline  # 返回扩写后的完整大纲
            }

        except Exception as e:
            logger.error(f"finalize_node: 内容扩写失败: {e}")
            # 扩写失败时，返回原始大纲
            return {
                "approved": True,
                "generation": json.dumps(outline, ensure_ascii=False),
                "outline": outline
            }

    return finalize_node


def should_await_approval(state: AgentState) -> Literal["outline_approval", "finalize"]:
    """
    判断是否需要等待用户确认大纲

    Returns:
        "outline_approval": 等待用户确认
        "finalize": 直接结束
    """
    return "outline_approval"
