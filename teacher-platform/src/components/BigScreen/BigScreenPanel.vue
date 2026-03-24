<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import LeftOne from './LeftOne.vue'
import LeftTwo from './LeftTwo.vue'
import LeftThree from './LeftThree.vue'
import CenterTwo from './CenterTwo.vue'
import RightOne from './RightOne.vue'
import RightTwo from './RightTwo.vue'
import RightThree from './RightThree.vue'

const currentTime = ref(getCurrentDateTime())

const kpiItems = [
  { label: '活跃教师数', value: '268', unit: '人' },
  { label: '备课任务总量', value: '1739', unit: '个' },
  { label: '备课完成率', value: '83', unit: '%' },
  { label: '系统平均响应时长', value: '2.9', unit: 's' }
]

function getCurrentDateTime() {
  const now = new Date()
  const year = now.getFullYear()
  const month = (now.getMonth() + 1).toString().padStart(2, '0')
  const day = now.getDate().toString().padStart(2, '0')
  const hours = now.getHours().toString().padStart(2, '0')
  const minutes = now.getMinutes().toString().padStart(2, '0')
  const seconds = now.getSeconds().toString().padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

let timer = null

onMounted(() => {
  timer = setInterval(() => {
    currentTime.value = getCurrentDateTime()
  }, 1000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
})
</script>

<template>
  <div class="bigscreen-home">
    <header class="top">
      <dv-border-box-11
        title="EduPrep 数据可视化"
        class="top-nav"
        :color="['#188ffe']"
      >
        <div class="name">教师备课平台</div>
        <div class="time">当前时间：{{ currentTime }}</div>
      </dv-border-box-11>
    </header>

    <main class="bottom">
      <div class="left">
        <dv-border-box-1 class="left-item">
          <LeftOne />
        </dv-border-box-1>
        <dv-border-box-1 class="left-item">
          <LeftTwo />
        </dv-border-box-1>
        <dv-border-box-1 class="left-item">
          <LeftThree />
        </dv-border-box-1>
      </div>

      <div class="center">
        <dv-border-box-1 class="center-top">
          <div class="center-top-item">
            <template v-for="(item, i) in kpiItems" :key="item.label">
              <div v-if="i > 0" class="kpi-divider" aria-hidden="true" />
              <div class="kpi-cell">
                <span class="kpi-label">{{ item.label }}</span>
                <div class="kpi-value-row">
                  <span class="kpi-num">{{ item.value }}</span>
                  <span class="kpi-unit">{{ item.unit }}</span>
                </div>
              </div>
            </template>
          </div>
        </dv-border-box-1>
        <dv-border-box-1 class="center-bottom">
          <CenterTwo />
        </dv-border-box-1>
      </div>

      <div class="right">
        <dv-border-box-1 class="right-item">
          <RightOne />
        </dv-border-box-1>

        <dv-border-box-1 class="right-item">
          <RightTwo />
        </dv-border-box-1>

        <dv-border-box-1 class="right-item">
          <RightThree />
        </dv-border-box-1>
      </div>
    </main>
  </div>
</template>

<style scoped lang="less">
.bigscreen-home {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 560px;
  background-color: #000;
  color: #fff;
  overflow: hidden;
  box-sizing: border-box;
}

.top {
  display: grid;
  height: 60px;
  flex-shrink: 0;
  .top-nav {
    width: 100%;
    height: 100%;
    position: relative;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    .name {
      position: absolute;
      left: 100px;
      top: 50%;
      transform: translateY(-50%);
      color: #00f2ff;
      text-shadow: 0 0 5px #00f2ff, 0 0 40px #00f2ff;
      font-weight: 700;
      font-size: 0.9rem;
    }
    .time {
      position: absolute;
      right: 100px;
      top: 50%;
      transform: translateY(-50%);
      font-weight: 700;
      color: #00f2ff;
      text-shadow: 0 0 5px #00f2ff, 0 0 40px #00f2ff;
      font-size: 0.9rem;
    }
  }
}

.bottom {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 3fr 6fr 3fr;
  gap: 10px;
}

.left {
  display: grid;
  grid-template-rows: repeat(3, 1fr);
  gap: 10px;
  min-height: 0;
  .left-item {
    width: 100%;
    border-radius: 8px;
    height: 100%;
    min-height: 0;
    box-shadow: inset 0 0 15px rgba(0, 98, 255, 0.2);
  }
}

.center {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  justify-content: space-between;
  .center-top {
    display: flex;
    width: 100%;
    height: 23%;
    min-height: 0;
    background-color: #000;
    border-radius: 8px;
    box-shadow: inset 0 0 15px rgba(0, 98, 255, 0.2);

    .center-top-item {
      display: flex;
      width: 100%;
      height: 100%;
      justify-content: space-evenly;
      align-items: stretch;
      padding: 6px 8px;
      box-sizing: border-box;
    }

    .kpi-divider {
      width: 3px;
      flex-shrink: 0;
      align-self: center;
      height: 55%;
      min-height: 36px;
      background: linear-gradient(180deg, transparent, #3be1c4, transparent);
      border-radius: 2px;
    }

    .kpi-cell {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 4px 6px;
    }

    .kpi-label {
      font-size: clamp(11px, 1.1vw, 14px);
      font-weight: 600;
      color: #7dd3fc;
      text-shadow: 0 0 6px rgba(0, 242, 255, 0.35);
      text-align: center;
      line-height: 1.25;
    }

    .kpi-value-row {
      display: flex;
      align-items: baseline;
      justify-content: center;
      flex-wrap: wrap;
      gap: 2px 4px;
    }

    .kpi-num {
      font-size: clamp(20px, 2.4vw, 32px);
      font-weight: 800;
      color: #00f2ff;
      text-shadow: 0 0 8px #00f2ff, 0 0 24px rgba(0, 242, 255, 0.45);
      font-variant-numeric: tabular-nums;
      line-height: 1;
    }

    .kpi-unit {
      font-size: clamp(12px, 1.2vw, 16px);
      font-weight: 600;
      color: #67e8f9;
      text-shadow: 0 0 4px rgba(103, 232, 249, 0.5);
    }
  }

  .center-bottom {
    display: flex;
    width: 100%;
    height: 75%;
    min-height: 0;
    background-color: #000;
    border-radius: 8px;
    box-shadow: inset 0 0 15px rgba(0, 98, 255, 0.2);
  }
}

.right {
  display: grid;
  grid-template-rows: repeat(3, 1fr);
  gap: 10px;
  min-height: 0;
  .right-item {
    width: 100%;
    height: 100%;
    min-height: 0;
    border-radius: 8px;
    box-shadow: inset 0 0 15px rgba(0, 98, 255, 0.2);
  }
}
</style>
