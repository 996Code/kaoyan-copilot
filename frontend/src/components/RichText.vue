<script setup>
import { computed } from 'vue'
import { renderRich } from '../markdown'

const props = defineProps({ text: { type: String, default: '' } })
const html = computed(() => renderRich(props.text))
</script>

<template>
  <div class="rich" v-html="html"></div>
</template>
