<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  NButton, NCard, NEmpty, NSelect, NSpin, NTag, useMessage,
} from 'naive-ui'
import { api } from '../api'
import { recall, remember } from '../memory'
import { renderRich } from '../markdown'
import QuestionItem from '../components/QuestionItem.vue'
import GroupMaterial from '../components/GroupMaterial.vue'
import AiPanel from '../components/AiPanel.vue'

const message = useMessage()

const subjects = [
  { code: 'gz199', name: '199 管综' },
  { code: 'en2', name: '英语二' },
]
// 恢复上次的筛选与浏览位置
const saved = recall('wb_state', {}) || {}
const subject = ref(saved.subject || 'gz199')
const showMastered = ref(saved.showMastered || false)
const moduleFilter = ref(saved.module ?? null)
const idx = ref(saved.idx || 0)

const subjectDetails = ref([])
const modules = computed(() => subjectDetails.value.find(s => s.code === subject.value)?.modules || [])
const items = ref([])
const loading = ref(false)
const loadError = ref('')
const subjectsError = ref('')
const mastering = ref(false)
let loadVersion = 0
let advanceTimer = null
const showNav = ref(false) // 答题卡面板
const collapseAnalysis = ref({}) // qid -> bool（默认展开解析）

const moduleOptions = computed(() => [
  { label: '全部模块', value: null },
  ...modules.value.map((m) => ({ label: m.name, value: m.code })),
])

const item = computed(() => items.value[idx.value] || null)
const activeStats = ref({})

