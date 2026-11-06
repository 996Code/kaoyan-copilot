<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NEmpty, NProgress, NSpin, NTag, useMessage } from 'naive-ui'
import { api } from '../api'

const message = useMessage()
const BATCH = 20

const loading = ref(true)
const words = ref([])
const idx = ref(0)
const learnedTotal = ref(0)
const totalWords = ref(5530)
const batchStats = reactive({ easy: 0, good: 0, hard: 0 })

const finished = computed(() => !loading.value && words.value.length && idx.value >= words.value.length)
const word = computed(() => words.value[idx.value] || null)
const percent = computed(() =>
  totalWords.value ? Math.round((learnedTotal.value / totalWords.value) * 100) : 0
)

async function load() {
  loading.value = true
  try {
    const data = await api(`/api/vocab/learn_batch?count=${BATCH}`)
    words.value = data.words
    learnedTotal.value = data.learned_total
    totalWords.value = data.total
    idx.value = 0
    batchStats.easy = batchStats.good = batchStats.hard = 0
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

const submitting = ref(false)
async function mark(familiarity) {
  if (!word.value || submitting.value) return
  submitting.value = true
  try {
    await api('/api/vocab/learn', {
      method: 'POST',
      body: { word_id: word.value.id, familiarity },
    })
    batchStats[familiarity] += 1
    learnedTotal.value += 1
    idx.value += 1
  } catch (e) {
    message.error(e.message)
  } finally {
    submitting.value = false
  }
}

function onKey(e) {
  if (e.key === '1') { mark('hard'); e.preventDefault() }
  if (e.key === '2') { mark('good'); e.preventDefault() }
  if (e.key === '3') { mark('easy'); e.preventDefault() }
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  load()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="page">
    <div class="vb-head">
      <h2 style="margin:18px 0 4px">背单词</h2>
      <p class="muted" style="margin:0">
        按真题词频排序学新词（最高频的先背）；标记熟悉度后进入 FSRS 复习队列。
      </p>
    </div>

    <n-card :bordered="false" style="border-radius:14px; margin-bottom:14px">
      <div style="display:flex; align-items:center; gap:14px">
        <span class="muted" style="font-size:13px; white-space:nowrap">
          已学 {{ learnedTotal }} / {{ totalWords }}（{{ percent }}%）
        </span>
        <n-progress :percentage="percent" :height="8" style="flex:1" />
      </div>
    </n-card>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

    <n-empty v-else-if="!words.length" description="5530 词全部学完！去复习中心巩固吧 🎉" style="margin:60px 0">
      <template #extra>
        <n-button type="primary" @click="$router.push('/review')">去复习</n-button>
      </template>
    </n-empty>

    <div v-else-if="word" class="vocab-card">
      <div class="batch-progress muted">
        本批 {{ idx + 1 }} / {{ words.length }}
        <n-tag v-if="word.freq_rank" size="small" style="margin-left:8px">词频 No.{{ word.freq_rank }}</n-tag>
      </div>

      <div class="word-main">
        <div class="word">{{ word.headword }}</div>
        <div class="muted">{{ word.phonetic || '' }}</div>
        <div class="definition">{{ word.definition }}</div>
        <div v-if="word.example" class="example">
          <div>{{ word.example }}</div>
          <div class="muted">{{ word.example_translation }}</div>
        </div>
      </div>

      <div class="mark-row">
        <n-button size="large" type="error" ghost :loading="submitting" @click="mark('hard')">
          😖 生 <span class="kbd-hint">(1)</span>
        </n-button>
        <n-button size="large" :loading="submitting" @click="mark('good')">
          😐 模糊 <span class="kbd-hint">(2)</span>
        </n-button>
        <n-button size="large" type="success" ghost :loading="submitting" @click="mark('easy')">
          😎 熟 <span class="kbd-hint">(3)</span>
        </n-button>
      </div>
    </div>

    <div v-else-if="finished" class="finish-card">
      <div style="font-size:44px">👏</div>
      <h2>本批 {{ words.length }} 词学完</h2>
      <p class="muted">熟 {{ batchStats.easy }} · 模糊 {{ batchStats.good }} · 生 {{ batchStats.hard }}——生词会很快在复习中心出现</p>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:14px">
        <n-button @click="load">再学一批</n-button>
        <n-button type="primary" @click="$router.push('/review')">去复习</n-button>
        <n-button @click="$router.push('/')">回看板</n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vocab-card { background:#fff; border:1px solid #eceef5; border-radius:16px; padding:26px 24px; text-align:center; }
.batch-progress { font-size:13px; margin-bottom:10px; }
.word-main { padding:14px 0 22px; }
.word { font-size:46px; font-weight:800; letter-spacing:.5px; }
.definition { font-size:19px; margin-top:10px; }
.example { color:#575e72; font-size:14px; line-height:1.7; margin-top:12px; }
.mark-row { display:flex; gap:14px; justify-content:center; }
.finish-card { text-align:center; padding:60px 0; }
</style>
