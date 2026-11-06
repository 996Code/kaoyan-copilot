<script setup>
/** 统一图标集：线性风格（stroke 1.8 / 圆角端点），颜色随 currentColor。全站禁止 emoji 当图标。 */
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
})

const PATHS = {
  home: 'M3 10.5L12 3l9 7.5M5.5 9.5V20a1 1 0 001 1h11a1 1 0 001-1V9.5M9.5 21v-6h5v6',
  review: 'M20 11A8 8 0 105.6 6.4M4 4v4h4M20 4v4h-4M4 13a8 8 0 0014.4 4.6',
  vocab: 'M12 6.5C10.5 4.8 8 4 4.5 4.2v13C8 17 10.5 17.8 12 19.5c1.5-1.7 4-2.5 7.5-2.3v-13C16 4 13.5 4.8 12 6.5zM12 6.5v13',
  practice: 'M14.5 4.5l5 5L8 21H3v-5L14.5 4.5zM12.5 6.5l5 5',
  wrong: 'M12 21a9 9 0 100-18 9 9 0 000 18zM8.6 8.6l6.8 6.8M15.4 8.6l-6.8 6.8',
  exam: 'M9 4h6v3H9zM7 5H5.5A1.5 1.5 0 004 6.5v13A1.5 1.5 0 005.5 21h13a1.5 1.5 0 001.5-1.5v-13A1.5 1.5 0 0018.5 5H17M8 12h8M8 16h5',
  timer: 'M12 21a8.5 8.5 0 100-17 8.5 8.5 0 000 17zM12 7.5V12l3 2M9 2.5h6',
  target: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 16.5a4.5 4.5 0 100-9 4.5 4.5 0 000 9zM12 13.2a1.2 1.2 0 100-2.4 1.2 1.2 0 000 2.4z',
  check: 'M4 12.5l5 5L20 6.5',
  spark: 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3zM19 16l.9 2.1L22 19l-2.1.9L19 22l-.9-2.1L16 19l2.1-.9L19 16z',
  trend: 'M3 17l6-6 4 4 8-8M15 7h6v6',
  ai: 'M12 4v2M12 18v2M4 12h2M18 12h2M6.3 6.3l1.4 1.4M16.3 16.3l1.4 1.4M6.3 17.7l1.4-1.4M16.3 7.7l1.4-1.4M12 15.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7z',
}
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
    style="flex:none">
    <path :d="PATHS[name] || PATHS.check" />
  </svg>
</template>
