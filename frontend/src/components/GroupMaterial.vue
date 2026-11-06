<script setup>
import RichText from './RichText.vue'
import { splitCloze, isClozeBlank, clozeNum } from '../markdown'

const props = defineProps({
  group: { type: Object, required: true },
  // 完形：题号 -> 已选字母
  blanks: { type: Object, default: () => ({}) },
  currentNumber: { type: Number, default: null },
})
const emit = defineEmits(['jump'])

const isCloze = () => (props.group.gtype === 'cloze' || /cloze/i.test(props.group.gtype || ''))
</script>

<template>
  <div class="gmat">
    <div v-if="group.title" class="gtitle">{{ group.title }}</div>

    <!-- 完形语段：{{n}} 渲染为可点击空位 -->
    <RichText v-if="group.material && !isCloze()" :text="group.material" />
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
    <img v-if="group.material_image" :src="'/paper-assets/' + group.material_image"
      :alt="group.title || '图表'" class="chart-img" />
  </div>
</template>

<style scoped>
.gmat { background: rgba(128,128,128,.045); border: 1px solid #eceef5; border-radius: 12px; padding: 14px 18px; }
.gtitle { font-weight: 700; margin-bottom: 6px; font-size: 15px; }
.shared-options { margin-top: 10px; display: grid; gap: 6px; }
.shared-opt { display: flex; gap: 8px; align-items: baseline; }
.so-key { flex: none; color: #2f6fed; }
.chart-img { max-width: 92%; display: block; margin: 10px auto; border: 1px solid #e5e8f0; border-radius: 8px; }
</style>
