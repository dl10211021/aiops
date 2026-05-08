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
    <div className="fixed inset-0 z-40 flex justify-end bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="ops-modal-surface h-full w-[min(720px,92vw)] overflow-y-auto rounded-none border-l border-ops-surface1 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-ops-text">{skill.name || skill.id}</h2>
          <button onClick={onClose} className="ops-muted-action px-3 py-1.5 text-sm">关闭</button>
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
