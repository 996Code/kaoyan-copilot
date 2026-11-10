<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NEmpty, NSelect, NSpin } from 'naive-ui'
import { api } from '../api'
import { recall, remember } from '../memory'
import HistoryView from './HistoryView.vue'

// embedded=true 时作为「练习」页的真题模考页签嵌入：不渲染页面壳与自身页签，固定显示模考内容
const props = defineProps({
  subject: { type: String, default: '' },
  embedded: { type: Boolean, default: false },
})
const route = useRoute()

const loading = ref(true)
const loadError = ref('')
const allPapers = ref({ gz199: [], en2: [] })
// 无参数进入时恢复上次科目；有参数（首页跳转）优先
const subject = ref(props.subject || recall('papers_subject', '') || '')
const year = ref(null)
// 页内页签：模考（选卷开考）/ 模考记录（历史成绩），支持 /papers?tab=record 深链
const pageTab = ref(props.embedded ? 'mock' : (route.query.tab === 'record' ? 'record' : 'mock'))
// 独立页内 query 变化时同步页签（如记录页空态「去模考」）
watch(() => route.query.tab, (t) => {
  if (!props.embedded) pageTab.value = t === 'record' ? 'record' : 'mock'
})

const subjectName = (c) => (c === 'gz199' ? '199 管综' : '英语二')
const years = computed(() => (allPapers.value[subject.value] || []).map((p) => p.year))
const paper = computed(() =>
  (allPapers.value[subject.value] || []).find((p) => p.year === year.value) || null
)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [gz, en] = await Promise.all([
      api('/api/papers?subject=gz199'),
      api('/api/papers?subject=en2'),
    ])
    allPapers.value = { gz199: gz, en2: en }
    if (!year.value || !years.value.includes(year.value)) {
      year.value = years.value[0] // 最新一年
    }
  } catch (e) {
    if (e.status !== 401) loadError.value = e.message
  } finally {
    loading.value = false
  }
}

function pick(c) {
  subject.value = c
  remember('papers_subject', c)
  year.value = (allPapers.value[c][0] || {}).year ?? null
}

onMounted(async () => {
  await load()
  if (props.subject && allPapers.value[props.subject]?.length) {
    subject.value = props.subject
  } else if (subject.value && allPapers.value[subject.value]?.length) {
    year.value = (allPapers.value[subject.value][0] || {}).year ?? null
  } else {
    pick('gz199')  // 默认进入管综最新年
  }
})

const yearOptions = computed(() => years.value.map((y) => ({ label: `${y} 年`, value: y })))
</script>

<template>
  <div :class="embedded ? '' : 'page'">
    <!-- 页签：真题模考 / 模考记录（嵌入模式下由父级「练习」页接管） -->
    <div v-if="!embedded" class="page-seg" role="group" aria-label="真题模考板块">
      <n-button size="small" :aria-pressed="pageTab === 'mock'" :type="pageTab === 'mock' ? 'primary' : 'default'" @click="pageTab = 'mock'">真题模考</n-button>
      <n-button size="small" :aria-pressed="pageTab === 'record'" :type="pageTab === 'record' ? 'primary' : 'default'" @click="pageTab = 'record'">模考记录</n-button>
    </div>

    <!-- 模考记录：整块复用记录页 -->
    <HistoryView v-if="pageTab === 'record'" embedded />

    <template v-else>
      <!-- 科目选择 + 年份下拉 -->
      <div class="subj-bar">
        <div class="subject-segment" role="group" aria-label="模考科目">
        <n-button v-for="c in ['gz199', 'en2']" :key="c" size="small" :disabled="loading"
          :aria-pressed="subject === c" :type="subject === c ? 'primary' : 'default'" @click="pick(c)">
          {{ subjectName(c) }}
        </n-button>
        </div>
        <div class="year-field"><span>年份</span><n-select v-model:value="year" aria-label="试卷年份" :input-props="{ 'aria-label': '试卷年份' }" :disabled="loading || !years.length" :options="yearOptions" placeholder="选择年份" /></div>
      </div>

      <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>
      <div v-else-if="loadError" class="error-state" role="alert">{{ loadError }} <n-button @click="load">重试试卷加载</n-button></div>

      <template v-else-if="subject && paper">
        <!-- 选中年份的试卷卡（一年一套，直接开考） -->
        <div class="paper-hero panel">
          <div class="ph-year">{{ paper.year }}</div>
          <div class="ph-name">{{ paper.name }}</div>
          <div class="ph-meta muted">
            {{ paper.total_score }} 分 · {{ paper.duration_minutes }} 分钟
            · {{ subject === 'gz199' ? '数学+逻辑+写作' : '完形+阅读+翻译+写作' }}
          </div>
          <n-button type="primary" size="large" style="margin-top:16px; width:100%"
            @click="$router.push(`/exam/${paper.id}`)">
            开始模考
          </n-button>
        </div>
        <p class="muted" style="font-size:12px; text-align:center; margin-top:10px">
          断点续答：中途退出自动保存，回来继续
        </p>
      </template>

      <n-empty v-else :description="subject ? '该科目暂无可用试卷' : '请选择科目'" style="margin:60px 0" />
    </template>
  </div>
</template>

<style scoped>
.page-seg { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:4px; padding:4px; border-radius:8px; background:var(--line-soft); margin:14px 0 12px; }
.page-seg .n-button { min-height:44px; }
.subj-bar { display:grid; grid-template-columns:minmax(0,1fr) minmax(140px,180px); align-items:end; gap:14px; margin:14px 0 12px; }
.subject-segment { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); max-width:360px; gap:4px; padding:4px; border-radius:8px; background:var(--line-soft); }
.subject-segment .n-button { min-width:0; min-height:44px; }
.year-field { display:grid; gap:6px; min-width:0; font-size:12px; color:var(--t2); }
.year-field :deep(.n-base-selection) { min-height:44px; }
.error-state { display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin:14px 0; }
.paper-hero .n-button { min-height:44px; }
.paper-hero { padding: 28px 24px; text-align: center; border-radius: var(--r-card); }
.ph-year { font-size: 34px; font-weight: 900; color: var(--blue); font-variant-numeric: tabular-nums; line-height: 1; }
.ph-name { font-size: 15px; margin: 10px 0 4px; font-weight: 600; }
.ph-meta { font-size: 12.5px; }
@media (max-width: 768px) {
  .subj-bar { grid-template-columns:minmax(0,1fr); }
  .subject-segment { max-width:none; }
  .year-field { grid-template-columns:auto minmax(0,1fr); align-items:center; gap:12px; }
  .paper-hero { padding:24px 16px; }
  .ph-name, .ph-meta { overflow-wrap:anywhere; }
}
</style>
