import DOMPurify from 'dompurify'
import katex from 'katex'
import mermaid from 'mermaid'
import { marked } from 'marked'

import 'katex/dist/katex.min.css'

mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'dark',
})

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const renderer = new marked.Renderer()

renderer.table = function (header, body) {
  return `<div class="table-wrapper"><table><thead>${header}</thead><tbody>${body}</tbody></table></div>`
}

renderer.code = function (code, infoString) {
  const language = (infoString || '').trim().split(/\s+/)[0]
  if (language === 'mermaid') {
    return `<pre class="mermaid">${escapeHtml(code)}</pre>`
  }
  const langAttr = language ? ` class="language-${escapeHtml(language)}"` : ''
  return `<pre><code${langAttr}>${escapeHtml(code)}</code></pre>`
}

marked.setOptions({
  breaks: true,
  gfm: true,
  renderer,
})

export function renderMarkdown(value, { enableMermaid = true } = {}) {
  if (!value) return ''

  const mathBlocks = []
  const mathInline = []
  let text = String(value)

  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
    const index = mathBlocks.length
    mathBlocks.push(formula.trim())
    return `@@MATHBLOCK${index}@@`
  })

  text = text.replace(/\$(.+?)\$/g, (_, formula) => {
    const index = mathInline.length
    mathInline.push(formula.trim())
    return `@@MATHINLINE${index}@@`
  })

  let html = marked.parse(text)

  html = html.replace(/@@MATHBLOCK(\d+)@@/g, (_, index) => {
    try {
      return katex.renderToString(mathBlocks[index], { displayMode: true, throwOnError: false })
    } catch {
      return `<pre>${escapeHtml(mathBlocks[index])}</pre>`
    }
  })

  html = html.replace(/@@MATHINLINE(\d+)@@/g, (_, index) => {
    try {
      return katex.renderToString(mathInline[index], { displayMode: false, throwOnError: false })
    } catch {
      return `<code>${escapeHtml(mathInline[index])}</code>`
    }
  })

  if (!enableMermaid) {
    html = html.replace(/<pre class="mermaid">([\s\S]*?)<\/pre>/g, '<pre><code class="language-mermaid">$1</code></pre>')
  }

  return DOMPurify.sanitize(html, {
    ADD_TAGS: ['annotation', 'math', 'mfrac', 'mi', 'mn', 'mo', 'mrow', 'msup', 'semantics'],
  })
}

export async function initializeMermaid(container) {
  if (!container) return
  const nodes = container.querySelectorAll('.mermaid:not([data-processed="true"])')
  if (!nodes.length) return

  for (const node of nodes) {
    const source = node.textContent || ''
    try {
      await mermaid.parse(source)
      await mermaid.run({ nodes: [node], suppressErrors: true })
    } catch (error) {
      console.warn('Mermaid render failed:', error)
      showMermaidFallback(node, source)
    }
  }
}

function showMermaidFallback(node, source) {
  const wrapper = document.createElement('div')
  wrapper.className = 'mermaid-fallback'

  const notice = document.createElement('div')
  notice.className = 'mermaid-fallback-notice'
  notice.textContent = '流程图语法无法解析，已保留原始内容'

  const pre = document.createElement('pre')
  const code = document.createElement('code')
  code.className = 'language-mermaid'
  code.textContent = source
  pre.appendChild(code)

  wrapper.appendChild(notice)
  wrapper.appendChild(pre)
  if (node.isConnected) {
    node.replaceWith(wrapper)
  }
}
