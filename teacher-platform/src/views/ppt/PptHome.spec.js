import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PptHome from './PptHome.vue'

vi.mock('@/api/ppt', () => ({
  getUserTemplates: vi.fn().mockResolvedValue([]),
  extractStyleFromImage: vi.fn(),
  deleteUserTemplate: vi.fn().mockResolvedValue(undefined),
}))

import { deleteUserTemplate, getUserTemplates } from '@/api/ppt'

vi.mock('@/api/http', () => ({
  resolveApiUrl: vi.fn((path) => path),
  getToken: vi.fn(() => ''),
}))

describe('PptHome view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getUserTemplates).mockResolvedValue([])
    vi.mocked(deleteUserTemplate).mockClear()
    window.confirm = vi.fn(() => true)
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

  it('renders the environmental protection preset template', () => {
    const wrapper = mount(PptHome)
    const environmentalTemplate = wrapper.get('img[alt="环保主题"]')

    expect(environmentalTemplate.attributes('src')).toBe('/templates/template_environmental_protection.png')
    expect(wrapper.text()).toContain('环保主题')
  })

  it('lets users delete an uploaded template image from my templates', async () => {
    vi.mocked(getUserTemplates).mockResolvedValue([
      {
        id: 7,
        name: '图片1',
        cover_url: '/uploads/template.png',
        thumbnail: '/uploads/template.png',
      },
    ])

    const wrapper = mount(PptHome)
    await flushPromises()

    expect(wrapper.text()).toContain('图片1')

    await wrapper.get('[data-test="delete-user-template-7"]').trigger('click')
    await flushPromises()

    expect(window.confirm).toHaveBeenCalledWith('确定删除“图片1”吗？')
    expect(deleteUserTemplate).toHaveBeenCalledWith(7)
    expect(wrapper.text()).not.toContain('图片1')
  })
})
