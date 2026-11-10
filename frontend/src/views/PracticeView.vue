<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  NButton, NCard, NSelect, NSpin, NTag, useMessage,
} from 'naive-ui'
import { api } from '../api'
import { recall, remember } from '../memory'
import { renderRich } from '../markdown'
import QuestionItem from '../components/QuestionItem.vue'
import GroupMaterial from '../components/GroupMaterial.vue'
import AiPanel from '../components/AiPanel.vue'
import PapersView from './PapersView.vue'
import HistoryView from './HistoryView.vue'

const message = useMessage()
const route = useRoute()

/* 「练习」归纳做题三入口：专项抽题 / 真题整卷 / 模考记录 */
const TABS = [
  { key: 'special', label: '专项练习' },
  { key: 'papers', label: '真题模考' },
  { key: 'record', label: '模考记录' },
]
const pageTab = ref(['papers', 'record'].includes(route.query.tab) ? route.query.tab : 'special')

const subjects = ref([])
const subject = ref('gz199')
const moduleCode = ref('math')
const year = ref(null)
const count = ref(10)

// 题型专项包（海绵刷题营思路：按题型集中突破）
const PACKS = [
  { label: '条充专项', subject: 'gz199', module: 'math', min: 16, max: 25 },
  { label: '数学求解', subject: 'gz199', module: 'math', min: 1, max: 15 },
  { label: '逻辑推理', subject: 'gz199', module: 'logic' },
  { label: '英二完形', subject: 'en2', module: 'cloze' },
  { label: '英二阅读', subject: 'en2', module: 'reading' },
]
const activePack = ref(null)
function packActive(pk) {
  return activePack.value && activePack.value.label === pk.label
}
function applyPack(pk) {
  if (loading.value || submitting.value) return
  subject.value = pk.subject
  moduleCode.value = pk.module
  activePack.value = pk
  minNumber.value = pk.min || null
  maxNumber.value = pk.max || null
  year.value = null
  start()
}
const minNumber = ref(null)
const maxNumber = ref(null)

const questions = ref([])
const loading = ref(false)
const submitting = ref(false)
const finished = ref(false)
const loadError = ref('')
const subjectsError = ref('')
const started = ref(false)
const current = ref(0)
const myAnswer = ref(null)
const checked = ref(null) // check 接口返回
const stats = reactive({ done: 0, correct: 0 })

const moduleOptions = computed(() => {
  const sub = subjects.value.find((s) => s.code === subject.value)
  return (sub?.modules || []).map((m) => ({ label: m.name, value: m.code }))
})
const yearOptions = computed(() => {
  const base = subject.value === 'gz199' ? 2009 : 2010
  const end = subject.value === 'gz199' ? 2026 : 2025
  const opts = [{ label: '全部年份（随机）', value: null }]
  for (let y = end; y >= base; y--) opts.push({ label: `${y} 年`, value: y })
  return opts
})

const item = computed(() => questions.value[current.value] || null)
const group = computed(() => {
  if (!item.value || !item.value.group_material && !item.value.group_options && !item.value.group_image && !item.value.group_title) return null
  if (item.value.qtype === 'single_choice' && !item.value.group_material && !item.value.group_options) return null
  const material = item.value.group_material || ''
  const gtype = item.value.group_options ? 'matching'
    : /\{\{\d+\}\}/.test(material) ? 'cloze'
    : item.value.qtype === 'essay' ? 'gz_essay'
    : 'reading'
  return {
    gtype,
    title: item.value.group_title,
    material: item.value.group_material,
    options: item.value.group_options,
    material_image: item.value.group_image,
  }
})

