interface SessionGroupManagerProps {
  groupDraft: string
  onDraftChange: (value: string) => void
  onCreateGroup: () => void
}

export default function SessionGroupManager({
  groupDraft,
  onDraftChange,
  onCreateGroup,
}: SessionGroupManagerProps) {
  return (
    <div className="mt-3 rounded-lg border border-ops-surface1/70 bg-ops-panel p-2.5">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold text-ops-overlay">新建会话组</span>
        <span className="text-[11px] text-ops-subtext">回车创建</span>
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_56px] gap-1.5">
        <input
          value={groupDraft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onCreateGroup()
          }}
          className="min-w-0 rounded-md border border-ops-surface1 bg-ops-dark/35 px-2.5 py-1.5 text-xs text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent"
          placeholder="例如：生产数据库、网络设备"
          aria-label="新建会话组名称"
        />
        <button
          onClick={onCreateGroup}
          className="rounded-md border border-ops-surface1 bg-ops-surface0/60 text-xs font-semibold text-ops-subtext transition-colors hover:border-ops-accent hover:text-ops-text"
          title="创建会话组"
        >
          创建
        </button>
      </div>
    </div>
  )
}
