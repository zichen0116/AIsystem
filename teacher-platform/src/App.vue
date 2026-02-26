<script setup>
import { useUserStore } from './stores/user'
import LoginView from './views/LoginView.vue'
import Home from './views/Home.vue'

const userStore = useUserStore()
</script>

<template>
  <LoginView v-if="!userStore.isLoggedIn" />
  <Home v-else />
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
