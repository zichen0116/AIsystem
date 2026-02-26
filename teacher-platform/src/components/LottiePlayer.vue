<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import lottie from 'lottie-web'

const props = defineProps({
  src: { type: String, default: '' },
  animationData: { type: Object, default: null },
  loop: { type: Boolean, default: true },
  autoplay: { type: Boolean, default: true }
})

const containerRef = ref(null)
let animation = null

onMounted(() => {
  if (!containerRef.value || (!props.src && !props.animationData)) return
  const options = {
    container: containerRef.value,
    renderer: 'svg',
    loop: props.loop,
    autoplay: props.autoplay
  }
  if (props.animationData) {
    options.animationData = props.animationData
  } else {
    options.path = props.src
  }
  animation = lottie.loadAnimation(options)
})

onUnmounted(() => {
  if (animation) {
    animation.destroy()
  }
})
</script>

<template>
  <div ref="containerRef" class="lottie-container"></div>
</template>

<style scoped>
.lottie-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
}

.lottie-container :deep(svg) {
  width: 100% !important;
  height: 100% !important;
}
</style>
