<script setup>
import { computed, onMounted, ref } from 'vue'
import { NButton, NCard, NEmpty, NProgress, NTag } from 'naive-ui'
import { api } from '../api'

const plan = ref(null)
const history = ref([])
const error = ref('')

onMounted(async () => {
  try {
    plan.value = await api('/api/plan/today')
    history.value = await api('/api/exams/history')
  } catch (e) {
    error.value = e.message
  }
})

const dueTotal = computed(() =>
  plan.value ? plan.value.due.wrong_question + plan.value.due.word : 0
)
const weakTop = computed(() => plan.value?.weak_modules?.[0] || null)
const wordPercent = computed(() =>
  plan.value ? Math.round((plan.value.words.learned_total / plan.value.words.total) * 100) : 0
)
const maxAcc = computed(() =>
  Math.max(100, ...(plan.value?.recent_accuracy || []).map((x) => x.accuracy))
)
</script>

<template>
  <div class="page">
    <!-- 倒计时 Hero -->
    <div class="hero-card">
      <div class="hero-left">
        <div class="days">
          <span class="num">{{ plan?.days_left ?? '—' }}</span>
          <span class="unit">天</span>
        </div>
        <div class="hero-text">
          <h2>距 2027 考研初试</h2>
          <p class="muted">{{ plan?.today || '' }} · 目标：管综 120 / 英二 55，过线！</p>
        </div>
      </div>
      <div class="hero-right">
        <div class="mini-stat">
          <b>{{ plan?.total_cards ?? 0 }}</b><span>记忆卡</span>
        </div>
        <div class="mini-stat">
          <b>{{ plan?.words?.learned_total ?? 0 }}/{{ plan?.words?.total ?? 5530 }}</b><span>词汇进度</span>
        </div>
        <div class="mini-stat">
          <b>{{ plan?.exams_today ?? 0 }}</b><span>今日模考</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="muted" style="padding:20px 0">{{ error }}</div>

    <!-- 今日任务 -->
    <div class="section-title" style="font-size:15px">今日任务</div>
    <div class="task-grid">
      <n-card class="task" :bordered="false" hoverable @click="$router.push('/review')">
        <div class="t-head review">
          <span class="t-icon">🔁</span>
          <div><b>复习到期</b><p class="muted">FSRS 记忆曲线调度</p></div>
        </div>
        <div class="t-body">
          <span class="t-num" :class="{ hot: dueTotal > 0 }">{{ dueTotal }}</span> 张待复习
          <n-tag v-if="plan?.due.wrong_question" size="small" style="margin-left:6px">错题 {{ plan.due.wrong_question }}</n-tag>
          <n-tag v-if="plan?.due.word" size="small" style="margin-left:4px">单词 {{ plan.due.word }}</n-tag>
        </div>
        <n-button type="primary" size="small" style="margin-top:8px" :disabled="dueTotal === 0">
          开始复习
        </n-button>
      </n-card>

      <n-card class="task" :bordered="false" hoverable @click="$router.push('/vocab')">
        <div class="t-head vocab">
          <span class="t-icon">📖</span>
          <div><b>背新单词</b><p class="muted">真题词频排序 · 每日 {{ plan?.words?.daily_target ?? 50 }} 词</p></div>
        </div>
        <div class="t-body">
          剩余 <span class="t-num">{{ plan?.words?.remaining_today ?? '—' }}</span> 个新词
        </div>
        <n-progress :percentage="wordPercent" :height="6" style="margin-top:8px" />
      </n-card>

      <n-card v-if="weakTop" class="task" :bordered="false" hoverable
        @click="$router.push(`/practice?subject=${weakTop.subject_code}&module=${weakTop.module_code}`)">
        <div class="t-head weak">
          <span class="t-icon">🎯</span>
          <div><b>专项强化</b><p class="muted">正确率最低的模块优先</p></div>
        </div>
        <div class="t-body">
          {{ weakTop.module_name }} <span class="t-num bad">{{ weakTop.accuracy }}%</span>
          <span class="muted">（近 {{ weakTop.attempts }} 次作答）</span>
        </div>
        <n-button size="small" style="margin-top:8px">去练 {{ weakTop.module_name }} →</n-button>
      </n-card>

      <n-card v-if="plan?.mock_suggestion" class="task" :bordered="false" hoverable
        @click="$router.push(`/papers/${plan.mock_suggestion.subject_code}`)">
        <div class="t-head mock">
          <span class="t-icon">📝</span>
          <div><b>整卷模考</b><p class="muted">限时找手感 · 每周 2-3 套</p></div>
        </div>
        <div class="t-body">建议：{{ plan.mock_suggestion.name }}</div>
        <n-button size="small" style="margin-top:8px">查看试卷 →</n-button>
      </n-card>
    </div>

    <!-- 数据面板 -->
    <div class="data-grid" v-if="plan">
      <n-card :bordered="false" style="border-radius:14px" title="各模块正确率" size="small">
        <div v-for="m in [...plan.modules_accuracy].sort((a, b) => (a.accuracy??0) - (b.accuracy??0))" :key="m.module_code + m.subject_code" class="acc-row">
          <span class="acc-name">{{ m.subject_code === 'gz199' ? '管综' : '英二' }}·{{ m.module_name }}</span>
          <div class="acc-bar">
            <div class="acc-fill" :style="{ width: (m.accuracy ?? 0) + '%' }"
              :class="{ bad: (m.accuracy ?? 0) < 60, warn: (m.accuracy ?? 0) >= 60 && (m.accuracy ?? 0) < 75 }"></div>
          </div>
          <span class="acc-val">{{ m.accuracy ?? '—' }}% <span class="muted">/{{ m.attempts }}题</span></span>
        </div>
      </n-card>

      <n-card :bordered="false" style="border-radius:14px" title="近 7 天正确率" size="small">
        <div class="trend">
          <div v-for="d in plan.recent_accuracy" :key="d.date" class="trend-col">
            <div class="trend-bar-wrap">
              <div class="trend-bar" :style="{ height: (d.accuracy / maxAcc) * 100 + '%' }"
                :class="{ bad: d.accuracy < 60 }"></div>
            </div>
            <span class="trend-val">{{ d.accuracy }}%</span>
            <span class="trend-date">{{ d.date }}</span>
          </div>
          <div v-if="!plan.recent_accuracy.length" class="muted" style="grid-column:1/-1">还没有作答数据</div>
        </div>
      </n-card>
    </div>

    <div class="section-title" style="font-size:15px">最近模考</div>
    <n-card v-if="history.length" :bordered="false" style="border-radius:12px">
      <div v-for="h in history.slice(0, 5)" :key="h.id" class="hist-row" @click="$router.push(`/report/${h.id}`)">
        <span>试卷 #{{ h.paper_id }}</span>
        <span class="muted">{{ (h.submitted_at || '').replace('T', ' ').slice(0, 16) }}</span>
        <n-tag :type="h.overtime ? 'error' : 'success'" size="small">
          {{ h.objective_score }} / {{ h.objective_total }}{{ h.overtime ? ' 超时' : '' }}
        </n-tag>
        <span class="link">查看报告 →</span>
      </div>
    </n-card>
    <n-empty v-else description="还没有模考记录" style="margin: 16px 0" />
  </div>
