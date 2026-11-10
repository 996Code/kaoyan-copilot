import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import { computed, reactive, ref, nextTick, watch } from 'vue'
import { parse } from '@vue/compiler-sfc'

function setupView(file, api = async () => ({})) {
  const source = readFileSync(new URL(file, import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const script = descriptor.scriptSetup.content.replace(/^import[\s\S]*?from ['"][^'"]+['"]\s*$/gm, '')
  const mounted = []
  const context = vm.createContext({
    computed, reactive, ref, watch, api,
    onMounted: (fn) => mounted.push(fn),
    defineProps: () => ({ examId: '1' }),
    useRouter: () => ({ replace() {} }),
    useMessage: () => ({ success() {}, error() {} }),
    useDialog: () => ({ warning() {}, error() {} }),
    localStorage: { getItem: () => '1' },
    window: { innerWidth: 375, scrollTo() {} },
  })
  vm.runInContext(script, context)
  return { run: (code) => vm.runInContext(code, context), mounted, source }
}

test('History uses the subject endpoint, not abbreviations in the paper name', async () => {
  const view = setupView('HistoryView.vue', async (path) => {
    if (path.endsWith('history')) return []
    if (path.endsWith('gz199')) return [{ id: 10, year: 2025, name: '管理类专业学位联考综合能力' }]
    return [{ id: 20, year: 2025, name: '英语（二）' }]
  })
  await view.mounted[0]()
  assert.equal(view.run('subjectName(10)'), '管综')
  assert.equal(view.run('subjectName(20)'), '英二')
  assert.equal(view.run('subjectName(999)'), '科目待确认')
})

test('Report unanswered filter matches its objective-only count and preserves real numbers', async () => {
  const view = setupView('ReportView.vue')
  view.run(`
    paper.value = { sections: [{ id: 1, name: '长分区名称', blocks: [
      { kind: 'question', question: { id: 101, number: 21, qtype: 'single_choice' } },
      { kind: 'question', question: { id: 102, number: 56, qtype: 'essay' } },
      { kind: 'question', question: { id: 103, number: 42, qtype: 'single_choice' } }
    ] }] };
    results.value = { 101: { your_answer: null }, 102: { your_answer: null }, 103: { your_answer: 'B', is_correct: false } };
    filter.value = 'unanswered';
  `)
  await nextTick()
  assert.equal(view.run('filtered.value.length'), view.run('counts.value.unanswered'))
  assert.equal(view.run('filtered.value[0].q.number'), 21)
  view.run("filter.value = 'all'; idx.value = 2; showNav.value = true; filter.value = 'wrong'")
  await nextTick()
  assert.equal(view.run('idx.value'), 0)
  assert.equal(view.run('showNav.value'), false)
  assert.equal(view.run('currentItem.value.q.number'), 42)
  view.run('goto(999)')
  assert.equal(view.run('idx.value'), 0)
})

test('Admin validates passwords and keeps modal open on a failed mocked reset', async () => {
  const requests = []
  const view = setupView('AdminView.vue', async (path, options) => {
    requests.push({ path, options })
    throw new Error('测试请求失败')
  })
  view.run("resetPassword({ id: 999, username: '测试用户' })")
  assert.equal(view.run('resetModalOpen.value'), true)
  view.run("resetForm.password = '123'; resetForm.confirmPassword = '123'")
  await view.run('submitResetPassword()')
  assert.equal(requests.length, 0)
  assert.match(view.run('resetError.value'), /4/)
  view.run("resetForm.password = 'abcd'; resetForm.confirmPassword = 'different'")
  await view.run('submitResetPassword()')
  assert.equal(requests.length, 0)
  view.run("resetForm.confirmPassword = 'abcd'")
  await view.run('submitResetPassword()')
  assert.equal(requests.length, 1)
  assert.equal(view.run('resetModalOpen.value'), true)
  assert.equal(view.run('resetSaving.value'), false)
  assert.match(view.run('resetError.value'), /测试请求失败/)
})

test('Admin prevents duplicate submissions and clears passwords after mocked success', async () => {
  let finish
  let requests = 0
  const view = setupView('AdminView.vue', () => {
    requests += 1
    return new Promise((resolve) => { finish = resolve })
  })
  view.run("resetPassword({ id: 999, username: '测试用户' }); resetForm.password = 'abcd'; resetForm.confirmPassword = 'abcd'")
  const pending = view.run('submitResetPassword()')
  assert.equal(view.run('resetSaving.value'), true)
  view.run('closeResetModal()')
  assert.equal(view.run('resetModalOpen.value'), true)
  await view.run('submitResetPassword()')
  assert.equal(requests, 1)
  finish({ ok: true })
  await pending
  assert.equal(view.run('resetSaving.value'), false)
  assert.equal(view.run('resetModalOpen.value'), false)
  assert.equal(view.run('resetForm.password'), '')
  assert.equal(view.run('resetForm.confirmPassword'), '')
})
