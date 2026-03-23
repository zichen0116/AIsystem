<template>
  <div ref="chartRef" class="tech-map-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import chinaJson from '@/assets/china.json'

const chartRef = ref(null)
let chartInstance = null

/**
 * 各省教师活跃数（演示数据，与 geo 中 properties.name 一致，可对接接口）
 */
const provinceTeacherData = [
  { name: '北京市', value: 312 },
  { name: '天津市', value: 158 },
  { name: '河北省', value: 228 },
  { name: '山西省', value: 142 },
  { name: '内蒙古自治区', value: 96 },
  { name: '辽宁省', value: 189 },
  { name: '吉林省', value: 124 },
  { name: '黑龙江省', value: 137 },
  { name: '上海市', value: 398 },
  { name: '江苏省', value: 456 },
  { name: '浙江省', value: 392 },
  { name: '安徽省', value: 268 },
  { name: '福建省', value: 241 },
  { name: '江西省', value: 206 },
  { name: '山东省', value: 334 },
  { name: '河南省', value: 301 },
  { name: '湖北省', value: 278 },
  { name: '湖南省', value: 265 },
  { name: '广东省', value: 512 },
  { name: '广西壮族自治区', value: 178 },
  { name: '海南省', value: 89 },
  { name: '重庆市', value: 223 },
  { name: '四川省', value: 289 },
  { name: '贵州省', value: 156 },
  { name: '云南省', value: 198 },
  { name: '西藏自治区', value: 42 },
  { name: '陕西省', value: 214 },
  { name: '甘肃省', value: 118 },
  { name: '青海省', value: 35 },
  { name: '宁夏回族自治区', value: 67 },
  { name: '新疆维吾尔自治区', value: 124 },
  { name: '台湾省', value: 188 },
  { name: '香港特别行政区', value: 142 },
  { name: '澳门特别行政区', value: 56 }
]

function getValueRange() {
  const vals = provinceTeacherData.map((d) => d.value)
  return { min: Math.min(...vals), max: Math.max(...vals) }
}

const initChart = async () => {
  try {
    chartInstance = echarts.init(chartRef.value, 'tech')
    echarts.registerMap('china', chinaJson)
    chartInstance.setOption(getChartOption())
    chartInstance.on('click', handleMapClick)
  } catch (error) {
    console.error('地图初始化失败:', error)
  }
}

const handleMapClick = (params) => {
  if (params.componentType === 'series' && params.seriesType === 'map') {
    chartInstance.dispatchAction({
      type: 'highlight',
      seriesIndex: 0,
      name: params.name
    })
  }
}

const getResponsiveFontSize = (width, largeSize, smallSize) =>
  width < 768 ? smallSize : largeSize

const getChartOption = () => {
  const w = window.innerWidth
  const { min: vmin, max: vmax } = getValueRange()

  return {
    backgroundColor: 'transparent',
    title: {
      text: '活跃教师人数省级分布',
      left: 'center',
      top: 6,
      itemGap: 6,
      textStyle: {
        color: '#00f2ff',
        fontSize: getResponsiveFontSize(w, 20, 15),
        fontWeight: 'bold',
        textShadow: '0 0 10px rgba(0, 242, 255, 0.6)'
      },
      subtextStyle: {
        color: '#94a3b8',
        fontSize: getResponsiveFontSize(w, 12, 10)
      }
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 20, 50, 0.92)',
      borderColor: '#00f2ff',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: {
        color: '#e0f2fe',
        fontSize: 13
      },
      formatter(params) {
        if (!params.name) return ''
        const v = params.value
        const n = typeof v === 'number' && !Number.isNaN(v) ? v : null
        const text =
          n != null ? `${n} 人` : '<span style="opacity:0.75">暂无数据</span>'
        return `
          <div style="font-weight:700;color:#00f2ff;margin-bottom:6px">${params.name}</div>
          <div>活跃教师人数：<b style="color:#7dd3fc">${text}</b></div>
        `
      }
    },
    visualMap: {
      type: 'continuous',
      min: vmin,
      max: vmax,
      text: ['高', '低'],
      dimension: 0,
      calculable: true,
      realtime: true,
      inRange: {
        color: ['#0a1628', '#0c4a6e', '#0369a1', '#0284c7', '#0ea5e9', '#38bdf8', '#7dd3fc']
      },
      textStyle: {
        color: '#cbd5e1'
      },
      formatter: (value) => `${Math.round(value)} 人`,
      left: '4%',
      bottom: '8%',
      itemWidth: 14,
      itemHeight: 120
    },
    series: [
      {
        name: '教师活跃数',
        type: 'map',
        map: 'china',
        roam: true,
        zoom: 1.12,
        data: provinceTeacherData,
        label: {
          show: true,
          color: '#e2e8f0',
          fontSize: getResponsiveFontSize(w, 9, 7)
        },
        itemStyle: {
          borderColor: 'rgba(0, 242, 255, 0.55)',
          borderWidth: 1,
          shadowColor: 'rgba(0, 242, 255, 0.2)',
          shadowBlur: 6
        },
        emphasis: {
          label: {
            color: '#fff',
            fontSize: getResponsiveFontSize(w, 11, 9),
            fontWeight: 'bold'
          },
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2,
            shadowBlur: 12,
            shadowColor: 'rgba(0, 242, 255, 0.45)'
          }
        },
        select: {
          label: { show: true, color: '#fff' },
          itemStyle: {
            borderColor: '#fde047',
            borderWidth: 2
          }
        }
      }
    ]
  }
}

const resizeChart = () => {
  chartInstance?.resize()
  chartInstance?.setOption(getChartOption())
}

echarts.registerTheme('tech', {
  backgroundColor: 'rgba(0, 10, 30, 0.8)',
  color: ['#00f2ff', '#1990ff', '#0b5bce', '#0a2dae'],
  title: {
    textStyle: {
      color: '#00f2ff'
    }
  }
})

onMounted(async () => {
  await initChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chartInstance?.dispose()
})
</script>

<style scoped>
.tech-map-container {
  width: 100%;
  height: 100%;
  overflow: hidden !important;
}
</style>
