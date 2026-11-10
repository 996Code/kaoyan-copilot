<script setup>
// 全局图片/SVG 点击放大：document 级事件委托，无需各页面接入。
// 规则：点击 .rich 内的 svg 或任意 .chart-img / .lightbox-img 时弹出全屏预览；选项行内不触发（避免干扰作答）。
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const visible = ref(false)
const stageRef = ref(null) // 用 ref 引用 stage 元素，不走 querySelector（有 Vue 渲染时序问题）

function onClick(e) {
  if (visible.value) return
  const target = e.target
  if (target.closest('.opt-row')) return // 选项点击不放大
  const svg = target.closest('svg')
  const img = target.closest('img.chart-img, img.lightbox-img')
  if (!svg && !img) return
  e.preventDefault()
  e.stopPropagation()

  const node = svg || img
  const clone = node.cloneNode(true)
  if (svg) {
    clone.removeAttribute('style')
    clone.setAttribute('width', '100%')
    clone.setAttribute('height', 'auto')
  }
  visible.value = true

  // nextTick 确保 v-if 已渲染出 .lightbox-stage，再插入克隆节点
  nextTick(() => {
    if (stageRef.value) {
      stageRef.value.innerHTML = ''
      stageRef.value.appendChild(clone)
    }
  })
}

onMounted(() => document.addEventListener('click', onClick, true))
onBeforeUnmount(() => document.removeEventListener('click', onClick, true))
</script>

<template>
  <div v-if="visible" class="lightbox" @click="visible = false">
    <div ref="stageRef" class="lightbox-stage"></div>
    <div class="lightbox-tip">点击任意处关闭</div>
  </div>
</template>

<style scoped>
.lightbox {
  position: fixed; inset: 0; z-index: 999;
  background: rgba(10, 14, 24, .92);
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.lightbox-stage {
  width: 100%; max-height: 88vh; display: flex; align-items: center; justify-content: center;
  background: #fff; border-radius: 12px; padding: 14px; overflow: auto;
}
.lightbox-stage :deep(svg),
.lightbox-stage :deep(img) {
  max-width: 100%; max-height: 80vh; width: auto; height: auto;
}
.lightbox-tip {
  position: absolute; bottom: calc(20px + env(safe-area-inset-bottom)); left: 0; right: 0;
  text-align: center; color: rgba(255,255,255,.75); font-size: 12px;
}
</style>
