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

const modules = ref([])
const items = ref([])
const loading = ref(false)
const showNav = ref(false) // 答题卡面板
const collapseAnalysis = ref({}) // qid -> bool（默认展开解析）

const moduleOptions = computed(() => [
  { label: '全部模块', value: null },
  ...modules.value.map((m) => ({ label: m.name, value: m.code })),
])

const item = computed(() => items.value[idx.value] || null)
const activeStats = ref({})

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ subject: subject.value, mastered: String(showMastered.value) })
    if (moduleFilter.value) params.set('module', moduleFilter.value)
    items.value = await api(`/api/wrongbook?${params}`)
    activeStats.value = await api(`/api/wrongbook/stats?subject=${subject.value}`)
    idx.value = Math.min(idx.value, Math.max(0, items.value.length - 1))
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
  } finally {
    loading.value = false
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

watch([subject, showMastered, moduleFilter], () => {
  idx.value = 0
  load()
})
watch(idx, persist)
onBeforeUnmount(persist)

function goto(i) {
  if (i < 0 || i >= items.value.length) return
  idx.value = i
  showNav.value = false
  window.scrollTo({ top: 0 })
}

async function toggleMastered(it) {
  const q = it.question
  try {
    await api(`/api/wrongbook/${q.id}/master`, {
      method: 'POST',
      body: { mastered: !it.mastered },
    })
    it.mastered = !it.mastered
    message.success(it.mastered ? '已标记消灭，即将跳到下一题' : '已放回待巩固')
    if (it.mastered) {
      setTimeout(() => {
        const nextIdx = items.value.findIndex((x) => !x.mastered)
        if (nextIdx >= 0) goto(nextIdx)
        else load()
      }, 1400)
    }
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
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
  if (tag === 'textarea' || tag === 'input') return
  if (e.key === 'ArrowRight' || e.key === 'k') { goto(idx.value + 1); e.preventDefault() }
  if (e.key === 'ArrowLeft' || e.key === 'j') { goto(idx.value - 1); e.preventDefault() }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    const subs = await api('/api/subjects')
    const sub = subs.find((s) => s.code === subject.value)
    modules.value = sub?.modules || []
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
  }
  load()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page">
    <!-- 筛选条 -->
    <n-card :bordered="false" style="border-radius: var(--r-card); margin-bottom: 12px">
      <div class="wb-filters">
        <n-button v-for="s in subjects" :key="s.code" size="small"
          :type="subject === s.code ? 'primary' : 'default'" @click="subject = s.code">
          {{ s.name }}
        </n-button>
        <span v-for="(st, code) in activeStats" :key="code" class="muted stat-chip">
          {{ (modules.find(m => m.code === code)?.name) || code }}：待巩固 {{ st.active }}
        </span>
        <span style="flex:1"></span>
        <n-select v-model:value="moduleFilter" :options="moduleOptions" size="small" style="width:140px" />
        <n-button size="small" :type="showMastered ? 'warning' : 'default'" @click="showMastered = !showMastered">
          {{ showMastered ? '看已消灭' : '看待巩固' }}
        </n-button>
      </div>
    </n-card>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>
    <n-empty v-else-if="!items.length" description="这个视图下没有错题——要么你很强，要么还没开始做题"
      style="margin:60px 0" />

    <template v-else-if="item">
      <!-- 导航条 + 答题卡开关 -->
      <div class="nav-bar panel">
        <n-button quaternary size="small" :disabled="idx === 0" @click="goto(idx - 1)">‹ 上一题</n-button>
        <span class="nav-pos">第 {{ idx + 1 }} / {{ items.length }} 题</span>
        <n-button size="small" @click="showNav = !showNav">答题卡</n-button>
        <n-button quaternary size="small" :disabled="idx === items.length - 1" @click="goto(idx + 1)">下一题 ›</n-button>
      </div>

      <!-- 答题卡面板 -->
      <div class="nav-grid panel" :class="{ open: showNav }">
        <div class="anscard">
          <div v-for="(it, i) in items" :key="it.question.id" class="cell"
            :class="{ answered: it.mastered, current: i === idx }"
            @click="goto(i)">
            {{ it.question.number || i + 1 }}
          </div>
        </div>
        <div class="muted" style="font-size:11.5px; margin-top:8px">
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
          <n-button size="tiny" :type="item.mastered ? 'success' : 'default'" style="margin-left:auto"
            @click="toggleMastered(item)">
            {{ item.mastered ? '已消灭（撤销）' : '标记已消灭' }}
          </n-button>
        </div>

        <GroupMaterial v-if="groupOf(item)" :group="groupOf(item)" />
        <QuestionItem :q="item.question" :model-value="item.last_answer" mode="review"
          :result="{ your_answer: item.last_answer, correct_answer: item.question.answer }"
          :shared-options="item.question.group_options" />

        <div class="verdict muted">
          我答：<b class="bad">{{ item.last_answer ?? '未答' }}</b>
          <span style="margin-left:12px">正确：<b class="ok">{{ item.question.answer }}</b></span>
        </div>

        <div v-if="item.question.analysis" class="analysis">
          <div class="section-title toggle"
            @click="collapseAnalysis[item.question.id] = !collapseAnalysis[item.question.id]">
            {{ collapseAnalysis[item.question.id] ? '▸ 显示解析' : '▾ 收起解析' }}
          </div>
          <div v-show="!collapseAnalysis[item.question.id]" class="rich"
            v-html="renderRich(item.question.analysis)"></div>
        </div>

        <AiPanel :endpoint="explainEndpoint(item)" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.wb-filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.stat-chip { font-size: 12.5px; }
.nav-bar { display: flex; align-items: center; justify-content: space-between; padding: 8px 14px; margin-bottom: 12px; gap: 8px; }
.nav-pos { font-size: 13.5px; color: var(--t2); font-variant-numeric: tabular-nums; }
.nav-grid { padding: 12px 14px; margin-bottom: 12px; display: none; }
.nav-grid.open { display: block; }
.wb-card { padding: 16px 18px; margin-bottom: 14px; }
.wb-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.meta-text { font-size: 12.5px; }
.verdict { margin-top: 8px; font-size: 14px; padding: 8px 12px; background: var(--line-soft); border-radius: 8px; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
.toggle { cursor: pointer; user-select: none; }
</style>
