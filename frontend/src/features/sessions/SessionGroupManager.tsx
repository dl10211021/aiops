import type { Session } from '@/types'

interface SessionGroupManagerProps {
  currentSession: Session | null
  groupDraft: string
  selectedGroup: string
  onDraftChange: (value: string) => void
  onCreateGroup: () => void
  onRenameGroup: () => void
  onDeleteGroup: () => void
  onMoveCurrentSession: () => void
}

export default function SessionGroupManager({
  currentSession,
  groupDraft,
  selectedGroup,
  onDraftChange,
  onCreateGroup,
  onRenameGroup,
  onDeleteGroup,
  onMoveCurrentSession,
}: SessionGroupManagerProps) {
  return (
    <div className="mt-4 rounded-lg border border-ops-surface0 bg-ops-dark/30 p-2.5">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold text-ops-overlay">会话组管理</span>
        <span className="truncate text-[11px] text-ops-subtext" title={selectedGroup}>
          当前：{selectedGroup}
        </span>
      </div>
      <div className="flex gap-1.5">
        <input
          value={groupDraft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onCreateGroup()
          }}
          className="min-w-0 flex-1 rounded-md border border-ops-surface1 bg-ops-panel px-2 py-1.5 text-xs text-ops-text outline-none focus:border-ops-accent"
          placeholder="新建或重命名"
          aria-label="会话组名称"
        />
        <button onClick={onCreateGroup} className="rounded-md border border-ops-surface1 px-2 text-xs font-semibold text-ops-subtext hover:border-ops-accent hover:text-ops-text" title="新建组">
          +
        </button>
        <button onClick={onRenameGroup} className="rounded-md border border-ops-surface1 px-2 text-xs font-semibold text-ops-subtext hover:border-ops-accent hover:text-ops-text" title="重命名选中组">
          改
        </button>
        <button onClick={onDeleteGroup} className="rounded-md border border-ops-alert/40 px-2 text-xs font-semibold text-ops-alert hover:bg-ops-alert/10" title="删除选中组">
          删
        </button>
      </div>
      <button
        onClick={onMoveCurrentSession}
        disabled={!currentSession}
        className="mt-2 h-8 w-full rounded-md border border-ops-surface1 bg-ops-surface0/45 text-xs font-semibold text-ops-subtext transition-colors hover:border-ops-accent hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-45"
      >
        移动当前会话到选中组
      </button>
    </div>
  )
}
