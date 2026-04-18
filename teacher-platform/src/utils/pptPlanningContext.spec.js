import {
  extractReferenceFileSummary,
  mergeReferenceSummariesIntoPlanningContext,
} from './pptPlanningContext'

describe('pptPlanningContext utils', () => {
  it('extracts a video summary from parsed_content.searchable_text', () => {
    const summary = extractReferenceFileSummary({
      filename: '课堂实录.mp4',
      parsed_content: {
        searchable_text: '本视频总结了生成式人工智能的课堂应用，包括概念导入、案例演示和互动设计。',
      },
    })

    expect(summary).toBe('本视频总结了生成式人工智能的课堂应用，包括概念导入、案例演示和互动设计。')
  })

  it('replaces stale completed-parse copy with the actual video summary', () => {
    const context = [
      '## 用户意图摘要',
      '主题：人工智能',
      '',
      '## 项目资料提炼',
      '- 课堂实录.mp4：已完成解析，可用于内容参考。',
      '',
      '## 知识库补充',
      '暂无',
    ].join('\n')

    const merged = mergeReferenceSummariesIntoPlanningContext(context, [
      {
        filename: '课堂实录.mp4',
        parsed_content: {
          searchable_text: '本视频总结了生成式人工智能的课堂应用，包括概念导入、案例演示和互动设计。',
        },
      },
    ])

    expect(merged).toContain('- 课堂实录.mp4：本视频总结了生成式人工智能')
    expect(merged).not.toContain('课堂实录.mp4：已完成解析，可用于内容参考。')
  })

  it('condenses legacy video time blocks instead of exposing keyframe logs', () => {
    const summary = extractReferenceFileSummary({
      filename: '课堂实录.mp4',
      parsed_content: {
        searchable_text: [
          '[时间块 0:00:00-0:00:20]',
          '',
          '【看到】[视频关键帧 at 0:00:00]',
          '这张截图显示的是一个名为 Edu Prep 的教学平台界面。',
          '',
          '【听到】老师正在介绍生成式人工智能在课堂导入、案例演示和互动提问中的应用。',
        ].join('\n'),
      },
    })

    expect(summary).toContain('视频概要')
    expect(summary).toContain('课堂导入')
    expect(summary).not.toContain('[时间块')
    expect(summary).not.toContain('视频关键帧')
  })

  it('ignores uninformative ASR when visual content is more useful', () => {
    const summary = extractReferenceFileSummary({
      filename: '平台演示.mp4',
      parsed_content: {
        searchable_text: [
          '[时间块 0:00:00-0:00:20]',
          '',
          '【看到】[视频关键帧 at 0:00:00]',
          '画面展示 Edu Prep 教育平台的浏览器页面，包含功能演示、令牌说明和教师备课入口。',
          '',
          '【听到】Thank you.',
        ].join('\n'),
      },
    })

    expect(summary).toContain('视频概要')
    expect(summary).toContain('Edu Prep')
    expect(summary).toContain('教师备课')
    expect(summary).not.toContain('Thank you')
  })

  it('replaces an existing keyframe line for the same video with video_summary', () => {
    const context = [
      '## 项目资料提炼',
      '- 平台演示.mp4：视频概要：这张截图显示的是一个名为 Edu Prep 的教育平台界面。',
      '',
      '## 知识库补充',
      '暂无',
    ].join('\n')

    const merged = mergeReferenceSummariesIntoPlanningContext(context, [
      {
        filename: '平台演示.mp4',
        parsed_content: {
          video_summary: '本视频整体演示智课坊平台的备课中心、PPT生成入口和教师备课流程。',
        },
      },
    ])

    expect(merged).toContain('本视频整体演示智课坊平台')
    expect(merged).not.toContain('这张截图显示')
  })
})
