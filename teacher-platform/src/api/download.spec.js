import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { downloadUrlAsFile } from './download'

describe('downloadUrlAsFile', () => {
  const originalCreateObjectURL = URL.createObjectURL
  const originalRevokeObjectURL = URL.revokeObjectURL

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:test-url')
    URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL
    URL.revokeObjectURL = originalRevokeObjectURL
  })

  it('hands a remote file URL to the browser without fetching it first', async () => {
    const appendChild = vi.spyOn(document.body, 'appendChild')
    const removeChild = vi.spyOn(document.body, 'removeChild')
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const createElement = vi.spyOn(document, 'createElement')

    await downloadUrlAsFile('https://cdn.example.com/ppt/export.zip', '保护地球，人人有责.zip')

    expect(URL.createObjectURL).not.toHaveBeenCalled()
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()
    expect(click).toHaveBeenCalledTimes(1)
    expect(appendChild).toHaveBeenCalledTimes(1)
    expect(removeChild).toHaveBeenCalledTimes(1)
    expect(createElement).toHaveBeenCalledWith('a')
    expect(appendChild.mock.calls[0][0].download).toBe('保护地球，人人有责.zip')
    expect(appendChild.mock.calls[0][0].href).toBe('https://cdn.example.com/ppt/export.zip')
  })
})
