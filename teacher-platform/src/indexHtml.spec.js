import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('index.html shell', () => {
  it('uses the updated browser title', () => {
    const html = readFileSync(resolve(import.meta.dirname, '../index.html'), 'utf8')

    expect(html).toContain('<title>智课坊 | EDU Prep</title>')
  })
})
