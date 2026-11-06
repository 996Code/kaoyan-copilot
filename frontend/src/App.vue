<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NConfigProvider, NMessageProvider, NDialogProvider,
  zhCN, dateZhCN, NTag,
} from 'naive-ui'
import { bindGlobalToast, clearToken } from './api'
import ToastBinder from './components/ToastBinder.vue'
import AppIcon from './components/AppIcon.vue'

const route = useRoute()
const router = useRouter()

const EXAM_DATE = new Date('2026-12-19T09:00:00+08:00')
const daysLeft = computed(() => {
  const d = Math.ceil((EXAM_DATE - Date.now()) / 86400000)
  return d > 0 ? d : 0
})

const inExam = computed(() => route.path.startsWith('/exam/'))
const isLogin = computed(() => route.path === '/login')
const PAGE_TITLES = [
  ['/review', '复习中心'], ['/vocab', '背单词'], ['/practice', '专项练习'],
  ['/wrongbook', '错题本'], ['/knowledge', '知识卡片'], ['/writing', '写作模板'],
  ['/admin', '系统管理'], ['/papers', '真题模考'],
]
const pageTitle = computed(() => {
  void route.fullPath
  const hit = PAGE_TITLES.find(([p]) => route.path.startsWith(p))
  return hit ? hit[1] : ''
})
// localStorage 非响应式：借路由变化触发重算（登录/退出必然改变路由）
const isLoggedIn = computed(() => {
  void route.fullPath
  return !!localStorage.getItem('kaoyan_token')
})
const username = computed(() => {
  void route.fullPath
  return localStorage.getItem('kaoyan_username') || ''
})
const isAdmin = computed(() => {
  void route.fullPath
  return localStorage.getItem('kaoyan_is_admin') === '1'
})
function logout() {
  clearToken()
  localStorage.removeItem('kaoyan_username')
  localStorage.removeItem('kaoyan_is_admin')
  router.push('/login')
}

/* 移动端「更多」菜单 */
const moreOpen = ref(false)
const moreActive = computed(() => ['/papers', '/admin', '/knowledge', '/writing'].some(p => route.path.startsWith(p)))
const moreItems = computed(() => {
  const items = [
    { to: '/knowledge', icon: 'ai', label: '知识卡片' },
    { to: '/writing', icon: 'vocab', label: '写作模板' },
    { to: '/papers', icon: 'exam', label: '真题模考（管综/英二）' },
  ]
  if (isAdmin.value) items.push({ to: '/admin', icon: 'ai', label: '系统管理' })
  return items
})
function goMore(to) {
  moreOpen.value = false
  router.push(to)
}
</script>

