<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  NButton, NCard, NSelect, NSpin, NTag, useMessage,
} from 'naive-ui'
import { api } from '../api'
import { renderRich } from '../markdown'
import QuestionItem from '../components/QuestionItem.vue'
import GroupMaterial from '../components/GroupMaterial.vue'
import AiPanel from '../components/AiPanel.vue'

const message = useMessage()

const subjects = ref([])
const subject = ref('gz199')
const moduleCode = ref('math')
const year = ref(null)
const count = ref(10)

const questions = ref([])
const loading = ref(false)
const current = ref(0)
const myAnswer = ref(null)
const checked = ref(null) // check 接口返回
const stats = reactive({ done: 0, correct: 0 })

const moduleOptions = computed(() => {
  const sub = subjects.value.find((s) => s.code === subject.value)
  return (sub?.modules || []).map((m) => ({ label: m.name, value: m.code }))
})
const yearOptions = computed(() => {
  const base = subject.value === 'gz199' ? 2009 : 2010
  const end = subject.value === 'gz199' ? 2026 : 2025
  const opts = [{ label: '全部年份（随机）', value: null }]
  for (let y = end; y >= base; y--) opts.push({ label: `${y} 年`, value: y })
  return opts
})

const item = computed(() => questions.value[current.value] || null)
const group = computed(() => {
  if (!item.value || !item.value.group_material && !item.value.group_options && !item.value.group_image && !item.value.group_title) return null
  if (item.value.qtype === 'single_choice' && !item.value.group_material && !item.value.group_options) return null
  const material = item.value.group_material || ''
  const gtype = item.value.group_options ? 'matching'
    : /\{\{\d+\}\}/.test(material) ? 'cloze'
    : item.value.qtype === 'essay' ? 'gz_essay'
    : 'reading'
  return {
    gtype,
    title: item.value.group_title,
    material: item.value.group_material,
    options: item.value.group_options,
    material_image: item.value.group_image,
  }
})

