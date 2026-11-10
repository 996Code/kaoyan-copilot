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
    // 试卷列表暂不返回科目字段，保留两个带科目筛选的请求来源。
    for (const [list, subject] of [[gz, 'gz199'], [en, 'en2']]) {
      for (const p of list) papers.value[p.id] = { ...p, subject_code: subject }
    }
    records.value = hist
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
})

const subjectName = (id) => {
  const code = papers.value[id]?.subject_code
  return code === 'gz199' ? '管综' : code === 'en2' ? '英二' : '科目待确认'
}
const paperYear = (id) => papers.value[id]?.year || '年份待确认'
const paperName = (id) => papers.value[id]?.name || '历史模考试卷'
const submittedAt = (record) => record.submitted_at
  ? String(record.submitted_at).replace('T', ' ').slice(0, 16)
  : '交卷时间待确认'
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
      <div v-for="r in records" :key="r.id" class="hist-item panel" role="link" tabindex="0"
        :aria-label="`${paperName(r.paper_id)}，${submittedAt(r)}，查看报告`"
        @click="$router.push(`/report/${r.id}`)" @keydown.enter="$router.push(`/report/${r.id}`)">
        <div class="hi-left">
          <div class="hi-heading">
            <span class="hi-year">{{ paperYear(r.paper_id) }}</span>
            <span class="hi-subj tag" :class="papers[r.paper_id]?.subject_code === 'gz199' ? 'b' : papers[r.paper_id]?.subject_code === 'en2' ? 'g' : ''">{{ subjectName(r.paper_id) }}</span>
          </div>
          <span class="hi-name">{{ paperName(r.paper_id) }}</span>
        </div>
        <div class="hi-score">
          <span class="score-label muted">客观题得分</span>
          <div>
            <b :class="r.objective_score == null ? '' : r.objective_score >= (r.objective_total || 1) * 0.5 ? 'ok' : 'bad'">{{ r.objective_score ?? '—' }}</b>
            <span class="muted"> / {{ r.objective_total ?? '—' }}</span>
          </div>
        </div>
        <span class="muted hi-date">交卷 {{ submittedAt(r) }}</span>
        <div class="hi-right">
          <n-tag v-if="r.overtime" type="error" size="small">超时</n-tag>
          <span class="go">查看报告 ›</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { font-size: 14px; }
.hist-list { display: flex; flex-direction: column; gap: 10px; }
.hist-item { display: grid; grid-template-columns: minmax(0, 1fr) minmax(100px, auto) auto auto; align-items: center; gap: 16px; padding: 14px 16px; cursor: pointer; border-radius: 8px; }
.hist-item:hover { border-color: var(--blue); }
.hist-item:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
.hi-left { min-width: 0; }
.hi-heading { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.hi-year { font-size: 20px; font-weight: 800; color: var(--blue); font-variant-numeric: tabular-nums; }
.hi-subj { flex-shrink: 0; font-size: 12px; }
.hi-name { display: block; font-size: 14px; margin-top: 4px; overflow-wrap: anywhere; }
.score-label { display: block; font-size: 12px; }
.hi-score { min-width: 0; font-variant-numeric: tabular-nums; }
.hi-score > div { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px; }
.hi-score b { font-size: 22px; }
.hi-date { font-size: 12px; font-variant-numeric: tabular-nums; }
.hi-right { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 8px; }
.go { color: var(--blue); font-size: 14px; min-height: 44px; display: flex; align-items: center; }
.page :deep(.n-button) { min-height: 44px; font-size: 14px; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
@media (max-width: 768px) {
  .hist-item { grid-template-columns: minmax(0, 1fr) minmax(88px, auto); gap: 12px; padding: 14px; }
  .hi-score { text-align: right; align-self: start; }
  .hi-score > div { justify-content: flex-end; }
  .hi-date { align-self: center; overflow-wrap: anywhere; line-height: 1.6; }
  .hi-right { gap: 6px; }
}
</style>
