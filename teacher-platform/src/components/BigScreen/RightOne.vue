<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref(null)
let chartInstance = null

/** 各学段备课需求占比（演示数据，总和 100，可对接接口） */
const stageData = [
  { value: 12, name: '小学' },
  { value: 26, name: '初中' },
  { value: 24, name: '高中' },
  { value: 38, name: '大学' }
]

const colors = ['#22d3ee', '#38bdf8', '#818cf8', '#c084fc']

function buildOption() {
  const w = window.innerWidth
  const isSmall = w < 768

  return {
    title: {
      text: '系统使用学段占比',
      left: 'center',
      top: isSmall ? 4 : 6,
      textStyle: {
        color: '#7dd3fc',
        fontSize: isSmall ? 12 : 13,
        fontWeight: 600
      },
      subtextStyle: {
        color: '#94a3b8',
        fontSize: isSmall ? 10 : 11
      }
    },
    color: colors,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 20, 40, 0.92)',
      borderColor: '#00bfff',
      textStyle: { color: '#e0f2fe' },
      formatter: (p) =>
        `${p.marker} ${p.name}<br/>占比：${p.percent}%<br/>需求指数：${p.value}`
    },
    legend: {
      orient: 'horizontal',
      bottom: isSmall ? 4 : 8,
      left: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        color: '#a5f3fc',
        fontSize: isSmall ? 10 : 11
      }
    },
    series: [
      {
        name: '学段',
        type: 'pie',
        radius: ['38%', '60%'],
        center: ['50%', '52%'],
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
          fontSize: isSmall ? 9 : 10,
          lineHeight: 14
        },
        labelLine: {
          length: 8,
          length2: 6,
          lineStyle: { color: 'rgba(125, 211, 252, 0.6)' }
        },
        emphasis: {
          scale: true,
          scaleSize: 6,
          itemStyle: {
            shadowBlur: 16,
            shadowColor: 'rgba(34, 211, 238, 0.45)'
          }
        },
        data: stageData
      }
    ]
  }
}

function updateChart() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), true)
}

function resizeChart() {
  chartInstance?.resize()
}

function onResize() {
  resizeChart()
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
