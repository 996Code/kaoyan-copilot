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
const stats = reactive({ done: 0, correctCount: 0 })
const cardFilter = ref('')  // ''=全部 / wrong_question / word / knowledge
const forecast = ref([])

const card = computed(() => cards.value[idx.value] || null)
const maxFc = computed(() => Math.max(1, ...forecast.value.map(d => d.total)))
const finished = computed(() => !loading.value && cards.value.length > 0 && idx.value >= cards.value.length)
const dueLeft = ref({ wrong_question: 0, word: 0 })

async function load() {
  loading.value = true
  try {
    const qp = cardFilter.value ? `&card_type=${cardFilter.value}` : ''
    const data = await api(`/api/review/queue?limit=40${qp}`)
    forecast.value = await api('/api/review/forecast')
    cards.value = data.cards
    dueLeft.value = data.due_counts
    // 恢复上次复习到的位置（队列变化时自动收敛到有效范围）
    const resume = recall('rv_idx', 0) || 0
    idx.value = Math.min(resume, Math.max(0, cards.value.length - 1))
    resetCard()
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
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
  if (myAnswer.value == null || result.value) return
  try {
    result.value = await api('/api/review/answer_question', {
      method: 'POST',
      body: { card_id: card.value.card_id, answer: myAnswer.value },
    })
    stats.done += 1
    if (result.value.correct) stats.correctCount += 1
  } catch (e) {
    message.error(e.message)
  }
}

async function rateWord(rating) {
  if (ratingWord.value) return
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
    message.error(e.message)
  } finally {
    ratingWord.value = false
  }
}

function next() {
  idx.value += 1
  // 一轮刷完即清零记忆，下次从头开始
  remember('rv_idx', idx.value < cards.value.length ? idx.value : 0)
  resetCard()
}

