<script setup>
import { computed, ref } from 'vue'
import RichText from './RichText.vue'
import { splitCloze, isClozeBlank, clozeNum } from '../markdown'
import { api } from '../api'
const base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') + '/'

const props = defineProps({
  group: { type: Object, required: true },
  blanks: { type: Object, default: () => ({}) },
  currentNumber: { type: Number, default: null },
})
const emit = defineEmits(['jump'])

const isCloze = () => (props.group.gtype === 'cloze' || /cloze/i.test(props.group.gtype || ''))

/* ---------- 精读模式：点词查义 ---------- */
const intensive = ref(false)
const popup = ref(null) // { x, y, loading, data, word }
const isTextMat = computed(
  () => !!props.group.material && !isCloze() && ['reading', 'gz_essay'].includes(props.group.gtype || '')
)

function lookup(evt, word) {
  if (!intensive.value) return
  const rect = (evt.target).closest('span, b, i')?.getBoundingClientRect() || evt.target.getBoundingClientRect()
  const clean = word.replace(/[^A-Za-z'-]/g, '')
  if (clean.length < 2) return
  popup.value = { x: Math.min(rect.left, window.innerWidth - 240), y: rect.bottom + 6, loading: true, word: clean }
  api(`/api/vocab/lookup?word=${encodeURIComponent(clean)}`)
    .then((d) => { if (popup.value) { popup.value.data = d; popup.value.loading = false } })
    .catch(() => { if (popup.value) { popup.value.data = { found: false }; popup.value.loading = false } })
}

async function addToVocab() {
  if (!popup.value?.data?.found) return
  try {
    await api('/api/vocab/learn', {
      method: 'POST',
      body: { word_id: popup.value.data.word_id, familiarity: 'hard' },
    })
    popup.value.data.learned = true
  } catch { /* 忽略 */ }
}

function closePopup() { popup.value = null }

// 材料按单词拆分（精读开启时），保留空白结构
const matSegments = computed(() => {
  if (!intensive.value || !props.group.material || isCloze()) return null
  return props.group.material.split(/([A-Za-z][A-Za-z'-]*)/)
})
</script>

<template>
  <div class="gmat" v-click-outside="closePopup">
    <div class="gmat-bar" v-if="isTextMat">
      <span class="muted" style="font-size: 12px">{{ intensive ? '精读中：点击单词查释义' : '' }}</span>
      <button class="intensive-btn" :class="{ on: intensive }" @click="intensive = !intensive">
        {{ intensive ? '退出精读' : '精读模式' }}
      </button>
    </div>

    <div v-if="group.title" class="gtitle">{{ group.title }}</div>

    <!-- 普通模式 -->
    <RichText v-if="group.material && (!intensive || !isTextMat || isCloze())" :text="group.material" />

    <!-- 精读模式：单词可点 -->
    <div v-if="intensive && isTextMat && matSegments" class="rich intensive-text">
      <template v-for="(seg, i) in matSegments" :key="i">
        <span v-if="/^[A-Za-z][A-Za-z'-]*$/.test(seg)" class="lookup-word"
          @click="lookup($event, seg)">{{ seg }}</span>
        <span v-else>{{ seg }}</span>
      </template>
    </div>

    <!-- 完形语段：{{n}} 渲染为可点击空位 -->
    <div v-if="group.material && isCloze()" class="rich cloze-passage">
      <template v-for="(seg, i) in splitCloze(group.material)" :key="i">
        <span v-if="isClozeBlank(seg)" class="blank-chip"
          :class="{ 'is-answered': blanks[clozeNum(seg)], 'is-current': currentNumber === clozeNum(seg) }"
          :title="`第 ${clozeNum(seg)} 空`"
          @click="emit('jump', clozeNum(seg))">
          {{ blanks[clozeNum(seg)] || clozeNum(seg) }}
        </span>
        <span v-else>{{ seg }}</span>
      </template>
    </div>

    <!-- 新题型共享选项 -->
    <div v-if="group.options" class="shared-options">
      <div v-for="(text, key) in group.options" :key="key" class="shared-opt">
        <b class="so-key">{{ key }}</b><RichText class="so-text" :text="String(text)" />
      </div>
    </div>

    <!-- 作文图表 -->
    <img v-if="group.material_image" :src="base + 'paper-assets/' + group.material_image"
      :alt="group.title || '图表'" class="chart-img lightbox-img" />

    <!-- 查词弹层 -->
    <div v-if="popup" class="word-popup" :style="{ left: popup.x + 'px', top: popup.y + 'px' }">
      <template v-if="popup.loading">
        <span class="muted" style="font-size:12px">查询中…</span>
      </template>
      <template v-else-if="popup.data?.found">
        <div class="wp-head">
          <b>{{ popup.data.headword }}</b>
          <span v-if="popup.data.freq_rank" class="muted" style="font-size:11px">#{{ popup.data.freq_rank }}</span>
          <span class="wp-close" @click="closePopup">✕</span>
        </div>
        <div class="wp-def">{{ popup.data.definition }}</div>
        <button v-if="!popup.data.learned" class="wp-add" @click="addToVocab">＋ 加入词本（进复习队列）</button>
        <span v-else class="muted" style="font-size:11px">已在词本中</span>
      </template>
      <template v-else>
        <span class="muted" style="font-size:12px">词表中未收录</span>
        <span class="wp-close" @click="closePopup">✕</span>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  directives: {
    'click-outside': {
      mounted(el, binding) {
        el.__co__ = (e) => { if (!el.contains(e.target)) binding.value() }
        document.addEventListener('click', el.__co__)
      },
      unmounted(el) { document.removeEventListener('click', el.__co__) },
    },
  },
}
</script>

<style scoped>
.gmat { background: rgba(128,128,128,.045); border: 1px solid var(--line-soft); border-radius: var(--r-card); padding: 14px 18px; }
.gmat-bar { display: flex; justify-content: flex-end; align-items: center; gap: 8px; min-height: 0; margin-bottom: -6px; }
.intensive-btn { border: 1px solid var(--line); background: var(--card); color: var(--t2);
  border-radius: 99px; padding: 2px 12px; font-size: 12px; cursor: pointer; }
.intensive-btn.on { background: var(--blue); border-color: var(--blue); color: #fff; }
.gtitle { font-weight: 700; margin-bottom: 6px; font-size: 15px; }
.intensive-text .lookup-word { cursor: pointer; border-bottom: 1px dotted var(--blue-line); }
.intensive-text .lookup-word:hover { background: var(--blue-bg); }
.shared-options { margin-top: 10px; display: grid; gap: 6px; }
.shared-opt { display: flex; gap: 8px; align-items: baseline; }
.so-key { flex: none; color: var(--blue); }
.chart-img { max-width: 92%; display: block; margin: 10px auto; border: 1px solid var(--line); border-radius: 8px; }
.word-popup { position: fixed; z-index: 60; width: 224px; background: #fff; border: 1px solid var(--line);
  border-radius: 10px; padding: 10px 12px; box-shadow: var(--shadow-pop); font-size: 13px; }
.wp-head { display: flex; align-items: center; gap: 6px; }
.wp-close { margin-left: auto; cursor: pointer; color: var(--t3); padding: 0 2px; }
.wp-def { margin: 6px 0; color: var(--t1); line-height: 1.5; }
.wp-add { border: none; background: var(--blue-bg); color: var(--blue-deep); border-radius: 6px;
  padding: 4px 10px; font-size: 12px; cursor: pointer; }
</style>
