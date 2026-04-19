import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function styleBlock(source, selector) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`${escapedSelector}\\s*\\{[^}]*\\}`))?.[0] || ''
}

describe('PptPreview view', () => {
  it('uses the brand logo for the empty slide placeholder', () => {
    const source = readFileSync(resolve(import.meta.dirname, './PptPreview.vue'), 'utf8')

    expect(source).toContain('class="placeholder-logo"')
    expect(source).toContain('src="/logo-character.svg"')
    expect(source).not.toContain('placeholder-icon')
    expect(source).not.toContain('🍌')
  })

  it('uses light blue for active multiselect and generating status accents', () => {
    const source = readFileSync(resolve(import.meta.dirname, './PptPreview.vue'), 'utf8')
    const activeMultiselect = styleBlock(source, '.multiselect-toggle.active')
    const generatingStatus = styleBlock(source, '.thumbnail-status.status-generating')

    expect(activeMultiselect).toContain('background: #dbeafe;')
    expect(activeMultiselect).toContain('color: #2563eb;')
    expect(generatingStatus).toContain('background: #dbeafe;')
    expect(generatingStatus).toContain('color: #2563eb;')
  })
})
