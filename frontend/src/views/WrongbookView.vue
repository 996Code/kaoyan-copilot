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
// 恢复上次的筛选与浏览位置（刷新/重进不再从头来）
const saved = recall('wb_state', {}) || {}
const subject = ref(saved.subject || 'gz199')
const showMastered = ref(saved.showMastered || false)
const moduleFilter = ref(saved.module ?? null)

const modules = ref([])
const items = ref([])
const loading = ref(false)
const openAnalysis = ref({}) // qid -> bool
const visibleCount = ref(saved.visibleCount || 30)

const moduleOptions = computed(() => [
  { label: '全部模块', value: null },
  ...modules.value.map((m) => ({ label: m.name, value: m.code })),
])

const visibleItems = computed(() => items.value.slice(0, visibleCount.value))

const activeStats = ref({})

let restoredScroll = false
async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ subject: subject.value, mastered: String(showMastered.value) })
    if (moduleFilter.value) params.set('module', moduleFilter.value)
    items.value = await api(`/api/wrongbook?${params}`)
    activeStats.value = await api(`/api/wrongbook/stats?subject=${subject.value}`)
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
    if (!restoredScroll && saved.scrollTop) {
      requestAnimationFrame(() => window.scrollTo({ top: saved.scrollTop }))
      restoredScroll = true
    }
  }
}

function persist() {
  remember('wb_state', {
    subject: subject.value,
    showMastered: showMastered.value,
    module: moduleFilter.value,
    visibleCount: visibleCount.value,
    scrollTop: window.scrollY,
  })
}

watch([subject, showMastered, moduleFilter], () => {
  visibleCount.value = 30
  window.scrollTo({ top: 0 })
  load()
})
const onScroll = () => persist()
window.addEventListener('scroll', onScroll, { passive: true })
onBeforeUnmount(() => {
  persist()
  window.removeEventListener('scroll', onScroll)
})

async function toggleMastered(item) {
  const q = item.question
  try {
    await api(`/api/wrongbook/${q.id}/master`, {
      method: 'POST',
      body: { mastered: !item.mastered },
    })
    item.mastered = !item.mastered
    if (!showMastered.value && item.mastered) {
      items.value = items.value.filter((x) => x.question.id !== q.id)
    }
    message.success(item.mastered ? '已标记消灭 ✅' : '已放回待巩固')
    load()
  } catch (e) {
    message.error(e.message)
  }
}

function groupOf(item) {
  if (!item.question.group_material && !item.question.group_options && !item.question.group_image && !item.question.group_title) return null
  return {
    gtype: item.question.group_options ? 'matching' : 'reading',
    title: item.question.group_title,
    material: item.question.group_material,
    options: item.question.group_options,
    material_image: item.question.group_image,
  }
}

function explainEndpoint(item) {
  const sa = item.last_answer != null ? `?student_answer=${encodeURIComponent(item.last_answer)}` : ''
  return `/api/ai/explain/${item.question.id}${sa}`
}

onMounted(async () => {
  try {
    const subs = await api('/api/subjects')
    const sub = subs.find((s) => s.code === subject.value)
    modules.value = sub?.modules || []
  } catch (e) {
    message.error(e.message)
  }
  load()
})
</script>

<template>
  <div class="page">
    <div class="wb-head">
      <h2 style="margin:18px 0 4px">错题本</h2>
      <p class="muted" style="margin:0">
        模考与练习中答错的题自动归集；反复错的题错次会累计。「已消灭」= 你确定掌握了。
      </p>
    </div>

    <n-card :bordered="false" style="border-radius:14px; margin-bottom:14px">
      <div class="wb-filters">
        <n-button v-for="s in subjects" :key="s.code" size="small"
          :type="subject === s.code ? 'primary' : 'default'" @click="subject = s.code">
          {{ s.name }}
        </n-button>
        <span v-for="(st, code) in activeStats" :key="code" class="muted stat-chip">
          {{ (modules.find(m => m.code === code)?.name) || code }}：待巩固 {{ st.active }} / 已消灭 {{ st.mastered }}
        </span>
        <span style="flex:1"></span>
        <n-select v-model:value="moduleFilter" :options="moduleOptions" size="small" style="width:150px" />
        <n-button size="small" :type="showMastered ? 'warning' : 'default'" @click="showMastered = !showMastered">
          {{ showMastered ? '看已消灭' : '看待巩固' }}
        </n-button>
      </div>
    </n-card>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>
    <n-empty v-else-if="!items.length" description="这个视图下没有错题——要么你很强，要么还没开始做题"
      style="margin:60px 0" />

    <div v-for="item in visibleItems" :key="item.question.id" class="wb-card">
      <div class="wb-meta">
        <n-tag type="error" size="small">错 {{ item.wrong_count }} 次</n-tag>
        <n-tag v-if="item.question.disputed" type="warning" size="small">答案存在版本争议</n-tag>
        <span class="muted meta-text">
          {{ item.question.year }} 年 · {{ item.module.name }} ·
          {{ item.question.qtype === 'single_choice' ? `第 ${item.question.number} 题` : item.module.name }}
          · 最近做错 {{ (item.last_wrong_at || '').replace('T', ' ').slice(0, 16) }}
        </span>
        <n-button size="tiny" :type="item.mastered ? 'success' : 'default'" style="margin-left:auto"
          @click="toggleMastered(item)">
          {{ item.mastered ? '✅ 已消灭（点击撤销）' : '标记已消灭' }}
        </n-button>
      </div>

      <GroupMaterial v-if="groupOf(item)" :group="groupOf(item)" />
      <QuestionItem :q="item.question" :model-value="item.question.answer" mode="review"
        :result="{ your_answer: item.last_answer, correct_answer: item.question.answer }"
        :shared-options="item.question.group_options" />

      <div v-if="item.question.qtype === 'single_choice'" class="verdict muted">
        我答：<b class="bad">{{ item.last_answer ?? '未答' }}</b>
        <span style="margin-left:12px">正确：<b class="ok">{{ item.question.answer }}</b></span>
      </div>

      <div v-if="item.question.analysis" class="analysis">
        <div class="section-title toggle" @click="openAnalysis[item.question.id] = !openAnalysis[item.question.id]">
          {{ openAnalysis[item.question.id] ? '▾' : '▸' }} 参考解析
        </div>
        <div v-show="openAnalysis[item.question.id]" class="rich" v-html="renderRich(item.question.analysis)"></div>
      </div>

      <AiPanel :endpoint="explainEndpoint(item)" />
    </div>

    <div v-if="items.length > visibleCount" class="load-more">
      <n-button @click="visibleCount += 30; persist()">
        加载更多（{{ visibleItems.length }} / {{ items.length }}）
      </n-button>
    </div>
  </div>
</template>

<style scoped>
.wb-filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.stat-chip { font-size: 12.5px; }
.wb-card { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; }
.wb-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.meta-text { font-size: 12.5px; }
.verdict { margin-top: 8px; font-size: 14px; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
.toggle { cursor: pointer; user-select: none; }
.load-more { text-align: center; padding: 16px 0 8px; }
</style>
