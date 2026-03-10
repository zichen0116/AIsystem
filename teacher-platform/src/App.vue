<script setup>
import { provide, computed } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import LayoutWithNav from './components/LayoutWithNav.vue'

const route = useRoute()
const router = useRouter()

provide('openLoginModal', () => { router.push('/login') })
provide('goToHome', () => { router.push('/') })

const layoutComponent = computed(() => (route.meta?.layout === 'nav' ? LayoutWithNav : 'div'))
</script>

<template>
  <component :is="layoutComponent">
    <RouterView />
  </component>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>
