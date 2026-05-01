export const ACCEPTED_KNOWLEDGE_EXTENSIONS = ['.txt', '.md', '.pdf', '.doc', '.docx', '.log']
export const ACCEPTED_KNOWLEDGE_TYPES = ACCEPTED_KNOWLEDGE_EXTENSIONS.join(',')

export function isAcceptedKnowledgeFile(filename: string) {
  const lower = filename.toLowerCase()
  return ACCEPTED_KNOWLEDGE_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

export function knowledgeFileKind(name: string) {
  const lower = name.toLowerCase()
  if (lower.endsWith('.pdf')) return { label: 'PDF', className: 'border-ops-alert/35 text-ops-alert' }
  if (lower.endsWith('.md')) return { label: 'MD', className: 'border-ops-accent/35 text-ops-accent' }
  if (lower.endsWith('.txt')) return { label: 'TXT', className: 'border-ops-surface1 text-ops-subtext' }
  if (lower.endsWith('.docx') || lower.endsWith('.doc')) return { label: 'DOC', className: 'border-ops-success/35 text-ops-success' }
  if (lower.endsWith('.log')) return { label: 'LOG', className: 'border-ops-accent/35 text-ops-accent' }
  return { label: 'FILE', className: 'border-ops-surface1 text-ops-subtext' }
}
