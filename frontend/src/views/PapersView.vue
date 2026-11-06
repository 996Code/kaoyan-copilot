<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NEmpty, NSelect, NSpin } from 'naive-ui'
import { api } from '../api'
import { recall, remember } from '../memory'

const props = defineProps({ subject: { type: String, default: '' } })

const loading = ref(true)
const allPapers = ref({ gz199: [], en2: [] })
// 无参数进入时恢复上次科目；有参数（首页跳转）优先
const subject = ref(props.subject || recall('papers_subject', '') || '')
const year = ref(null)

const subjectName = (c) => (c === 'gz199' ? '199 管综' : '英语二')
const years = computed(() => (allPapers.value[subject.value] || []).map((p) => p.year))
const paper = computed(() =>
  (allPapers.value[subject.value] || []).find((p) => p.year === year.value) || null
)

async function load() {
  loading.value = true
  try {
    const [gz, en] = await Promise.all([
      api('/api/papers?subject=gz199'),
      api('/api/papers?subject=en2'),
    ])
    allPapers.value = { gz199: gz, en2: en }
    if (!year.value || !years.value.includes(year.value)) {
      year.value = years.value[0] // 最新一年
    }
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
  <div class="page">
    <!-- 科目选择 + 年份下拉 -->
    <div class="subj-bar">
      <n-button v-for="c in ['gz199', 'en2']" :key="c" size="small"
        :type="subject === c ? 'primary' : 'default'" @click="pick(c)">
        {{ subjectName(c) }}
      </n-button>
      <span style="flex:1"></span>
      <n-select v-model:value="year" :options="yearOptions" size="small"
        style="width:120px" placeholder="选择年份" />
    </div>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

    <template v-else-if="subject && paper">
      <!-- 年份快捷条 -->
      <div class="year-strip">
        <button v-for="y in years" :key="y" class="year-chip" :class="{ on: y === year }"
          @click="year = y">{{ y }}</button>
      </div>

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

    <n-empty v-else description="请选择科目" style="margin:60px 0" />
  </div>
</template>

<style scoped>
.subj-bar { display: flex; align-items: center; gap: 8px; margin: 14px 0 12px; }
.year-strip { display: flex; gap: 6px; overflow-x: auto; padding: 2px 2px 8px; scrollbar-width: none; }
.year-strip::-webkit-scrollbar { display: none; }
.year-chip {
  flex: none; border: 1px solid var(--line); background: var(--card); color: var(--t2);
  border-radius: 99px; padding: 5px 14px; font-size: 13px; cursor: pointer;
  font-variant-numeric: tabular-nums;
}
.year-chip.on { background: var(--blue); border-color: var(--blue); color: #fff; font-weight: 600; }
.paper-hero { padding: 28px 24px; text-align: center; border-radius: var(--r-card); }
.ph-year { font-size: 34px; font-weight: 900; color: var(--blue); font-variant-numeric: tabular-nums; line-height: 1; }
.ph-name { font-size: 15px; margin: 10px 0 4px; font-weight: 600; }
.ph-meta { font-size: 12.5px; }
@media (max-width: 768px) {
  .ph-year { font-size: 44px; }
}
</style>
