<template>
  <div class="subtitle-panel" v-if="text">
    <p class="subtitle-text">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({ text: { type: String, default: '' } })
</script>

<style scoped>
.subtitle-panel { background: #161b22; padding: 12px 20px; border-top: 1px solid #30363d; min-height: 48px; display: flex; align-items: center; justify-content: center; }
.subtitle-text { color: #e6edf3; font-size: 15px; text-align: center; line-height: 1.6; margin: 0; max-width: 800px; }
</style>
