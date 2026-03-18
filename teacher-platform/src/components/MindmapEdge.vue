<script setup>
import { computed } from 'vue'
import { BaseEdge, getBezierPath } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  sourceX: { type: Number, required: true },
  sourceY: { type: Number, required: true },
  targetX: { type: Number, required: true },
  targetY: { type: Number, required: true },
  sourcePosition: { type: String, required: true },
  targetPosition: { type: String, required: true },
  data: { type: Object, default: () => ({}) }
})

const stroke = computed(() => props.data?.stroke || '#94a3b8')
const strokeWidth = computed(() => props.data?.strokeWidth || 2)

// 思维导图风格：更圆润、偏“树枝”曲线
const path = computed(() => {
  const curvature = props.data?.curvature ?? 0.42
  const [p] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
    curvature
  })
  return p
})
</script>

<template>
  <BaseEdge
    :id="id"
    :path="path"
    :style="{
      stroke,
      strokeWidth,
      fill: 'none',
      strokeLinecap: 'round',
      strokeLinejoin: 'round'
    }"
  />
</template>

