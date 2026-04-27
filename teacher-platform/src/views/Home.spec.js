import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Home from './Home.vue'

const push = vi.fn()
const openLoginModal = vi.fn()

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRouter: () => ({ push }),
  }
})

vi.mock('../components/LottiePlayer.vue', () => ({
  default: {
    name: 'LottiePlayer',
    template: '<div data-test="lottie-stub" />',
  },
}))

describe('Home view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockReset()
    openLoginModal.mockReset()
    window.scrollY = 0
  })

  function mountHome() {
    return mount(Home, {
      global: {
        provide: {
          openLoginModal,
        },
      },
    })
  }

  it('renders the migrated EDU Prep hero copy and footer copy', () => {
    const wrapper = mountHome()

    expect(wrapper.text()).toContain('EDU Prep')
    expect(wrapper.text()).toContain('MULTIMODAL AI')
    expect(wrapper.text()).toContain('The Next Generation Teaching Agent Paradigm')
    expect(wrapper.text()).toContain('Creators: LZC, ZZT, MCM, YCX')
  })

  it('shows the login button for logged-out users and opens login flow on click', async () => {
    const wrapper = mountHome()

    await wrapper.get('[data-test="home-login"]').trigger('click')

    expect(openLoginModal).toHaveBeenCalledTimes(1)
  })

  it('uses the requested logo svg and homepage preview image', () => {
    const wrapper = mountHome()

    const brandImage = wrapper.get('[data-test="brand-logo"]')
    const previewImage = wrapper.get('[data-test="vision-image"]')

    expect(brandImage.attributes('src')).toBe('/logo-character.svg')
    expect(previewImage.attributes('src')).toBe('/home-preview.png')
  })

  it('routes the primary CTA to lesson prep', async () => {
    const wrapper = mountHome()

    await wrapper.get('[data-test="hero-cta"]').trigger('click')

    expect(push).toHaveBeenCalledWith({ path: '/login', query: { redirect: '/lesson-prep' } })
  })

  it('updates hero animation styles when scrolling', async () => {
    const wrapper = mountHome()

    window.scrollY = 600
    window.dispatchEvent(new Event('scroll'))
    await wrapper.vm.$nextTick()

    const hero = wrapper.get('[data-test="curtain-hero"]')
    expect(hero.attributes('data-scroll-ready')).toBe('true')
  })
})
