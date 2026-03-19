import test from 'node:test'
import assert from 'node:assert/strict'

import {
  CLARIFICATION_STEPS,
  buildClarificationRequest,
  getClarificationQuestion,
} from '../src/utils/pptOutlineFlow.js'

test('clarification flow asks one gentle question at a time', () => {
  assert.equal(CLARIFICATION_STEPS.length, 5)

  const question = getClarificationQuestion('中国传统文化', 0)
  assert.match(question, /中国传统文化/)
  assert.doesNotMatch(question, /1\.|2\.|3\./)
})

test('clarification request includes confirmed teaching intent', () => {
  const prompt = buildClarificationRequest('中国传统文化', {
    audience: '高中生',
    goal: '理解传统文化核心价值',
    duration: '20-25页',
    focus: '哲学与传统节日',
    style: '课堂讲授',
  })

  assert.match(prompt, /PPT主题：中国传统文化/)
  assert.match(prompt, /受众：高中生/)
  assert.match(prompt, /教学目标：理解传统文化核心价值/)
  assert.match(prompt, /重点内容：哲学与传统节日/)
})
