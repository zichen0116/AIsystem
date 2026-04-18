import { describe, expect, it } from 'vitest'

import { buildApiUrl } from './http'

describe('buildApiUrl', () => {
  it('does not duplicate the api prefix when base already points to /api', () => {
    expect(buildApiUrl('/api', '/api/v1/auth/login')).toBe('/api/v1/auth/login')
  })

  it('joins absolute backend bases with api paths', () => {
    expect(buildApiUrl('http://127.0.0.1:8000', '/api/v1/auth/login')).toBe(
      'http://127.0.0.1:8000/api/v1/auth/login',
    )
  })
})
