from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.html_llm import _call_llm


router = APIRouter(prefix="/mindmap", tags=["mindmap"])


LayoutType = Literal["center", "split", "timeline"]


class MindmapNode(BaseModel):
    title: str = Field(..., description="节点标题")
    children: List["MindmapNode"] = Field(default_factory=list, description="子节点")


MindmapNode.model_rebuild()


class MindmapGenerateRequest(BaseModel):
    layout: LayoutType = Field("center", description="布局：center/split/timeline")
    prompt: str = Field(..., min_length=1, description="用户输入的主题/要点")
    source: Optional[str] = Field(None, description="可选：上传材料提取文本或补充材料")


class MindmapGenerateResponse(BaseModel):
    layout: LayoutType
    root: Optional[MindmapNode] = None
    raw_text: Optional[str] = Field(
        None, description="模型未按 JSON 返回时的原始文本"
    )

class MindmapGenerateMarkdownResponse(BaseModel):
    markdown: str = Field(..., description="用于 markmap 渲染的 Markdown")


def _extract_first_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    s = text.strip()
    if "```" in s:
        s = s.replace("```json", "```").replace("```JSON", "```")
        parts = s.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("{") and p.endswith("}"):
                return p
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


@router.post("/generate", response_model=MindmapGenerateResponse)
async def generate_mindmap(payload: MindmapGenerateRequest) -> Any:
    system = (
        "你是一名擅长结构化知识整理的教学助手。"
        "你的任务是把用户输入的主题与要点，整理为思维导图的树形结构。"
        "你必须只输出一个 JSON 对象，不要输出 Markdown，不要输出多余说明。\n\n"
        "输出 JSON 的格式如下：\n"
        "{\n"
        '  \"layout\": \"center\",\n'
        '  \"root\": {\n'
        '    \"title\": \"主题\",\n'
        '    \"children\": [\n'
        '      {\"title\": \"一级要点\", \"children\": [ {\"title\": \"二级要点\", \"children\": []} ]}\n'
        "    ]\n"
        "  }\n"
        "}\n\n"
        "约束：\n"
        "- root.title 为主题概括（尽量不超过 20 字）\n"
        "- 深度建议 3-4 层\n"
        "- 每个节点 children 最多 6 个\n"
        "- 节点 title 以短语为主（不超过 30 字），避免长段落\n"
    )

    user_parts = [
        f"用户选择的布局：{payload.layout}",
        "用户输入：",
        payload.prompt.strip()[:2000],
    ]
    if payload.source:
        user_parts.extend(
            [
                "",
                "以下是用户上传/提供的参考材料（必须参考整理）：",
                payload.source.strip()[:4000],
            ]
        )
    else:
        user_parts.extend(["", "用户未上传材料，仅根据用户输入整理。"])

    user = "\n".join(user_parts)

    llm_text = await _call_llm(system, user, max_tokens=3000)
    if not llm_text:
        raise HTTPException(status_code=500, detail="调用大模型失败或未返回内容")

    raw = llm_text.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        extracted = _extract_first_json_object(raw)
        if not extracted:
            return MindmapGenerateResponse(layout=payload.layout, root=None, raw_text=raw)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            return MindmapGenerateResponse(layout=payload.layout, root=None, raw_text=raw)

    layout = data.get("layout") or payload.layout
    root_data = data.get("root")
    try:
        root = MindmapNode(**root_data) if isinstance(root_data, dict) else None
    except Exception:
        root = None

    if not root:
        return MindmapGenerateResponse(layout=payload.layout, root=None, raw_text=raw)

    # 限制 children 数量，避免过大
    def _trim(node: MindmapNode, depth: int = 0) -> MindmapNode:
        node.children = node.children[:6]
        if depth >= 4:
            node.children = []
            return node
        node.children = [_trim(c, depth + 1) for c in node.children]
        return node

    root = _trim(root)

    return MindmapGenerateResponse(layout=layout, root=root, raw_text=None)


@router.post("/generate_markdown", response_model=MindmapGenerateMarkdownResponse)
async def generate_mindmap_markdown(payload: MindmapGenerateRequest) -> Any:
    system = (
        "你是一名擅长结构化知识整理的教学助手。"
        "你的任务是把用户输入的主题与要点整理为一份可用于 markmap 渲染的 Markdown 思维导图。"
        "你必须只输出 Markdown 正文，不要输出代码块围栏（不要```），不要输出多余说明。\n\n"
        "格式要求：\n"
        "- 用 1 个一级标题（#）作为主题（尽量不超过 20 字）\n"
        "- 用二级标题（##）表示一级分支\n"
        "- 用无序列表（-）表示更深层级的子要点\n"
        "- 深度建议 3-4 层\n"
        "- 每层最多 6 个点\n"
        "- 每个要点尽量短（不超过 30 字），避免长段落\n"
    )

    user_parts = [
        f"用户选择的布局（仅供参考）：{payload.layout}",
        "用户输入：",
        payload.prompt.strip()[:2000],
    ]
    if payload.source:
        user_parts.extend(
            [
                "",
                "以下是用户上传/提供的参考材料（必须参考整理）：",
                payload.source.strip()[:4000],
            ]
        )
    else:
        user_parts.extend(["", "用户未上传材料，仅根据用户输入整理。"])

    user = "\n".join(user_parts)

    llm_text = await _call_llm(system, user, max_tokens=2500)
    if not llm_text:
        raise HTTPException(status_code=500, detail="调用大模型失败或未返回内容")

    md = llm_text.strip()
    # 容错：去掉可能的 ``` 包裹
    if "```" in md:
        md = md.replace("```markdown", "```").replace("```md", "```")
        parts = [p.strip() for p in md.split("```") if p.strip()]
        # 优先取最长的片段当正文
        md = max(parts, key=len) if parts else llm_text.strip()

    return MindmapGenerateMarkdownResponse(markdown=md)

