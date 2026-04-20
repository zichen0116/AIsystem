import { describe, expect, it } from 'vitest'
import { normalizeIntentState } from './pptIntent'

describe('normalizeIntentState', () => {
  it('keeps first-round intent values from the backend', () => {
    const intent = normalizeIntentState({
      round: 1,
      confidence: 65,
      scores: {
        goal: 90,
        audience: 95,
        structure: 70,
        interaction: 30
      },
      summary: '已明确主题、年级、基础认知、课时、页数和核心目标；待确认先备知识、风格倾向与互动安排。'
    })

    expect(intent.confidence).toBe(65)
    expect(intent.scores).toEqual({
      goal: 90,
      audience: 95,
      structure: 70,
      interaction: 30
    })
    expect(intent.summary).toBe('已明确主题、年级、基础认知、课时、页数和核心目标；待确认先备知识、风格倾向与互动安排。')
  })

  it('locks second-round confidence, matrix scores, and summary', () => {
    const intent = normalizeIntentState({
      round: 2,
      confidence: 65,
      scores: {
        goal: 90,
        audience: 95,
        structure: 70,
        interaction: 30
      },
      summary: '继续澄清中'
    })

    expect(intent.confidence).toBe(75)
    expect(intent.scores).toEqual({
      goal: 90,
      audience: 95,
      structure: 80,
      interaction: 50
    })
    expect(intent.summary).toBe('因明确教学风格，互动设计，待确认课件偏好')
  })

  it('locks second-round values when the response round is supplied separately', () => {
    const intent = normalizeIntentState({
      confidence: 35,
      scores: {
        goal: 35,
        audience: 35,
        structure: 35,
        interaction: 35
      },
      summary: '继续澄清中'
    }, '', 2)

    expect(intent.round).toBe(2)
    expect(intent.confidence).toBe(75)
    expect(intent.scores).toEqual({
      goal: 90,
      audience: 95,
      structure: 80,
      interaction: 50
    })
    expect(intent.summary).toBe('因明确教学风格，互动设计，待确认课件偏好')
  })
})