<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN"
    style="min-height:100vh"
    :theme-overrides="{
      common: {
        primaryColor: '#1677FF',
        primaryColorHover: '#3C8DFF',
        primaryColorPressed: '#0E5FD8',
        primaryColorSuppl: '#1677FF',
        borderRadius: '6px',
      },
    }">
    <n-message-provider>
      <ToastBinder />
      <n-dialog-provider>
        <div class="shell" :class="{ 'in-exam': inExam }">
          <header v-if="!inExam && !isLogin" class="topbar">
            <div class="topbar-inner">
              <div class="brand">
                <span class="logo">考</span>
                <span class="title">考研助手</span>
              </div>
              <span class="bar-title">{{ pageTitle }}</span>
              <nav class="nav">
                <router-link to="/">首页</router-link>
                <router-link to="/review">复习</router-link>
                <router-link to="/vocab">背单词</router-link>
                <router-link to="/knowledge">知识卡片</router-link>
                <router-link to="/practice">专项练习</router-link>
                <router-link to="/wrongbook">错题本</router-link>
                <router-link to="/writing">写作模板</router-link>
                <router-link to="/papers">真题模考</router-link>
                <router-link v-if="isAdmin" to="/admin">系统管理</router-link>
              </nav>
              <div class="right">
                <div v-if="daysLeft" class="exam-chip">距初试 <b>{{ daysLeft }}</b> 天</div>
                <div v-if="isLoggedIn && username" class="username">
                  <span class="avatar">{{ username[0].toUpperCase() }}</span>
                  <span class="u-name">{{ username }}</span>
                </div>
                <button v-if="isLoggedIn" class="ghost-btn" @click="logout">退出</button>
              </div>
            </div>
          </header>
          <router-view />
        </div>

        <!-- 移动端底部 Tab 栏 -->
        <nav v-if="!inExam && !isLogin" class="tabbar">
          <router-link to="/"><AppIcon name="home" :size="22" />首页</router-link>
          <router-link to="/review"><AppIcon name="review" :size="22" />复习</router-link>
          <router-link to="/vocab"><AppIcon name="vocab" :size="22" />单词</router-link>
          <router-link to="/practice"><AppIcon name="practice" :size="22" />练习</router-link>
          <router-link to="/wrongbook"><AppIcon name="wrong" :size="22" />错题</router-link>
          <a :class="{ 'router-link-active': moreActive }" @click.prevent="moreOpen = true">
            <AppIcon name="trend" :size="22" />更多
          </a>
        </nav>

        <!-- 移动端「更多」底部菜单 -->
        <div v-if="moreOpen" class="more-mask" @click="moreOpen = false"></div>
        <div v-if="moreOpen" class="more-sheet">
          <div class="more-grab"></div>
          <button v-for="m in moreItems" :key="m.to" class="more-item" @click="goMore(m.to)">
            <span class="mi-ic"><AppIcon :name="m.icon" :size="20" /></span>
            <span>{{ m.label }}</span>
            <AppIcon name="check" :size="14" style="margin-left:auto;opacity:.25" />
          </button>
          <button v-if="isLoggedIn" class="more-item" @click="moreOpen = false; logout()">
            <span class="mi-ic"><AppIcon name="wrong" :size="20" /></span>
            <span>退出登录（{{ username }}）</span>
          </button>
        </div>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.shell { min-height: 100vh; background: #f6f7fb; }
.shell.in-exam { background: #fff; }
.dark .shell, .in-exam { background: inherit; }
.topbar { position: sticky; top: 0; z-index: 20; background: var(--card); border-bottom: 1px solid var(--line); }
.topbar-inner { max-width: 1240px; margin: 0 auto; padding: 0 20px; height: 52px; display: flex; align-items: center; gap: 20px; }
.brand { display: flex; align-items: center; gap: 9px; font-weight: 700; font-size: 15px; }
.logo { width: 28px; height: 28px; border-radius: 7px; background: var(--blue); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.title { font-size: 15px; }
.nav { display: flex; gap: 2px; flex: 1; }
.nav a { padding: 6px 14px; border-radius: 6px; color: var(--t2); text-decoration: none; font-size: 14px; }
.nav a.router-link-active { background: var(--blue-bg); color: var(--blue); font-weight: 600; }
.exam-chip { display: flex; align-items: center; gap: 6px; background: var(--blue-bg);
  color: var(--blue-deep); font-weight: 700; border-radius: 6px; padding: 5px 12px; font-size: 13px; }
.exam-chip b { font-size: 17px; font-variant-numeric: tabular-nums; }
.right { display: flex; gap: 6px; align-items: center; }
.username { font-size: 13px; color: var(--t2); display: flex; align-items: center; gap: 7px; }
.avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #3C8DFF, #0E5FD8);
  color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.tabbar { display: none; }
.bar-title { display: none; }

/* 「更多」底部菜单（移动端） */
.more-mask { display: none; }
.more-sheet { display: none; }


@media (max-width: 768px) {
  .nav { display: none; }
  .topbar-inner { padding: 0 14px; gap: 8px; }
  .title { font-size: 15px; }
  .username span.u-name { display: none; }
  .right .ghost-btn { display: none; }  /* 退出在「更多」菜单里 */
  .right { margin-left: auto; gap: 10px; }  /* nav 隐藏后仍靠右 */
  .bar-title { display: block; flex: 1; text-align: center; font-size: 15px; font-weight: 600; color: var(--t1); white-space: nowrap; }
  .shell:not(.in-exam) { padding-bottom: calc(58px + env(safe-area-inset-bottom)); }
  .tabbar {
    display: flex; position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
    background: rgba(255,255,255,.94); backdrop-filter: blur(12px);
    border-top: 1px solid var(--line); padding-bottom: env(safe-area-inset-bottom);
  }
  .tabbar a {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px;
    padding: 8px 0 6px; font-size: 10.5px; color: var(--t3); text-decoration: none;
    transition: color .15s;
  }
  .tabbar a.router-link-active { color: var(--blue); font-weight: 600; }
  .tabbar a.router-link-active svg { transform: translateY(-1px); }

  .more-mask {
    display: block; position: fixed; inset: 0; z-index: 45;
    background: rgba(16, 22, 34, 0.4);
  }
  .more-sheet {
    display: block; position: fixed; left: 0; right: 0; bottom: 0; z-index: 46;
    background: var(--card); border-radius: 16px 16px 0 0;
    padding: 6px 14px calc(18px + env(safe-area-inset-bottom));
    box-shadow: 0 -8px 30px rgba(20, 30, 60, 0.18);
  }
  .more-grab { width: 36px; height: 4px; border-radius: 2px; background: var(--line); margin: 4px auto 10px; }
  .more-item {
    display: flex; align-items: center; gap: 12px; width: 100%;
    background: transparent; border: none; cursor: pointer;
    padding: 14px 8px; font-size: 15px; color: var(--t1);
    border-bottom: 1px solid var(--line-soft); text-align: left;
  }
  .more-item:last-child { border-bottom: none; }
  .more-item:active { background: var(--card-hover); }
  .mi-ic { width: 36px; height: 36px; border-radius: 9px; background: var(--blue-bg); color: var(--blue);
    display: flex; align-items: center; justify-content: center; }
}
.ghost-btn { border: none; background: transparent; cursor: pointer; padding: 6px 10px; border-radius: 8px; font-size: 13px; color: #575e72; }
.ghost-btn:hover { background: rgba(128,128,128,.1); }
</style>
