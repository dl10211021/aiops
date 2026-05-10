import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

const markdownCache = new Map<string, string>()
const MARKDOWN_CACHE_LIMIT = 80
const MARKDOWN_CACHE_MAX_SOURCE_CHARS = 60_000

export function renderMarkdown(md: string): string {
  const cached = markdownCache.get(md)
  if (cached !== undefined) return cached
  const raw = marked.parse(md)
  if (typeof raw === 'string') {
    const rendered = addCodeCopyButtons(DOMPurify.sanitize(raw))
    if (md.length <= MARKDOWN_CACHE_MAX_SOURCE_CHARS) {
      markdownCache.set(md, rendered)
      if (markdownCache.size > MARKDOWN_CACHE_LIMIT) {
        const oldest = markdownCache.keys().next().value
        if (oldest !== undefined) markdownCache.delete(oldest)
      }
    }
    return rendered
  }
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
