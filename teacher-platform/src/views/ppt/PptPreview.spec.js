import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('PptPreview view', () => {
  it('uses the brand logo for the empty slide placeholder', () => {
    const source = readFileSync(resolve(import.meta.dirname, './PptPreview.vue'), 'utf8')

    expect(source).toContain('class="placeholder-logo"')
    expect(source).toContain('src="/logo-character.svg"')
    expect(source).not.toContain('placeholder-icon')
    expect(source).not.toContain('🍌')
  })
})
