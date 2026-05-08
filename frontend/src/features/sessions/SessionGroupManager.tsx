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
    <div className="mt-2">
      <div className="grid grid-cols-[minmax(0,1fr)_48px] gap-1.5 rounded-xl border border-ops-surface1/65 bg-ops-dark/32 p-1.5">
        <input
          value={groupDraft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onCreateGroup()
          }}
          className="h-8 min-w-0 rounded-lg border border-transparent bg-transparent px-2 text-xs text-ops-text outline-none transition-colors placeholder:text-ops-overlay focus:border-ops-accent/55 focus:bg-ops-panel/55"
          placeholder="新建会话组，回车创建"
          aria-label="新建会话组名称"
        />
        <button
          onClick={onCreateGroup}
          className="h-8 rounded-lg border border-ops-surface1/75 bg-ops-panel/55 text-xs font-semibold text-ops-subtext transition-colors hover:border-ops-accent/55 hover:text-ops-text"
          title="创建会话组"
        >
          创建
        </button>
      </div>
    </div>
  )
}
