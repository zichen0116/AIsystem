<template>
  <div ref="chartRef" style="width: 100%; height: 100%"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { ref, onMounted, onUnmounted } from 'vue'

const chartRef = ref(null)
let chartInstance = null

/** 横轴：周次（演示数据，可换为具体日期区间） */
const weekLabels = ['第1周', '第2周', '第3周', '第4周', '第5周', '第6周', '第7周', '第8周']

/** 平均备课耗时（分钟/份） */
const avgMinutesPerTask = [8, 7.5, 6, 7, 6.5, 5, 4, 3]

/** 备课任务完成率（%） */
const completionRate = [78, 80, 82, 83, 84, 85, 86, 83]

function buildOption() {
  const isSmall = window.innerWidth < 768

  return {
    color: ['#22d3ee', '#a78bfa'],
    title: {
      text: '备课效率周度趋势',
      left: 'center',
      top: 4,
      textStyle: {
        color: '#7dd3fc',
        fontSize: isSmall ? 12 : 13,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 20, 40, 0.92)',
      borderColor: '#00bfff',
      borderWidth: 1,
      textStyle: { color: '#e0f2fe' },
      axisPointer: { type: 'cross' },
      formatter(params) {
        if (!params?.length) return ''
        const lines = [params[0].axisValue]
        for (const p of params) {
          if (p.seriesName === '平均备课耗时') {
            lines.push(`${p.marker}${p.seriesName}：${p.value} 分钟/份`)
          } else if (p.seriesName === '备课任务完成率') {
            lines.push(`${p.marker}${p.seriesName}：${p.value}%`)
          }
        }
        return lines.join('<br/>')
      }
    },
    legend: {
      data: ['平均备课耗时', '备课任务完成率'],
      top: isSmall ? 26 : 28,
      left: 'center',
      textStyle: { color: '#94a3b8', fontSize: isSmall ? 10 : 11 },
      itemWidth: 14,
      itemHeight: 8
    },
    grid: {
      left: '3%',
      /* 为右侧「%」刻度留最小边距；containLabel 会再为刻度文字扩边。勿对右 Y 轴设 offset，否则曲线画不到轴线 */
      right: isSmall ? '11%' : '3%',
      top: isSmall ? 62 : 58,
      bottom: isSmall ? 14 : 10,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      nameLocation: 'middle',
      nameGap: 22,
      nameTextStyle: { color: '#67e8f9', fontSize: 11 },
      data: weekLabels,
      axisLine: { lineStyle: { color: '#00bfff' } },
      axisLabel: {
        color: '#7dd3fc',
        fontSize: isSmall ? 9 : 10,
        rotate: isSmall ? 28 : 0
      },
      splitLine: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        name: '分钟/份',
        position: 'left',
        nameTextStyle: { color: '#22d3ee', fontSize: 10, padding: [0, 0, 0, 0] },
        axisLine: { show: true, lineStyle: { color: '#22d3ee' } },
        axisLabel: { color: '#67e8f9', fontSize: 10 },
        splitLine: {
          lineStyle: { color: 'rgba(0, 191, 255, 0.12)' }
        }
      },
      {
        type: 'value',
        name: '完成率',
        position: 'right',
        min: (value) => Math.max(0, Math.floor(value.min) - 5),
        max: (value) => Math.min(100, Math.ceil(value.max) + 2),
        nameTextStyle: { color: '#a78bfa', fontSize: 10 },
        axisLine: { show: true, lineStyle: { color: '#a78bfa' } },
        axisLabel: {
          color: '#c4b5fd',
          fontSize: 10,
          formatter: '{value}%'
        },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '平均备课耗时',
        type: 'line',
        yAxisIndex: 0,
        smooth: true,
        symbol: 'circle',
        symbolSize: isSmall ? 5 : 6,
        data: avgMinutesPerTask,
        lineStyle: { width: 2 },
        itemStyle: { color: '#22d3ee' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(34, 211, 238, 0.22)' },
            { offset: 1, color: 'rgba(0, 0, 0, 0)' }
          ])
        }
      },
      {
        name: '备课任务完成率',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: isSmall ? 5 : 6,
        data: completionRate,
        lineStyle: { width: 2 },
        itemStyle: { color: '#a78bfa' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(167, 139, 250, 0.18)' },
            { offset: 1, color: 'rgba(0, 0, 0, 0)' }
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

function resizeChart() {
  if (chartInstance) {
    chartInstance.resize()
    updateChart()
  }
}

onMounted(() => {
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
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
