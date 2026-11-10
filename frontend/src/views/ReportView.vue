<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NEmpty, NSpin, NTag, useDialog } from 'naive-ui'
import { api } from '../api'
import { renderRich } from '../markdown'
import QuestionItem from '../components/QuestionItem.vue'
import GroupMaterial from '../components/GroupMaterial.vue'
import AiPanel from '../components/AiPanel.vue'

const props = defineProps({ examId: { type: String, required: true } })
const router = useRouter()
const dialog = useDialog()

const loading = ref(true)
const exam = ref(null)
const paper = ref(null)
const results = ref({})
const answers = ref({})
const filter = ref('wrong') // wrong | unanswered | subjective | all
// 解析默认展开于桌面、折叠于移动端（移动端报告页太长）
const isDesktop = typeof window !== 'undefined' && window.innerWidth > 768
const openAnalysis = ref({})
function analysisOpen(id) {
  const v = openAnalysis.value[id]
  return v === undefined ? isDesktop : v
}
const gradeResults = reactive({}) // qid -> {loading, data, error}
const idx = ref(0)
const showNav = ref(false)
const currentItem = computed(() => filtered.value[idx.value] || null)

watch(filter, () => {
  idx.value = 0
  showNav.value = false
})

function goto(i) {
  if (i < 0 || i >= filtered.value.length) return
  idx.value = i
  showNav.value = false
  window.scrollTo({ top: 0 })
}

async function doGrade(q) {
  if (gradeResults[q.id]?.loading) return
  gradeResults[q.id] = { loading: true }
  try {
    const res = await api('/api/ai/grade', {
      method: 'POST',
      body: { exam_id: Number(props.examId), question_id: q.id },
    })
    gradeResults[q.id] = { loading: false, data: res.result, cached: res.cached }
  } catch (e) {
    gradeResults[q.id] = { loading: false, error: e.message }
  }
}

onMounted(async () => {
  try {
    const data = await api(`/api/exams/${Number(props.examId)}`)
    if (data.exam.status !== 'submitted') {
      router.replace(`/exam/${data.exam.paper_id}`)
      return
    }
    exam.value = data.exam
    paper.value = data.paper
    results.value = data.results || {}
    answers.value = data.answers || {}
  } catch (e) {
    if (e.status === 401) return
    dialog.error({ title: '加载失败', content: String(e.message || e) })
  } finally {
    loading.value = false
  }
})

const items = computed(() => {
  if (!paper.value) return []
  const list = []
  paper.value.sections.forEach((sec, si) => {
    sec.blocks.forEach((b) => {
      if (b.kind === 'group') {
        b.group.questions.forEach((q) => list.push({ q, group: b.group, sectionIndex: si }))
      } else {
        list.push({ q: b.question, group: null, sectionIndex: si })
      }
    })
  })
  return list
})

const sections = computed(() => paper.value?.sections || [])

const sectionStats = computed(() =>
  sections.value.map((sec, si) => {
    const secItems = items.value.filter((it) => it.sectionIndex === si)
    let earned = 0, total = 0, wrong = 0, subjective = 0
    secItems.forEach(({ q }) => {
      const r = results.value[String(q.id)]
      if (q.qtype === 'single_choice') {
        total += q.score || 0
        if (r?.is_correct) earned += r.score_earned || 0
        else if (r && r.is_correct === false) wrong += 1
      } else subjective += 1
    })
    return { id: sec.id ?? si, name: sec.name, earned: Math.round(earned * 10) / 10, total, wrong, subjective }
  })
)

const duration = computed(() => {
  if (!exam.value?.submitted_at) return '-'
  const ms = new Date(exam.value.submitted_at) - new Date(exam.value.started_at)
  const m = Math.round(ms / 60000)
  const h = Math.floor(m / 60)
  return h > 0 ? `${h}h${m % 60}m` : `${m}min`
})

const filtered = computed(() => {
  if (filter.value === 'all') return items.value
  return items.value.filter(({ q }) => {
    const r = results.value[String(q.id)]
    if (filter.value === 'wrong') return r && r.is_correct === false
    if (filter.value === 'unanswered') return q.qtype === 'single_choice' && (!r || r.your_answer == null || r.your_answer === '')
    if (filter.value === 'subjective') return q.qtype !== 'single_choice'
    return true
  })
})

const counts = computed(() => {
  const wrong = items.value.filter(({ q }) => results.value[String(q.id)]?.is_correct === false).length
  const unanswered = items.value.filter(({ q }) => {
    const r = results.value[String(q.id)]
    return q.qtype === 'single_choice' && (!r || r.your_answer == null || r.your_answer === '')
  }).length
  return { wrong, unanswered }
})
</script>

