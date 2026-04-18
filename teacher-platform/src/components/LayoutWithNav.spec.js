import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LayoutWithNav from './LayoutWithNav.vue'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/lesson-prep', query: { tab: 'ppt' } }),
  useRouter: () => ({ push }),
}))

vi.mock('./ThemeToggle.vue', () => ({
  default: { template: '<div data-test="theme-toggle-stub" />' },
}))

vi.mock('./DigitalHumanAssistant.vue', () => ({
  default: { template: '<div data-test="digital-human-stub" />' },
}))

describe('LayoutWithNav', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
  })

  it('renders the Zhikefang brand logo in the sidebar', () => {
    const wrapper = mount(LayoutWithNav)

    expect(wrapper.get('[data-test="sidebar-brand-logo"]').attributes('src')).toBe('/logo.svg')
    expect(wrapper.get('[data-test="sidebar-brand-name"]').attributes('src')).toBe('/character.svg')
    expect(wrapper.get('[data-test="sidebar-brand-name"]').attributes('alt')).toBe('智课坊')
  })
})