async function load() {
  const version = ++loadVersion
  clearTimeout(advanceTimer)
  loading.value = true
  loadError.value = ''
  try {
    const params = new URLSearchParams({ subject: subject.value, mastered: String(showMastered.value) })
    if (moduleFilter.value) params.set('module', moduleFilter.value)
    const [data, stats] = await Promise.all([
      api(`/api/wrongbook?${params}`),
      api(`/api/wrongbook/stats?subject=${subject.value}`),
    ])
    if (version !== loadVersion) return
    items.value = data
    activeStats.value = stats
    idx.value = Math.min(idx.value, Math.max(0, items.value.length - 1))
  } catch (e) {
    if (version !== loadVersion || e.status === 401) return
    loadError.value = e.message
    message.error(e.message)
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function persist() {
  remember('wb_state', {
    subject: subject.value,
    showMastered: showMastered.value,
    module: moduleFilter.value,
    idx: idx.value,
  })
}

watch(subject, () => {
  moduleFilter.value = null
}, { flush: 'sync' })
watch([subject, showMastered, moduleFilter], () => {
  idx.value = 0
  showNav.value = false
  persist()
  load()
})
watch(idx, persist)
onBeforeUnmount(persist)

function goto(i) {
  if (loading.value || mastering.value || i < 0 || i >= items.value.length) return
  clearTimeout(advanceTimer)
  idx.value = i
  showNav.value = false
  window.scrollTo({ top: 0 })
}

async function toggleMastered(it) {
  if (mastering.value || loading.value) return
  mastering.value = true
  const version = loadVersion
  const q = it.question
  try {
    await api(`/api/wrongbook/${q.id}/master`, {
      method: 'POST',
      body: { mastered: !it.mastered },
    })
    if (version !== loadVersion) return
    it.mastered = !it.mastered
    message.success(it.mastered ? '已标记消灭，即将跳到下一题' : '已放回待巩固')
    if (it.mastered) {
      advanceTimer = setTimeout(() => {
        if (version !== loadVersion || item.value?.question.id !== q.id) return
        const nextIdx = items.value.findIndex((x) => !x.mastered)
        if (nextIdx >= 0) goto(nextIdx)
        else load()
      }, 1400)
    }
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
  } finally {
    mastering.value = false
  }
}

function groupOf(it) {
  const q = it.question
  if (!q.group_material && !q.group_options && !q.group_image && !q.group_title) return null
  return {
    gtype: q.group_options ? 'matching' : /\{\{\d+\}\}/.test(q.group_material || '') ? 'cloze' : 'reading',
    title: q.group_title,
    material: q.group_material,
    options: q.group_options,
    material_image: q.group_image,
  }
}

function explainEndpoint(it) {
  const sa = it.last_answer != null ? `?student_answer=${encodeURIComponent(it.last_answer)}` : ''
  return `/api/ai/explain/${it.question.id}${sa}`
}

function onKey(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (['textarea', 'input', 'button', 'select'].includes(tag) || e.target.isContentEditable || e.repeat) return
  if (e.key === 'ArrowRight' || e.key === 'k') { goto(idx.value + 1); e.preventDefault() }
  if (e.key === 'ArrowLeft' || e.key === 'j') { goto(idx.value - 1); e.preventDefault() }
}

async function loadSubjects() {
  subjectsError.value = ''
  try {
    subjectDetails.value = await api('/api/subjects')
    if (moduleFilter.value && !modules.value.some(m => m.code === moduleFilter.value)) moduleFilter.value = null
  } catch (e) {
    if (e.status === 401) return
    subjectsError.value = e.message
    message.error(e.message)
  }
}
onMounted(async () => {
  window.addEventListener('keydown', onKey)
  await loadSubjects()
  load()
})
onBeforeUnmount(() => {
  loadVersion += 1
  clearTimeout(advanceTimer)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="page">
    <!-- 筛选条 -->
    <n-card :bordered="false" style="border-radius: var(--r-card); margin-bottom: 12px">
      <div class="wb-filters">
        <div class="subject-segment" role="group" aria-label="错题科目">
        <n-button v-for="s in subjects" :key="s.code" size="small" :disabled="mastering"
          :type="subject === s.code ? 'primary' : 'default'" @click="subject = s.code">
          {{ s.name }}
        </n-button>
        </div>
        <div class="wb-stats">
        <span v-for="(st, code) in activeStats" :key="code" class="muted stat-chip">
          {{ (modules.find(m => m.code === code)?.name) || code }}：待巩固 {{ st.active }}
        </span>
        </div>
        <div class="filter-field"><span>模块</span><n-select v-model:value="moduleFilter" aria-label="错题模块" :input-props="{ 'aria-label': '错题模块' }" :disabled="mastering || !subjectDetails.length" :options="moduleOptions" /></div>
        <n-button class="mastered-filter" size="small" :disabled="mastering" :type="showMastered ? 'warning' : 'default'" @click="showMastered = !showMastered">
          {{ showMastered ? '看已消灭' : '看待巩固' }}
        </n-button>
      </div>
      <div v-if="subjectsError" class="error-state" role="alert">{{ subjectsError }} <n-button @click="loadSubjects">重试科目加载</n-button></div>
    </n-card>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>
    <div v-else-if="loadError" class="error-state" role="alert">{{ loadError }} <n-button @click="load">重试错题加载</n-button></div>
    <n-empty v-else-if="!items.length" description="这个视图下没有错题——要么你很强，要么还没开始做题"
      style="margin:60px 0" />

    <template v-else-if="item">
      <!-- 导航条 + 答题卡开关 -->
      <div class="nav-bar panel">
        <n-button class="nav-prev" quaternary size="small" :disabled="idx === 0 || mastering" @click="goto(idx - 1)">‹ 上一题</n-button>
        <span class="nav-pos">第 {{ idx + 1 }} / {{ items.length }} 题</span>
        <n-button class="nav-toggle" size="small" :aria-expanded="showNav" @click="showNav = !showNav">答题卡</n-button>
        <n-button class="nav-next" quaternary size="small" :disabled="idx === items.length - 1 || mastering" @click="goto(idx + 1)">下一题 ›</n-button>
      </div>

      <!-- 答题卡面板 -->
      <div class="nav-grid panel" :class="{ open: showNav }">
        <div class="anscard">
          <button v-for="(it, i) in items" :key="it.question.id" type="button" class="cell"
            :class="{ answered: it.mastered, current: i === idx }"
            :title="`${it.question.year} 年 · 真题第 ${it.question.number} 题`"
            :aria-label="`第 ${i + 1} 项，${it.question.year} 年真题第 ${it.question.number} 题`"
            :aria-current="i === idx ? 'step' : undefined" :disabled="mastering"
            @click="goto(i)">
            {{ i + 1 }}
          </button>
        </div>
        <div class="muted" style="font-size:12px; margin-top:8px">
          橙框＝当前 · 深色＝已消灭 · ←→ 切题
        </div>
      </div>

      <!-- 当前错题 -->
      <div class="wb-card panel">
        <div class="wb-meta">
          <n-tag type="error" size="small">错 {{ item.wrong_count }} 次</n-tag>
          <n-tag v-if="item.question.disputed" type="warning" size="small">答案存在版本争议</n-tag>
          <n-tag v-if="item.mastered" type="success" size="small">已消灭</n-tag>
          <span class="muted meta-text">
            {{ item.question.year }} 年 · {{ item.module.name }} · 第 {{ item.question.number }} 题
            · 最近做错 {{ (item.last_wrong_at || '').replace('T', ' ').slice(0, 16) }}
          </span>
          <n-button class="master-action" size="small" :loading="mastering" :type="item.mastered ? 'success' : 'default'" style="margin-left:auto"
            @click="toggleMastered(item)">
            {{ item.mastered ? '已消灭（撤销）' : '标记已消灭' }}
          </n-button>
        </div>

        <GroupMaterial v-if="groupOf(item)" :key="item.question.id" :group="groupOf(item)" />
        <QuestionItem :key="item.question.id" :q="item.question" :model-value="item.last_answer" mode="review"
          :result="{ your_answer: item.last_answer, correct_answer: item.question.answer }"
          :shared-options="item.question.group_options" />

        <div class="verdict muted">
          我答：<b class="bad">{{ item.last_answer ?? '未答' }}</b>
          <span style="margin-left:12px">正确：<b class="ok">{{ item.question.answer }}</b></span>
          <!-- 知识卡↔题目打通：错题直达对应知识卡分类 -->
          <button type="button" class="kp-link"
            @click="$router.push(`/knowledge?subject=${subject}&module=${item.module.code}`)">
            相关知识卡 ›
          </button>
        </div>

        <div v-if="item.question.analysis" class="analysis">
          <div class="section-title toggle"
            @click="collapseAnalysis[item.question.id] = !collapseAnalysis[item.question.id]">
            {{ collapseAnalysis[item.question.id] ? '▸ 显示解析' : '▾ 收起解析' }}
          </div>
          <div v-show="!collapseAnalysis[item.question.id]" class="rich"
            v-html="renderRich(item.question.analysis)"></div>
        </div>

        <AiPanel :key="item.question.id" :endpoint="explainEndpoint(item)" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.wb-filters { display:grid; grid-template-columns:auto minmax(0,1fr) minmax(140px,180px) auto; align-items:end; gap:10px; }
.subject-segment { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; }
.wb-stats { display:flex; flex-wrap:wrap; gap:6px; align-self:center; }
.stat-chip { font-size:12px; background:var(--line-soft); border-radius:6px; padding:5px 8px; }
.filter-field { display:grid; gap:6px; min-width:0; font-size:12px; color:var(--t2); }
.filter-field :deep(.n-base-selection) { min-height:44px; }
.wb-filters .n-button, .master-action, .nav-bar .n-button { min-height:44px; }
.error-state { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:14px 0; }
.nav-bar { display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; margin-bottom: 12px; gap: 8px; }
.nav-pos { font-size: 13.5px; color: var(--t2); font-variant-numeric: tabular-nums; }
.nav-grid { padding: 12px 14px; margin-bottom: 12px; display: none; }
.nav-grid.open { display: block; }
.wb-card { padding: 16px 18px; margin-bottom: 14px; }
.wb-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.meta-text { font-size: 12.5px; }
.verdict { margin-top: 8px; font-size: 14px; padding: 8px 12px; background: var(--line-soft); border-radius: 8px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 0; }
.kp-link { border: none; background: none; cursor: pointer; margin-left: auto; padding: 6px 4px 6px 12px; font-size: 13px; color: var(--blue); min-height: 36px; }
.kp-link:hover { text-decoration: underline; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
.toggle { cursor: pointer; user-select: none; }
.anscard .cell { width:44px; height:44px; flex-shrink:0; font-family:inherit; }
@media (max-width:768px) {
  .wb-filters { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .subject-segment, .wb-stats { grid-column:1 / -1; }
  .subject-segment { grid-row:1; }
  .wb-stats { grid-row:3; }
  .nav-bar { display:grid; grid-template-columns:minmax(0,1fr) auto; position:sticky; top:52px; z-index:15; background:var(--card,#fff); padding:8px; }
  .nav-pos { grid-area:1 / 1; white-space:nowrap; padding-left:8px; }
  .nav-toggle { grid-area:1 / 2; }
  .nav-prev { grid-area:2 / 1; }
  .nav-next { grid-area:2 / 2; }
  .wb-card { padding:14px; }
}
</style>
