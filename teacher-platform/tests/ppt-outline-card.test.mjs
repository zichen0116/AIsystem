import test from 'node:test'
import assert from 'node:assert/strict'

import {
  hasRenderableOutlinePayload,
  markdownToOutlinePayload,
  payloadToMarkdown,
} from '../src/utils/pptOutlineCard.js'

test('markdownToOutlinePayload parses flat page outlines into page cards with image candidates', () => {
  const payload = markdownToOutlinePayload(
    `# 中国传统文化

## 第 1 页：封面与课程信息
- 主标题：中国传统文化
- 适用对象：本科生

## 第 2 页：教学目标与课程导入
- 核心目标：建立整体认识
`,
    {
      0: ['https://img.example.com/cover-a.png', 'https://img.example.com/cover-b.png'],
      1: ['https://img.example.com/goal-a.png', 'https://img.example.com/goal-b.png'],
    },
  )

  assert.equal(payload.title, '中国传统文化')
  assert.equal(hasRenderableOutlinePayload(payload), true)
  assert.equal(payload.sections.length, 1)
  assert.equal(payload.sections[0].pages.length, 2)
  assert.equal(payload.sections[0].pages[0].image_candidates.length, 2)
})

test('payloadToMarkdown keeps selected image and page content', () => {
  const markdown = payloadToMarkdown({
    title: '中国传统文化',
    sections: [
      {
        title: '内容大纲',
        pages: [
          {
            title: '第 1 页：封面与课程信息',
            blocks: [{ title: '', content: ['主标题：中国传统文化'] }],
            image_candidates: [
              { id: 'img-a', url: 'https://img.example.com/a.png' },
              { id: 'img-b', url: 'https://img.example.com/b.png' },
            ],
            selected_image_id: 'img-b',
          },
        ],
      },
    ],
  })

  assert.match(markdown, /### 第 1 页：封面与课程信息/)
  assert.match(markdown, /- 主标题：中国传统文化/)
  assert.match(markdown, /!\[配图2\]\(https:\/\/img\.example\.com\/b\.png\)/)
})

test('markdownToOutlinePayload realigns legacy shifted image indexes', () => {
  const payload = markdownToOutlinePayload(
    `# 中国传统文化

## 第 1 页：封面与课程信息
- 主标题：中国传统文化

## 第 2 页：教学目标与课程导入
- 核心目标：建立整体认识
`,
    {
      0: ['https://img.example.com/title-a.png', 'https://img.example.com/title-b.png'],
      1: ['https://img.example.com/page1-a.png', 'https://img.example.com/page1-b.png'],
      2: ['https://img.example.com/page2-a.png', 'https://img.example.com/page2-b.png'],
    },
  )

  assert.equal(payload.sections[0].pages[0].image_candidates[0].url, 'https://img.example.com/page1-a.png')
  assert.equal(payload.sections[0].pages[1].image_candidates[0].url, 'https://img.example.com/page2-a.png')
})
