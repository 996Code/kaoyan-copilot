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
import Lightbox from './components/Lightbox.vue'

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
  ['/review', '复习中心'], ['/vocab', '背单词'], ['/practice', '练习'],
  ['/wrongbook', '错题本'], ['/knowledge', '知识卡片'], ['/writing', '写作模板'],
  ['/admin', '系统管理'], ['/papers', '真题模考'],
  ['/history', '模考记录'], ['/report', '成绩报告'],
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
  avatarMenuOpen.value = false
  router.push('/login')
}

/* 右上角头像下拉菜单（系统管理 / 退出登录）：点空白处收起 */
const avatarMenuOpen = ref(false)
onMounted(() => {
  document.addEventListener('click', () => { avatarMenuOpen.value = false })
})
function goAvatarAdmin() {
  avatarMenuOpen.value = false
  router.push('/admin')
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
                <router-link to="/practice">练习</router-link>
                <router-link to="/papers">真题模考</router-link>
                <router-link to="/wrongbook">错题本</router-link>
                <router-link to="/knowledge">知识</router-link>
                <router-link v-if="isAdmin" to="/admin">系统管理</router-link>
              </nav>
              <div class="right">
                <div v-if="daysLeft" class="exam-chip" :title="`距初试 ${daysLeft} 天`"
                  :aria-label="`距初试 ${daysLeft} 天`">
                  <span class="chip-text">距初试 </span><b>{{ daysLeft }}</b><span class="chip-text"> 天</span>
                </div>
                <div v-if="isLoggedIn && username" class="username avatar-wrap">
                  <button class="avatar-btn" :aria-expanded="avatarMenuOpen" aria-label="账号菜单"
                    @click.stop="avatarMenuOpen = !avatarMenuOpen">
                    <span class="avatar">{{ username[0].toUpperCase() }}</span>
                    <span class="u-name">{{ username }}</span>
                  </button>
                  <!-- 头像下拉：系统管理（admin）/ 退出登录 -->
                  <div v-if="avatarMenuOpen" class="avatar-menu">
                    <button v-if="isAdmin" class="av-item" @click="goAvatarAdmin()">
                      <AppIcon name="ai" :size="16" />系统管理
                    </button>
                    <button class="av-item av-logout" @click="logout()">
                      <AppIcon name="wrong" :size="16" />退出登录
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </header>
          <router-view />
        </div>

        <!-- 全局点击放大（SVG 图形 / 图表图片） -->
        <Lightbox />

        <!-- 移动端底部 Tab 栏 -->
        <nav v-if="!inExam && !isLogin" class="tabbar">
          <router-link to="/"><AppIcon name="home" :size="22" />首页</router-link>
          <router-link to="/review"><AppIcon name="review" :size="22" />复习</router-link>
          <router-link to="/vocab"><AppIcon name="vocab" :size="22" />单词</router-link>
          <router-link to="/practice"><AppIcon name="practice" :size="22" />练习</router-link>
          <router-link to="/wrongbook"><AppIcon name="wrong" :size="22" />错题</router-link>
          <router-link to="/knowledge"><AppIcon name="spark" :size="22" />知识</router-link>
        </nav>

      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.shell { min-height: 100vh; background: #f6f7fb; }
.shell.in-exam { background: #fff; }
.dark .shell, .in-exam { background: inherit; }
.topbar { position: sticky; top: 0; z-index: 20; background: var(--card); border-bottom: 1px solid var(--line); }
.topbar-inner { max-width: 1480px; margin: 0 auto; padding: 0 20px; min-height: 52px; display: flex; align-items: center; gap: 12px; position: relative; }
.brand, .right { flex-shrink: 0; }
.nav { min-width: 0; }
.nav a { white-space: nowrap; }
.u-name { max-width: 90px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.brand { display: flex; align-items: center; gap: 9px; font-weight: 700; font-size: 15px; }
.logo { width: 28px; height: 28px; border-radius: 7px; background: var(--blue); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.title { font-size: 15px; }
.nav { display: flex; gap: 2px; flex: 1; }
.nav a { padding: 8px 9px; border-radius: 6px; color: var(--t2); text-decoration: none; font-size: 14px; }
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

@media (max-width: 768px) {
  .nav { display: none; }
  .brand .title { display: none; }  /* 移动端只留 logo 徽标 */
  .chip-text { display: none; }  /* 倒计时只显示数字 */
  .right .ghost-btn { display: none; }  /* 退出在头像菜单里 */
  .right { margin-left: auto; gap: 10px; }  /* nav 隐藏后仍靠右 */
  .bar-title {
    display: block; position: absolute; left: 50%; transform: translateX(-50%);
    font-size: 15px; font-weight: 600; color: var(--t1); white-space: nowrap;
  }
  .shell:not(.in-exam) { padding-bottom: calc(58px + env(safe-area-inset-bottom)); }
  .tabbar {
    display: flex; position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
    background: rgba(255,255,255,.94); backdrop-filter: blur(12px);
    border-top: 1px solid var(--line); padding-bottom: env(safe-area-inset-bottom);
  }
  .tabbar a {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px;
    padding: 8px 0 6px; font-size: 12px; color: var(--t2); text-decoration: none;
    transition: color .15s;
  }
  .tabbar a.router-link-active { color: var(--blue); font-weight: 600; }
  .tabbar a.router-link-active svg { transform: translateY(-1px); }
}
.ghost-btn { border: none; background: transparent; cursor: pointer; padding: 6px 10px; border-radius: 8px; font-size: 13px; color: #575e72; }
.ghost-btn:hover { background: rgba(128,128,128,.1); }
.avatar-wrap { position: relative; }
.avatar-btn { display: flex; align-items: center; gap: 7px; border: none; background: transparent;
  cursor: pointer; color: var(--t2); font-size: 13px; padding: 4px; border-radius: 8px; }
.avatar-btn:hover { background: var(--card-hover); }
.avatar-menu {
  position: absolute; right: 0; top: calc(100% + 8px); z-index: 60;
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  box-shadow: var(--shadow-pop); min-width: 150px; overflow: hidden;
}
.av-item { display: flex; align-items: center; gap: 8px; width: 100%; border: none;
  background: transparent; cursor: pointer; padding: 11px 14px; font-size: 13.5px;
  color: var(--t1); text-align: left; }
.av-item:hover { background: var(--card-hover); }
.av-logout { color: var(--bad); }
</style>
