<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NModal, NSpin, useDialog } from 'naive-ui'
import { api } from '../api'
import QuestionItem from '../components/QuestionItem.vue'
import GroupMaterial from '../components/GroupMaterial.vue'

const props = defineProps({ paperId: { type: String, required: true } })
const route = useRoute()
const router = useRouter()
const dialog = useDialog()

const loading = ref(true)
const exam = ref(null)
const paper = ref(null)
const answers = reactive({}) // qid(str) -> answer
const flat = ref([]) // [{q, group, sectionIndex}]
const sections = ref([])
const current = ref(0)
const saving = ref(false)
const savedAt = ref('')
const submitting = ref(false)
const confirmSubmit = ref(false)
const showCard = ref(false) // 移动端答题卡抽屉
let clockTimer = null
let saveTimer = null
let serverOffset = 0
const remainingMs = ref(0)

/* ---------- 载入 / 构建 ---------- */
async function load() {
  const data = await api('/api/exams', { method: 'POST', body: { paper_id: Number(props.paperId) } })
  if (data.exam.status === 'submitted') {
    router.replace(`/report/${data.exam.id}`)
    return
  }
  exam.value = data.exam
  paper.value = data.paper
  sections.value = data.paper.sections
  serverOffset = Date.now() - new Date(data.exam.server_now).getTime()

  const list = []
  data.paper.sections.forEach((sec, si) => {
    sec.blocks.forEach((b) => {
      if (b.kind === 'group') {
        b.group.questions.forEach((q) => list.push({ q, group: b.group, sectionIndex: si }))
      } else {
        list.push({ q: b.question, group: null, sectionIndex: si })
      }
    })
  })
  flat.value = list
  Object.assign(answers, data.answers || {})
  const firstUnanswered = list.findIndex((it) => !answers[String(it.q.id)])
  current.value = firstUnanswered >= 0 ? firstUnanswered : 0
  loading.value = false
}

