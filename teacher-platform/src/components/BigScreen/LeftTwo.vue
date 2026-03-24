<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { ref, onMounted, onBeforeUnmount } from 'vue'

const chartRef = ref(null)
let chartInstance = null

/** 数据库使用占比（演示数据，总和 100，可对接接口） */
const dbUsageData = [
  { value: 48, name: '系统数据库使用' },
  { value: 35, name: '个人数据库使用' },
  { value: 17, name: '跨库复用占比' }
]

const colors = ['#22d3ee', '#38bdf8', '#a78bfa']

function buildOption() {
  const w = window.innerWidth
  const isSmall = w < 768

  return {
    title: {
      text: '数据库调用占比',
      left: 'center',
      top: isSmall ? 4 : 6,
      textStyle: {
        color: '#7dd3fc',
        fontSize: isSmall ? 11 : 12,
        fontWeight: 600
      }
    },
    color: colors,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 20, 40, 0.92)',
      borderColor: '#00bfff',
      textStyle: { color: '#e0f2fe' },
      formatter: (p) =>
        `${p.marker} ${p.name}<br/>占比：${p.percent}%<br/>使用量指数：${p.value}`
    },
    legend: {
      orient: 'horizontal',
      bottom: isSmall ? 2 : 6,
      left: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        color: '#a5f3fc',
        fontSize: isSmall ? 8 : 9
      }
    },
    series: [
      {
        name: '数据库',
        type: 'pie',
        radius: ['38%', '58%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#0a0a0f',
          borderWidth: 2,
          shadowBlur: 8,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          color: '#e0f2fe',
          fontSize: isSmall ? 8 : 9,
          lineHeight: 13
        },
        labelLine: {
          length: 6,
          length2: 4,
          lineStyle: { color: 'rgba(125, 211, 252, 0.55)' }
        },
        emphasis: {
          scale: true,
          scaleSize: 5,
          itemStyle: {
            shadowBlur: 14,
            shadowColor: 'rgba(34, 211, 238, 0.4)'
          }
        },
        data: dbUsageData
      }
    ]
  }
}

function updateChart() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), true)
}

function onResize() {
  chartInstance?.resize()
  updateChart()
}

onMounted(() => {
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style scoped lang="less">
.chart-container {
  width: 100%;
  height: 100%;
}

:deep(.echarts-fullscreen) {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
  background-color: #000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0;
  margin: 0;
}

:deep(.echarts-fullscreen .chart) {
  width: 100%;
  height: 100%;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
}
</style>
