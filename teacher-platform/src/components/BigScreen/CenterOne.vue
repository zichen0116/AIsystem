<template>
  <dv-digital-flop
    :config="config"
    class="animate__animated animate__fadeIn myData"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
const formatter = (number) => {
  const numbers = number.toString().split("").reverse();
  const segs = [];

  while (numbers.length) segs.push(numbers.splice(0, 3).join(""));

  return segs.join(",").split("").reverse().join("");
};

const config = ref({
  number: [123456],
  content: "{nt}个",
  formatter,
});

let intervalId;

onMounted(() => {
  intervalId = setInterval(() => {
    // 生成1000-10000随机数字
    config.value.number = [Math.floor(Math.random() * 9000) + 1000];
  }, 2000);
});

onUnmounted(() => {
  clearInterval(intervalId);
});
</script>

<style scoped lang="less">
.myData{
  display: flex;
  width: 200px;
  height: 50px;
}
</style>
