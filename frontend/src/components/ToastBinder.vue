<script setup>
// 挂在 NMessageProvider 内部，把 naive 的 message 实例绑定给 api.js 做全局错误提示
import { useMessage } from 'naive-ui'
import { bindGlobalToast } from '../api'

bindGlobalToast(useMessage())
</script>

<template></template>