async function start() {
  loading.value = true
  try {
    const params = new URLSearchParams({ subject: subject.value, module: moduleCode.value, limit: String(count.value), random: 'true' })
    if (year.value) params.set('year', String(year.value))
    questions.value = await api(`/api/practice/questions?${params}`)
    current.value = 0
    myAnswer.value = null
    checked.value = null
    stats.done = 0
    stats.correct = 0
    if (!questions.value.length) message.warning('没有符合条件的题目')
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

async function check() {
  if (myAnswer.value == null || myAnswer.value === '') return
  checked.value = await api('/api/practice/check', {
    method: 'POST',
    body: { question_id: item.value.id, answer: myAnswer.value },
  })
  stats.done += 1
  if (checked.value.correct) stats.correct += 1
}

function next() {
  if (current.value >= questions.value.length - 1) {
    message.success(`本组完成：${stats.correct}/${stats.done} 正确`)
    return
  }
  current.value += 1
  myAnswer.value = null
  checked.value = null
}

function onKey(e) {
  const tag = (e.target.tagName || '').toLowerCase()
  if (tag === 'textarea' || tag === 'input') return
  if (!item.value) return
  const letters = ['a', 'b', 'c', 'd', 'e']
  if (item.value.qtype === 'single_choice' && item.value.options && !checked.value) {
    const li = letters.indexOf(e.key.toLowerCase())
    const ni = Number(e.key) >= 1 && Number(e.key) <= 5 ? Number(e.key) - 1 : -1
    const idx = li >= 0 ? li : ni
    if (idx >= 0 && idx < item.value.options.length) {
      myAnswer.value = item.value.options[idx].key
      e.preventDefault(); return
    }
    if (e.key === 'Enter') { check(); e.preventDefault(); return }
  }
  if (e.key === 'Enter' && checked.value) { next(); e.preventDefault() }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  subjects.value = await api('/api/subjects')
  // 支持看板跳转预选：/practice?subject=gz199&module=math
  const qs = new URLSearchParams((location.hash.split('?')[1] || ''))
  const qsSubject = qs.get('subject')
  const qsModule = qs.get('module')
  const preset = subjects.value.find((s) => s.code === qsSubject) || subjects.value[0]
  if (preset) {
    subject.value = preset.code
    moduleCode.value = preset.modules.find((m) => m.code === qsModule)?.code || preset.modules[0]?.code
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page">
    <h2 style="margin:18px 0 4px">专项练习</h2>
    <p class="muted" style="margin:0 0 14px">按模块/年份抽题，即答即判，错题自动进错题记录（AI 讲解即将上线）</p>

    <n-card :bordered="false" style="border-radius:14px; margin-bottom:16px">
      <div class="filters">
        <n-select v-model:value="subject" :options="subjects.map(s => ({ label: s.name, value: s.code }))"
          style="width:200px" @update:value="moduleCode = moduleOptions[0]?.value" />
        <n-select v-model:value="moduleCode" :options="moduleOptions" style="width:150px" />
        <n-select v-model:value="year" :options="yearOptions" style="width:180px" />
        <n-select v-model:value="count" :options="[{label:'10 题',value:10},{label:'20 题',value:20},{label:'30 题',value:30}]" style="width:100px" />
        <n-button type="primary" :loading="loading" @click="start">开始练习</n-button>
      </div>
    </n-card>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

    <template v-else-if="item">
      <div class="pstats">
        <span>第 {{ current + 1 }} / {{ questions.length }} 题</span>
        <span>{{ item.year }} 年真题</span>
        <span :style="stats.done ? '' : 'opacity:.4'">
          正确率 {{ stats.done ? Math.round((stats.correct / stats.done) * 100) : 0 }}%（{{ stats.correct }}/{{ stats.done }}）
        </span>
      </div>

      <div class="practice-card">
        <GroupMaterial v-if="group" :group="group" />
        <QuestionItem :q="item" v-model="myAnswer" :mode="checked ? 'review' : 'take'"
          :result="checked ? { your_answer: myAnswer, correct_answer: checked.correct_answer } : null"
          :shared-options="group?.options" />

        <div v-if="checked" class="feedback">
          <div class="fb-line">
            <n-tag :type="checked.correct === true ? 'success' : checked.correct === false ? 'error' : 'info'">
              {{ checked.correct === true ? '✓ 回答正确' : checked.correct === false ? '✗ 回答错误' : '主观题，待 AI 批改' }}
            </n-tag>
            <span v-if="checked.correct === false" style="margin-left:10px">
              正确答案：<b style="color:#18a058">{{ checked.correct_answer }}</b>
            </span>
            <n-tag v-if="checked.disputed" type="warning" size="small" style="margin-left:10px">该题答案存在版本争议</n-tag>
          </div>
          <div v-if="checked.analysis">
            <div class="section-title">解析</div>
            <div class="rich" v-html="renderRich(checked.analysis)"></div>
          </div>
          <AiPanel :endpoint="`/api/ai/explain/${item.id}?student_answer=${encodeURIComponent(String(myAnswer ?? ''))}`"
            label="AI 讲解本题" />
        </div>

        <div class="p-actions">
          <span class="kbd-hint">
            <kbd>A</kbd>-<kbd>E</kbd> 选题 · <kbd>Enter</kbd> {{ checked ? '下一题' : '确认' }}
          </span>
          <n-button v-if="!checked" type="primary" :disabled="myAnswer == null || myAnswer === ''" @click="check">
            确认答案
          </n-button>
          <n-button v-else type="primary" @click="next">下一题 →</n-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.pstats { display: flex; gap: 18px; font-size: 13px; color: #7c849a; margin-bottom: 10px; }
.practice-card { background: #fff; border: 1px solid #eceef5; border-radius: 14px; padding: 18px 20px; }
.feedback { margin-top: 14px; padding-top: 12px; border-top: 1px dashed #e4e7f0; }
.fb-line { display: flex; align-items: center; margin-bottom: 8px; }
.p-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
</style>
