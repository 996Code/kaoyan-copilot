<script setup>
import { onMounted, ref } from 'vue'
import { NButton, NCard, NEmpty, NSpin, NTag, useMessage } from 'naive-ui'
import { api } from '../api'

const message = useMessage()
const loading = ref(true)
const records = ref([])
const papers = ref({})

onMounted(async () => {
  try {
    const [hist, gz, en] = await Promise.all([
      api('/api/exams/history'),
      api('/api/papers?subject=gz199'),
      api('/api/papers?subject=en2'),
    ])
    papers.value = {}
    for (const p of [...gz, ...en]) papers.value[p.id] = p
    records.value = hist
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
})

const subjectName = (id) => {
  const p = papers.value[id]
  if (!p) return ''
  return p.name.includes('管综') ? '管综' : '英二'
}
const paperYear = (id) => papers.value[id]?.year || ''
</script>

<template>
  <div class="page">
    <div class="kb-head">
      <h1 class="page-h2">模考记录</h1>
    </div>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>
    <n-empty v-else-if="!records.length" description="还没有模考记录，去真题页开始第一套" style="margin:60px 0">
      <template #extra><n-button size="small" @click="$router.push('/papers')">去模考</n-button></template>
    </n-empty>

    <div v-else class="hist-list">
      <div v-for="r in records" :key="r.id" class="hist-item panel" @click="$router.push(`/report/${r.id}`)">
        <div class="hi-left">
          <span class="hi-year">{{ paperYear(r.paper_id) }}</span>
          <span class="hi-subj tag" :class="subjectName(r.paper_id) === '管综' ? 'b' : 'g'">{{ subjectName(r.paper_id) }}</span>
        </div>
        <div class="hi-mid">
          <div class="hi-score">
            <b :class="(r.objective_score || 0) >= (r.objective_total || 1) * 0.5 ? 'ok' : 'bad'">{{ r.objective_score ?? '—' }}</b>
            <span class="muted"> / {{ r.objective_total }} 客观</span>
          </div>
          <span class="muted hi-date">{{ (r.submitted_at || '').replace('T', ' ').slice(0, 16) }}</span>
        </div>
        <div class="hi-right">
          <n-tag v-if="r.overtime" type="error" size="small">超时</n-tag>
          <span class="go">报告 ›</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hist-list { display: flex; flex-direction: column; gap: 10px; }
.hist-item { display: flex; align-items: center; gap: 14px; padding: 14px 16px; cursor: pointer; border-radius: var(--r-card); }
.hist-item:hover { border-color: var(--blue); }
.hi-left { display: flex; align-items: center; gap: 8px; min-width: 80px; }
.hi-year { font-size: 20px; font-weight: 800; color: var(--blue); font-variant-numeric: tabular-nums; }
.hi-mid { flex: 1; }
.hi-score b { font-size: 22px; font-variant-numeric: tabular-nums; }
.hi-date { font-size: 12px; display: block; margin-top: 2px; }
.hi-right { display: flex; align-items: center; gap: 8px; }
.go { color: var(--blue); font-size: 13px; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
</style>
