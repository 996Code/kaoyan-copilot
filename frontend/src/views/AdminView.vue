<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NCard, NInput, NSpin, NTabs, NTabPane, NTag, useDialog, useMessage,
} from 'naive-ui'
import { api } from '../api'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const users = ref([])
const stats = ref(null)

const llm = reactive({ llm_base_url: '', llm_model: '', llm_api_key: '' })
const llmState = ref({ llm_api_key_masked: '', llm_ready: false })
const savingLlm = ref(false)
const testing = ref(false)
const testResult = ref(null)

const isAdminLocal = localStorage.getItem('kaoyan_is_admin') === '1'
if (!isAdminLocal) {
  // 非管理员直接弹回首页（接口层还有 403 兜底）
  router.replace('/')
}

async function load() {
  loading.value = true
  try {
    const [u, s, cfg] = await Promise.all([
      api('/api/admin/users'),
      api('/api/admin/stats'),
      api('/api/admin/settings'),
    ])
    users.value = u
    stats.value = s
    llm.llm_base_url = cfg.llm_base_url
    llm.llm_model = cfg.llm_model
    llmState.value = cfg
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

async function saveLlm() {
  savingLlm.value = true
  try {
    llmState.value = await api('/api/admin/settings', { method: 'PUT', body: { ...llm } })
    llm.llm_api_key = ''
    message.success('已保存')
  } catch (e) {
    message.error(e.message)
  } finally {
    savingLlm.value = false
  }
}

async function testLlm() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await api('/api/admin/settings/test', { method: 'POST', body: {} })
  } catch (e) {
    testResult.value = { ok: false, error: e.message }
  } finally {
    testing.value = false
  }
}

function fmt(dt) {
  return dt ? String(dt).replace('T', ' ').slice(0, 16) : '—'
}

function resetPassword(u) {
  dialog.warning({
    title: `重置 ${u.username} 的密码`,
    content: '输入新密码（至少 4 位）',
    positiveText: '重置',
    negativeText: '取消',
    onPositiveClick: async () => {
      // naive-ui dialog 无输入框，这里用 prompt 简化（内部工具可用）
      const pwd = window.prompt(`给 ${u.username} 设置新密码（至少 4 位）`)
      if (!pwd || pwd.length < 4) return
      try {
        await api(`/api/admin/users/${u.id}/reset_password`, {
          method: 'POST', body: { password: pwd },
        })
        message.success(`已重置 ${u.username} 的密码`)
      } catch (e) {
        message.error(e.message)
      }
    },
  })
}

