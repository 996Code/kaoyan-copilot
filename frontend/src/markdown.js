import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const md = new MarkdownIt({ html: false, linkify: false, typographer: false })

/**
 * SVG 安全提取：题目数据里的 <svg>...</svg>（管综几何图形）。
 * 仅放行 svg 标签（黑名单剔除 script/事件属性/外部引用），其余 HTML 依旧被 md 转义为文本。
 */
function extractSvgs(text) {
  const out = { text, svgs: [] }
  const re = /<svg[\s\S]*?<\/svg>/gi
  out.text = String(text).replace(re, (m) => {
    // 安全校验：拒绝 script、事件属性、外部引用
    if (/<script|on\w+\s*=|xlink:href\s*=\s*["']?(?!#)|href\s*=\s*["']?http/i.test(m)) {
      return '[不安全的图形已屏蔽]'
    }
    m = m.replace(/\s(on\w+|script)\s*=/gi, ' data-blocked=')
    out.svgs.push(m)
    return `\n@@SVG${out.svgs.length - 1}@@\n`
  })
  return out
}

/** markdown + 行内/块级 LaTeX 公式 -> HTML（公式先占位再渲染，避免下划线等被 md 吞掉） */
export function renderRich(text) {
  if (!text) return ''
  const svgCtx = extractSvgs(text)
  text = svgCtx.text
  const math = []
  const stash = (tex, display) => {
    try {
      math.push(katex.renderToString(tex, { displayMode: display, throwOnError: false }))
    } catch {
      math.push(`<code>${md.utils.escapeHtml(tex)}</code>`)
    }
    return `@@MATH${math.length - 1}@@`
  }
  let s = String(text)
  s = s.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => stash(tex, true))
  s = s.replace(/\$([^$\n]+?)\$/g, (_, tex) => stash(tex, false))
  let html = md.render(s)
  html = html.replace(/@@MATH(\d+)@@/g, (_, i) => math[Number(i)])
  // SVG 回填（原样输出已 sanitize 的图形）
  html = html.replace(/@@SVG(\d+)@@/g, (_, i) => svgCtx.svgs[Number(i)] || '')
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