function onKey(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (tag === 'textarea' || tag === 'input') return
  if (!card.value) return
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
  } else if (card.value.card_type === 'word') {
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
      <h2 style="margin:18px 0 4px">复习中心</h2>
      <p class="muted" style="margin:0">
        到期卡片按 FSRS 记忆曲线调度；答对自动推迟下次复习，答错加快重现。
      </p>
      <div class="filter-bar">
        <n-button size="small" :type="cardFilter === '' ? 'primary' : 'default'" @click="cardFilter = ''; load()">
          全部
        </n-button>
        <n-button size="small" :type="cardFilter === 'wrong_question' ? 'primary' : 'default'" @click="cardFilter = 'wrong_question'; load()">
          错题卡 {{ dueLeft.wrong_question }}
        </n-button>
        <n-button size="small" :type="cardFilter === 'word' ? 'primary' : 'default'" @click="cardFilter = 'word'; load()">
          单词卡 {{ dueLeft.word }}
        </n-button>
        <n-button v-if="dueLeft.knowledge" size="small" :type="cardFilter === 'knowledge' ? 'primary' : 'default'" @click="cardFilter = 'knowledge'; load()">
          知识卡 {{ dueLeft.knowledge }}
        </n-button>
      </div>

      <div v-if="forecast.length" class="fc panel">
        <div class="fc-title">未来 7 天复习压力</div>
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
        <div class="fc-legend muted">
          <span><i class="seg wr"></i>错题</span><span><i class="seg wd"></i>单词</span><span><i class="seg kn"></i>知识</span>
        </div>
      </div>
    </div>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

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

        <GroupMaterial v-if="groupOf(card)" :group="groupOf(card)" />
        <QuestionItem :q="card.question" v-model="myAnswer" :mode="result ? 'review' : 'take'"
          :result="result ? { your_answer: myAnswer, correct_answer: result.correct_answer } : null"
          :shared-options="card.question.group_options" />

        <div v-if="result" class="feedback">
          <n-tag :type="result.correct ? 'success' : 'error'">
            {{ result.correct ? '✓ 答对了，记忆已巩固' : '✗ 又错了，将尽快重现' }}
          </n-tag>
          <span v-if="!result.correct" style="margin-left:10px">
            正确答案：<b style="color:var(--ok)">{{ result.correct_answer }}</b>
          </span>
          <span class="muted" style="margin-left:12px;font-size:12px">下次复习：{{ (result.new_due || '').replace('T', ' ').slice(5, 16) }}</span>
          <div v-if="result.analysis">
            <div class="section-title">解析</div>
            <div class="rich" v-html="renderRich(result.analysis)"></div>
          </div>
          <AiPanel v-if="!result.correct"
            :endpoint="`/api/ai/explain/${card.question.id}?student_answer=${encodeURIComponent(String(myAnswer ?? ''))}`" />
        </div>

        <div class="rv-actions">
          <span class="kbd-hint"><kbd>A</kbd>-<kbd>E</kbd> 选题 · <kbd>Enter</kbd> {{ result ? '下一张' : '确认' }}</span>
          <n-button v-if="!result" type="primary" :disabled="myAnswer == null" @click="submitQuestion">确认</n-button>
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
            <n-button size="large" type="error" ghost @click="rateWord(1)">没记住 (1)</n-button>
            <n-button size="large" @click="rateWord(3)">记得 (2)</n-button>
            <n-button size="large" type="success" ghost @click="rateWord(4)">很熟 (3)</n-button>
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
            <n-button size="large" type="error" ghost @click="rateWord(1)">不认识 <span class="kbd-hint">(1)</span></n-button>
            <n-button size="large" @click="rateWord(3)">记得 <span class="kbd-hint">(2)</span></n-button>
            <n-button size="large" type="success" ghost @click="rateWord(4)">很熟 <span class="kbd-hint">(3)</span></n-button>
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
.pstats { display:flex; gap:18px; font-size:13px; color:var(--t3); margin-bottom:10px; }
.filter-bar { display:flex; gap:8px; margin:12px 0 4px; flex-wrap:wrap; }
.fc { display:flex; align-items:center; gap:14px; padding:12px 16px; margin:10px 0 14px; border-radius:var(--r-card); }
.fc-title { font-size:13px; font-weight:600; color:var(--t2); writing-mode:vertical-lr; letter-spacing:2px; }
.fc-bars { flex:1; display:flex; gap:8px; height:72px; }
.fc-col { flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; }
.fc-stack { flex:1; width:58%; display:flex; flex-direction:column-reverse; border-radius:4px 4px 0 0; overflow:hidden; }
.seg { display:block; width:100%; }
.seg.wr { background:var(--blue); } .seg.wd { background:var(--ok); } .seg.kn { background:var(--warn); }
.fc-v { font-size:11px; color:var(--t2); font-variant-numeric:tabular-nums; }
.fc-d { font-size:10px; color:var(--t3); }
.fc-legend { display:flex; gap:10px; font-size:11px; }
.fc-legend .seg { width:9px; height:9px; display:inline-block; border-radius:2px; margin-right:3px; vertical-align:-1px; }
.review-card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:18px 20px; }
.rc-head { display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
.feedback { margin-top:14px; padding-top:12px; border-top:1px dashed var(--line-soft); }
.rv-actions { display:flex; justify-content:space-between; align-items:center; margin-top:16px; }
.word-card { text-align:center; padding:34px 20px; }
.word-front { padding:20px 0 26px; }
.word { font-size:42px; font-weight:800; letter-spacing:.5px; }
.word-back .definition { font-size:18px; margin:6px 0 12px; }
.example { color:var(--t2); font-size:14px; line-height:1.7; margin-bottom:18px; }
.word-rating { display:flex; gap:12px; justify-content:center; }
.finish-card { text-align:center; padding:60px 0; }

@media (max-width: 768px) {
  .word { font-size: 34px; }
  .review-card { padding: 14px; }
  .word-rating { gap: 8px; }
  .word-rating button { font-size: 14px !important; }
}
</style>
