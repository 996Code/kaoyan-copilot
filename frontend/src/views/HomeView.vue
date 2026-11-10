<script setup>
import { computed, onMounted, ref } from 'vue'
import { NButton, NCard, NEmpty, NTag } from 'naive-ui'
import { api } from '../api'
import AppIcon from '../components/AppIcon.vue'

const plan = ref(null)
const history = ref([])
const trends = ref(null)
const calendar = ref(null)
const dataTab = ref('trend')  // 移动端数据区 Tab：trend / mods / week
const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768
const showTab = (name) => !isMobile || dataTab.value === name
const error = ref('')

onMounted(async () => {
  try {
    plan.value = await api('/api/plan/today')
    history.value = await api('/api/exams/history')
    trends.value = await api('/api/plan/trends')
    calendar.value = await api('/api/plan/calendar')
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
const sortedModules = computed(() =>
  [...(plan.value?.modules_accuracy || [])].sort((a, b) => (a.accuracy ?? 0) - (b.accuracy ?? 0))
)
</script>

<template>
  <div class="page">
    <!-- 任务头 -->
    <div class="m-hero">
      <div class="mh-num">{{ plan?.days_left ?? '—' }}<small>天</small></div>
      <div class="mh-text">
        <b>距 2027 考研初试</b>
        <span>{{ plan?.today || '' }} · 目标 管综 120 / 英二 55</span>
      </div>
    </div>

    <div class="kb-head">
      <h1>今日任务</h1>
      <span class="sub">{{ plan?.today || '' }} · 目标 管综 120 / 英二 55</span>
    </div>

    <div v-if="error" class="muted" style="padding:20px 0">{{ error }}</div>

    <div class="task-grid">
      <div class="task panel" @click="$router.push('/review')">
        <div class="th">
          <div class="ic"><AppIcon name="review" /></div>
          <div><b>复习到期</b><span>FSRS 记忆调度</span></div>
        </div>
        <div class="tv hot">{{ dueTotal }}</div>
        <div class="tl">
          <span v-if="plan">错题 {{ plan.due.wrong_question }} · 单词 {{ plan.due.word }}</span>
          <span v-else>&nbsp;</span>
          <span class="go">去复习 ›</span>
        </div>
      </div>

      <div class="task panel" @click="$router.push('/vocab')">
        <div class="th">
          <div class="ic"><AppIcon name="vocab" /></div>
          <div><b>背新单词</b><span>词频排序 · 每日 {{ plan?.words?.daily_target ?? 50 }}</span></div>
        </div>
        <div class="tv">{{ plan?.words?.remaining_today ?? '—' }}<small>个待背</small></div>
        <div class="tl">
          <span>已学 {{ plan?.words?.learned_total ?? 0 }}/{{ plan?.words?.total ?? 5530 }}（{{ wordPercent }}%）</span>
          <span class="go">去背词 ›</span>
        </div>
        <div class="track"><i :style="{ width: wordPercent + '%' }"></i></div>
      </div>

      <div v-if="weakTop" class="task panel" @click="$router.push(`/practice?subject=${weakTop.subject_code}&module=${weakTop.module_code}`)">
        <div class="th">
          <div class="ic warn"><AppIcon name="target" /></div>
          <div><b>专项强化</b><span>最弱模块优先</span></div>
        </div>
        <div class="tv" style="color:var(--warn)">{{ weakTop.accuracy }}%</div>
        <div class="tl">
          <span>{{ weakTop.module_name }} · 近 {{ weakTop.attempts }} 次作答</span>
          <span class="go">去练 ›</span>
        </div>
      </div>

      <div v-if="plan?.mock_suggestion" class="task panel" @click="$router.push(`/papers/${plan.mock_suggestion.subject_code}`)">
        <div class="th">
          <div class="ic ok"><AppIcon name="exam" /></div>
          <div><b>整卷模考</b><span>限时找手感</span></div>
        </div>
        <div class="tv" style="font-size:17px">{{ plan.mock_suggestion.year }} 年<small>{{ plan.mock_suggestion.subject_code === 'gz199' ? '管综' : '英二' }}</small></div>
        <div class="tl">
          <span>{{ plan.exams_today }} 场今日已考</span>
          <span class="go">查看 ›</span>
        </div>
      </div>
    </div>

    <!-- 冲刺日历 -->
    <div v-if="calendar && calendar.days" class="cal panel" style="margin-bottom:12px">
      <div class="panel-h"><b>冲刺日历</b>
        <span class="muted" style="font-size:11px;margin-left:8px">
          {{ calendar.days.length }} 天 · {{ calendar.days_left }} 天后考试
        </span>
      </div>
      <div class="cal-grid">
        <div v-for="d in calendar.days.slice(0, 14)" :key="d.date" class="cal-day"
          :class="{ today: d.is_today, past: d.is_past, exam: d.is_exam_day, studied: d.studied }"
          :title="d.date + ' · ' + d.phase + (d.studied ? ' · 已学习' : '')">
          <span class="cd-num">{{ d.days_to_exam > 0 ? d.days_to_exam : '考' }}</span>
          <span class="cd-dot" :class="{ on: d.studied, exam: d.is_exam_day }"></span>
        </div>
      </div>
      <div class="cal-legend muted">
        <span>数字=距考试天数</span><span>●=已学习</span><span class="exam-mark">◆=考试日</span>
      </div>
    </div>

    <!-- 数据区 Tab（置于面板上方，移动端显示） -->
    <div class="data-tabs">
      <n-button size="small" :type="dataTab === 'trend' ? 'primary' : 'default'" v-if="trends?.subjects.gz199.count" @click="dataTab = 'trend'">过线预测</n-button>
      <n-button size="small" :type="dataTab === 'mods' ? 'primary' : 'default'" @click="dataTab = 'mods'">模块正确率</n-button>
      <n-button size="small" :type="dataTab === 'week' ? 'primary' : 'default'" @click="dataTab = 'week'">近况</n-button>
    </div>

    <!-- 模考趋势与过线预测 -->
    <div v-if="trends && (trends.subjects.gz199.count || trends.subjects.en2.count)" style="margin-bottom: 12px" v-show="showTab('trend')">
      <div class="panel">
        <div class="panel-h"><b>模考趋势与过线预测</b>
          <span class="muted" style="font-size:12px; margin-left:10px">估分 = 客观得分 + 主观 AI 批改；预测按近期趋势外推至考试日</span>
        </div>
        <div class="trend-grid">
          <div v-for="(sub, code) in trends.subjects" :key="code" class="tr-col" v-show="sub.count">
            <div class="tr-head">
              <b>{{ code === 'gz199' ? '199 管综' : '英语二' }}</b>
              <span class="muted" style="font-size:12px">{{ sub.count }} 场 · 目标 {{ sub.goal }}</span>
            </div>
            <div v-if="sub.forecast" class="tr-nums">
              <div class="tr-cell">
                <span class="tr-v">{{ sub.forecast.predicted }}</span>
                <span class="tr-l">预测分</span>
              </div>
              <div class="tr-cell">
                <span class="tr-v" :style="{ color: sub.forecast.probability >= 60 ? 'var(--ok)' : sub.forecast.probability >= 30 ? 'var(--warn)' : 'var(--bad)' }">{{ sub.forecast.probability }}%</span>
                <span class="tr-l">过线概率</span>
              </div>
              <div class="tr-cell">
                <span class="tr-v" :style="{ color: sub.forecast.gap >= 0 ? 'var(--ok)' : 'var(--bad)' }">{{ sub.forecast.gap >= 0 ? '+' : '' }}{{ sub.forecast.gap }}</span>
                <span class="tr-l">距目标</span>
              </div>
            </div>
            <div class="tr-bars">
              <div v-for="(e, i) in sub.exams" :key="e.exam_id" class="tr-bar-col" :title="`${e.year} 年 ${e.date}：估 ${e.estimate}（客观 ${e.objective}）`">
                <div class="tr-bar-wrap">
                  <div class="tr-bar" :style="{ height: Math.max(3, e.estimate / sub.full * 100) + '%' }"></div>
                </div>
                <span class="tr-bar-v">{{ e.estimate }}</span>
                <span class="tr-bar-d">{{ e.date }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据区（移动端 Tab 切换，Tab 条已上移至趋势面板前） -->
    <div class="data-grid" v-if="plan">
      <div class="panel" v-show="showTab('mods')">
        <div class="panel-h"><b>各模块正确率</b></div>
        <table class="mods">
          <tr v-for="m in sortedModules" :key="m.module_code + m.subject_code">
            <td class="nm">{{ m.subject_code === 'gz199' ? '管综' : '英二' }} · {{ m.module_name }}</td>
            <td class="pc" :style="{ color: (m.accuracy ?? 200) < 60 ? 'var(--bad)' : (m.accuracy ?? 200) < 75 ? 'var(--warn)' : 'var(--t1)' }">
              {{ m.accuracy ?? '—' }}%
            </td>
            <td class="bar-cell">
              <div class="stat-bar">
                <i :style="{ width: (m.accuracy || 0) + '%', background: (m.accuracy ?? 0) < 60 ? 'var(--bad)' : (m.accuracy ?? 0) < 75 ? 'var(--warn)' : 'var(--blue)' }"></i>
              </div>
            </td>
            <td class="cnt">{{ m.attempts }} 题</td>
          </tr>
          <tr v-if="!sortedModules.length"><td class="cnt" colspan="4">还没有作答数据，先去练两手</td></tr>
        </table>
      </div>

      <div v-show="showTab('week')">
        <div class="panel">
          <div class="panel-h"><b>近 7 天正确率</b></div>
          <div class="week">
            <div v-for="d in plan.recent_accuracy" :key="d.date" class="wc">
              <span class="wv">{{ d.accuracy }}%</span>
              <div class="wbar-wrap"><div class="wbar" :class="{ lo: d.accuracy < 60 }"
                :style="{ height: (d.accuracy / maxAcc) * 100 + '%' }"></div></div>
              <span class="wd">{{ d.date }}</span>
            </div>
            <div v-if="!plan.recent_accuracy.length" class="cnt" style="padding:12px">暂无数据</div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-h"><b>最近模考</b></div>
          <div v-for="h in history.slice(0, 3)" :key="h.id" class="hist" @click="$router.push(`/report/${h.id}`)">
            <span class="hy">试卷 #{{ h.paper_id }}</span>
            <span class="hs">{{ (h.submitted_at || '').replace('T', ' ').slice(5, 16) }}</span>
            <n-tag :type="h.overtime ? 'error' : 'success'" size="small">
              {{ h.objective_score }}/{{ h.objective_total }}{{ h.overtime ? ' 超时' : '' }}
            </n-tag>
            <span class="go">报告 ›</span>
          </div>
          <div v-if="!history.length" class="cnt" style="padding:14px 18px">还没有模考记录</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb-head { display: flex; align-items: baseline; gap: 12px; margin: 6px 0 14px; }
.kb-head h1 { font-size: 20px; font-weight: 700; margin: 0; }
.kb-head .sub { color: var(--t3); font-size: 13px; }

.task-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.task { padding: 16px; cursor: pointer; transition: border-color .15s; }
.task:hover { border-color: var(--blue); }
.th { display: flex; gap: 11px; align-items: center; margin-bottom: 12px; }
.th b { font-size: 14.5px; display: block; }
.th span { display: block; color: var(--t3); font-size: 11.5px; margin-top: 1px; }
.ic { width: 38px; height: 38px; border-radius: 9px; background: var(--blue-bg); color: var(--blue); display: flex; align-items: center; justify-content: center; flex: none; }
.ic svg { width: 19px; height: 19px; }
.ic.warn { background: var(--warn-bg); color: var(--warn); }
.ic.ok { background: var(--ok-bg); color: var(--ok); }
.tv { font-size: 26px; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1.1; }
.tv.hot { color: var(--warn); }
.tv small { font-size: 12px; color: var(--t3); font-weight: 500; margin-left: 4px; }
.tl { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 12px; color: var(--t3); }
.go { color: var(--blue); }
.track { height: 6px; border-radius: 3px; background: var(--line-soft); overflow: hidden; margin-top: 10px; }
.track i { display: block; height: 100%; background: var(--blue); border-radius: 3px; }

.data-grid { display: grid; grid-template-columns: 1.55fr 1fr; gap: 12px; }
.mods { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.mods td { padding: 11px 18px; border-bottom: 1px solid var(--line-soft); }
.mods tr:last-child td { border-bottom: none; }
.mods tr:hover td { background: var(--card-hover); }
.nm { font-weight: 600; }
.pc { font-weight: 800; font-size: 15px; width: 56px; font-variant-numeric: tabular-nums; }
.bar-cell { width: 160px; }
.cnt { color: var(--t3); font-size: 12.5px; }

.week { display: flex; gap: 10px; align-items: flex-end; height: 110px; padding: 14px 16px; }
.wc { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; justify-content: flex-end; height: 100%; }
.wbar-wrap { flex: 1; width: 64%; display: flex; align-items: flex-end; }
.wbar { width: 100%; border-radius: 4px 4px 0 0; background: linear-gradient(180deg, #4D9AFF, var(--blue)); }
.wbar.lo { background: linear-gradient(180deg, #FFB87E, var(--warn)); }
.wv { font-size: 11.5px; color: var(--t2); font-variant-numeric: tabular-nums; }
.wd { font-size: 10.5px; color: var(--t3); }

.hist { display: flex; align-items: center; gap: 10px; padding: 11px 18px; border-bottom: 1px solid var(--line-soft); cursor: pointer; font-size: 13px; }
.hist:last-child { border-bottom: none; }
.hist:hover { background: var(--card-hover); }
.hy { font-weight: 600; }
.hs { color: var(--t3); font-size: 12px; }
.go { margin-left: auto; color: var(--blue); font-size: 12.5px; }

/* 冲刺日历 */
.mh-streak { font-size: 13px; color: #fff; background: rgba(255,255,255,.2); border-radius: 99px; padding: 2px 10px; margin-left: 8px; vertical-align: 2px; }
.cal { border-radius: var(--r-card); }
.cal-grid { display: flex; gap: 4px; padding: 10px 12px; overflow-x: auto; scrollbar-width: none; }
.cal-grid::-webkit-scrollbar { display: none; }
.cal-day {
  flex: none; width: 38px; height: 44px; border-radius: 8px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 3px; border: 1px solid var(--line);
}
.cal-day.today { outline: 2px solid var(--blue); outline-offset: 1px; }
.cal-day.past { opacity: .45; }
.cal-day.exam { background: var(--bad); border-color: var(--bad); }
.cal-day.studied { background: var(--blue-bg); border-color: var(--blue-line); }
.cd-num { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
.cd-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--line); }
.cd-dot.on { background: var(--blue); }
.cd-dot.exam { background: #fff; }
.cal-legend { display: flex; gap: 12px; font-size: 10.5px; padding: 0 12px 8px; }
.exam-mark { color: var(--bad); }

/* 移动端 hero：仅手机显示 */
.m-hero { display: none; }

.trend-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.tr-col { padding: 14px 18px; }
.tr-col + .tr-col { border-left: 1px solid var(--line-soft); }
.tr-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.tr-nums { display: flex; gap: 22px; margin-bottom: 12px; }
.tr-cell { text-align: center; }
.tr-v { display: block; font-size: 24px; font-weight: 800; font-variant-numeric: tabular-nums; }
.tr-l { font-size: 11.5px; color: var(--t3); }
.tr-bars { display: flex; gap: 8px; align-items: flex-end; height: 64px; }
.tr-bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
.tr-bar-wrap { flex: 1; width: 62%; display: flex; align-items: flex-end; }
.tr-bar { width: 100%; border-radius: 3px 3px 0 0; background: linear-gradient(180deg, var(--blue-soft), var(--blue)); min-height: 3px; }
.tr-bar-v { font-size: 10.5px; color: var(--t2); font-variant-numeric: tabular-nums; }
.tr-bar-d { font-size: 9px; color: var(--t3); white-space: nowrap; }

.data-tabs { display: none; }

@media (max-width: 768px) {
  .data-tabs { display: flex; gap: 8px; margin: 2px 0 10px; }
  .tr-col { padding: 12px 14px; }
  .tr-nums { gap: 0; justify-content: space-around; }
  .tr-v { font-size: 17px; }
  .tr-l { font-size: 9.5px; }
  .tr-cell { min-width: 0; }
  .trend-grid { grid-template-columns: 1fr; }
  .tr-col + .tr-col { border-left: none; border-top: 1px solid var(--line-soft); }
  .m-hero {
    display: flex; align-items: center; gap: 16px;
    background: linear-gradient(120deg, var(--blue) 0%, var(--blue-deep) 100%);
    border-radius: var(--r-card); color: #fff;
    padding: 18px 20px; margin: 10px 0 14px;
  }
  .mh-num { font-size: 46px; font-weight: 900; line-height: 1; font-variant-numeric: tabular-nums; letter-spacing: -1px; }
  .mh-num small { font-size: 15px; font-weight: 600; margin-left: 2px; opacity: .85; }
  .mh-text b { display: block; font-size: 16px; }
  .mh-text span { display: block; font-size: 12px; opacity: .82; margin-top: 3px; }
  .kb-head { display: none; }

  /* 任务卡 2×2 紧凑排版 */
  .task-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .task { padding: 12px; }
  .th { margin-bottom: 8px; gap: 8px; }
  .th .ic { width: 30px; height: 30px; border-radius: 8px; }
  .th .ic svg { width: 15px; height: 15px; }
  .th b { font-size: 13px; }
  .th span { display: none; }
  .tv { font-size: 20px; }
  .tv small { font-size: 10px; }
  .tl { font-size: 10.5px; white-space: nowrap; overflow: hidden; }
  .tl .go { display: none; }
  .track { margin-top: 6px; }

  .data-grid { grid-template-columns: 1fr; }
  .bar-cell { width: auto; }
  .mods .cnt { display: none; }
}
</style>