</template>

<style scoped>
.hero-card { display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;
  background: linear-gradient(135deg, #2f6fed 0%, #6a5cff 100%); border-radius: 18px;
  padding: 24px 28px; color: #fff; margin-top: 18px; }
.hero-left { display:flex; align-items:center; gap:18px; }
.days { display:flex; align-items:baseline; }
.days .num { font-size: 64px; font-weight: 900; line-height: 1; font-variant-numeric: tabular-nums; }
.days .unit { font-size: 18px; margin-left: 4px; opacity: .9; }
.hero-text h2 { margin:0 0 4px; font-size:18px; }
.hero-text p { margin:0; font-size:13px; opacity:.85; }
.hero-right { display:flex; gap:26px; }
.mini-stat { text-align:center; }
.mini-stat b { display:block; font-size:18px; font-variant-numeric:tabular-nums; }
.mini-stat span { font-size:11.5px; opacity:.8; }
.task-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:14px; }
.task { border-radius:14px; cursor:pointer; }
.t-head { display:flex; gap:12px; align-items:center; margin-bottom:10px; }
.t-icon { font-size:26px; }
.t-head b { font-size:15px; }
.t-head p { margin:2px 0 0; font-size:12px; }
.t-body { font-size:14px; }
.t-num { font-size:22px; font-weight:800; color:#2f6fed; }
.t-num.hot { color:#d03050; }
.t-num.bad { color:#d03050; }
.data-grid { display:grid; grid-template-columns: 1.2fr 1fr; gap:14px; margin-top:16px; }
@media (max-width: 900px) { .data-grid { grid-template-columns: 1fr; } }
.acc-row { display:grid; grid-template-columns: 110px 1fr 90px; gap:10px; align-items:center; padding:5px 0; font-size:13px; }
.acc-bar { background:#eef0f6; border-radius:5px; height:10px; overflow:hidden; }
.acc-fill { height:100%; background:#18a058; border-radius:5px; transition:width .4s; }
.acc-fill.bad { background:#d03050; } .acc-fill.warn { background:#f0a020; }
.acc-val { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.trend { display:flex; gap:8px; align-items:flex-end; height:120px; padding-top:6px; }
.trend-col { flex:1; display:flex; flex-direction:column; align-items:center; height:100%; }
.trend-bar-wrap { flex:1; width:70%; display:flex; align-items:flex-end; }
.trend-bar { width:100%; background:#2f6fed; border-radius:4px 4px 0 0; min-height:2px; }
.trend-bar.bad { background:#d03050; }
.trend-val { font-size:11px; font-variant-numeric:tabular-nums; }
.trend-date { font-size:10.5px; color:#9aa1b2; }
.hist-row { display:flex; align-items:center; gap:16px; padding:9px 4px; border-bottom:1px dashed #eceef4; cursor:pointer; }
.hist-row:last-child { border-bottom:none; }
.hist-row .link { margin-left:auto; color:#2f6fed; font-size:13px; }

@media (max-width: 768px) {
  .hero-card { padding: 16px 18px; border-radius: 14px; margin-top: 10px; }
  .days .num { font-size: 42px; }
  .hero-text h2 { font-size: 15px; }
  .hero-text p { font-size: 11.5px; }
  .hero-right { gap: 14px; }
  .mini-stat b { font-size: 15px; }
  .mini-stat span { font-size: 10.5px; }
  .task-grid { gap: 10px; }
  .t-icon { font-size: 22px; }
  .t-num { font-size: 19px; }
  .acc-row { grid-template-columns: 92px 1fr 78px; font-size: 12px; }
}
</style>