/* ---------- 倒计时 ---------- */
function tick() {
  if (!exam.value) return
  remainingMs.value = new Date(exam.value.deadline_at).getTime() - (Date.now() - serverOffset)
  if (remainingMs.value <= 0 && !submitting.value) {
    doSubmit(true)
  }
}
const countdownText = computed(() => {
  const s = Math.max(0, Math.floor(remainingMs.value / 1000))
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(h)}:${pad(m)}:${pad(sec)}`
})
const urgent = computed(() => remainingMs.value > 0 && remainingMs.value < 5 * 60 * 1000)

/* ---------- 自动保存 ---------- */
watch(answers, () => {
  if (loading.value || submitting.value) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(saveNow, 1200)
})
async function saveNow() {
  if (!exam.value || exam.value.status !== 'in_progress') return
  saving.value = true
  try {
    await api(`/api/exams/${exam.value.id}/answers`, { method: 'PUT', body: { answers: { ...answers } } })
    savedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch { /* 稍后重试 */ } finally {
    saving.value = false
  }
}

/* ---------- 当前题目 ---------- */
const item = computed(() => flat.value[current.value] || null)
const answeredCount = computed(() => flat.value.filter((it) => answers[String(it.q.id)] != null && answers[String(it.q.id)] !== '').length)
const sectionName = computed(() => (item.value ? sections.value[item.value.sectionIndex]?.name : ''))

const clozeBlanks = computed(() => {
  // 完形：题号 -> 字母
  const map = {}
  if (item.value?.group && /cloze/i.test(item.value.group.gtype || '')) {
    item.value.group.questions.forEach((q) => {
      if (answers[String(q.id)]) map[q.number] = answers[String(q.id)]
    })
  }
  return map
})

const isReadingSplit = computed(() => item.value?.group && ['reading'].includes(item.value.group.gtype))

function goto(i) {
  if (i < 0 || i >= flat.value.length) return
  current.value = i
  showCard.value = false
  window.scrollTo({ top: 0 })
}
function jumpNumber(number) {
  const idx = flat.value.findIndex((it) => it.q.number === number)
  if (idx >= 0) goto(idx)
}

/* ---------- 键盘 ---------- */
function onKey(e) {
  if (submitting.value || confirmSubmit.value) return
  const tag = (e.target.tagName || '').toLowerCase()
  const typing = tag === 'textarea' || tag === 'input'
  if (typing) return
  const q = item.value?.q
  const letters = ['a', 'b', 'c', 'd', 'e']
  if (q && q.qtype === 'single_choice') {
    const li = letters.indexOf(e.key.toLowerCase())
    const ni = Number(e.key) >= 1 && Number(e.key) <= 5 ? Number(e.key) - 1 : -1
    const idx = li >= 0 ? li : ni
    if (idx >= 0 && q.options && idx < q.options.length) {
      const key = q.options[idx].key
      answers[String(q.id)] = answers[String(q.id)] === key ? null : key
      e.preventDefault()
      return
    }
  }
  if (e.key === 'ArrowRight' || e.key === 'k') { goto(current.value + 1); e.preventDefault() }
  if (e.key === 'ArrowLeft' || e.key === 'j') { goto(current.value - 1); e.preventDefault() }
}

/* ---------- 交卷 ---------- */
function askSubmit() {
  saveNow()
  confirmSubmit.value = true
}
async function doSubmit(auto = false) {
  if (submitting.value || !exam.value) return
  submitting.value = true
  confirmSubmit.value = false
  clearTimeout(saveTimer)
  try {
    await api(`/api/exams/${exam.value.id}/submit`, { method: 'POST', body: { answers: { ...answers } } })
    router.replace(`/report/${exam.value.id}`)
  } catch (e) {
    dialog.error({ title: '交卷失败', content: String(e.message || e) })
    submitting.value = false
    if (auto) clockTimer = setInterval(tick, 1000)
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  clockTimer = setInterval(tick, 1000)
  try {
    await load()
    tick()
  } catch (e) {
    dialog.error({ title: '加载失败', content: String(e.message || e) })
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  clearInterval(clockTimer)
  clearTimeout(saveTimer)
  saveNow() // 离开页面前兜底保存
})
</script>

<template>
  <div class="exam-page">
    <div v-if="loading" class="loading-center"><n-spin size="large" /></div>

    <template v-else-if="item">
      <!-- 顶栏 -->
      <div class="exam-topbar">
        <div class="et-left">
          <b><span class="pn-full">{{ paper.name }}</span><span class="pn-short">{{ paper.year }} {{ paper.subject_code === 'gz199' ? '管综' : '英二' }}真题</span></b>
          <span class="muted et-section">{{ sectionName }}</span>
        </div>
        <div class="et-right">
          <span class="autosave muted">
            {{ saving ? '保存中…' : savedAt ? `已保存 ${savedAt}` : '自动保存已开启' }}
          </span>
          <span class="countdown" :class="{ urgent, overtime: remainingMs <= 0 }">{{ countdownText }}</span>
          <span class="progress muted">{{ answeredCount }}/{{ flat.length }}</span>
          <n-button type="primary" :loading="submitting" @click="askSubmit">交卷</n-button>
        </div>
      </div>

      <div class="exam-body">
        <!-- 题目区 -->
        <div class="q-area">
          <!-- 分区说明 -->
          <div v-if="sections[item.sectionIndex]?.instructions" class="section-instr muted">
            {{ sections[item.sectionIndex].instructions }}
          </div>

          <div :class="isReadingSplit ? 'split reading-split' : ''">
            <!-- 共享材料 -->
            <div v-if="item.group" class="material-pane">
              <GroupMaterial :group="item.group" :blanks="clozeBlanks"
                :current-number="item.q.number" @jump="jumpNumber" />
            </div>
            <!-- 题目 -->
            <div class="q-pane">
              <QuestionItem :q="item.q" v-model="answers[String(item.q.id)]"
                :shared-options="item.group?.options" />
              <div class="q-nav">
                <n-button quaternary :disabled="current === 0" @click="goto(current - 1)">← 上一题</n-button>
                <span class="kbd-hint">
                  <kbd>A</kbd>-<kbd>E</kbd> 选题 · <kbd>←</kbd><kbd>→</kbd> 切题
                </span>
                <n-button type="primary" ghost :disabled="current === flat.length - 1" @click="goto(current + 1)">
                  下一题 →
                </n-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 答题卡 -->
        <aside class="anscard-pane" :class="{ open: showCard }">
          <div class="anscard-close" @click="showCard = false">收起 ✕</div>
          <div class="anscard-title">答题卡</div>
          <template v-for="(sec, si) in sections" :key="sec.id">
            <div class="section-title">{{ sec.name }}</div>
            <div class="anscard">
              <template v-for="(it, idx) in flat" :key="it.q.id">
                <div v-if="it.sectionIndex === si" class="cell"
                  :class="{ answered: answers[String(it.q.id)] != null && answers[String(it.q.id)] !== '', current: idx === current }"
                  @click="goto(idx)">{{ it.q.number }}</div>
              </template>
            </div>
          </template>
          <div class="muted" style="font-size:12px; margin-top:12px">
            深色＝已作答 · 橙框＝当前题
          </div>
        </aside>
      </div>

      <!-- 交卷确认 -->
      <n-modal v-model:show="confirmSubmit" preset="dialog" title="确认交卷？"
        :content="`还有 ${flat.length - answeredCount} 题未作答，交卷后立即出分。`"
        positive-text="交卷" negative-text="继续作答" @positive-click="doSubmit()" />

      <!-- 移动端答题卡浮钮 -->
      <button class="card-fab" @click="showCard = !showCard">
        答题卡 {{ answeredCount }}/{{ flat.length }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.exam-page { min-height: 100vh; background: #fff; }
.loading-center { display: flex; justify-content: center; padding-top: 120px; }
.exam-topbar { position: sticky; top: 0; z-index: 15; display: flex; align-items: center; justify-content: space-between;
  padding: 10px 20px; background: rgba(255,255,255,.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--line-soft); }
.et-left { display: flex; align-items: baseline; gap: 10px; min-width: 0; max-width: 60%; }
.et-left b { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pn-short { display: none; }
.et-section { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.et-right { display: flex; align-items: center; gap: 14px; flex: none; }
.countdown { font-variant-numeric: tabular-nums; font-weight: 700; font-size: 16px; }
.countdown.urgent { color: var(--bad); animation: pulse 1s infinite; }
.countdown.overtime { color: var(--bad); }
@keyframes pulse { 50% { opacity: .55; } }
.autosave { font-size: 12px; }
.progress { font-size: 13px; font-variant-numeric: tabular-nums; }
.exam-body { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 22px;
  max-width: var(--page-max); margin: 0 auto; padding: 20px; }
.anscard-close { display: none; }
.card-fab { display: none; }
@media (max-width: 768px) {
  .exam-topbar { padding: 8px 14px; }
  .et-left { flex: 0 1 auto; max-width: 46%; }
  .pn-full { display: none; }
  .pn-short { display: inline; }
  .et-section { display: none; }
  .autosave { display: none; }
  .countdown { font-size: 18px; }
  .et-right { gap: 10px; }
}
@media (max-width: 980px) {
  .exam-body { grid-template-columns: 1fr; padding: 14px; padding-bottom: 84px; }
  .anscard-pane {
    position: fixed !important; left: 0; right: 0; bottom: 0; z-index: 30;
    max-height: 62vh; border-radius: 16px 16px 0 0;
    transform: translateY(105%); transition: transform .25s ease;
    box-shadow: 0 -8px 30px rgba(20,30,60,.15);
  }
  .anscard-pane.open { transform: translateY(0); }
  .anscard-close { display: block; text-align: center; font-size: 13px; color: var(--blue);
    padding: 8px 0 4px; cursor: pointer; }
  .card-fab {
    display: block; position: fixed; right: 14px; bottom: calc(74px + env(safe-area-inset-bottom));
    z-index: 25; border: none; border-radius: 24px; padding: 10px 16px;
    background: var(--blue); color: #fff; font-size: 13px; font-weight: 600;
    box-shadow: 0 6px 18px rgba(47,111,237,.4); cursor: pointer;
  }
  .q-nav {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 20;
    background: rgba(255,255,255,.95); backdrop-filter: blur(8px);
    padding: 8px 12px calc(8px + env(safe-area-inset-bottom)); border-top: 1px solid var(--line-soft);
    margin: 0; max-width: none; gap: 8px;
  }
  .q-nav .n-button { flex: 1; }
  .q-nav .kbd-hint { display: none; }
}
.section-instr { font-size: 12.5px; padding: 8px 12px; background: rgba(128,128,128,.05); border-radius: 8px; margin-bottom: 12px; }
.material-pane { min-width: 0; }
.q-pane { min-width: 0; }
.reading-split { align-items: start; }
.q-nav { display: flex; align-items: center; justify-content: space-between; margin-top: 18px; }
.anscard-pane { position: sticky; top: 66px; align-self: start; max-height: calc(100vh - 90px); overflow: auto;
  border: 1px solid var(--line); border-radius: 12px; padding: 14px; background: var(--bg); }
.anscard-title { font-weight: 700; margin-bottom: 4px; }
</style>
