import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const md = new MarkdownIt({ html: true, linkify: false, typographer: false })

/** markdown + 行内/块级 LaTeX 公式 -> HTML（公式先占位再渲染，避免下划线等被 md 吞掉） */
export function renderRich(text) {
  if (!text) return ''
  const math = []
  const stash = (tex, display) => {
    try {
      math.push(katex.renderToString(tex, { displayMode: display, throwOnError: false }))
    } catch {
      math.push(`<code>${tex}</code>`)
    }
    return `@@MATH${math.length - 1}@@`
  }
  let s = String(text)
  s = s.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => stash(tex, true))
  s = s.replace(/\$([^$\n]+?)\$/g, (_, tex) => stash(tex, false))
  let html = md.render(s)
  html = html.replace(/@@MATH(\d+)@@/g, (_, i) => math[Number(i)])
  return html
}

/** 完形语段：把 {{n}} 占位替换为高亮空位标记 */
export function splitCloze(material) {
  if (!material) return []
  return material.split(/(\{\{\d+\}\})/)
}
export function isClozeBlank(seg) {
  return /^\{\{(\d+)\}\}$/.test(seg)
}
export function clozeNum(seg) {
  const m = seg.match(/^{{(\d+)}}$/)
  return m ? Number(m[1]) : null
}
