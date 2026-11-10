<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NEmpty, NSpin, NTag, useMessage } from 'naive-ui'
import { api } from '../api'
import { recall, remember } from '../memory'
import { renderRich } from '../markdown'
import QuestionItem from '../components/QuestionItem.vue'
import GroupMaterial from '../components/GroupMaterial.vue'
import AiPanel from '../components/AiPanel.vue'
import AppIcon from '../components/AppIcon.vue'

const message = useMessage()

const loading = ref(true)
const cards = ref([])
const idx = ref(0)
const myAnswer = ref(null)
const result = ref(null) // answer_question 返回
const revealed = ref(false) // 单词卡翻面
const ratingWord = ref(false)
const submitting = ref(false)
const loadError = ref('')
const forecastError = ref('')
const forecastLoading = ref(false)
let loadVersion = 0
const stats = reactive({ done: 0, correctCount: 0 })
const showAnalysis = ref(typeof window !== 'undefined' && window.innerWidth > 768)
const cardFilter = ref('')  // ''=全部 / wrong_question / word / knowledge
const forecast = ref([])

const card = computed(() => cards.value[idx.value] || null)
const maxFc = computed(() => Math.max(1, ...forecast.value.map(d => d.total)))
const finished = computed(() => !loading.value && cards.value.length > 0 && idx.value >= cards.value.length)
const dueLeft = ref({ wrong_question: 0, word: 0 })

