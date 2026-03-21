"""
调用 Dify Workflow「资源推荐助手」并解析为前端卡片结构。
工作流开始节点变量：course_name、node_name（与 Dify 编排保持一致）。
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_ICONS = ["📚", "🧬", "⚛️", "🤖", "📊", "🌐", "📘", "🧪", "🔐", "🏙️", "📝", "🎓"]


def build_resource_workflow_inputs(
    keyword: str,
    grade: str,
    subject: str,
    file_type: str,
    sort_by: str,
) -> Dict[str, str]:
    kw = (keyword or "").strip()
    course = (subject or "").strip()
    if course in ("", "全部学科"):
        course = "综合"

    parts = []
    if kw:
        parts.append(kw)
    filters = []
    if grade and grade != "全部年级":
        filters.append(f"年级:{grade}")
    if file_type and file_type != "全部类型":
        filters.append(f"类型:{file_type}")
    if sort_by and sort_by != "相关度优先":
        filters.append(f"排序:{sort_by}")
    if filters:
        parts.append("（" + "，".join(filters) + "）")

    # 无关键词时由上层返回 400；此处不再用课程名顶替，避免空搜误触 Dify
    node_name = "\n".join(parts) if parts else ""
    return {"course_name": course, "node_name": node_name}


def _extract_json_block(text: str) -> Optional[str]:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _coerce_resource_list(data: Any) -> Optional[List[dict]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "resources", "data", "list", "结果"):
            v = data.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return None


def _normalize_item(obj: dict, idx: int) -> dict:
    title = (
        obj.get("title")
        or obj.get("name")
        or obj.get("主题")
        or obj.get("resource_title")
        or f"推荐资源 {idx + 1}"
    )
    if not isinstance(title, str):
        title = str(title)

    tag = (
        obj.get("tag")
        or obj.get("subject")
        or obj.get("学科")
        or obj.get("category")
        or ""
    )
    if not isinstance(tag, str):
        tag = str(tag)

    desc = (
        obj.get("desc")
        or obj.get("description")
        or obj.get("summary")
        or obj.get("简介")
        or obj.get("content")
        or ""
    )
    if not isinstance(desc, str):
        desc = str(desc)

    icon = obj.get("icon") or obj.get("emoji") or DEFAULT_ICONS[idx % len(DEFAULT_ICONS)]
    if not isinstance(icon, str):
        icon = str(icon)[:4] or DEFAULT_ICONS[idx % len(DEFAULT_ICONS)]

    url = obj.get("url") or obj.get("link") or obj.get("href") or ""
    if not isinstance(url, str):
        url = str(url) if url is not None else ""
    url = url.strip()

    return {
        "id": str(obj.get("id") or uuid.uuid4()),
        "title": title.strip() or f"推荐资源 {idx + 1}",
        "tag": tag.strip(),
        "desc": desc.strip(),
        "icon": icon,
        "url": url or None,
    }


MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", re.IGNORECASE)


def _guess_icon_from_line_prefix(prefix: str) -> str:
    for emo in ("📺", "💻", "📖", "🏫", "🔗", "🎓", "📚", "🌐", "⭐", "💡"):
        if emo in prefix[:32]:
            return emo
    return "📚"


def parse_markdown_link_items(text: str) -> List[dict]:
    """
    从 Dify 常见输出中解析 [标题](https://...) ，每条生成一张可跳转卡片。
    """
    if not text or not str(text).strip():
        return []

    raw = str(text).replace("\r\n", "\n")
    matches = list(MD_LINK_RE.finditer(raw))
    if not matches:
        return []

    out: List[dict] = []
    for idx, m in enumerate(matches):
        title = (m.group(1) or "").strip()
        url = (m.group(2) or "").strip().rstrip(".,;)]}\"'")
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        desc = raw[start:end].strip()
        desc = re.sub(r"^[\s\-–—:|·，,、]+", "", desc)
        desc = re.sub(r"\s+", " ", desc)
        if len(desc) > 800:
            desc = desc[:797] + "..."

        line_start = raw.rfind("\n", 0, m.start()) + 1
        line_prefix = raw[line_start : m.start()]
        icon = _guess_icon_from_line_prefix(line_prefix.strip())

        out.append(
            {
                "id": str(uuid.uuid4()),
                "title": title or f"资源 {idx + 1}",
                "tag": "",
                "desc": desc,
                "icon": icon,
                "url": url,
            }
        )
    return out


def enrich_json_items_with_urls(items: List[dict]) -> List[dict]:
    """若 JSON 项未带 url 但 desc 中含 Markdown 链接，补全第一条链接。"""
    enriched = []
    for i, obj in enumerate(items):
        if not isinstance(obj, dict):
            continue
        url = obj.get("url") or obj.get("link")
        if url:
            enriched.append(obj)
            continue
        desc = obj.get("desc") or obj.get("description") or ""
        if not isinstance(desc, str):
            desc = str(desc)
        m = MD_LINK_RE.search(desc)
        if m:
            u = m.group(2).strip().rstrip(".,;)]}\"'")
            rest = MD_LINK_RE.sub("", desc, count=1).strip()
            obj = {**obj, "url": u, "desc": rest}
        enriched.append(obj)
    return enriched


def parse_llm_output_to_items(text: str) -> List[dict]:
    """将工作流 LLM 输出解析为资源卡片列表。"""
    if not text or not str(text).strip():
        return []

    raw = str(text).strip()
    candidates = [raw]
    inner = _extract_json_block(raw)
    if inner:
        candidates.insert(0, inner)

    for cand in candidates:
        try:
            data = json.loads(cand)
            lst = _coerce_resource_list(data)
            if lst:
                lst = enrich_json_items_with_urls(lst)
                return [_normalize_item(x, i) for i, x in enumerate(lst)]
        except json.JSONDecodeError:
            continue

    # 尝试从全文截取第一个 JSON 数组
    start = raw.find("[")
    end = raw.rfind("]")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start : end + 1])
            lst = _coerce_resource_list(data)
            if lst:
                lst = enrich_json_items_with_urls(lst)
                return [_normalize_item(x, i) for i, x in enumerate(lst)]
        except json.JSONDecodeError:
            pass

    # Markdown [标题](url) 多资源（Dify 工作流常见输出）
    md_items = parse_markdown_link_items(raw)
    if md_items:
        return md_items

    # 兜底：单条卡片展示全文（截断）
    snippet = raw.replace("\r\n", "\n").strip()
    if len(snippet) > 2000:
        snippet = snippet[:1997] + "..."
    return [
        {
            "id": str(uuid.uuid4()),
            "title": "智能推荐结果",
            "tag": "综合",
            "desc": snippet,
            "icon": "📚",
            "url": None,
        }
    ]


def _collect_output_text(outputs: Any) -> str:
    """Dify 工作流 outputs 结构因编排而异，尽量拼出可读文本。"""
    if outputs is None:
        return ""
    if isinstance(outputs, str):
        return outputs
    if isinstance(outputs, dict):
        # 常见字段名（含 LLM 节点嵌套）
        for key in ("text", "output", "result", "answer", "content", "llm", "response"):
            v = outputs.get(key)
            if isinstance(v, str) and v.strip():
                return v
            if isinstance(v, dict):
                inner = _collect_output_text(v)
                if inner.strip():
                    return inner
        # 任意第一个非空字符串
        for v in outputs.values():
            if isinstance(v, str) and v.strip():
                return v
            if isinstance(v, (list, dict)):
                s = _collect_output_text(v)
                if s:
                    return s
        return json.dumps(outputs, ensure_ascii=False)
    if isinstance(outputs, list):
        parts = []
        for x in outputs:
            s = _collect_output_text(x)
            if s:
                parts.append(s)
        return "\n".join(parts)
    return str(outputs)


async def run_resource_recommend_workflow(
    *,
    course_name: str,
    node_name: str,
    dify_user: str,
) -> Tuple[List[dict], Optional[str], Optional[str]]:
    """
    调用 Dify POST /workflows/run（blocking）。
    返回 (items, raw_text, workflow_run_id)
    """
    api_key = (settings.DIFY_RESOURCE_WORKFLOW_API_KEY or "").strip()
    if not api_key:
        raise ValueError("未配置 DIFY_RESOURCE_WORKFLOW_API_KEY，请在 backend/.env 中填写 Dify 工作流 API 密钥")

    base = (settings.DIFY_API_BASE_URL or "https://api.dify.ai/v1").rstrip("/")
    url = f"{base}/workflows/run"

    payload = {
        "inputs": {
            "course_name": course_name,
            "node_name": node_name,
        },
        "response_mode": "blocking",
        "user": dify_user,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(180.0, connect=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        detail = resp.text[:2000]
        try:
            err_j = resp.json()
            detail = err_j.get("message") or err_j.get("detail") or detail
        except Exception:
            pass
        logger.warning("Dify workflow HTTP %s: %s", resp.status_code, detail)
        raise RuntimeError(f"Dify 请求失败 ({resp.status_code}): {detail}")

    body = resp.json()
    workflow_run_id = body.get("workflow_run_id") or body.get("task_id")

    data = body.get("data") or body
    status = (data.get("status") if isinstance(data, dict) else None) or body.get("status")
    if status and str(status).lower() in ("failed", "error", "stopped"):
        err = data.get("error") if isinstance(data, dict) else None
        raise RuntimeError(f"Dify 工作流执行失败: {err or body}")

    outputs = data.get("outputs") if isinstance(data, dict) else None
    raw_text = _collect_output_text(outputs)
    items = parse_llm_output_to_items(raw_text)

    return items, raw_text, workflow_run_id
