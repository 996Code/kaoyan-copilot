<script setup>
import { ref } from 'vue'
import { NButton, NInput } from 'naive-ui'
import { api, setToken } from '../api'

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const mode = ref('login') // login | register

async function submit() {
  if (!username.value || !password.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await api(`/api/auth/${mode.value}`, {
      method: 'POST',
      body: { username: username.value.trim(), password: password.value },
    })
    setToken(data.token)
    localStorage.setItem('kaoyan_username', data.username)
    localStorage.setItem('kaoyan_is_admin', data.is_admin ? '1' : '0')
    location.hash = '#/'
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-left">
      <div class="slogan">
        <div class="big-num">40<span>天</span></div>
        <h1>过线，就够了</h1>
        <p>199 管综 + 英语二 · 真题模考 · FSRS 记忆复习 · AI 讲解批改</p>
      </div>
      <div class="features">
        <div class="feat"><b>📝</b><div>34 套真题整卷<br />限时模考自动判分</div></div>
        <div class="feat"><b>🔁</b><div>FSRS 记忆引擎<br />答错自动进复习队列</div></div>
        <div class="feat"><b>✨</b><div>AI 讲解与作文批改<br />按阅卷标准从紧给分</div></div>
      </div>
    </div>

    <div class="login-card">
      <div class="login-head">
        <div class="logo">考</div>
        <h2>考研助手</h2>
      </div>
      <n-input v-model:value="username" placeholder="用户名" size="large" @keyup.enter="submit" />
      <n-input v-model:value="password" type="password" show-password-on="click"
        placeholder="密码" size="large" style="margin-top:10px" @keyup.enter="submit" />
      <div v-if="error" class="error">{{ error }}</div>
      <n-button type="primary" block size="large" style="margin-top:14px" :loading="loading" @click="submit">
        {{ mode === 'login' ? '进入' : '注册并进入' }}
      </n-button>
      <div class="switch-mode">
        <span v-if="mode === 'login'">
          没有账号？<a @click="mode = 'register'">注册一个</a>
        </span>
        <span v-else>
          已有账号？<a @click="mode = 'login'">直接登录</a>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh; display: flex; align-items: center; justify-content: center; gap: 72px;
  background:
    radial-gradient(1200px 600px at 15% -10%, rgba(106,92,255,.16), transparent 60%),
    radial-gradient(900px 500px at 110% 110%, rgba(47,111,237,.14), transparent 55%),
    linear-gradient(160deg, #f8faff 0%, #eef1f9 100%);
  padding: 24px;
}
.login-left { max-width: 460px; }
.big-num { font-size: 88px; font-weight: 900; line-height: 1; color: var(--blue);
  letter-spacing: -2px; }
.big-num span { font-size: 24px; margin-left: 6px; color: var(--t3); font-weight: 600; }
.slogan h1 { margin: 10px 0 8px; font-size: 34px; letter-spacing: 1px; }
.slogan p { margin: 0; color: var(--t3); font-size: 14.5px; }
.features { display: flex; gap: 14px; margin-top: 34px; }
.feat {
  flex: 1; background: rgba(255,255,255,.75); backdrop-filter: blur(6px);
  border: 1px solid rgba(47,111,237,.14); border-radius: 14px; padding: 14px;
  font-size: 12.5px; color: var(--t2); line-height: 1.65;
}
.feat b { font-size: 22px; display: block; margin-bottom: 6px; }
.login-card { width: min(360px, calc(100vw - 36px)); border-radius: 18px;
  box-shadow: 0 16px 48px rgba(30,41,80,.12); background: #fff; padding: 30px 28px;
  border: 1px solid var(--line-soft); }
.login-head { text-align: center; margin-bottom: 18px; }
.logo { width: 48px; height: 48px; margin: 0 auto 8px; border-radius: 14px; background: var(--blue);
  color: #fff; font-size: 24px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
h2 { margin: 4px 0; }
.error { color: var(--bad); font-size: 13px; margin-top: 10px; text-align: center; }
.switch-mode { text-align: center; margin-top: 14px; font-size: 13px; color: var(--t3); }
.switch-mode a { color: var(--blue); cursor: pointer; }

@media (max-width: 860px) {
  /* 移动端：登录卡在上首屏直达，品牌介绍收为页脚 */
  .login-wrap { flex-direction: column; gap: 20px; padding: 28px 20px; justify-content: center; }
  .login-card { order: 0; box-shadow: 0 8px 28px rgba(30,41,80,.10); }
  .login-left { order: 1; max-width: 360px; text-align: center; }
  .big-num { font-size: 40px; }
  .slogan h1 { font-size: 20px; margin: 6px 0 4px; }
  .slogan p { font-size: 12.5px; }
  .features { flex-direction: row; gap: 8px; margin-top: 14px; }
  .feat { flex: 1; flex-direction: column; text-align: center; padding: 10px 6px; font-size: 11px; gap: 4px; }
  .feat b { margin: 0; font-size: 18px; }
}
</style>
