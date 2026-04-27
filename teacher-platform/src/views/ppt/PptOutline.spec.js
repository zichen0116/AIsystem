import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('PptOutline layout', () => {
  it('keeps the PPT idea textarea tall enough for longer concepts', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/ppt/PptOutline.vue'), 'utf8')

    expect(source).toContain('.input-textarea')
    expect(source).toContain('min-height: 260px;')
  })
})
