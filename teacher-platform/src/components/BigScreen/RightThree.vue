<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref(null)
let chartInstance = null

/** 热门学科 TOP5（演示数据：热度指数，可对接接口） */
const subjects = ['工学类', '医学类', '经济学类', '文学类', '理学类']
const heatValues = [892, 756, 621, 534, 418]

function getResponsiveFontSize(width, largeSize, smallSize) {
  return width < 768 ? smallSize : largeSize
}

function buildOption() {
  const w = window.innerWidth
  const fs = getResponsiveFontSize(w, 12, 10)
  const titleFs = getResponsiveFontSize(w, 13, 11)

  return {
    title: {
      text: '热门学科 TOP5',
      left: 'center',
      top: 6,
      textStyle: {
        color: '#7dd3fc',
        fontSize: titleFs,
        fontWeight: 600
      }
    },
    color: ['#22d3ee'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(0, 20, 40, 0.92)',
      borderColor: '#00bfff',
      textStyle: { color: '#e0f2fe' },
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>热度指数：${p.value}`
      }
    },
    grid: {
      left: '3%',
      right: '12%',
      top: 40,
      bottom: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '热度',
      nameTextStyle: { color: '#67e8f9', fontSize: 10 },
      axisLine: {
        lineStyle: { color: '#00bfff' }
      },
      axisLabel: {
        color: '#7dd3fc',
        fontSize: fs - 1
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 191, 255, 0.12)'
        }
      }
    },
    yAxis: {
      type: 'category',
      data: subjects,
      inverse: true,
      axisLine: {
        lineStyle: { color: '#00bfff' }
      },
      axisLabel: {
        color: '#a5f3fc',
        fontSize: fs,
        width: 72,
        overflow: 'truncate',
        ellipsis: '…'
      },
      axisTick: { show: false }
    },
    series: [
      {
        name: '热度',
        type: 'bar',
        data: heatValues,
        barMaxWidth: 22,
        label: {
          show: true,
          position: 'right',
          color: '#e0f2fe',
          fontSize: fs - 1,
          formatter: '{c}'
        },
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#0369a1' },
            { offset: 1, color: '#22d3ee' }
          ])
        }
      }
    ]
  }
}

function updateChart() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), true)
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
