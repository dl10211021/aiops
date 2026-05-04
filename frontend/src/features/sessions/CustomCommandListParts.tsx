import type { Session, SlashCommand } from '@/types'
import { commandStableId, displayCommandLabel, scopeLabel } from './slashCommands'

type CommandSortMode = 'custom' | 'builtin' | null

export function CustomCommandListHeader({
  busy,
  sortMode,
  userCommandCount,
  onBeginSort,
  onCancelSort,
  onNew,
  onSaveSort,
}: {
  busy: boolean
  sortMode: CommandSortMode
  userCommandCount: number
  onBeginSort: () => void
  onCancelSort: () => void
  onNew: () => void
  onSaveSort: () => void
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2">
      <span className="text-sm font-semibold text-ops-text">自定义命令</span>
      <div className="flex shrink-0 items-center gap-2">
        {sortMode === 'custom' ? (
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
            <button onClick={onBeginSort} disabled={userCommandCount === 0 || busy} className="rounded-md border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext hover:border-ops-accent/45 hover:text-ops-text disabled:opacity-40">
              排序编辑
            </button>
            <button onClick={onNew} className="rounded-md border border-ops-accent/45 px-3 py-1.5 text-xs text-ops-accent hover:bg-ops-accent/10">
              新增
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export function CustomSortHint() {
  return (
    <div className="mb-3 rounded-lg border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-xs leading-5 text-ops-subtext">
      按目标显示顺序点击命令，第一条就是 1，第二条就是 2；未点击的命令会按当前顺序接在后面。
    </div>
  )
}

export function CustomCommandEmptyState({ session }: { session: Session | null }) {
  return (
    <div className="rounded-lg border border-dashed border-ops-surface1 p-4 text-sm text-ops-subtext">
      还没有自定义命令。可以先为当前 {session?.asset_type || '系统'} 建一个常用排查入口。
    </div>
  )
}

export function CustomCommandCard({
  command,
  pickedOrder,
  sortMode,
  onEdit,
  onToggleSortPick,
}: {
  command: SlashCommand
  pickedOrder: number
  sortMode: CommandSortMode
  onEdit: (command: SlashCommand) => void
  onToggleSortPick: (command: SlashCommand) => void
}) {
  return (
    <button
      key={command.id}
      type="button"
      onClick={() => sortMode === 'custom' ? onToggleSortPick(command) : onEdit(command)}
      className={`w-full rounded-lg border p-3 text-left transition-colors hover:border-ops-accent/45 ${pickedOrder > 0 ? 'border-ops-accent/55 bg-ops-accent/10' : 'border-ops-surface0 bg-ops-dark/45'}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-ops-text">{displayCommandLabel(command.label)}</span>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] ${pickedOrder > 0 ? 'border-ops-accent/45 text-ops-accent' : 'border-ops-surface1 text-ops-subtext'}`}>
          {sortMode === 'custom' ? (pickedOrder > 0 ? `第 ${pickedOrder}` : '点击排序') : scopeLabel(command)}
        </span>
      </div>
      <div className="mt-1 line-clamp-2 text-xs text-ops-subtext">{command.description || command.prompt_template}</div>
      <div className="mt-2 flex gap-2 text-[11px] text-ops-overlay">
        <span>{command.category || '自定义'}</span>
        <span>顺序 {command.sort_order || 1}</span>
        <span>{command.enabled === false ? '已停用' : '启用'}</span>
        {command.pinned && <span>快捷栏</span>}
      </div>
    </button>
  )
}

export function customCommandPickedOrder(command: SlashCommand, sortPickIds: string[]) {
  return sortPickIds.indexOf(commandStableId(command)) + 1
}
