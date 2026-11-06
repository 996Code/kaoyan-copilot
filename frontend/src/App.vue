<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NConfigProvider, NMessageProvider, NDialogProvider,
  zhCN, dateZhCN, NTag,
} from 'naive-ui'
import { clearToken } from './api'

const route = useRoute()
const router = useRouter()

const EXAM_DATE = new Date('2026-12-19T09:00:00+08:00')
const daysLeft = computed(() => {
  const d = Math.ceil((EXAM_DATE - Date.now()) / 86400000)
  return d > 0 ? d : 0
})

const inExam = computed(() => route.path.startsWith('/exam/'))
// localStorage 非响应式：借路由变化触发重算（登录/退出必然改变路由）
const isLoggedIn = computed(() => {
  void route.fullPath
  return !!localStorage.getItem('kaoyan_token')
})
const username = computed(() => {
  void route.fullPath
  return localStorage.getItem('kaoyan_username') || ''
})
function logout() {
  clearToken()
  localStorage.removeItem('kaoyan_username')
  router.push('/login')
}
</script>

<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN"
    style="min-height:100vh" :theme-overrides="{ common: { primaryColor: '#2f6fed' } }">
    <n-message-provider>
      <n-dialog-provider>
        <div class="shell" :class="{ 'in-exam': inExam }">
          <header v-if="!inExam" class="topbar">
            <div class="topbar-inner">
              <div class="brand">
                <span class="logo">考</span>
                <span class="title">考研助手</span>
                <n-tag v-if="daysLeft" size="small" type="warning" round style="margin-left:10px">
                  距初试约 {{ daysLeft }} 天
                </n-tag>
              </div>
              <nav class="nav">
                <router-link to="/">首页</router-link>
                <router-link to="/review">复习</router-link>
                <router-link to="/vocab">背单词</router-link>
                <router-link to="/practice">专项练习</router-link>
                <router-link to="/wrongbook">错题本</router-link>
                <router-link to="/papers/gz199">管综真题</router-link>
                <router-link to="/papers/en2">英二真题</router-link>
              </nav>
              <div class="right">
                <span v-if="isLoggedIn && username" class="username">👤 {{ username }}</span>
                <button v-if="isLoggedIn" class="ghost-btn" @click="logout">退出</button>
              </div>
            </div>
          </header>
          <router-view />
        </div>

        <!-- 移动端底部 Tab 栏 -->
        <nav v-if="!inExam" class="tabbar">
          <router-link to="/"><span class="tb-icon">🏠</span>首页</router-link>
          <router-link to="/review"><span class="tb-icon">🔁</span>复习</router-link>
          <router-link to="/vocab"><span class="tb-icon">📖</span>单词</router-link>
          <router-link to="/practice"><span class="tb-icon">✏️</span>练习</router-link>
          <router-link to="/wrongbook"><span class="tb-icon">📕</span>错题</router-link>
        </nav>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.shell { min-height: 100vh; background: #f6f7fb; }
.shell.in-exam { background: #fff; }
.dark .shell, .in-exam { background: inherit; }
.topbar { position: sticky; top: 0; z-index: 20; background: rgba(255,255,255,.86); backdrop-filter: blur(10px); border-bottom: 1px solid #e8eaf1; }
.topbar-inner { max-width: var(--page-max); margin: 0 auto; padding: 0 20px; height: 54px; display: flex; align-items: center; gap: 22px; }
.brand { display: flex; align-items: center; gap: 8px; font-weight: 700; }
.logo { width: 26px; height: 26px; border-radius: 8px; background: #2f6fed; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.title { font-size: 16px; }
.nav { display: flex; gap: 4px; flex: 1; }
.nav a { padding: 6px 12px; border-radius: 8px; color: #575e72; text-decoration: none; font-size: 14px; }
.nav a.router-link-active { background: rgba(47,111,237,.1); color: #2f6fed; font-weight: 600; }
.right { display: flex; gap: 6px; align-items: center; }
.username { font-size: 13px; color: #575e72; }
.tabbar { display: none; }

@media (max-width: 768px) {
  .nav { display: none; }
  .topbar-inner { padding: 0 14px; gap: 8px; }
  .title { font-size: 15px; }
  .username { display: none; }
  .right .ghost-btn { font-size: 12px; padding: 4px 8px; }
  .shell:not(.in-exam) { padding-bottom: calc(58px + env(safe-area-inset-bottom)); }
  .tabbar {
    display: flex; position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
    background: rgba(255,255,255,.94); backdrop-filter: blur(12px);
    border-top: 1px solid #e8eaf1; padding-bottom: env(safe-area-inset-bottom);
  }
  .tabbar a {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 1px;
    padding: 7px 0 5px; font-size: 10.5px; color: #8b93a7; text-decoration: none;
  }
  .tabbar a.router-link-active { color: #2f6fed; font-weight: 600; }
  .tb-icon { font-size: 19px; line-height: 1; }
}
.ghost-btn { border: none; background: transparent; cursor: pointer; padding: 6px 10px; border-radius: 8px; font-size: 13px; color: #575e72; }
.ghost-btn:hover { background: rgba(128,128,128,.1); }
</style>
