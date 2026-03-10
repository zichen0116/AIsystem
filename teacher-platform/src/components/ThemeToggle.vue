<script setup>
import { ref } from 'vue'

const isDark = ref(localStorage.getItem('theme') === 'dark')

function toggleTheme(e) {
  isDark.value = e.target.checked
}

function persistTheme(e) {
  if (e.target.checked) {
    localStorage.setItem('theme', 'dark')
  } else {
    localStorage.setItem('theme', 'light')
  }
}
</script>

<template>
  <label class="theme theme--sun-moon">
    <input
      id="theme-toggle"
      type="checkbox"
      class="theme__toggle"
      :checked="isDark"
      @change="toggleTheme($event); persistTheme($event)"
    />
    <span class="theme__fill" aria-hidden="true"></span>
    <!-- 图1：左侧太阳、中间椭圆轨道+白色圆形把手、右侧月亮 -->
    <span class="theme__sun" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="4"/>
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
      </svg>
    </span>
    <span class="theme__track" aria-hidden="true">
      <span class="theme__knob"></span>
    </span>
    <span class="theme__moon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
    </span>
  </label>
</template>

<style scoped>
.theme {
  --transDur: 0.3s;
  display: flex;
  align-items: center;
  position: relative;
  -webkit-tap-highlight-color: transparent;
  cursor: pointer;
}

.theme__fill {
  background-color: hsl(0, 0%, 100%);
  display: block;
  mix-blend-mode: difference;
  position: fixed;
  inset: 0;
  height: 100%;
  transform: translateX(-100%);
  pointer-events: none;
  z-index: 9998;
  transition: transform var(--transDur);
}

.theme__toggle:checked ~ .theme__fill {
  transform: translateX(0);
}

.theme__toggle {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* 还原为左右太阳+月亮的简单样式，整体稍微缩小 */
.theme--sun-moon {
  gap: 8px;
}

.theme__sun,
.theme__moon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: #4B5563;
  transition: color var(--transDur);
}

.theme__sun svg,
.theme__moon svg {
  width: 100%;
  height: 100%;
}

.theme__track {
  display: block;
  width: 40px;
  height: 22px;
  border-radius: 999px;
  background-color: #D1D5DB;
  position: relative;
  padding: 3px;
  transition: background-color var(--transDur);
}

.theme__knob {
  display: block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
  transition: transform var(--transDur);
}

.theme__toggle:checked ~ .theme__track .theme__knob {
  transform: translateX(18px);
}

.theme__toggle:checked ~ .theme__track {
  background-color: #9CA3AF;
}

.theme__toggle:focus-visible ~ .theme__track {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
</style>