async function load() {
  if (submitting.value || ratingWord.value) return
  const version = ++loadVersion
  const filter = cardFilter.value
  loading.value = true
  loadError.value = ''
  try {
    const qp = filter ? `&card_type=${filter}` : ''
    const data = await api(`/api/review/queue?limit=40${qp}`)
    if (version !== loadVersion) return
    cards.value = data.cards
    dueLeft.value = data.due_counts
    // 旧索引不适用于动态到期队列；按类型与身份恢复，并保留游标前仍到期的卡片。
    const resume = recall(`rv_cursor_${filter || 'all'}`, null)
    const position = cards.value.findIndex(c => c.card_id === resume?.card_id && c.card_type === resume?.card_type)
    if (position > 0) cards.value = [...cards.value.slice(position), ...cards.value.slice(0, position)]
    idx.value = 0
    stats.done = stats.correctCount = 0
    resetCard()
    persistCursor()
    await loadForecast()
  } catch (e) {
    if (version !== loadVersion || e.status === 401) return
    loadError.value = e.message
    message.error(e.message)
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

async function loadForecast() {
  forecastLoading.value = true
  forecastError.value = ''
  try {
    forecast.value = await api('/api/review/forecast')
  } catch (e) {
    if (e.status !== 401) {
      forecastError.value = e.message
      message.error(e.message)
    }
  } finally {
    forecastLoading.value = false
  }
}

function persistCursor(offset = 0) {
  const target = cards.value[idx.value + offset]
  remember(`rv_cursor_${cardFilter.value || 'all'}`, target ? { card_id: target.card_id, card_type: target.card_type } : null)
}

function resetCard() {
  myAnswer.value = null
  result.value = null
  revealed.value = false
}

function groupOf(c) {
  const q = c.question
  if (!q || (!q.group_material && !q.group_options && !q.group_image && !q.group_title)) return null
  return {
    gtype: q.group_options ? 'matching' : /\{\{\d+\}\}/.test(q.group_material || '') ? 'cloze' : 'reading',
    title: q.group_title, material: q.group_material,
    options: q.group_options, material_image: q.group_image,
  }
}

async function submitQuestion() {
  if (!card.value || loading.value || submitting.value || myAnswer.value == null || myAnswer.value === '' || result.value) return
  submitting.value = true
  const answer = myAnswer.value
  try {
    result.value = await api('/api/review/answer_question', {
      method: 'POST',
      body: { card_id: card.value.card_id, answer },
    })
    myAnswer.value = answer
    stats.done += 1
    if (result.value.correct) stats.correctCount += 1
    persistCursor(1)
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function rateWord(rating) {
  if (!card.value || loading.value || !revealed.value || ratingWord.value) return
  ratingWord.value = true
  try {
    await api('/api/review/answer', {
      method: 'POST',
      body: { card_id: card.value.card_id, rating, source: 'manual' },
    })
    stats.done += 1
    if (rating >= 3) stats.correctCount += 1
    next()
  } catch (e) {
    if (e.status === 401) return
    message.error(e.message)
  } finally {
    ratingWord.value = false
  }
}

function next() {
  if (loading.value || submitting.value || !card.value || (card.value.card_type === 'wrong_question' && !result.value)) return
  idx.value += 1
  persistCursor()
  resetCard()
}

function onKey(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (['textarea', 'input', 'button', 'select'].includes(tag) || e.target.isContentEditable || e.repeat) return
  if (!card.value || loading.value || submitting.value || ratingWord.value) return
  const letters = ['a', 'b', 'c', 'd', 'e']
  if (card.value.card_type === 'wrong_question' && !result.value) {
    const q = card.value.question
    if (q.qtype === 'single_choice' && q.options) {
      const li = letters.indexOf(e.key.toLowerCase())
      const ni = Number(e.key) >= 1 && Number(e.key) <= 5 ? Number(e.key) - 1 : -1
      const i = li >= 0 ? li : ni
      if (i >= 0 && i < q.options.length) {
        myAnswer.value = q.options[i].key
        e.preventDefault(); return
      }
    }
    if (e.key === 'Enter') { submitQuestion(); e.preventDefault(); return }
  } else if (['word', 'knowledge'].includes(card.value.card_type)) {
    if (!revealed.value && e.key === ' ') { revealed.value = true; e.preventDefault(); return }
    if (revealed.value) {
      if (e.key === '1') { rateWord(1); e.preventDefault() }
      if (e.key === '2') { rateWord(3); e.preventDefault() }
      if (e.key === '3') { rateWord(4); e.preventDefault() }
    }
  } else if (e.key === 'Enter') { next(); e.preventDefault() }
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  load()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page">
    <div class="rv-head">
      <h2 class="page-h2" style="margin:18px 0 4px">复习中心</h2>
      <p class="muted rv-sub" style="margin:0">到期卡片按 FSRS 记忆曲线调度；答对自动推迟，答错加快重现</p>
      <div class="filter-bar">
        <n-button size="small" :disabled="loading || submitting || ratingWord" :type="cardFilter === '' ? 'primary' : 'default'" @click="cardFilter = ''; load()">
          全部
        </n-button>
        <n-button size="small" :disabled="loading || submitting || ratingWord" :type="cardFilter === 'wrong_question' ? 'primary' : 'default'" @click="cardFilter = 'wrong_question'; load()">
          错题卡 {{ dueLeft.wrong_question }}
        </n-button>
        <n-button size="small" :disabled="loading || submitting || ratingWord" :type="cardFilter === 'word' ? 'primary' : 'default'" @click="cardFilter = 'word'; load()">
          单词卡 {{ dueLeft.word }}
        </n-button>
        <n-button v-if="dueLeft.knowledge" size="small" :disabled="loading || submitting || ratingWord" :type="cardFilter === 'knowledge' ? 'primary' : 'default'" @click="cardFilter = 'knowledge'; load()">
          知识卡 {{ dueLeft.knowledge }}
        </n-button>
      </div>

      <div v-if="forecast.length" class="fc panel">
        <div class="fc-head">
          <span class="fc-title">未来 7 天复习压力</span>
          <span class="fc-legend muted"><span><i class="seg wr"></i>错题</span><span><i class="seg wd"></i>单词</span><span><i class="seg kn"></i>知识</span></span>
        </div>
        <div class="fc-bars">
          <div v-for="d in forecast" :key="d.date" class="fc-col" :title="`${d.date}：错题${d.wrong_question} 单词${d.word} 知识${d.knowledge}`">
            <div class="fc-stack">
              <i v-if="d.knowledge" class="seg kn" :style="{ height: (d.knowledge / maxFc) * 100 + '%' }"></i>
              <i v-if="d.word" class="seg wd" :style="{ height: (d.word / maxFc) * 100 + '%' }"></i>
              <i v-if="d.wrong_question" class="seg wr" :style="{ height: (d.wrong_question / maxFc) * 100 + '%' }"></i>
            </div>
            <span class="fc-v">{{ d.total }}</span>
            <span class="fc-d">{{ d.date.slice(3) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="forecastError" class="error-state" role="alert">复习预测加载失败：{{ forecastError }} <n-button :loading="forecastLoading" @click="loadForecast">重试预测</n-button></div>
    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

    <div v-else-if="loadError" class="error-state" role="alert">{{ loadError }} <n-button @click="load">重试复习队列</n-button></div>
    <n-empty v-else-if="!cards.length" description="当前没有到期卡片 记忆状态良好，去做点新题或背新词吧"
      style="margin:60px 0">
      <template #extra>
        <div style="display:flex;gap:10px;justify-content:center">
          <n-button @click="$router.push('/practice')">去练习</n-button>
          <n-button type="primary" @click="$router.push('/vocab')">背新词</n-button>
        </div>
      </template>
    </n-empty>

    <template v-else-if="card">
      <div class="pstats">
        <span>{{ idx + 1 }} / {{ cards.length }}</span>
        <span v-if="dueLeft.wrong_question">错题待复习 {{ dueLeft.wrong_question }}</span>
        <span v-if="dueLeft.word">单词待复习 {{ dueLeft.word }}</span>
        <span>本轮正确 {{ stats.correctCount }}/{{ stats.done }}</span>
      </div>

      <!-- 错题卡 -->
      <div v-if="card.card_type === 'wrong_question'" class="review-card">
        <div class="rc-head">
          <n-tag type="info" size="small">错题卡</n-tag>
          <n-tag v-if="card.lapses > 0" type="warning" size="small">已遗忘 {{ card.lapses }} 次</n-tag>
          <n-tag v-if="card.question.disputed" type="warning" size="small">答案存在版本争议</n-tag>
          <span class="muted" style="font-size:12px">
            {{ card.question.year }} 年 · 第 {{ card.question.number }} 题 · 第 {{ card.reps }} 次复习
          </span>
        </div>

        <GroupMaterial v-if="groupOf(card)" :key="card.card_id" :group="groupOf(card)" />
        <div :inert="submitting">
        <QuestionItem :key="card.card_id" :q="card.question" v-model="myAnswer" :mode="result ? 'review' : 'take'"
          :result="result ? { your_answer: myAnswer, correct_answer: result.correct_answer } : null"
          :shared-options="card.question.group_options" />
        </div>

        <div v-if="result" class="feedback">
          <n-tag :type="result.correct ? 'success' : 'error'">
            {{ result.correct ? '✓ 答对了，记忆已巩固' : '✗ 又错了，将尽快重现' }}
          </n-tag>
          <span v-if="!result.correct" style="margin-left:10px">
            正确答案：<b style="color:var(--ok)">{{ result.correct_answer }}</b>
          </span>
          <span class="muted" style="margin-left:12px;font-size:12px">下次复习：{{ (result.new_due || '').replace('T', ' ').slice(5, 16) }}</span>
          <div v-if="result.analysis">
            <div class="section-title toggle" @click="showAnalysis = !showAnalysis">
              {{ showAnalysis ? '▾ 收起解析' : '▸ 显示解析' }}
            </div>
            <div v-show="showAnalysis" class="rich" v-html="renderRich(result.analysis)"></div>
          </div>
          <AiPanel v-if="!result.correct" :key="card.card_id"
            :endpoint="`/api/ai/explain/${card.question.id}?student_answer=${encodeURIComponent(String(myAnswer ?? ''))}`" />
        </div>

        <div class="rv-actions">
          <span class="kbd-hint"><kbd>A</kbd>-<kbd>E</kbd> 选题 · <kbd>Enter</kbd> {{ result ? '下一张' : '确认' }}</span>
          <n-button v-if="!result" type="primary" :loading="submitting" :disabled="submitting || myAnswer == null || myAnswer === ''" @click="submitQuestion">确认</n-button>
          <n-button v-else type="primary" @click="next">下一张 →</n-button>
        </div>
      </div>

      <!-- 知识卡 -->
      <div v-else-if="card.card_type === 'knowledge'" class="review-card word-card">
        <div class="rc-head">
          <n-tag size="small">{{ card.knowledge.module_name }} · {{ card.knowledge.category }}</n-tag>
          <span class="muted" style="font-size:12px">第 {{ card.reps }} 次复习</span>
        </div>
        <div class="word-front">
          <div class="word" style="font-size:26px">{{ card.knowledge.title }}</div>
          <n-button v-if="!revealed" size="large" style="margin-top:20px" @click="revealed = true">
            查看内容（空格）
          </n-button>
        </div>
        <div v-if="revealed" class="word-back">
          <div class="rich" style="text-align:left" v-html="renderRich(card.knowledge.back)"></div>
          <div class="word-rating">
            <n-button size="large" type="error" ghost :disabled="ratingWord" @click="rateWord(1)">没记住 <span class="kbd-hint">(1)</span></n-button>
            <n-button size="large" :disabled="ratingWord" @click="rateWord(3)">记得 <span class="kbd-hint">(2)</span></n-button>
            <n-button size="large" type="success" ghost :disabled="ratingWord" @click="rateWord(4)">很熟 <span class="kbd-hint">(3)</span></n-button>
          </div>
        </div>
      </div>

      <!-- 单词卡 -->
      <div v-else class="review-card word-card">
        <div class="rc-head">
          <n-tag type="success" size="small">单词卡</n-tag>
          <span class="muted" style="font-size:12px">第 {{ card.reps }} 次复习</span>
        </div>
        <div class="word-front">
          <div class="word">{{ card.word.headword }}</div>
          <div class="muted">{{ card.word.phonetic || '' }}</div>
          <n-button v-if="!revealed" size="large" style="margin-top:20px" @click="revealed = true">
            显示释义（空格）
          </n-button>
        </div>
        <div v-if="revealed" class="word-back">
          <div class="definition">{{ card.word.definition }}</div>
          <div v-if="card.word.example" class="example">
            <div>{{ card.word.example }}</div>
            <div class="muted">{{ card.word.example_translation }}</div>
          </div>
          <div class="word-rating">
            <n-button size="large" type="error" ghost :disabled="ratingWord" @click="rateWord(1)">不认识 <span class="kbd-hint">(1)</span></n-button>
            <n-button size="large" :disabled="ratingWord" @click="rateWord(3)">记得 <span class="kbd-hint">(2)</span></n-button>
            <n-button size="large" type="success" ghost :disabled="ratingWord" @click="rateWord(4)">很熟 <span class="kbd-hint">(3)</span></n-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 完成页 -->
    <div v-else-if="finished" class="finish-card">
      <AppIcon name="check" :size="52" style="color:var(--ok)" />
      <h2>本轮复习完成</h2>
      <p class="muted">共 {{ stats.done }} 张 · 答对 {{ stats.correctCount }}（{{ stats.done ? Math.round(stats.correctCount / stats.done * 100) : 0 }}%）</p>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:14px">
        <n-button @click="load">再刷一轮</n-button>
        <n-button type="primary" @click="$router.push('/')">回看板</n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pstats { display:flex; flex-wrap:wrap; gap:10px 18px; font-size:13px; color:var(--t3); margin-bottom:10px; }
.filter-bar { display:flex; gap:8px; margin:12px 0 4px; flex-wrap:wrap; }
.filter-bar .n-button, .rv-actions .n-button { min-height:44px; }
.error-state { display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin:14px 0; }
.toggle { cursor:pointer; user-select:none; }
@media (max-width: 768px) {
  .rv-sub { display:none; }
  .rv-head h2 { margin-top: 12px; }
  .review-card { padding: 12px; }
  .fc { padding: 10px 12px; }
  .fc-bars { height: 56px; }
}
.fc { padding:12px 14px; margin:10px 0 14px; border-radius:var(--r-card); }
.fc-head { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; justify-content:space-between; margin-bottom:8px; }
.fc-title { font-size:13px; font-weight:600; color:var(--t2); white-space:nowrap; flex-shrink:0; }
.fc-legend { display:flex; flex-wrap:wrap; gap:8px; font-size:12px; align-items:center; }
.fc-legend > span { display:inline-flex; align-items:center; white-space:nowrap; }
.fc-legend .seg { width:9px; height:9px; display:inline-block; border-radius:2px; margin-right:3px; vertical-align:-1px; }
.fc-legend .seg + .seg { margin-left:6px; }
.fc-bars { display:flex; gap:8px; height:72px; }
.fc-col { flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; }
.fc-stack { flex:1; width:58%; display:flex; flex-direction:column-reverse; border-radius:4px 4px 0 0; overflow:hidden; }
.seg { display:block; width:100%; }
.seg.wr { background:var(--blue); } .seg.wd { background:var(--ok); } .seg.kn { background:var(--warn); }
.fc-v { font-size:12px; color:var(--t2); font-variant-numeric:tabular-nums; }
.fc-d { font-size:12px; color:var(--t3); white-space:nowrap; }

.review-card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:18px 20px; }
.rc-head { display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
.feedback { margin-top:14px; padding-top:12px; border-top:1px dashed var(--line-soft); }
.rv-actions { display:flex; justify-content:space-between; align-items:center; margin-top:16px; }
.word-card { text-align:center; padding:34px 20px; }
.word-front { padding:20px 0 26px; }
.word { font-size:42px; font-weight:800; letter-spacing:0; overflow-wrap:anywhere; }
.word-back .definition { font-size:18px; margin:6px 0 12px; }
.example { color:var(--t2); font-size:14px; line-height:1.7; margin-bottom:18px; }
.word-rating { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; max-width:480px; margin:0 auto; }
.word-rating .n-button { min-width:0; min-height:44px; padding:0 8px; }
.finish-card { text-align:center; padding:60px 0; }

@media (max-width: 768px) {
  .word { font-size: 34px; }
  .review-card { padding: 14px; }
  .word-rating { gap: 8px; }
  .word-rating button { font-size: 14px !important; }
  .filter-bar { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }
  .rv-actions { justify-content:flex-end; }
  .fc-bars { height:80px; gap:4px; }
  .fc-col { min-width:0; }
}
</style>
