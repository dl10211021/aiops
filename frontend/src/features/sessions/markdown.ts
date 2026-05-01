import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

export function renderMarkdown(md: string): string {
  const raw = marked.parse(md)
  if (typeof raw === 'string') return DOMPurify.sanitize(raw)
  return ''
}
