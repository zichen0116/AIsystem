export const CLARIFICATION_STEPS = [
  {
    key: 'audience',
    ask: (topic) => `好的，我先帮你梳理一下。这份“${topic}”PPT 主要是讲给什么学段或人群听呢？`,
  },
  {
    key: 'goal',
    ask: () => '明白了。那这份 PPT 里，你最希望学生最后收获什么，或者达成什么教学目标呢？',
  },
  {
    key: 'duration',
    ask: () => '收到。你预计这次大概讲多久，或者希望控制在多少页左右呢？',
  },
  {
    key: 'focus',
    ask: () => '好的。那你最想重点展开哪几个部分内容呢？我会把篇幅更多留给它们。',
  },
  {
    key: 'style',
    ask: () => '最后我再帮你确认一个小细节。你希望整体风格更偏课堂讲授、汇报展示，还是有别的偏好吗？',
  },
]

export function getClarificationQuestion(topic, stepIndex) {
  const step = CLARIFICATION_STEPS[stepIndex]
  if (!step) return ''
  return step.ask(topic)
}

export function buildClarificationRequest(topic, answers) {
  return [
    `PPT主题：${topic}`,
    '',
    '下面是已经和用户逐轮确认过的真实教学意图，请基于这些信息生成结构化 PPT 大纲：',
    `受众：${answers?.audience || '未明确'}`,
    `教学目标：${answers?.goal || '未明确'}`,
    `时长/页数：${answers?.duration || '未明确'}`,
    `重点内容：${answers?.focus || '未明确'}`,
    `风格偏好：${answers?.style || '未明确'}`,
    '',
    '请输出 markdown 大纲，要求主题、章节、页面层级清晰，语言适合教学场景。',
  ].join('\n')
}
