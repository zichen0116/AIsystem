<script setup>
import TopNav from './TopNav.vue'
</script>

<template>
  <div class="layout">
    <TopNav />
    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main {
  flex: 1;
}
</style>