async function start() {
  if (loading.value || submitting.value || !moduleCode.value) return
  loading.value = true
  loadError.value = ''
  started.value = true
  try {
    const params = new URLSearchParams({ subject: subject.value, module: moduleCode.value, limit: String(count.value), random: 'true' })
    if (year.value) params.set('year', String(year.value))
    if (minNumber.value != null) params.set('min_number', String(minNumber.value))
    if (maxNumber.value != null) params.set('max_number', String(maxNumber.value))
    questions.value = await api(`/api/practice/questions?${params}`)
    current.value = 0
    myAnswer.value = null
    checked.value = null
    finished.value = false
    stats.done = 0
    stats.correct = 0
    if (!questions.value.length) message.warning('没有符合条件的题目')
  } catch (e) {
    if (e.status === 401) return
    loadError.value = e.message
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

async function check() {
  if (!item.value || loading.value || submitting.value || checked.value || finished.value || myAnswer.value == null || myAnswer.value === '') return
  submitting.value = true
  const answer = myAnswer.value
  try {
    checked.value = await api('/api/practice/check', {
      method: 'POST',
      body: { question_id: item.value.id, answer },
    })
    myAnswer.value = answer
    stats.done += 1
    if (checked.value.correct) stats.correct += 1
  } catch (e) {
    if (e.status !== 401) message.error(e.message)
  } finally {
    submitting.value = false
  }
}

function next() {
  if (!checked.value || submitting.value || finished.value) return
  if (current.value >= questions.value.length - 1) {
    finished.value = true
    return
  }
  current.value += 1
  myAnswer.value = null
  checked.value = null
}

watch(subject, () => {
  activePack.value = null
  minNumber.value = maxNumber.value = null
  year.value = null
  moduleCode.value = moduleOptions.value[0]?.value
}, { flush: 'sync' })
watch(moduleCode, () => {
  activePack.value = null
  minNumber.value = maxNumber.value = null
}, { flush: 'sync' })
watch([subject, moduleCode, year, count], () => {
  remember('pf_state', { subject: subject.value, module: moduleCode.value, year: year.value, count: count.value })
})

function onKey(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (['textarea', 'input', 'button', 'select'].includes(tag) || e.target.isContentEditable || e.repeat) return
  if (!item.value || loading.value || submitting.value || finished.value) return
  const letters = ['a', 'b', 'c', 'd', 'e']
  if (item.value.qtype === 'single_choice' && item.value.options && !checked.value) {
    const li = letters.indexOf(e.key.toLowerCase())
    const ni = Number(e.key) >= 1 && Number(e.key) <= 5 ? Number(e.key) - 1 : -1
    const idx = li >= 0 ? li : ni
    if (idx >= 0 && idx < item.value.options.length) {
      myAnswer.value = item.value.options[idx].key
      e.preventDefault(); return
    }
    if (e.key === 'Enter') { check(); e.preventDefault(); return }
  }
  if (e.key === 'Enter' && checked.value) { next(); e.preventDefault() }
}

async function loadSubjects() {
  subjectsError.value = ''
  try {
  subjects.value = await api('/api/subjects')
  // 支持看板跳转预选：/practice?subject=gz199&module=math
  const qs = new URLSearchParams((location.hash.split('?')[1] || ''))
  const qsSubject = qs.get('subject')
  const qsModule = qs.get('module')
  const mem = recall('pf_state', {}) || {}
  const qsOverride = qsSubject != null
  const preset = subjects.value.find((s) => s.code === qsSubject)
    || subjects.value.find((s) => s.code === mem.subject)
    || subjects.value[0]
  if (preset) {
    subject.value = preset.code
    const wantModule = qsModule || (qsOverride ? null : mem.module)
    moduleCode.value = preset.modules.find((m) => m.code === wantModule)?.code || preset.modules[0]?.code
  }
  if (!qsOverride && mem.year !== undefined) year.value = mem.year
  if (!qsOverride && mem.count) count.value = mem.count
  } catch (e) {
    if (e.status !== 401) {
      subjectsError.value = e.message
      message.error(e.message)
    }
  }
}
onMounted(() => {
  window.addEventListener('keydown', onKey)
  loadSubjects()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page">
    <!-- 页签：专项练习 / 真题模考 / 模考记录（做题三入口归纳于一页） -->
    <div class="page-seg" role="group" aria-label="练习板块">
      <n-button v-for="t in TABS" :key="t.key" size="small" :aria-pressed="pageTab === t.key"
        :type="pageTab === t.key ? 'primary' : 'default'" @click="pageTab = t.key">{{ t.label }}</n-button>
    </div>

    <!-- 真题模考 / 模考记录：整块复用对应页面 -->
    <PapersView v-if="pageTab === 'papers'" embedded />
    <HistoryView v-else-if="pageTab === 'record'" embedded />

    <template v-else>
    <h2 class="page-h2" style="margin:2px 0 4px">专项练习</h2>
    <p class="muted pf-sub" style="margin:0 0 14px">按模块/年份抽题，即答即判，错题自动进错题记录</p>

    <n-card :bordered="false" style="border-radius:14px; margin-bottom:16px">
      <div class="packs">
        <span class="packs-label muted">专项包：</span>
        <n-button v-for="pk in PACKS" :key="pk.label" size="small" :disabled="loading || submitting || !subjects.length"
          :type="packActive(pk) ? 'primary' : 'default'" @click="applyPack(pk)">
          {{ pk.label }}
        </n-button>
      </div>
      <div class="filters" style="margin-top:10px">
        <div class="filter-field"><span>科目</span><n-select v-model:value="subject" aria-label="练习科目" :input-props="{ 'aria-label': '练习科目' }" :disabled="loading || submitting" :options="subjects.map(s => ({ label: s.name, value: s.code }))" /></div>
        <div class="filter-field"><span>模块</span><n-select v-model:value="moduleCode" aria-label="练习模块" :input-props="{ 'aria-label': '练习模块' }" :disabled="loading || submitting" :options="moduleOptions" /></div>
        <div class="filter-field"><span>年份</span><n-select v-model:value="year" aria-label="练习年份" :input-props="{ 'aria-label': '练习年份' }" :disabled="loading || submitting" :options="yearOptions" /></div>
        <div class="filter-field"><span>题量</span><n-select v-model:value="count" aria-label="练习题量" :input-props="{ 'aria-label': '练习题量' }" :disabled="loading || submitting" :options="[{label:'10 题',value:10},{label:'20 题',value:20},{label:'30 题',value:30}]" /></div>
        <n-button type="primary" :loading="loading" :disabled="submitting || !subjects.length || !moduleCode" @click="start">开始练习</n-button>
      </div>
      <div v-if="subjectsError" class="error-state" role="alert">{{ subjectsError }} <n-button @click="loadSubjects">重试科目加载</n-button></div>
    </n-card>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

    <div v-else-if="loadError" class="error-state" role="alert">{{ loadError }} <n-button @click="start">重试练习加载</n-button></div>
    <div v-else-if="finished" class="finish-card panel">
      <h3>本组练习完成</h3>
      <p>已提交 {{ stats.done }} 题 · 答对 {{ stats.correct }} 题</p>
      <n-button type="primary" @click="start">再练一组</n-button>
    </div>
    <div v-else-if="started && !questions.length" class="error-state">没有符合条件的题目，请调整筛选后重试。</div>
    <template v-else-if="item">
      <div class="pstats">
        <span>第 {{ current + 1 }} / {{ questions.length }} 题</span>
        <span>{{ item.year }} 年真题</span>
        <span :style="stats.done ? '' : 'opacity:.4'">
          正确率 {{ stats.done ? Math.round((stats.correct / stats.done) * 100) : 0 }}%（{{ stats.correct }}/{{ stats.done }}）
        </span>
      </div>

      <div class="practice-card">
        <GroupMaterial v-if="group" :key="item.group_id ?? item.id" :group="group" />
        <div :inert="submitting">
        <QuestionItem :key="item.id" :q="item" v-model="myAnswer" :mode="checked ? 'review' : 'take'"
          :result="checked ? { your_answer: myAnswer, correct_answer: checked.correct_answer } : null"
          :shared-options="group?.options" />
        </div>

        <div v-if="checked" class="feedback">
          <div class="fb-line">
            <n-tag :type="checked.correct === true ? 'success' : checked.correct === false ? 'error' : 'info'">
              {{ checked.correct === true ? '✓ 回答正确' : checked.correct === false ? '✗ 回答错误' : '主观题，待 AI 批改' }}
            </n-tag>
            <span v-if="checked.correct === false" style="margin-left:10px">
              正确答案：<b style="color:var(--ok)">{{ checked.correct_answer }}</b>
            </span>
            <n-tag v-if="checked.disputed" type="warning" size="small" style="margin-left:10px">该题答案存在版本争议</n-tag>
          </div>
          <div v-if="checked.analysis">
            <div class="section-title">解析</div>
            <div class="rich" v-html="renderRich(checked.analysis)"></div>
          </div>
          <AiPanel :key="item.id" :endpoint="`/api/ai/explain/${item.id}?student_answer=${encodeURIComponent(String(myAnswer ?? ''))}`"
            label="AI 讲解本题" />
        </div>

        <div class="p-actions">
          <span class="kbd-hint">
            <kbd>A</kbd>-<kbd>E</kbd> 选题 · <kbd>Enter</kbd> {{ checked ? '下一题' : '确认' }}
          </span>
          <n-button v-if="!checked" type="primary" :loading="submitting" :disabled="submitting || myAnswer == null || myAnswer === ''" @click="check">
            确认答案
          </n-button>
          <n-button v-else type="primary" @click="next">{{ current === questions.length - 1 ? '完成本组' : '下一题 →' }}</n-button>
        </div>
      </div>
    </template>
    </template>
  </div>
</template>

<style scoped>
.page-seg { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:4px; padding:4px; border-radius:8px; background:var(--line-soft); margin:14px 0 12px; }
.page-seg .n-button { min-height:44px; }
.filters { display:grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1.3fr) minmax(0, .8fr) auto; gap:10px; align-items:end; }
.filter-field { display:grid; gap:6px; min-width:0; font-size:12px; color:var(--t2); }
.filter-field :deep(.n-base-selection) { min-height:44px; }
.filters > .n-button, .packs .n-button, .p-actions .n-button { min-height:44px; }
.error-state { display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin:14px 0; font-size:14px; }
.finish-card { padding:28px 18px; text-align:center; }
.packs { display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.packs-label { font-size:12px; }
@media (max-width: 768px) {
  .pf-sub, .packs-label { display:none; }
  .vb-head h2, h2 { margin-top: 12px; }
  .practice-card { padding: 14px; }
  .pstats { font-size: 12px; gap: 12px; }
}
.pstats { display: flex; flex-wrap:wrap; gap: 18px; font-size: 13px; color: var(--t3); margin-bottom: 10px; }
.practice-card { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; }
.feedback { margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--line-soft); }
.fb-line { display: flex; flex-wrap:wrap; gap:8px; align-items: center; margin-bottom: 8px; }
.p-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
@media (max-width: 768px) {
  .filters { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .filters > .n-button { grid-column:1 / -1; }
  .p-actions { justify-content:flex-end; }
  .practice-card { padding:14px; }
}
</style>
