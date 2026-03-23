<template>
  <div ref="chartRef" style="width: 100%; height: 100%"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref(null)
let chartInstance = null

const featureNames = [
  'PPT',
  '教案',
  '动游',
  '数据',
  '思维导图',
  '知识图谱',
  '试题生成',
  '资源搜索'
]

const weekLabels = ['第1周', '第2周', '第3周', '第4周', '第5周', '第6周', '第7周', '第8周']

/** 各功能按周的使用量（演示数据，可对接接口） */
const usageByFeature = [
  [118, 126, 138, 151, 159, 168, 176, 185],
  [92, 98, 105, 112, 118, 124, 131, 138],
  [45, 52, 58, 64, 71, 76, 82, 88],
  [62, 68, 74, 79, 85, 91, 96, 102],
  [38, 44, 49, 55, 61, 66, 72, 78],
  [55, 60, 66, 72, 78, 83, 89, 95],
  [72, 78, 85, 91, 98, 104, 111, 118],
  [88, 94, 101, 108, 115, 122, 128, 136]
]

const colors = [
  '#22d3ee',
  '#a78bfa',
  '#fbbf24',
  '#34d399',
  '#fb7185',
  '#818cf8',
  '#2dd4bf',
  '#f472b6'
]

function buildOption() {
  const isSmall = window.innerWidth < 768

  const series = featureNames.map((name, i) => ({
    name,
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: isSmall ? 3 : 4,
    showSymbol: true,
    lineStyle: { width: isSmall ? 1.2 : 1.6 },
    itemStyle: { color: colors[i] },
    emphasis: { focus: 'series', scale: 1.4 },
    data: usageByFeature[i]
  }))

  return {
    color: colors,
    title: {
      text: '功能周度使用趋势',
      left: 'center',
      top: 4,
      textStyle: {
        color: '#7dd3fc',
        fontSize: isSmall ? 11 : 12,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: 'rgba(0, 20, 40, 0.92)',
      borderColor: '#00bfff',
      borderWidth: 1,
      textStyle: { color: '#e0f2fe', fontSize: 11 },
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          borderColor: '#00bfff',
          color: '#fff'
        }
      }
    },
    legend: {
      type: 'scroll',
      orient: 'horizontal',
      bottom: 0,
      left: 'center',
      width: '96%',
      data: featureNames,
      textStyle: { color: '#94a3b8', fontSize: isSmall ? 8 : 9 },
      itemWidth: 10,
      itemHeight: 6,
      pageIconColor: '#7dd3fc',
      pageTextStyle: { color: '#94a3b8' }
    },
    grid: {
      left: '3%',
      right: '5%',
      top: isSmall ? 36 : 32,
      bottom: isSmall ? 40 : 36,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: weekLabels,
      axisLine: { lineStyle: { color: '#00bfff' } },
      axisLabel: {
        color: '#7dd3fc',
        fontSize: isSmall ? 8 : 9,
        rotate: isSmall ? 25 : 0
      },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '使用次数',
      nameTextStyle: { color: '#67e8f9', fontSize: 10 },
      axisLine: { lineStyle: { color: '#00bfff' } },
      axisLabel: { color: '#7dd3fc', fontSize: 9 },
      splitLine: {
        lineStyle: { color: 'rgba(0, 191, 255, 0.12)' }
      }
    },
    series
  }
}

function updateChart() {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), true)
}

function resizeChart() {
  chartInstance?.resize()
  updateChart()
}

onMounted(() => {
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
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
