import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('logo-character.svg asset', () => {
  it('uses a tight viewBox instead of the original oversized canvas', () => {
    const svg = readFileSync(resolve(import.meta.dirname, '../public/logo-character.svg'), 'utf8')

    expect(svg).toContain('viewBox="566 355 410 110"')
    expect(svg).not.toContain('viewBox="0 0 1440 809.999993"')
  })
})
