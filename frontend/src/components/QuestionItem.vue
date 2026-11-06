<script setup>
import { computed } from 'vue'
import RichText from './RichText.vue'

const props = defineProps({
  q: { type: Object, required: true },
  modelValue: { default: null }, // 字母或文本
  mode: { type: String, default: 'take' }, // take | review
  result: { type: Object, default: null }, // {your_answer, is_correct}
  sharedOptions: { type: Object, default: null }, // 新题型共享选项 {A:text}
})
const emit = defineEmits(['update:modelValue'])

const options = computed(() => {
  if (props.q.options && props.q.options.length) return props.q.options
  if (props.sharedOptions) {
    return Object.entries(props.sharedOptions).map(([key, text]) => ({ key, text: String(text) }))
  }
  return []
})

const isChoice = computed(() => props.q.qtype === 'single_choice')

function pick(key) {
  if (props.mode !== 'take' || !isChoice.value) return
  emit('update:modelValue', props.modelValue === key ? null : key)
}

function optClass(o) {
  if (props.mode !== 'review' || !props.result) return props.modelValue === o.key ? 'selected' : ''
  const your = props.result.your_answer
  const correct = props.result.correct_answer
  if (o.key === correct) return 'correct'
  if (o.key === your && your !== correct) return 'wrong'
  return ''
}
const wordCount = computed(() =>
  props.modelValue ? String(props.modelValue).replace(/\s/g, '').length : 0
)
</script>

<template>
  <div class="qitem">
    <div class="stem-wrap">
      <span class="qnum">{{ q.number }}.</span>
      <RichText :text="q.stem" />
    </div>

    <div v-if="isChoice" class="opts">
      <div v-for="o in options" :key="o.key" class="opt-row" :class="optClass(o)" @click="pick(o.key)">
        <span class="opt-key">{{ o.key }}</span>
        <RichText :text="o.text" style="flex:1" />
      </div>
    </div>

    <div v-else class="subjective">
      <textarea v-if="mode === 'take'" class="essay" placeholder="在此作答…"
        :value="modelValue || ''"
        @input="emit('update:modelValue', $event.target.value)"></textarea>
      <div v-else class="essay readonly-essay">{{ modelValue || '（未作答）' }}</div>
      <div class="muted" style="text-align:right; font-size:12px; margin-top:4px">
        {{ wordCount }} 字
      </div>
    </div>
  </div>
</template>

<style scoped>
.qitem { font-size: 15px; }
.stem-wrap { display: flex; gap: 8px; margin-bottom: 8px; align-items: baseline; }
.qnum { font-weight: 700; flex: none; }
.subjective { margin-top: 6px; }
.readonly-essay { white-space: pre-wrap; background: rgba(128,128,128,.05); border: 1px dashed #d5d9e4; border-radius: 10px; padding: 12px 14px; min-height: 60px; }
</style>
