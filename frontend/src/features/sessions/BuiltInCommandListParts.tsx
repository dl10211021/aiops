import type { SlashCommand } from '@/types'
import { commandStableId, displayCommandLabel } from './slashCommands'

type CommandSortMode = 'custom' | 'builtin' | null

export function BuiltInCommandHeader({
  busy,
  overriddenBuiltinIds,
  sortMode,
  onBeginSort,
  onCancelSort,
  onRestoreMany,
  onSaveSort,
}: {
  busy: boolean
  overriddenBuiltinIds: string[]
  sortMode: CommandSortMode
  onBeginSort: () => void
  onCancelSort: () => void
  onRestoreMany: (commandIds: string[]) => void
  onSaveSort: () => void
}) {
  return (
    <div className="mb-2 flex items-center justify-between gap-2">
      <span className="text-sm font-semibold text-ops-text">内置命令模板</span>
      <div className="flex shrink-0 items-center gap-2">
        {sortMode === 'builtin' ? (
          <>
            <button onClick={onSaveSort} disabled={busy} className="rounded-md bg-ops-accent px-3 py-1.5 text-xs font-semibold text-ops-dark disabled:opacity-50">
              保存排序
            </button>
            <button onClick={onCancelSort} disabled={busy} className="rounded-md border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext hover:text-ops-text disabled:opacity-50">
              取消
            </button>
          </>
        ) : (
          <>
            <button onClick={onBeginSort} disabled={busy} className="rounded-md border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-text disabled:opacity-40">
              排序编辑
            </button>
            {overriddenBuiltinIds.length > 0 && (
              <button onClick={() => onRestoreMany(overriddenBuiltinIds)} disabled={busy} className="rounded-md border border-ops-alert/35 px-3 py-1.5 text-xs text-ops-alert hover:bg-ops-alert/10 disabled:opacity-40">
                全部恢复默认
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export function BuiltInSortHint() {
  return (
    <div className="mb-3 rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-xs leading-5 text-ops-subtext">
      按目标显示顺序点击模板，第一条就是 1，第二条就是 2；保存后会生成内置模板的排序覆盖配置。
    </div>
  )
}

export function BuiltInCommandCard({
  command,
  pickedOrder,
  sortMode,
  onCopy,
  onEdit,
  onRestore,
  onToggleSortPick,
  onView,
}: {
  command: SlashCommand
  pickedOrder: number
  sortMode: CommandSortMode
  onCopy: (command: SlashCommand) => void
  onEdit: (command: SlashCommand) => void
  onRestore: (commandId: string) => void
  onToggleSortPick: (command: SlashCommand) => void
  onView: (command: SlashCommand) => void
}) {
  const handleSelect = () => {
    if (sortMode === 'builtin') onToggleSortPick(command)
    else onView(command)
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleSelect}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          handleSelect()
        }
      }}
      className={`w-full rounded-lg border p-3 text-left transition-colors hover:border-ops-accent/45 ${pickedOrder > 0 ? 'border-ops-accent/55 bg-ops-accent/10' : 'border-ops-surface0 bg-ops-dark/30'}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-ops-text">{displayCommandLabel(command.label)}</span>
        <BuiltInCommandActions
          command={command}
          pickedOrder={pickedOrder}
          sortMode={sortMode}
          onCopy={onCopy}
          onEdit={onEdit}
          onRestore={onRestore}
        />
      </div>
      <div className="mt-1 line-clamp-2 text-xs text-ops-subtext">{command.description}</div>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-ops-overlay">
        <span>{command.category || '通用'}</span>
        <span>顺序 {command.sort_order || 1}</span>
        <span>{command.pinned ? '快捷栏' : '菜单'}</span>
        <span>{command.enabled === false ? '已停用' : '启用'}</span>
      </div>
    </div>
  )
}

function BuiltInCommandActions({
  command,
  pickedOrder,
  sortMode,
  onCopy,
  onEdit,
  onRestore,
}: {
  command: SlashCommand
  pickedOrder: number
  sortMode: CommandSortMode
  onCopy: (command: SlashCommand) => void
  onEdit: (command: SlashCommand) => void
  onRestore: (commandId: string) => void
}) {
  return (
    <div className="flex shrink-0 items-center gap-1">
      {sortMode === 'builtin' && (
        <span className={`rounded-full border px-2 py-0.5 text-[10px] ${pickedOrder > 0 ? 'border-ops-accent/45 text-ops-accent' : 'border-ops-surface1 text-ops-subtext'}`}>
          {pickedOrder > 0 ? `第 ${pickedOrder}` : '点击排序'}
        </span>
      )}
      {command.is_override && (
        <span className="rounded-full border border-ops-accent/35 px-2 py-0.5 text-[10px] text-ops-accent">
          已覆盖
        </span>
      )}
      {sortMode !== 'builtin' && (
        <>
          {command.is_override && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                onRestore(commandStableId(command))
              }}
              className="rounded-md border border-ops-alert/35 px-2 py-1 text-[11px] text-ops-alert hover:bg-ops-alert/10"
            >
              恢复默认
            </button>
          )}
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation()
              onEdit(command)
            }}
            className="rounded-md border border-ops-accent/35 px-2 py-1 text-[11px] text-ops-accent hover:bg-ops-accent/10"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation()
              onCopy(command)
            }}
            className="rounded-md border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext hover:text-ops-text"
          >
            复制
          </button>
        </>
      )}
    </div>
  )
}
