<template>
  <div class="admin-page">
    <BigScreenPanel />
  </div>
</template>

<script setup>
import BigScreenPanel from '../../components/BigScreen/BigScreenPanel.vue'
</script>

<style scoped>
.admin-page {
  width: 100%;
  min-height: calc(100vh - 0px);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
}

.admin-page :deep(.bigscreen-home) {
  flex: 1;
  min-height: 560px;
}
</style>
