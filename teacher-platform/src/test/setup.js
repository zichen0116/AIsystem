import { afterEach, vi } from 'vitest'

Object.defineProperty(window, 'scrollY', {
  value: 0,
  writable: true,
})

Object.defineProperty(window, 'innerHeight', {
  value: 1080,
  writable: true,
})

window.scrollTo = vi.fn()

afterEach(() => {
  vi.restoreAllMocks()
})
