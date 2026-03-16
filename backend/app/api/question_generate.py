from typing import List, Literal, Optional, Any, Dict
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from app.services.html_llm import _call_llm


router = APIRouter(prefix="/question-generate", tags=["question-generate"])


class QuestionGenerateRequest(BaseModel):
    subject: str = Field(..., description="学科，例如：高等数学、计算机科学")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        "medium", description="难度等级：easy/medium/hard"
    )
    types: List[Literal["mc", "tf", "sa", "essay"]] = Field(
        ..., description="需要生成的题目类型列表"
    )
    count: int = Field(
        1,
        ge=1,
        le=50,
        description="题目数量，1-50 之间的整数",
    )
    source: Optional[str] = Field(
        None,
        description="来源材料 / 知识点文本（可选，来自前端输入或文件解析）",
    )

    @validator("types")
    def validate_types(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("至少选择一种题目类型")
        return v


class QuestionOption(BaseModel):
    label: str
    text: str


class GeneratedQuestion(BaseModel):
    type: Literal["mc", "tf", "sa", "essay"]
    stem: str
    options: Optional[List[QuestionOption]] = None
    answer: Optional[Any] = None
    analysis: Optional[str] = None


class QuestionGenerateResponse(BaseModel):
    subject: str
    difficulty: str
    count: int
    questions: List[GeneratedQuestion]
    raw_text: Optional[str] = Field(
        None,
        description="当大模型未能严格按 JSON 返回时，保留原始文本以便前端展示/排查",
    )


def _extract_first_json_object(text: str) -> Optional[str]:
    """
    从任意文本中提取第一个 JSON 对象（最外层 {}），用于容错处理：
    - 模型可能返回带解释文字
    - 或返回 ```json ... ``` 包裹
    - 或把 JSON 作为字符串片段嵌在段落里
    """
    if not text:
        return None
    s = text.strip()
    # 去掉常见的 Markdown code fence
    if "```" in s:
        s = s.replace("```json", "```").replace("```JSON", "```")
        parts = s.split("```")
        # 尝试在 code fence 片段里找 JSON
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
        else:
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


def _normalize_tf_answer(ans: Any) -> Optional[str]:
    """
    统一判断题答案格式，前端按字符串 'true'/'false' 展示。
    允许模型输出：true/false、正确/错误、对/错、T/F、1/0 等。
    """
    if ans is None:
        return None
    if isinstance(ans, bool):
        return "true" if ans else "false"
    s = str(ans).strip().lower()
    if s in {"true", "t", "1", "yes", "y", "正确", "对"}:
        return "true"
    if s in {"false", "f", "0", "no", "n", "错误", "错"}:
        return "false"
    # 尝试包含判断
    if "正确" in s or "为真" in s or "true" in s:
        return "true"
    if "错误" in s or "为假" in s or "false" in s:
        return "false"
    return str(ans).strip()


def _postprocess_questions(questions: List[GeneratedQuestion]) -> List[GeneratedQuestion]:
    """
    按题型修正字段，避免不同题型混用字段导致前端展示异常。
    """
    fixed: List[GeneratedQuestion] = []
    for q in questions:
        if q.type == "mc":
            # 单选题必须有 options，且答案建议为 A/B/C/D
            fixed.append(q)
            continue
        if q.type == "tf":
            q.options = None
            q.answer = _normalize_tf_answer(q.answer)
            fixed.append(q)
            continue
        # 简答/论述不需要 options
        q.options = None
        if q.answer is not None and not isinstance(q.answer, str):
            q.answer = str(q.answer)
        fixed.append(q)
    return fixed


@router.post("", response_model=QuestionGenerateResponse)
async def generate_questions(payload: QuestionGenerateRequest) -> Any:
    """
    根据学科、题目类型、难度、数量和可选来源材料，调用 DeepSeek（通过 HTML_LLM_* 配置）
    生成试题列表。
    """
    # 计算各题型应生成的题目数：尽量平均分配，若无法整除则从前几种题型开始每个多 1 题
    type_counts: Dict[str, int] = {}
    base = payload.count // len(payload.types)
    remainder = payload.count % len(payload.types)
    for idx, t in enumerate(payload.types):
        type_counts[t] = base + (1 if idx < remainder else 0)

    # 构造系统提示，定义输出格式
    system_prompt = (
        "你是一名资深命题专家，负责为教师生成符合教学大纲的考试试题。"
        "请严格按照指定的 JSON 结构输出，不要添加任何多余的说明文字。"
        "\n\n"
        "你必须严格输出一个 JSON 对象，且仅输出 JSON（不要 Markdown，不要反引号，不要多余文本）。\n"
        "\n"
        "题型字段约束：\n"
        "- mc（单选题）：必须包含 options（A-D 四项），answer 为 'A'/'B'/'C'/'D'\n"
        "- tf（判断题）：不要包含 options，answer 为 true/false（布尔值）\n"
        "- sa（简答题）：不要包含 options，answer 为参考答案文本\n"
        "- essay（论述题）：不要包含 options，answer 为要点式参考答案文本\n"
        "\n"
        "JSON 输出格式示例（注意这只是结构示例，内容请根据用户要求重写）：\n"
        "{\n"
        '  \"subject\": \"高等数学\",\n'
        '  \"difficulty\": \"medium\",\n'
        '  \"count\": 3,\n'
        '  \"questions\": [\n'
        "    {\n"
        '      \"type\": \"mc\",\n'
        '      \"stem\": \"已知函数 f(x)=x^2 ，则 f(2) 等于多少？\",\n'
        '      \"options\": [\n'
        '        {\"label\": \"A\", \"text\": \"2\"},\n'
        '        {\"label\": \"B\", \"text\": \"4\"},\n'
        '        {\"label\": \"C\", \"text\": \"6\"},\n'
        '        {\"label\": \"D\", \"text\": \"8\"}\n'
        "      ],\n"
        '      \"answer\": \"B\",\n'
        '      \"analysis\": \"将 x=2 代入 f(x)=x^2，得到 f(2)=4。\"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )

    # 构造用户提示，带入学科、题型、难度、数量和来源材料
    type_map = {
        "mc": "单选题",
        "tf": "判断题",
        "sa": "简答题",
        "essay": "论述题",
    }
    type_names = [type_map[t] for t in payload.types]

    user_parts = [
        f"学科：{payload.subject}",
        f"难度：{payload.difficulty}（easy=简单，medium=中等，hard=困难）",
        f"题目类型：{', '.join(type_names)}",
        f"题目数量：{payload.count}",
        "请根据以上配置生成对应数量的试题，并给出标准答案与简要解析。",
        f"题型与题目数量的分配如下（必须严格遵守）：{type_counts}。",
        f"注意：questions 数组长度必须严格等于 {payload.count}，且每题的 type 必须在：{payload.types} 之中，并且每种题型的题目数量要与上述 {type_counts} 完全一致。",
        "题目要贴近中国中高等教育课堂场景，符合教学常识。",
    ]

    if payload.source:
        user_parts.append(
            "以下是教师提供的来源材料 / 知识点，请务必在命题时严格围绕这些内容命题：\n"
            f"{payload.source[:4000]}"
        )
    else:
        user_parts.append("教师没有提供额外材料，请根据常规教材知识点合理命题。")

    user_prompt = "\n".join(user_parts)

    llm_text = await _call_llm(system_prompt, user_prompt, max_tokens=4000)
    if not llm_text:
        raise HTTPException(status_code=500, detail="调用大模型失败或未返回内容")

    raw_text = llm_text.strip()

    # 优先尝试解析为 JSON；若失败，尝试从文本中抽取 JSON；仍失败则返回 raw_text
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        extracted = _extract_first_json_object(raw_text)
        if not extracted:
            return QuestionGenerateResponse(
                subject=payload.subject,
                difficulty=payload.difficulty,
                count=payload.count,
                questions=[],
                raw_text=raw_text,
            )
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            return QuestionGenerateResponse(
                subject=payload.subject,
                difficulty=payload.difficulty,
                count=payload.count,
                questions=[],
                raw_text=raw_text,
            )

    # 容错：大模型返回的 JSON 里可能没有 subject/difficulty/count 字段
    subject = str(data.get("subject") or payload.subject)
    difficulty = str(data.get("difficulty") or payload.difficulty)
    count = int(data.get("count") or payload.count)
    questions_data = data.get("questions") or []

    try:
        questions = [GeneratedQuestion(**q) for q in questions_data]
    except Exception:
        # 结构不完全符合预期时，也把原始 JSON 文本放到 raw_text 中
        return QuestionGenerateResponse(
            subject=subject,
            difficulty=difficulty,
            count=count,
            questions=[],
            raw_text=raw_text,
        )

    questions = _postprocess_questions(questions)

    return QuestionGenerateResponse(
        subject=subject,
        difficulty=difficulty,
        count=count,
        questions=questions,
        raw_text=None,
    )

