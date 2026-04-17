export const DEFAULT_INTENT_PENDING = [
  '受众基础层次',
  '核心教学目标',
  '章节重点和节奏',
  '互动形式与限制条件'
]

export const DEFAULT_INTENT_SCORES = {
  goal: 35,
  audience: 35,
  structure: 35,
  interaction: 35
}

export function createEmptyIntentSummary(initialTopic = '') {
  return {
    topic: initialTopic || '',
    audience: '',
    goal: '',
    duration: '',
    constraints: '',
    style: '',
    interaction: '',
    extra: ''
  }
}

export function createDefaultIntentState(initialTopic = '') {
  return {
    status: 'CLARIFYING',
    confirmed: [],
    pending: [...DEFAULT_INTENT_PENDING],
    scores: { ...DEFAULT_INTENT_SCORES },
    confidence: 35,
    ready_for_confirmation: false,
    summary: '继续澄清中',
    intent_summary: createEmptyIntentSummary(initialTopic),
    round: 0,
    confirmed_at: null
  }
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeList(value) {
  return Array.isArray(value)
    ? value.map(item => normalizeText(item)).filter(Boolean)
    : []
}

function normalizeScores(value) {
  const source = value && typeof value === 'object' ? value : {}
  return {
    goal: Number.isFinite(source.goal) ? Math.max(0, Math.min(100, Number(source.goal))) : DEFAULT_INTENT_SCORES.goal,
    audience: Number.isFinite(source.audience) ? Math.max(0, Math.min(100, Number(source.audience))) : DEFAULT_INTENT_SCORES.audience,
    structure: Number.isFinite(source.structure) ? Math.max(0, Math.min(100, Number(source.structure))) : DEFAULT_INTENT_SCORES.structure,
    interaction: Number.isFinite(source.interaction) ? Math.max(0, Math.min(100, Number(source.interaction))) : DEFAULT_INTENT_SCORES.interaction
  }
}

export function normalizeIntentState(payload, fallbackTopic = '') {
  const base = createDefaultIntentState(fallbackTopic)
  const source = payload && typeof payload === 'object' ? payload : {}
  const summary = source.intent_summary && typeof source.intent_summary === 'object'
    ? source.intent_summary
    : source.intentSummary

  const normalizedSummary = {
    ...base.intent_summary,
    ...Object.fromEntries(
      Object.keys(base.intent_summary).map((key) => [key, normalizeText(summary?.[key]) || base.intent_summary[key]])
    )
  }

  const pending = normalizeList(source.pending)
  const status = normalizeText(source.status) || (source.ready_for_confirmation ? 'READY' : 'CLARIFYING')

  return {
    status,
    confirmed: normalizeList(source.confirmed),
    pending: pending.length ? pending : (status === 'CLARIFYING' ? [...DEFAULT_INTENT_PENDING] : []),
    scores: normalizeScores(source.scores),
    confidence: Number.isFinite(source.confidence) ? Math.max(0, Math.min(100, Number(source.confidence))) : base.confidence,
    ready_for_confirmation: Boolean(source.ready_for_confirmation ?? (status !== 'CLARIFYING')),
    summary: normalizeText(source.summary) || base.summary,
    intent_summary: normalizedSummary,
    round: Number.isFinite(source.round) ? Number(source.round) : base.round,
    confirmed_at: source.confirmed_at || null
  }
}

export function intentSummaryToText(summary) {
  const source = summary && typeof summary === 'object' ? summary : {}
  const parts = []
  if (source.topic) parts.push(`主题：${source.topic}`)
  if (source.audience) parts.push(`受众：${source.audience}`)
  if (source.goal) parts.push(`目标：${source.goal}`)
  if (source.duration) parts.push(`课时：${source.duration}`)
  if (source.constraints) parts.push(`约束：${source.constraints}`)
  if (source.style) parts.push(`风格：${source.style}`)
  if (source.interaction) parts.push(`互动：${source.interaction}`)
  if (source.extra) parts.push(`其他：${source.extra}`)
  return parts.join('\n\n')
}

export function buildOutlinePromptFromIntent(summary) {
  const source = summary && typeof summary === 'object' ? summary : {}
  const parts = []
  if (source.topic) parts.push(`主题：${source.topic}`)
  if (source.audience) parts.push(`受众：${source.audience}`)
  if (source.goal) parts.push(`目标：${source.goal}`)
  if (source.duration) parts.push(`课时：${source.duration}`)
  if (source.constraints) parts.push(`约束：${source.constraints}`)
  if (source.style) parts.push(`风格：${source.style}`)
  if (source.interaction) parts.push(`互动：${source.interaction}`)
  if (source.extra) parts.push(`其他：${source.extra}`)
  return parts.join('\n')
}

export function resolveIntentPhase(project, pageCount, intentState) {
  if (project?.cover_image_url) return 'preview'
  if (project?.creation_type === 'renovation') return 'description'
  if (pageCount > 0) return 'outline'
  if (intentState?.status === 'CONFIRMED') return 'outline'
  if (project?.status === 'INTENT_CONFIRMED') return 'outline'
  if (project?.creation_type === 'dialog') return 'dialog'
  return 'outline'
}
