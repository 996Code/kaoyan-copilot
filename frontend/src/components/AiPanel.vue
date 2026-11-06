<script setup>
import { computed, ref } from 'vue'
import { NButton, NTag } from 'naive-ui'
import { sse } from '../api'
import { renderRich } from '../markdown'

const props = defineProps({
  endpoint: { type: String, required: true }, // SSE 地址
  label: { type: String, default: 'AI 讲解' },
})
const status = ref('idle') // idle | streaming | done | error
const text = ref('')
const errorMsg = ref('')
const cached = ref(false)

const renderedHtml = computed(() => (status.value === 'done' ? renderRich(text.value) : ''))

async function start() {
  if (status.value === 'streaming') return
  // 已有内容：点击即折叠/展开
  if (status.value === 'done' && text.value) {
    collapsed.value = !collapsed.value
    return
  }
  status.value = 'streaming'
  text.value = ''
  errorMsg.value = ''
  try {
    await sse(props.endpoint, {
      onEvent(ev) {
        if (ev.type === 'delta') {
          text.value += ev.text
        } else if (ev.type === 'done') {
          cached.value = !!ev.cached
          status.value = 'done'
        } else if (ev.type === 'error') {
          errorMsg.value = ev.message
          status.value = 'error'
        }
      },
    })
    if (status.value === 'streaming') status.value = 'done'
  } catch (e) {
    errorMsg.value = e.message
    status.value = 'error'
  }
}

const collapsed = ref(false)
</script>

<template>
  <div class="ai-panel">
    <div class="ai-bar">
      <n-button size="tiny" :type="status === 'done' && !collapsed ? 'primary' : 'default'"
        :loading="status === 'streaming'" @click="start">
        ✨ {{ status === 'streaming' ? '讲解中…' : label }}
      </n-button>
      <n-tag v-if="cached && status === 'done'" size="tiny" type="info" :bordered="false">缓存</n-tag>
    </div>

    <div v-if="status === 'streaming'" class="ai-body streaming">
      <span>{{ text }}</span><span class="cursor">▍</span>
    </div>
    <div v-else-if="status === 'done' && !collapsed" class="ai-body rich" v-html="renderedHtml"></div>
    <div v-else-if="status === 'error'" class="ai-body error">{{ errorMsg }}</div>
  </div>
</template>

<style scoped>
.ai-panel { margin-top: 10px; }
.ai-bar { display: flex; gap: 8px; align-items: center; }
.ai-body {
  margin-top: 8px; padding: 10px 14px; border-radius: 10px; font-size: 14px;
  background: linear-gradient(135deg, rgba(106,92,255,.06), rgba(47,111,237,.05));
  border: 1px solid rgba(106,92,255,.18);
}
.ai-body.streaming { white-space: pre-wrap; line-height: 1.7; }
.ai-body.error { background: rgba(208,48,80,.06); border-color: rgba(208,48,80,.25); color: #b03050; }
.cursor { animation: blink 0.9s infinite; color: #6a5cff; }
@keyframes blink { 50% { opacity: 0; } }
</style>
