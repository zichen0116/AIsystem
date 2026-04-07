from typing import List, Literal, Optional, Any, Dict, cast
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.services.html_llm import _call_llm, call_llm_chat


router = APIRouter(prefix="/question-generate", tags=["question-generate"])

ALLOWED_Q_TYPES = frozenset({"mc", "tf", "sa", "essay"})


class QuestionGenerateRequest(BaseModel):
    subject: str = Field(..., description="学科，例如：高等数学、计算机科学")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        "medium", description="难度等级：easy/medium/hard"
    )
    types: Optional[List[Literal["mc", "tf", "sa", "essay"]]] = Field(
        None,
        description="需要生成的题目类型列表；若提供 type_counts 可由服务端自动推导",
    )
    count: Optional[int] = Field(
        None,
        ge=1,
        le=50,
        description="题目总数；若提供 type_counts 则与 type_counts 之和一致",
    )
    type_counts: Optional[Dict[str, int]] = Field(
        None,
        description="各题型数量（mc/tf/sa/essay）；提供时按该分配命题，总数 1–50",
    )
    source: Optional[str] = Field(
        None,
        description="来源材料 / 知识点文本（可选，来自前端输入或文件解析）",
    )

    @model_validator(mode="after")
    def normalize_types_and_count(self) -> "QuestionGenerateRequest":
        if self.type_counts:
            for k, v in self.type_counts.items():
                if k not in ALLOWED_Q_TYPES:
                    raise ValueError(f"非法题型: {k}")
                if v < 1:
                    raise ValueError(f"题型 {k} 的数量至少为 1")
            total = sum(self.type_counts.values())
            if total > 50:
                raise ValueError("题目总数不能超过 50")
            object.__setattr__(self, "types", list(self.type_counts.keys()))
            object.__setattr__(self, "count", total)
            return self
        if not self.types:
            raise ValueError("至少选择一种题目类型")
        cnt = self.count if self.count is not None else 1
        object.__setattr__(self, "count", cnt)
        return self


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QuestionClarifyRequest(BaseModel):
    messages: List[ChatTurn] = Field(..., description="当前对话，含用户与助手轮次")
    material_text: Optional[str] = Field(
        None,
        description="用户在本页输入或上传解析得到的补充材料（供判断是否可开始生成）",
    )


class QuestionSpecPayload(BaseModel):
    """大模型在 ready=true 时返回的命题参数（经服务端校验）。"""

    subject: str
    knowledge_points: str = Field(
        ...,
        description="考察的知识点或范围说明（将并入生成时的 source）",
    )
    types: List[Literal["mc", "tf", "sa", "essay"]]
    counts_per_type: Dict[str, int]
    difficulty: Literal["easy", "medium", "hard"]
    wants_upload: bool = Field(
        ...,
        description="用户是否打算使用上传文件作为命题依据",
    )


class QuestionClarifyResponse(BaseModel):
    ready: bool
    assistant_message: str
    spec: Optional[QuestionSpecPayload] = None


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


