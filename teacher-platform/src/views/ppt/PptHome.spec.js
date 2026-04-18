import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PptHome from './PptHome.vue'

vi.mock('@/api/ppt', () => ({
  getUserTemplates: vi.fn().mockResolvedValue([]),
  extractStyleFromImage: vi.fn(),
}))

vi.mock('@/api/http', () => ({
  resolveApiUrl: vi.fn((path) => path),
  getToken: vi.fn(() => ''),
}))

describe('PptHome view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    })
  })

  it('renders the premium hero copy for PPT generation', () => {
    const wrapper = mount(PptHome)
    const title = wrapper.get('[data-test="ppt-home-hero-title"]')
    const subtitle = wrapper.get('[data-test="ppt-home-hero-subtitle"]')
    const subtitleLines = wrapper.findAll('.hero-subtitle-line')

    expect(title.text()).toBe('让每一页，都更像作品')
    expect(subtitleLines).toHaveLength(2)
    expect(subtitleLines[0].text()).toBe('从教学主题到完整演示，')
    expect(subtitleLines[1].text()).toBe('智课坊助力完成构思、结构与表达')
    expect(title.classes()).toContain('hero-title-editorial')
    expect(subtitle.classes()).toContain('hero-subtitle-editorial')
  })
})
