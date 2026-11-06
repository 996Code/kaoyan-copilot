<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NSpin, NTag, useDialog } from 'naive-ui'
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
const gradeResults = reactive({}) // qid -> {loading, data, error}

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
    return { name: sec.name, earned: Math.round(earned * 10) / 10, total, wrong, subjective }
  })
)

const duration = computed(() => {
  if (!exam.value?.submitted_at) return '-'
  const ms = new Date(exam.value.submitted_at) - new Date(exam.value.started_at)
  const m = Math.round(ms / 60000)
  return `${Math.floor(m / 60)} 小时 ${m % 60} 分`
})

const filtered = computed(() => {
  if (filter.value === 'all') return items.value
  return items.value.filter(({ q }) => {
    const r = results.value[String(q.id)]
    if (filter.value === 'wrong') return r && r.is_correct === false
    if (filter.value === 'unanswered') return !r || r.your_answer == null || r.your_answer === ''
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
        <div>
          <h2 style="margin:0 0 4px">{{ paper.name }} · 成绩单</h2>
          <span class="muted">用时 {{ duration }}
            <n-tag v-if="exam.overtime" type="error" size="small" style="margin-left:8px">超时交卷</n-tag>
          </span>
        </div>
        <div style="display:flex; gap:10px">
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
          <div class="sc-value" style="font-size:20px">待 AI 批改<small>（即将上线）</small></div>
        </n-card>
      </div>

      <n-card :bordered="false" style="border-radius:12px; margin-bottom:16px">
        <div class="sec-table">
          <div class="sec-row sec-head-row">
            <span>分区</span><span>客观得分</span><span>错题</span><span>主观题</span>
          </div>
          <div v-for="s in sectionStats" :key="s.name" class="sec-row">
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
          未答 {{ counts.unanswered }}
        </n-button>
        <n-button size="small" :type="filter === 'subjective' ? 'primary' : 'default'" @click="filter = 'subjective'">
          主观题参考
        </n-button>
        <n-button size="small" :type="filter === 'all' ? 'primary' : 'default'" @click="filter = 'all'">全部</n-button>
      </div>

      <div v-for="(it, i) in filtered" :key="it.q.id" class="review-card">
        <div class="rc-head">
          <n-tag :type="results[String(it.q.id)]?.is_correct === true ? 'success'
            : results[String(it.q.id)]?.is_correct === false ? 'error' : 'info'" size="small">
            {{ results[String(it.q.id)]?.is_correct === true ? '答对'
              : results[String(it.q.id)]?.is_correct === false ? '答错' : '主观题' }}
          </n-tag>
          <n-tag v-if="it.q.disputed" type="warning" size="small">该题答案存在版本争议</n-tag>
          <span class="muted" style="font-size:12px">
            第 {{ it.q.number }} 题 · {{ sections[it.sectionIndex]?.name }} · 得分
            {{ results[String(it.q.id)]?.score_earned ?? '—' }}/{{ it.q.score ?? '—' }}
          </span>
        </div>

        <GroupMaterial v-if="it.group" :group="it.group" />

        <QuestionItem :q="it.q" :model-value="answers[String(it.q.id)]" mode="review"
          :result="{ your_answer: results[String(it.q.id)]?.your_answer, correct_answer: it.q.answer }"
          :shared-options="it.group?.options" />

        <div class="verdict">
          <div v-if="it.q.qtype === 'single_choice'">
            你的答案：<b :class="results[String(it.q.id)]?.is_correct ? 'ok' : 'bad'">
              {{ results[String(it.q.id)]?.your_answer || '未作答' }}</b>
            <span style="margin-left:14px">正确答案：<b class="ok">{{ it.q.answer }}</b></span>
          </div>
          <div v-else>
            <div class="section-title">参考答案</div>
            <div class="rich" v-html="renderRich(it.q.answer)"></div>
          </div>
        </div>

        <div v-if="it.q.analysis" class="analysis">
          <div class="section-title">解析</div>
          <div class="rich" v-html="renderRich(it.q.analysis)"></div>
        </div>

        <!-- 错题：AI 讲解 -->
        <AiPanel v-if="results[String(it.q.id)]?.is_correct === false"
          :endpoint="`/api/ai/explain/${it.q.id}?student_answer=${encodeURIComponent(results[String(it.q.id)]?.your_answer || '')}`" />

        <!-- 主观题：AI 批改 -->
        <div v-if="it.q.qtype !== 'single_choice'" class="ai-grade">
          <n-button size="small" type="warning" ghost
            :loading="gradeResults[it.q.id]?.loading" @click="doGrade(it.q)">
            AI 批改本题
          </n-button>
          <template v-if="gradeResults[it.q.id]?.data">
            <div class="grade-card">
              <div class="grade-score">
                AI 评分：<b>{{ gradeResults[it.q.id].data.score }}</b> / {{ gradeResults[it.q.id].data.max_score }}
              </div>
              <div class="grade-dims">
                <div v-for="(d, di) in gradeResults[it.q.id].data.dimensions" :key="di" class="dim-row">
                  <span class="dim-name">{{ d.name }}</span>
                  <span class="dim-score">{{ d.score }}/{{ d.max }}</span>
                  <span class="muted dim-comment">{{ d.comment }}</span>
                </div>
              </div>
              <div v-if="gradeResults[it.q.id].data.suggestions?.length" class="grade-sug">
                <div class="section-title">改进建议</div>
                <ul>
                  <li v-for="(s, si) in gradeResults[it.q.id].data.suggestions" :key="si">{{ s }}</li>
                </ul>
              </div>
            </div>
          </template>
          <div v-else-if="gradeResults[it.q.id]?.error" class="muted" style="font-size:13px; margin-top:6px">
            {{ gradeResults[it.q.id].error }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-head { display: flex; align-items: center; justify-content: space-between; margin: 18px 0 14px; }
.score-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 16px; }
.score-card { border-radius: 14px; text-align: center; }
.score-card.main { background: linear-gradient(135deg, rgba(47,111,237,.12), rgba(106,92,255,.08)); }
.sc-label { font-size: 12.5px; color: var(--t3); }
.sc-value { font-size: 30px; font-weight: 800; color: var(--blue); font-variant-numeric: tabular-nums; }
.sc-value small { font-size: 14px; color: var(--t3); font-weight: 500; }
.sec-table { font-size: 14px; }
.sec-row { display: grid; grid-template-columns: 2fr 1fr .6fr .8fr; padding: 7px 4px; border-bottom: 1px dashed var(--line-soft); }
.sec-row:last-child { border-bottom: none; }
.sec-head-row { color: var(--t3); font-size: 12.5px; }
.filter-bar { display: flex; gap: 8px; margin: 4px 0 14px; }
.review-card { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; }
.rc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.verdict { margin-top: 10px; padding: 8px 12px; background: rgba(128,128,128,.05); border-radius: 8px; }
.ok { color: var(--ok); } .bad { color: var(--bad); }
.analysis { margin-top: 10px; }
.ai-grade { margin-top: 10px; }
.grade-card { margin-top: 8px; border: 1px solid rgba(240,160,32,.35); background: rgba(240,160,32,.06); border-radius: 10px; padding: 12px 14px; }
.grade-score { font-size: 15px; margin-bottom: 8px; }
.grade-score b { font-size: 22px; color: var(--warn-ink); }
.grade-dims { display: grid; gap: 4px; }
.dim-row { display: grid; grid-template-columns: 110px 70px 1fr; gap: 10px; font-size: 13.5px; align-items: baseline; }
.dim-name { font-weight: 600; }
.dim-score { color: var(--warn-ink); font-variant-numeric: tabular-nums; }
.grade-sug ul { margin: 4px 0; padding-left: 20px; }
</style>