function removeUser(u) {
  dialog.warning({
    title: `删除用户 ${u.username}？`,
    content: `将级联删除其全部数据：${u.exams} 场模考、${u.answers} 条作答、${u.cards} 张记忆卡、${u.wrong_active} 条错题。此操作不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api(`/api/admin/users/${u.id}`, { method: 'DELETE' })
        message.success(`已删除 ${u.username} 及其全部数据`)
        load()
      } catch (e) {
        message.error(e.message)
      }
    },
  })
}

const statCards = computed(() => {
  if (!stats.value) return []
  return [
    { label: '用户', value: stats.value.users },
    { label: '真题试卷', value: `${stats.value.papers} 套` },
    { label: '题目', value: stats.value.questions },
    { label: '词汇', value: stats.value.words },
    { label: '已交模考', value: stats.value.exams_submitted },
    { label: '作答记录', value: stats.value.answers },
    { label: '记忆卡', value: stats.value.review_cards },
    { label: 'AI 缓存', value: stats.value.ai_cache },
  ]
})

onMounted(load)
</script>

<template>
  <div class="page">
    <h2 class="page-h2" style="margin:18px 0 14px">系统管理 <n-tag :type="llmState.llm_ready ? 'success' : 'error'" size="small">LLM {{ llmState.llm_ready ? '已就绪' : '未配置' }}</n-tag></h2>

    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0"><n-spin size="large" /></div>

    <n-tabs v-else type="line" animated>
      <!-- 用户管理 -->
      <n-tab-pane name="users" tab="用户管理">
        <n-card :bordered="false" style="border-radius:12px">
          <div class="tbl head">
            <span>用户</span><span>注册</span><span>模考</span><span>作答</span><span>正确率</span>
            <span>待巩固</span><span>记忆卡</span><span>已学词</span><span>最近活跃</span><span>操作</span>
          </div>
          <div v-for="u in users" :key="u.id" class="tbl row">
            <span>
              <b>{{ u.username }}</b>
              <n-tag v-if="u.is_admin" type="info" size="tiny" style="margin-left:4px">管理员</n-tag>
            </span>
            <span class="muted">{{ fmt(u.created_at) }}</span>
            <span>{{ u.exams }}</span>
            <span>{{ u.answers }}</span>
            <span :style="u.accuracy != null && u.accuracy < 60 ? 'color:var(--bad)' : ''">
              {{ u.accuracy != null ? u.accuracy + '%' : '—' }}
            </span>
            <span>{{ u.wrong_active }}</span>
            <span>{{ u.cards }}</span>
            <span>{{ u.words_learned }}</span>
            <span class="muted">{{ fmt(u.last_active) }}</span>
            <span class="ops">
              <n-button size="small" @click="resetPassword(u)">重置密码</n-button>
              <n-button size="small" type="error" ghost :disabled="u.is_admin" @click="removeUser(u)">删除</n-button>
            </span>
          </div>
        </n-card>
        <p class="muted" style="font-size:12.5px; margin-top:8px">
          数据口径：模考=已交卷场次；作答=有判分结果的客观题；待巩固=错题本未消灭条目；记忆卡=FSRS 卡片（错题+单词）。
          删除用户会级联清理其全部个人数据，题库与试卷等公共数据不受影响。
        </p>
      </n-tab-pane>

      <!-- LLM 配置 -->
      <n-tab-pane name="llm" tab="LLM 配置">
        <n-card :bordered="false" style="border-radius:12px; max-width:640px">
          <div class="form-row">
            <label>接口地址（OpenAI 兼容）</label>
            <n-input v-model:value="llm.llm_base_url" placeholder="https://your-gateway/v1" />
          </div>
          <div class="form-row">
            <label>API Key
              <span class="muted" style="font-size:12px">当前：{{ llmState.llm_api_key_masked || '未设置' }}，留空表示不修改</span>
            </label>
            <n-input v-model:value="llm.llm_api_key" type="password" show-password-on="click" placeholder="sk-..." />
          </div>
          <div class="form-row">
            <label>模型名</label>
            <n-input v-model:value="llm.llm_model" placeholder="qwen3.7-plus / gpt-4o-mini / ..." />
          </div>
          <div style="display:flex; gap:10px; margin-top:16px">
            <n-button type="primary" :loading="savingLlm" @click="saveLlm">保存配置</n-button>
            <n-button :loading="testing" @click="testLlm">测试连接</n-button>
          </div>
          <div v-if="testResult" class="test-result" :class="testResult.ok ? 'ok' : 'bad'">
            <template v-if="testResult.ok">
              ✓ 连接成功 · 延迟 {{ testResult.latency_ms }}ms · 模型回复「{{ testResult.reply }}」
            </template>
            <template v-else>✗ {{ testResult.error }}</template>
          </div>
          <p class="muted" style="font-size:12.5px; margin-top:10px">
            保存后立即生效（无需重启）。AI 讲解与主观题批改都走这套配置；讲解结果按题目缓存，多用户共享不重复计费。
          </p>
        </n-card>
      </n-tab-pane>

      <!-- 系统统计 -->
      <n-tab-pane name="stats" tab="系统统计">
        <div class="stat-grid">
          <n-card v-for="c in statCards" :key="c.label" :bordered="false" class="stat-card">
            <div class="sc-label">{{ c.label }}</div>
            <div class="sc-value">{{ c.value }}</div>
          </n-card>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style scoped>
.tbl { display: grid; grid-template-columns: 1.3fr 1.2fr .5fr .6fr .7fr .7fr .7fr .7fr 1.2fr 1.3fr;
  gap: 6px; align-items: center; font-size: 13px; padding: 7px 4px; }
.tbl.head { color: var(--t3); font-size: 12px; border-bottom: 1px solid var(--line); }
.tbl.row { border-bottom: 1px dashed var(--line-soft); }
.tbl.row:last-child { border-bottom: none; }
.ops { display: flex; gap: 6px; }
.form-row { margin-bottom: 14px; display: flex; flex-direction: column; gap: 6px; }
.form-row label { font-size: 13px; color: var(--t2); font-weight: 600; }
.test-result { margin-top: 12px; padding: 10px 14px; border-radius: 8px; font-size: 13.5px; }
.test-result.ok { background: rgba(24,160,88,.08); color: var(--ok); }
.test-result.bad { background: rgba(208,48,80,.07); color: var(--bad); }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.stat-card { border-radius: 12px; text-align: center; }
.sc-label { font-size: 12.5px; color: var(--t3); }
.sc-value { font-size: 26px; font-weight: 800; color: var(--blue); font-variant-numeric: tabular-nums; }
@media (max-width: 768px) {
  .tbl { grid-template-columns: repeat(2, 1fr); font-size: 12.5px; }
  .tbl.head { display: none; }
}
</style>
