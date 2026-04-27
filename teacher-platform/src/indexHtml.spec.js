import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('index.html shell', () => {
  it('uses the updated browser title', () => {
    const html = readFileSync(resolve(import.meta.dirname, '../index.html'), 'utf8')

    expect(html).toContain('<title>智课坊 | EDU Prep</title>')
  })

  it('uses the 智课坊 logo as the browser tab icon', () => {
    const html = readFileSync(resolve(import.meta.dirname, '../index.html'), 'utf8')

    expect(html).toContain('<link rel="icon" type="image/svg+xml" href="/logo.svg" />')
    expect(html).not.toContain('/vite.svg')
  })
})
