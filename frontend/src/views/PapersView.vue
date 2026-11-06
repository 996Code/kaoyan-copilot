<script setup>
import { onMounted, ref } from 'vue'
import { NCard, NButton, NSpin } from 'naive-ui'
import { api } from '../api'

const props = defineProps({ subject: { type: String, required: true } })
const papers = ref([])
const loading = ref(true)
const names = { gz199: '199 管综', en2: '英语二' }

onMounted(async () => {
  try {
    papers.value = await api(`/api/papers?subject=${props.subject}`)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <h2 style="margin:18px 0 4px">{{ names[subject] || subject }} · 历年真题整卷模考</h2>
    <p class="muted" style="margin:0 0 16px">限时作答 · 客观题自动判分 · 断点续答（中途退出不丢答案）</p>
    <n-spin v-if="loading" style="display:block;margin:60px auto" />
    <div v-else class="paper-grid">
      <n-card v-for="p in papers" :key="p.id" class="paper-card" :bordered="false">
        <div class="pc-year">{{ p.year }}</div>
        <div class="pc-name">{{ p.name }}</div>
        <div class="pc-meta muted">{{ p.total_score }} 分 · {{ p.duration_minutes }} 分钟</div>
        <n-button type="primary" block style="margin-top:12px" @click="$router.push(`/exam/${p.id}`)">
          开始模考
        </n-button>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.paper-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.paper-card { border-radius: 14px; text-align: left; }
.pc-year { font-size: 26px; font-weight: 800; color: var(--blue); }
.pc-name { margin: 6px 0 2px; font-size: 14px; }
.pc-meta { font-size: 12.5px; }
</style>
