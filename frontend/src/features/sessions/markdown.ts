import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

export function renderMarkdown(md: string): string {
  const raw = marked.parse(md)
  if (typeof raw === 'string') return addCodeCopyButtons(DOMPurify.sanitize(raw))
  return ''
}

function addCodeCopyButtons(html: string): string {
  if (typeof document === 'undefined') return html
  const template = document.createElement('template')
  template.innerHTML = html
  template.content.querySelectorAll('pre').forEach((pre) => {
    const code = pre.querySelector('code')
    const text = code?.textContent || pre.textContent || ''
    if (!text.trim()) return
    if (pre.querySelector('[data-copy-code]')) return
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'markdown-code-copy'
    button.dataset.copyCode = text
    button.textContent = '复制'
    button.setAttribute('aria-label', '复制代码块')
    pre.prepend(button)
  })
  return template.innerHTML
}