<template>
  <div class="page">
    <div v-if="loading" style="display:flex;justify-content:center;padding-top:100px"><n-spin size="large" /></div>
    <template v-else-if="paper">
      <div class="report-head">
        <div class="report-title-row">
          <h2>
            <span class="rp-full">{{ paper.name }}</span>
            <span class="rp-short">{{ paper.year }} {{ paper.subject_code === 'gz199' ? '管综' : paper.subject_code === 'en2' ? '英二' : '模考' }}成绩</span>
          </h2>
          <div class="report-meta">
            <span class="rp-time muted">用时 {{ duration }}</span>
            <n-tag v-if="exam.overtime" type="error" size="small">超时</n-tag>
          </div>
        </div>
        <div class="report-actions">
          <n-button @click="$router.push(`/papers/${paper.subject_code}`)">返回试卷列表</n-button>
          <n-button type="primary" @click="$router.push(`/exam/${paper.id}`)">再考一次</n-button>
        </div>
      </div>

      <div class="score-cards">
        <n-card class="score-card main" :bordered="false">
          <div class="sc-label">客观题得分</div>
          <div class="sc-value">{{ exam.objective_score }}<small> / {{ exam.objective_total }}</small></div>
        </n-card>
        <n-card class="score-card" :bordered="false">
          <div class="sc-label">卷面满分</div>
          <div class="sc-value">{{ paper.total_score }}</div>
        </n-card>
        <n-card class="score-card" :bordered="false">
          <div class="sc-label">错题 / 未答</div>
          <div class="sc-value">{{ counts.wrong }} <small>/ {{ counts.unanswered }}</small></div>
        </n-card>
        <n-card class="score-card" :bordered="false">
          <div class="sc-label">主观题</div>
          <div class="sc-value sc-subjective">{{ items.filter(it => it.q.qtype !== 'single_choice').length }}<small> 题可批改</small></div>
        </n-card>
      </div>

      <n-card :bordered="false" style="border-radius:8px; margin-bottom:16px">
        <div class="sec-table">
          <div class="sec-row sec-head-row">
            <span>分区</span><span>客观得分</span><span>错题</span><span>主观题</span>
          </div>
          <div v-for="s in sectionStats" :key="s.id" class="sec-row">
            <span>{{ s.name }}</span>
            <span class="bold">{{ s.earned }} / {{ s.total }}</span>
            <span :style="s.wrong ? 'color:var(--bad)' : ''">{{ s.wrong }}</span>
            <span class="muted">{{ s.subjective }}</span>
          </div>
        </div>
      </n-card>

      <div class="filter-bar">
        <n-button size="small" :type="filter === 'wrong' ? 'primary' : 'default'" @click="filter = 'wrong'">
          错题 {{ counts.wrong }}
        </n-button>
        <n-button size="small" :type="filter === 'unanswered' ? 'primary' : 'default'" @click="filter = 'unanswered'">
          客观未答 {{ counts.unanswered }}
        </n-button>
        <n-button size="small" :type="filter === 'subjective' ? 'primary' : 'default'" @click="filter = 'subjective'">
          主观题参考
        </n-button>
        <n-button size="small" :type="filter === 'all' ? 'primary' : 'default'" @click="filter = 'all'">全部</n-button>
      </div>

      <n-empty v-if="!filtered.length" class="review-empty"
        :description="filter === 'wrong' ? '本次没有错题' : filter === 'unanswered' ? '客观题均已作答' : filter === 'subjective' ? '本卷没有主观题' : '本卷暂无题目'">
        <template v-if="filter !== 'all' && items.length" #extra>
          <n-button @click="filter = 'all'">查看全部题目</n-button>
        </template>
      </n-empty>

      <!-- 导航条 + 答题卡开关 -->
      <div v-if="filtered.length" class="nav-bar panel" style="margin-bottom:12px">
        <n-button quaternary size="small" :disabled="idx === 0" @click="goto(idx - 1)">‹ 上一题</n-button>
        <span class="nav-pos">{{ idx + 1 }} / {{ filtered.length }}</span>
        <n-button size="small" @click="showNav = !showNav">答题卡</n-button>
        <n-button quaternary size="small" :disabled="idx >= filtered.length - 1" @click="goto(idx + 1)">下一题 ›</n-button>
      </div>

      <!-- 答题卡面板 -->
      <div v-if="showNav && filtered.length" class="nav-grid panel" style="margin-bottom:12px;padding:12px 14px">
        <div class="anscard">
          <button v-for="(it, i) in filtered" :key="it.q.id" type="button" class="cell"
            :class="{ answered: results[String(it.q.id)]?.is_correct === true, current: i === idx }"
            :aria-label="`第 ${it.q.number ?? '未标号'} 题，${sections[it.sectionIndex]?.name}`"
            :aria-current="i === idx ? 'step' : undefined"
            @click="goto(i)">{{ it.q.number ?? '—' }}</button>
        </div>
        <div class="muted nav-legend">深色＝答对 · 橙框＝当前</div>
      </div>

      <div v-if="currentItem" :key="currentItem.q.id" class="review-card">
        <div class="rc-head">
          <n-tag :type="results[String(currentItem.q.id)]?.is_correct === true ? 'success'
            : results[String(currentItem.q.id)]?.is_correct === false ? 'error' : 'info'" size="small">
            {{ results[String(currentItem.q.id)]?.is_correct === true ? '答对'
              : results[String(currentItem.q.id)]?.is_correct === false ? '答错' : currentItem.q.qtype === 'single_choice' ? '未作答' : '主观题' }}
          </n-tag>
          <n-tag v-if="currentItem.q.disputed" type="warning" size="small">该题答案存在版本争议</n-tag>
          <span class="muted" style="font-size:12px">
            第 {{ currentItem.q.number }} 题 · {{ sections[currentItem.sectionIndex]?.name }} · 得分
            {{ results[String(currentItem.q.id)]?.score_earned ?? '—' }}/{{ currentItem.q.score ?? '—' }}
          </span>
        </div>

        <GroupMaterial v-if="currentItem.group" :group="currentItem.group" />

        <QuestionItem :q="currentItem.q" :model-value="answers[String(currentItem.q.id)]" mode="review"
          :result="{ your_answer: results[String(currentItem.q.id)]?.your_answer, correct_answer: currentItem.q.answer }"
          :shared-options="currentItem.group?.options" />

        <div class="verdict">
          <div v-if="currentItem.q.qtype === 'single_choice'">
            你的答案：<b :class="results[String(currentItem.q.id)]?.is_correct ? 'ok' : 'bad'">
              {{ results[String(currentItem.q.id)]?.your_answer || '未作答' }}</b>
            <span style="margin-left:14px">正确答案：<b class="ok">{{ currentItem.q.answer }}</b></span>
          </div>
          <div v-else>
            <div class="section-title">参考答案</div>
            <div class="rich" v-html="renderRich(currentItem.q.answer)"></div>
          </div>
        </div>

        <div v-if="currentItem.q.analysis" class="analysis">
          <div class="section-title toggle"
            @click="openAnalysis[currentItem.q.id] = !analysisOpen(currentItem.q.id)">
            {{ analysisOpen(currentItem.q.id) ? '▾ 收起解析' : '▸ 显示解析' }}
          </div>
          <div v-show="analysisOpen(currentItem.q.id)" class="rich" v-html="renderRich(currentItem.q.analysis)"></div>
        </div>

        <!-- 错题：AI 讲解 -->
        <AiPanel v-if="results[String(currentItem.q.id)]?.is_correct === false"
          :key="`explain-${exam.id}-${currentItem.q.id}`"
          :endpoint="`/api/ai/explain/${currentItem.q.id}?student_answer=${encodeURIComponent(results[String(currentItem.q.id)]?.your_answer || '')}`" />

        <!-- 主观题：AI 批改 -->
        <div v-if="currentItem.q.qtype !== 'single_choice'" class="ai-grade">
          <n-button size="small" type="warning" ghost
            :loading="gradeResults[currentItem.q.id]?.loading" @click="doGrade(currentItem.q)">
            AI 批改本题
          </n-button>
          <template v-if="gradeResults[currentItem.q.id]?.data">
            <div class="grade-card">
              <div class="grade-score">
                AI 评分：<b>{{ gradeResults[currentItem.q.id].data.score }}</b> / {{ gradeResults[currentItem.q.id].data.max_score }}
              </div>
              <div class="grade-dims">
                <div v-for="(d, di) in gradeResults[currentItem.q.id].data.dimensions" :key="di" class="dim-row">
                  <span class="dim-name">{{ d.name }}</span>
                  <span class="dim-score">{{ d.score }}/{{ d.max }}</span>
                  <span class="muted dim-comment">{{ d.comment }}</span>
                </div>
              </div>
              <div v-if="gradeResults[currentItem.q.id].data.suggestions?.length" class="grade-sug">
                <div class="section-title">改进建议</div>
                <ul>
                  <li v-for="(s, si) in gradeResults[currentItem.q.id].data.suggestions" :key="si">{{ s }}</li>
                </ul>
              </div>
            </div>
          </template>
          <div v-else-if="gradeResults[currentItem.q.id]?.error" class="muted" style="font-size:13px; margin-top:6px">
            {{ gradeResults[currentItem.q.id].error }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { font-size: 14px; }
.report-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 18px 0 14px; }
.report-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; flex: 1; }
.report-title-row h2 { min-width: 0; margin: 0; font-size: 20px; overflow-wrap: anywhere; }
.report-meta { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px; flex-shrink: 0; }
.rp-time { font-size: 13px; font-weight: 400; white-space: nowrap; }
.report-actions { display: flex; flex-wrap: wrap; gap: 8px; flex-shrink: 0; }
.score-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.score-card { border-radius: 8px; text-align: center; min-width: 0; }
.score-card.main { background: var(--blue-bg); }
.sc-label { font-size: 13px; color: var(--t3); }
.sc-value { font-size: 28px; font-weight: 800; color: var(--blue); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.sc-value small { font-size: 14px; color: var(--t3); font-weight: 500; }
.sc-subjective { font-size: 24px; }
.sec-table { font-size: 14px; }
.sec-row { display: grid; grid-template-columns: minmax(0, 2fr) minmax(75px, 1fr) 48px 60px; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--line-soft); }
.sec-row > span { min-width: 0; overflow-wrap: anywhere; }
.sec-row > span:not(:first-child) { text-align: right; }
.sec-row:last-child { border-bottom: none; }
.sec-head-row { color: var(--t3); font-size: 12px; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 14px; }
.review-empty { padding: 32px 0; }
.review-card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; margin-bottom: 14px; }
.rc-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 8px; }
.rc-head > span { min-width: 0; overflow-wrap: anywhere; }
.verdict { margin-top: 10px; padding: 8px 12px; background: var(--line-soft); border-radius: 8px; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
.analysis { margin-top: 10px; }
.rp-short { display: none; }
.nav-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; padding: 8px 10px; gap: 6px; }
.nav-pos { font-size: 14px; color: var(--t2); font-variant-numeric: tabular-nums; }
.nav-legend { font-size: 12px; margin-top: 10px; }
.anscard { gap: 8px; }
.anscard .cell { width: 44px; height: 44px; font-size: 14px; font-family: inherit; }
.toggle { cursor: pointer; user-select: none; min-height: 44px; display: flex; align-items: center; }
.page :deep(.n-button) { min-height: 44px; font-size: 14px; }
.ai-grade { margin-top: 10px; }
.grade-card { margin-top: 8px; border: 1px solid var(--line); background: var(--warn-bg); border-radius: 8px; padding: 12px 14px; }
.grade-score { font-size: 15px; margin-bottom: 8px; }
.grade-score b { font-size: 22px; color: var(--warn-ink); }
.grade-dims { display: grid; gap: 10px; }
.dim-row { display: grid; grid-template-columns: 110px 70px minmax(0, 1fr); gap: 10px; font-size: 14px; align-items: baseline; }
.dim-name { font-weight: 600; overflow-wrap: anywhere; }
.dim-score { color: var(--warn-ink); font-variant-numeric: tabular-nums; }
.dim-comment { overflow-wrap: anywhere; }
.grade-sug ul { margin: 4px 0; padding-left: 20px; }
@media (max-width: 768px) {
  .rp-full { display: none; }
  .rp-short { display: inline; }
  .report-head { flex-direction: column; align-items: stretch; gap: 10px; padding: 8px 0; }
  .report-title-row { width: 100%; gap: 8px; }
  .report-title-row h2 { font-size: 18px; }
  .report-actions { justify-content: flex-end; gap: 8px; }
  .score-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .score-card :deep(.n-card__content) { padding: 12px 8px; }
  .sc-value { font-size: 24px; }
  .sec-row { grid-template-columns: minmax(0, 1fr) 76px 32px 42px; gap: 6px; }
  .sec-table { font-size: 14px; }
  .review-card { padding: 12px; }
  .dim-row { grid-template-columns: minmax(0, 1fr) auto; gap: 4px 10px; }
  .dim-score { text-align: right; }
  .dim-comment { grid-column: 1 / -1; }
}
</style>