_CLARIFY_SYSTEM = """你是「试题生成」助手，通过多轮对话向教师确认命题需求。你必须用中文交流。

需要确认的 6 项信息（缺一不可才能开始生成）：
1. 学科（subject）
2. 知识点或考察范围（knowledge_points）：用户用文字描述要考什么；若打算完全依赖上传文件，可简要写「见上传材料」
3. 题型（types）：从 mc(单选)、tf(判断)、sa(简答)、essay(论述) 中选至少一种
4. 每种已选题型的数量（counts_per_type）：键为 mc/tf/sa/essay，值为正整数；未选的题型不要出现在字典里；总数 1–50
5. 难度（difficulty）：easy / medium / hard
6. 是否要上传文件作为命题依据（wants_upload）：布尔值。若用户打算上传，必须等页面上已有材料文本（系统会告诉你「当前补充材料是否非空」）；若材料仍为空，你应继续追问请对方上传或粘贴，此时 ready 必须为 false。

【重要】多轮追问时，每一轮 assistant_message 里只能包含**一个**问题（一句问话），禁止在同一条回复里并列多个问号、禁止编号列表式连问（如「1.…2.…3.…」）。若多项未齐，只问**优先级最高**的那一项，下一轮再问下一项。

未齐多项时，按下面顺序每次只问一条（缺什么就从前往后找第一条缺的来问）：
- 先问学科 → 再问知识点 → 再问需要哪些题型 → 题型已定后再问每种各几题 → 再问难度 → 再问是否上传文件。
- 若用户已表示要上传但补充材料仍为空：本轮只问与上传/粘贴相关的一句话，不要同时问其它项。

规则：
- 每次只输出一个 JSON 对象，不要 Markdown、不要代码围栏、不要其它说明。
- 【格式硬性要求】整条回复中第一个非空白字符必须是左大括号 {，最后一个非空白字符必须是右大括号 }；不要在 JSON 前后增加任何寒暄、解释或「好的」等自然语言（自然语言只写在 JSON 字符串字段 assistant_message 的值里）。
- 若任一项未明确，或用户想上传但补充材料仍为空：ready=false，assistant_message 字段内仅为**一个**简短、自然的中文问句（可加一句礼貌承接，但只能有一个核心问题）。
- 若已全部明确，且（wants_upload 为 false，或补充材料非空）：ready=true，填写 spec，assistant_message 可一两句确认即将生成（不要生成题目内容）。
- spec.knowledge_points 要完整写出用户确认的知识点描述（可与对话摘要合并）。

JSON 形状（二选一）：
{"ready": false, "assistant_message": "..."}
或
{"ready": true, "assistant_message": "...", "spec": {
  "subject": "...",
  "knowledge_points": "...",
  "types": ["mc"],
  "counts_per_type": {"mc": 5},
  "difficulty": "medium",
  "wants_upload": false
}}
"""


def _material_nonempty(material_text: Optional[str]) -> bool:
    return bool((material_text or "").strip())


def _try_parse_clarify_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        extracted = _extract_first_json_object(raw)
        if not extracted:
            return None
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            return None


def _recover_assistant_prose_when_not_json(llm_text: str) -> Optional[str]:
    """
    若模型未按约定输出 JSON、但整段是自然语言，可展示给用户以免误报「你没说清楚」。
    一旦含有未解析成功的 {{ 则视为结构损坏，不展示原文以免混乱。
    """
    t = (llm_text or "").strip()
    if len(t) < 6:
        return None
    if "{" in t:
        return None
    out = t.replace("```", "").strip()
    if len(out) > 1800:
        out = out[:1800] + "…"
    return out or None


def _build_spec_from_dict(spec_raw: dict) -> Optional[QuestionSpecPayload]:
    try:
        types = spec_raw.get("types") or []
        counts = spec_raw.get("counts_per_type") or {}
        if not isinstance(types, list) or not isinstance(counts, dict):
            return None
        types_norm: List[Any] = []
        for t in types:
            if t not in ALLOWED_Q_TYPES:
                return None
            types_norm.append(t)
        if not types_norm:
            return None
        counts_norm: Dict[str, int] = {}
        for k, v in counts.items():
            if k not in ALLOWED_Q_TYPES:
                return None
            try:
                iv = int(v)
            except (TypeError, ValueError):
                return None
            if iv < 1:
                return None
            counts_norm[str(k)] = iv
        for t in types_norm:
            if t not in counts_norm:
                return None
        for k in counts_norm:
            if k not in types_norm:
                return None
        total = sum(counts_norm.values())
        if total > 50 or total < 1:
            return None
        diff = spec_raw.get("difficulty")
        if diff not in ("easy", "medium", "hard"):
            return None
        subj = (spec_raw.get("subject") or "").strip()
        if not subj:
            return None
        kp = (spec_raw.get("knowledge_points") or "").strip()
        if not kp:
            return None
        wu_raw = spec_raw.get("wants_upload")
        if isinstance(wu_raw, bool):
            wu = wu_raw
        elif isinstance(wu_raw, str):
            s = wu_raw.strip().lower()
            wu = s in ("true", "1", "yes", "y", "是", "要", "需要", "上传", "好")
        elif isinstance(wu_raw, (int, float)):
            wu = bool(int(wu_raw))
        else:
            return None
        return QuestionSpecPayload(
            subject=subj,
            knowledge_points=kp,
            types=cast(List[Literal["mc", "tf", "sa", "essay"]], types_norm),
            counts_per_type=counts_norm,
            difficulty=cast(Literal["easy", "medium", "hard"], diff),
            wants_upload=wu,
        )
    except Exception:
        return None


