<template>
  <div ref="chartRef1" style="width: 100%; height: 100%"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useWindowSize } from '@vueuse/core'

const chartRef1 = ref(null)
let chartInstance = null

const { width, height } = useWindowSize()

/** 各备课功能使用量（演示数据，可对接接口） */
const categories = ['PPT', '教案', '动游', '数据', '思维导图', '知识图谱']
const usageValues = [312, 268, 145, 119, 156, 94]

const initChart = () => {
  chartInstance = echarts.init(chartRef1.value)
  updateChart()
  resizeChart()
}

const updateChart = () => {
  const isNarrow = width.value < 900
  const option = {
    color: ['#00bfff'],
    title: {
      text: '备课功能使用量统计',
      left: 'center',
      top: 6,
      textStyle: {
        color: '#7dd3fc',
        fontSize: isNarrow ? 12 : 13,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(0, 20, 40, 0.92)',
      borderColor: '#00bfff',
      textStyle: { color: '#e0f2fe' },
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>使用量：${p.value} 次`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      top: 36,
      bottom: isNarrow ? 18 : 8,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: {
        lineStyle: { color: '#00bfff' }
      },
      axisLabel: {
        color: '#7dd3fc',
        fontSize: isNarrow ? 9 : 11,
        interval: 0,
        rotate: isNarrow ? 32 : 22
      }
    },
    yAxis: {
      type: 'value',
      name: '次',
      nameTextStyle: { color: '#67e8f9', fontSize: 11 },
      axisLine: {
        lineStyle: { color: '#00bfff' }
      },
      axisLabel: {
        color: '#7dd3fc',
        fontSize: 10
      },
      splitLine: {
        lineStyle: { color: 'rgba(0, 191, 255, 0.12)' }
      }
    },
    series: [
      {
        name: '使用量',
        type: 'bar',
        data: usageValues,
        barMaxWidth: 28,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#22d3ee' },
            { offset: 1, color: '#0369a1' }
          ]),
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true,
          position: 'top',
          color: '#a5f3fc',
          fontSize: 10,
          formatter: '{c}'
        }
      }
    ],
    graphic: [
      {
        type: 'group',
        right: 12,
        top: 10,
        children: [
          {
            type: 'rect',
            shape: { width: 28, height: 28 },
            style: {
              lineWidth: 1,
              cursor: 'pointer',
              fill: 'rgba(0, 191, 255, 0.08)'
            },
            onclick: () => toggleFullScreen(chartRef1.value)
          },
          {
            type: 'text',
            style: {
              text: '⛶',
              textAlign: 'center',
              fontSize: 14,
              color: '#00bfff',
              cursor: 'pointer',
              x: 14,
              y: 18
            },
            onclick: () => toggleFullScreen(chartRef1.value)
          }
        ]
      }
    ]
  }
  chartInstance.setOption(option)
}

const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

const toggleFullScreen = (element) => {
  if (!document.fullscreenElement) {
    element.requestFullscreen().then(() => {
      element.classList.add('echarts-fullscreen')
    }).catch((err) => {
      console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`)
    })
  } else if (document.exitFullscreen) {
    document.exitFullscreen().then(() => {
      element.classList.remove('echarts-fullscreen')
    })
  }
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) {
    chartInstance.dispose()
  }
})

watch([width, height], () => {
  resizeChart()
  updateChart()
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
