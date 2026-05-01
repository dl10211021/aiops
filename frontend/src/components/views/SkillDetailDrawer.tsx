import DOMPurify from 'dompurify'
import { marked } from 'marked'
import type { SkillInfo } from '@/types'

export function SkillDetailDrawer({
  content,
  skill,
  onClose,
}: {
  content: string
  skill: SkillInfo
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex justify-end" onClick={onClose}>
      <div className="h-full w-[min(720px,92vw)] overflow-y-auto border-l border-ops-surface1 bg-ops-panel p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">{skill.name || skill.id}</h2>
          <button onClick={onClose} className="rounded-lg bg-ops-surface0 px-3 py-1.5 text-sm text-ops-subtext hover:text-ops-text">关闭</button>
        </div>
        <div
          className="markdown-body text-sm"
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(
              typeof marked.parse(content) === 'string'
                ? marked.parse(content) as string
                : ''
            ),
          }}
        />
      </div>
    </div>
  )
}
