<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { NButton, NCard, NEmpty, NProgress, NSpin, useMessage } from 'naive-ui'
import { api } from '../api'
import { renderRich } from '../markdown'
import AppIcon from '../components/AppIcon.vue'

const message = useMessage()
const loading = ref(true)
const groups = ref([])
const loadError = ref('')
const failedCategory = ref(null)

// 卡片流状态
const active = ref(null) // 当前分类组
const cards = ref([])
const idx = ref(0)
const revealed = ref(false)
const ratingBusy = ref(false)
const stats = reactive({ done: 0 })

import { reactive } from 'vue'

const finished = computed(() => active.value && cards.value.length && idx.value >= cards.value.length)
const card = computed(() => cards.value[idx.value] || null)

const subjectName = (code) => (code === 'gz199' ? '管综' : '英二')
const grouped = computed(() => {
  const by = {}
  for (const g of groups.value) {
    const key = `${g.subject_code}|${g.module_name}`
    by[key] = by[key] || { subject_code: g.subject_code, module_name: g.module_name, cats: [] }
    by[key].cats.push(g)
  }
  return Object.values(by)
})

async function loadOverview() {
  if (ratingBusy.value) return
  loading.value = true
  loadError.value = ''
  failedCategory.value = null
  active.value = null
  try {
    groups.value = await api('/api/knowledge/overview')
  } catch (e) {
    if (e.status === 401) return
    loadError.value = e.message
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

async function openCategory(g) {
  if (loading.value || ratingBusy.value) return
  loading.value = true
  loadError.value = ''
  failedCategory.value = g
  try {
    // 拉全量卡片 + 学习状态（overview 只给统计；卡片状态在 learn/复习后刷新 overview）
    const data = await api('/api/knowledge/states')
    const key = `${g.subject_code}|${g.category}`
    cards.value = (data[key] || []).map((c) => ({ ...c }))
    idx.value = cards.value.findIndex((c) => !c.learned)
    if (idx.value < 0) idx.value = 0
    revealed.value = false
    stats.done = 0
    active.value = g
  } catch (e) {
    if (e.status === 401) return
    loadError.value = e.message
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

async function rate(fam) {
  if (!card.value || !revealed.value || loading.value || ratingBusy.value) return
  ratingBusy.value = true
  try {
    await api('/api/knowledge/learn', {
      method: 'POST',
      body: { card_id: card.value.id, familiarity: fam },
    })
    card.value.learned = true
    stats.done += 1
    idx.value += 1
    revealed.value = false
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
  } finally {
    ratingBusy.value = false
  }
}

function onKey(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (['textarea', 'input', 'button', 'select'].includes(tag) || e.target.isContentEditable || e.repeat || loading.value || ratingBusy.value) return
  if (!active.value || !card.value) return
  if (!revealed.value && e.key === ' ') { revealed.value = true; e.preventDefault(); return }
  if (revealed.value) {
    if (e.key === '1') { rate(1); e.preventDefault() }
    if (e.key === '2') { rate(2); e.preventDefault() }
    if (e.key === '3') { rate(3); e.preventDefault() }
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  loadOverview()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page">
    <!-- 总览 -->
    <template v-if="!active">
      <div class="kb-head">
        <h1 class="page-h2">知识速成卡</h1>
        <span class="sub">公式 / 技法 / 谬误 / 句型，标记熟悉度即进 FSRS 复习队列</span>
      </div>
      <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>
      <div v-else-if="loadError" class="error-state" role="alert">{{ loadError }} <n-button @click="failedCategory ? openCategory(failedCategory) : loadOverview()">重试加载</n-button></div>
      <n-empty v-else-if="!groups.length" description="暂无知识卡" style="margin:60px 0" />

      <template v-if="!loading && !loadError">
      <div v-for="g in grouped" :key="g.subject_code + g.module_name" style="margin-bottom:18px">
        <div class="section-title" style="font-size:14px">
          {{ subjectName(g.subject_code) }} · {{ g.module_name }}
        </div>
        <div class="cat-grid">
          <n-card v-for="c in g.cats" :key="c.category" class="cat panel" :bordered="false" @click="openCategory(c)">
            <div class="cat-top">
              <b>{{ c.category }}</b>
              <span class="cat-num">{{ c.learned }}/{{ c.total }}</span>
            </div>
            <n-progress :height="6" :percentage="c.total ? Math.round(c.learned / c.total * 100) : 0" :show-indicator="false" />
            <div class="cat-foot muted">
              <span v-if="c.due" style="color:var(--warn)">{{ c.due }} 张待复习</span>
              <span v-else-if="c.learned >= c.total" style="color:var(--ok)">已全部学过</span>
              <span v-else>{{ c.total - c.learned }} 张待学</span>
              <span class="go">进入 ›</span>
            </div>
          </n-card>
        </div>
      </div>
      </template>
    </template>

    <!-- 卡片流 -->
    <template v-else>
      <div class="flow-head">
        <n-button quaternary size="small" :disabled="ratingBusy" @click="loadOverview()">‹ 返回分类</n-button>
        <span class="nav-pos">{{ subjectName(active.subject_code) }} · {{ active.category }}
          <template v-if="cards.length">（{{ Math.min(idx + 1, cards.length) }} / {{ cards.length }}）</template>
        </span>
      </div>

      <n-empty v-if="!loading && !cards.length" description="该分类暂无卡片" style="margin:60px 0">
        <template #extra><n-button size="small" @click="loadOverview()">返回</n-button></template>
      </n-empty>

      <div v-else-if="card" class="kcard panel">
        <div class="kcard-tag">
          <span class="tag b">{{ card.module_name }}</span>
          <span class="tag" :class="card.learned ? 'g' : 'o'">{{ card.learned ? '已学过' : '新卡' }}</span>
        </div>
        <div class="kfront">
          <div class="ktitle">{{ card.title }}</div>
          <n-button v-if="!revealed" size="large" style="margin-top:22px" @click="revealed = true">
            查看内容（空格）
          </n-button>
        </div>
        <div v-if="revealed" class="kback">
          <div class="rich" v-html="renderRich(card.back)"></div>
          <div class="krate">
            <n-button size="large" type="error" ghost :loading="ratingBusy" @click="rate(1)">没记住 <span class="kbd-hint">(1)</span></n-button>
            <n-button size="large" :loading="ratingBusy" @click="rate(2)">模糊 <span class="kbd-hint">(2)</span></n-button>
            <n-button size="large" type="success" ghost :loading="ratingBusy" @click="rate(3)">记住了 <span class="kbd-hint">(3)</span></n-button>
          </div>
        </div>
      </div>

      <div v-else-if="finished" class="finish-card">
        <AppIcon name="check" :size="52" style="color:var(--ok)" />
        <h2>本组学完</h2>
        <p class="muted">共 {{ stats.done }} 张首评完成——没记住的会尽快出现在复习中心</p>
        <div style="display:flex;gap:10px;justify-content:center;margin-top:14px">
          <n-button @click="loadOverview()">回分类</n-button>
          <n-button type="primary" @click="$router.push('/review')">去复习</n-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.kb-head { display:flex; align-items:baseline; gap:12px; margin:6px 0 14px; }
.kb-head h1 { font-size:20px; font-weight:700; margin:0; }
.kb-head .sub { color:var(--t3); font-size:13px; }
.cat-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:10px; }
.cat { border-radius:var(--r-card); cursor:pointer; }
.cat:hover { border-color:var(--blue); }
.cat-top { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:8px; align-items:baseline; margin-bottom:8px; }
.cat-top b { font-size:14.5px; min-width:0; overflow-wrap:anywhere; }
.cat-num { font-size:12px; color:var(--t3); font-variant-numeric:tabular-nums; white-space:nowrap; flex-shrink:0; }
.cat-foot { display:flex; justify-content:space-between; font-size:12px; margin-top:8px; }
.flow-head { display:grid; grid-template-columns:auto minmax(0,1fr); align-items:center; gap:12px; margin:6px 0 12px; }
.flow-head .n-button { min-height:44px; }
.nav-pos { font-size:14px; font-weight:600; overflow-wrap:anywhere; }
.kcard { padding:26px 24px; min-height:300px; }
.kcard-tag { display:flex; gap:8px; margin-bottom:14px; }
.kfront { text-align:center; padding:18px 0 26px; }
.ktitle { font-size:26px; font-weight:800; overflow-wrap:anywhere; }
.kback .rich { font-size:15.5px; line-height:1.9; }
.krate { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; max-width:480px; margin:22px auto 0; }
.krate .n-button { min-width:0; min-height:44px; padding:0 8px; }
.error-state { display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin:14px 0; }
.finish-card { text-align:center; padding:60px 0; }
@media (max-width:768px) {
  .ktitle { font-size:21px; }
  .kcard { padding:18px 16px; }
  .cat-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .cat :deep(.n-card__content) { padding:14px 12px; }
  .cat-top b { font-size:13px; }
  .cat-foot { font-size:12px; gap:6px; flex-wrap:wrap; }
  .go { flex-shrink:0; white-space:nowrap; }
  .krate { gap:8px; }
  .krate .n-button { font-size:14px; }
}
@media (max-width:420px) {
  .cat-grid { grid-template-columns:minmax(0,1fr); }
}
</style>