@router.post("/clarify", response_model=QuestionClarifyResponse)
async def clarify_question_requirements(body: QuestionClarifyRequest) -> Any:
    """
    多轮对话收集命题所需的 6 项信息；未齐全时返回追问，齐全时返回 spec 供前端调用正式生成接口。
    """
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")

    if not (settings.HTML_LLM_API_KEY or "").strip():
        raise HTTPException(
            status_code=503,
            detail="未配置 HTML_LLM_API_KEY，无法连接命题助手。请在 backend/.env 中填写后重启服务。",
        )

    mat_flag = "是" if _material_nonempty(body.material_text) else "否"
    sys_with_ctx = (
        _CLARIFY_SYSTEM
        + f"\n\n【系统状态】当前页面「补充材料」（用户粘贴或上传解析文本）是否非空：{mat_flag}。"
    )

    api_messages: List[Dict[str, str]] = [{"role": "system", "content": sys_with_ctx}]
    for turn in body.messages:
        api_messages.append({"role": turn.role, "content": turn.content})

    llm_text = await call_llm_chat(api_messages, max_tokens=2000, json_object=True)
    if not llm_text:
        raise HTTPException(
            status_code=502,
            detail=(
                "大模型接口未返回有效正文。请在后端控制台查看以「LLM call_llm_chat」开头的日志；"
                "并检查 HTML_LLM_BASE_URL、HTML_LLM_MODEL、密钥与余额/限流。"
            ),
        )

    data = _try_parse_clarify_json(llm_text)
    if not data:
        prose = _recover_assistant_prose_when_not_json(llm_text)
        if prose:
            return QuestionClarifyResponse(ready=False, assistant_message=prose, spec=None)
        print(
            "question-generate/clarify: JSON parse failed, raw (truncated):",
            llm_text[:900],
        )
        return QuestionClarifyResponse(
            ready=False,
            assistant_message=(
                "助手返回格式异常（应为 JSON），不是您输入的问题；请再点一次「发送」重试。"
                "若多次失败，请检查 HTML_LLM 模型是否支持严格 JSON 输出。"
            ),
            spec=None,
        )

    assistant_message = (data.get("assistant_message") or "").strip() or "请补充命题需求。"
    ready = bool(data.get("ready"))

    if not ready:
        return QuestionClarifyResponse(
            ready=False, assistant_message=assistant_message, spec=None
        )

    spec_raw = data.get("spec")
    if not isinstance(spec_raw, dict):
        return QuestionClarifyResponse(
            ready=False,
            assistant_message="还缺少完整的命题参数，请按学科、知识点、题型与每种题量、难度、是否上传文件说明一下。",
            spec=None,
        )

    spec = _build_spec_from_dict(spec_raw)
    if not spec:
        return QuestionClarifyResponse(
            ready=False,
            assistant_message="部分参数不合法或未对齐，请说明各题型（单选/判断/简答/论述）各需要几道题，总数不超过 50。",
            spec=None,
        )

    if spec.wants_upload and not _material_nonempty(body.material_text):
        return QuestionClarifyResponse(
            ready=False,
            assistant_message="您希望依据上传文件命题，请先点击上传或把材料粘贴到补充材料框中，再发送一条消息（例如「已粘贴」）。",
            spec=None,
        )

    return QuestionClarifyResponse(
        ready=True, assistant_message=assistant_message, spec=spec
    )


@router.post("", response_model=QuestionGenerateResponse)
async def generate_questions(payload: QuestionGenerateRequest) -> Any:
    """
    根据学科、题目类型、难度、数量和可选来源材料，调用 DeepSeek（通过 HTML_LLM_* 配置）
    生成试题列表。
    """
    # 各题型数量：优先使用 type_counts；否则在 types 间尽量平均分配
    type_counts: Dict[str, int]
    if payload.type_counts:
        type_counts = {k: int(v) for k, v in payload.type_counts.items()}
    else:
        type_counts = {}
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

