import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import { parse } from '@vue/compiler-sfc'

test('image preview ignores navigation icons and opens only question graphics', () => {
  const source = readFileSync(new URL('./Lightbox.vue', import.meta.url), 'utf8')
  const { descriptor } = parse(source)
  const script = descriptor.scriptSetup.content.replace(/^import[^\n]+$/gm, '')
  const holder = { innerHTML: '', children: [], appendChild(node) { this.children.push(node) } }
  class Element {
    constructor(matches = {}) { this.matches = matches }
    closest(selector) { return this.matches[selector] || null }
  }
  const context = vm.createContext({
    Element,
    ref: (value) => ({ value }),
    onMounted() {},
    onBeforeUnmount() {},
    nextTick: (fn) => fn(),
  })
  vm.runInContext(script, context)
  context.holder = holder
  vm.runInContext('stageRef.value = holder', context)
  const click = (matches) => {
    const event = { target: new Element(matches), preventDefault() {}, stopPropagation() {} }
    context.event = event
    vm.runInContext('onClick(event)', context)
  }
  click({ svg: {} })
  assert.equal(vm.runInContext('visible.value', context), false)
  click({ 'button, a, .opt-row, nav': {} })
  assert.equal(vm.runInContext('visible.value', context), false)
  const clone = { removeAttribute() {}, setAttribute() {} }
  click({ '.rich svg': { cloneNode: () => clone } })
  assert.equal(vm.runInContext('visible.value', context), true)
  assert.equal(holder.children[0], clone)
})
