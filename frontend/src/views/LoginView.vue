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
    <div class="login-card">
      <div class="login-head">
        <div class="logo">考</div>
        <h2>考研助手</h2>
        <p class="muted">199 管综 + 英语二 · 40 天冲刺</p>
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
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f6f7fb 60%); }
.login-card { width: 360px; border-radius: 16px; box-shadow: 0 10px 40px rgba(30,41,80,.08);
  background: #fff; padding: 28px; border: 1px solid #eef0f6; }
.login-head { text-align: center; margin-bottom: 18px; }
.logo { width: 44px; height: 44px; margin: 0 auto 8px; border-radius: 12px; background: #2f6fed;
  color: #fff; font-size: 22px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
h2 { margin: 4px 0; }
.error { color: #d03050; font-size: 13px; margin-top: 10px; text-align: center; }
.switch-mode { text-align: center; margin-top: 14px; font-size: 13px; color: #8b93a7; }
.switch-mode a { color: #2f6fed; cursor: pointer; }
</style>
