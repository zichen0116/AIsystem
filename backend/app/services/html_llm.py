"""大模型对话服务。支持任意 OpenAI 兼容的 Chat API（OpenAI / 智谱 / 通义 / DeepSeek 等）。"""
from typing import Optional, AsyncGenerator, List, Dict, Any
import json
import httpx
from app.core.config import settings


def _choice_text_content(data: Dict[str, Any]) -> str:
    """从 chat/completions 的 JSON 中取出助手文本；兼容 content 为字符串或多段文本数组。"""
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    c = msg.get("content")
    if c is None:
        return ""
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        parts: List[str] = []
        for p in c:
            if isinstance(p, dict):
                if p.get("type") == "text" and p.get("text"):
                    parts.append(str(p["text"]))
                elif "text" in p:
                    parts.append(str(p.get("text") or ""))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts).strip()
    return str(c).strip()


async def call_llm_chat(
    messages: List[Dict[str, Any]],
    max_tokens: int = 2000,
    *,
    json_object: bool = False,
) -> str:
    """
    多轮对话调用大模型；messages 为 OpenAI 格式（须含 system 与若干 user/assistant）。
    json_object=True 时优先走 JSON 模式；若接口拒识、或 200 但 content 为空，会自动改走普通请求再试。
    失败返回空字符串。
    """
    if not settings.HTML_LLM_API_KEY:
        return ""
    base = (settings.HTML_LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HTML_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    plain_payload: Dict[str, Any] = {
        "model": settings.HTML_LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    attempt_payloads: List[Dict[str, Any]] = [plain_payload]
    if json_object:
        attempt_payloads.insert(
            0,
            {**plain_payload, "response_format": {"type": "json_object"}},
        )

    async with httpx.AsyncClient(timeout=300.0) as client:
        for pi, payload in enumerate(attempt_payloads):
            try:
                r = await client.post(url, json=payload, headers=headers)
                if (
                    r.status_code in (400, 422)
                    and payload.get("response_format") is not None
                ):
                    print(
                        "LLM call_llm_chat: json_object rejected:",
                        r.status_code,
                        (r.text or "")[:500],
                    )
                    continue
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as e:
                print(
                    "LLM call_llm_chat HTTP error:",
                    e.response.status_code,
                    e.response.text[:800] if e.response is not None else "",
                )
                if pi < len(attempt_payloads) - 1:
                    continue
                return ""
            except Exception as e:
                print("LLM call_llm_chat general error:", repr(e))
                return ""

            text = _choice_text_content(data)
            if text:
                return text
            print(
                "LLM call_llm_chat: 200 OK but empty content; attempt",
                pi,
                "body snippet:",
                json.dumps(data, ensure_ascii=False)[:900],
            )
            # 例如 JSON 模式下部分厂商仍返回空串，继续尝试下一套 payload（通常是不带 response_format）
    return ""


async def _call_llm(system: str, user: str, max_tokens: int = 1500) -> str:
    """调用大模型，返回回复文本；失败返回空字符串。"""
    if not settings.HTML_LLM_API_KEY:
        return ""
    base = (settings.HTML_LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HTML_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.HTML_LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
    }
    try:
        # 将超时时间从 60s 提高到 300s，便于长代码生成
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        # 打印 HTTP 级别错误，方便排查（例如 401/403/429 等）
        print(
            "LLM _call_llm HTTP error:",
            e.response.status_code,
            e.response.text[:500] if e.response is not None else "",
        )
        return ""
    except Exception as e:
        # 其它网络或解析错误
        print("LLM _call_llm general error:", repr(e))
        return ""
    choices = data.get("choices") or []
    if not choices:
        return ""
    return ((choices[0].get("message") or {}).get("content") or "").strip()


async def chat_with_llm(
    message: str,
    context_text: Optional[str] = None,
) -> tuple[str, list[str]]:
    """调用大模型得到回复和可选的建议句。若未配置 llm_api_key，则返回模拟回复。"""
    if not settings.HTML_LLM_API_KEY:
        return "", []

    base = (settings.HTML_LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HTML_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    system = (
        "你是教学对话小助手，擅长帮教师理解和重构教学内容，"
        "可以结合用户上传的教案（若有）进行解释、总结和改写。"
        "回答要简洁、清晰、友好。"
    )
    if context_text:
        system += f"\n\n以下是用户上传教学材料的摘要（供参考）：\n{context_text[:2000]}"

    # 自动续写逻辑：
    # 如果大模型因为长度上限中断（finish_reason == 'length'），
    # 在后端自动再调用最多 2 次续写，把多轮结果拼接后一次性返回前端。
    full_content: str = ""
    last_finish_reason: Optional[str] = None
    current_user_message: str = message

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            for round_idx in range(3):  # 最多 3 轮：1 次主回答 + 2 次续写
                payload = {
                    "model": settings.HTML_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": current_user_message},
                    ],
                    # 允许单轮生成较长代码/文本
                    "max_tokens": 6000,
                }
                r = await client.post(url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()

                choices = data.get("choices") or []
                if not choices:
                    break

                choice0 = choices[0] or {}
                finish_reason = choice0.get("finish_reason")
                last_finish_reason = finish_reason
                print(f"LLM chat finish_reason (round {round_idx + 1}):", finish_reason)

                chunk = (choice0.get("message") or {}).get("content") or ""
                chunk = chunk.strip()
                if not chunk:
                    break

                # 累积内容
                full_content += (("\n" if full_content else "") + chunk)

                # 如果不是因为长度被截断，就结束循环
                if finish_reason != "length":
                    break

                # 如果因为长度被截断，则构造下一轮“从中断处继续写”的指令
                tail = chunk[-2000:]
                current_user_message = (
                    "你刚才的回答因为长度限制被截断了。"
                    "请从刚才中断的位置继续往后写，不要重复已输出的内容，"
                    "只输出需要补充的后续部分。\n\n"
                    "这是你刚才回答的最后一部分，供你衔接使用：\n"
                    f"{tail}"
                )
    except httpx.HTTPStatusError as e:
        print(
            "LLM chat HTTP error:",
            e.response.status_code,
            e.response.text[:500] if e.response is not None else "",
        )
        return "", []
    except Exception as e:
        print("LLM chat general error:", repr(e))
        return "", []

    if not full_content:
        return "", []

    content = full_content.strip()

    # 多轮之后仍因长度被截断，在末尾附加提示，告知用户可能仍不完整
    if last_finish_reason == "length":
        content += "\n\n【提示：本次回复已达到长度上限，仍可能不完整，如需完整代码可拆分为多次生成。】"

    # 简单建议句（与原来保持一致）
    suggestions = [
        "帮我概括这份教案的重点",
        "根据这份教案设计几个课堂提问",
        "帮我把教学内容改写成适合学生理解的说法",
    ]
    return content, suggestions


async def chat_with_llm_stream(
    message: str,
    context_text: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """流式调用大模型，逐个 yield 文本片段。若未配置 API Key 则 yield 空后结束。"""
    if not settings.HTML_LLM_API_KEY:
        return

    base = (settings.HTML_LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HTML_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    system = (
        "你是教学对话小助手，擅长帮教师理解和重构教学内容，"
        "可以结合用户上传的教案（若有）进行解释、总结和改写。"
        "回答要简洁、清晰、友好。"
    )
    if context_text:
        system += f"\n\n以下是用户上传教学材料的摘要（供参考）：\n{context_text[:2000]}"

    payload = {
        "model": settings.HTML_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "max_tokens": 6000,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        choices = obj.get("choices") or []
                        if not choices:
                            continue
                        delta = (choices[0] or {}).get("delta") or {}
                        content = delta.get("content") or ""
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except httpx.HTTPStatusError as e:
        print(
            "LLM stream HTTP error:",
            e.response.status_code,
            e.response.text[:500] if e.response is not None else "",
        )
    except Exception as e:
        print("LLM stream general error:", repr(e))
