import type { Session, SlashCommand } from '@/types'
import BuiltInCommandList from './BuiltInCommandList'
import CustomCommandList from './CustomCommandList'

type CommandSortMode = 'custom' | 'builtin' | null

interface CommandManagerCatalogProps {
  session: Session | null
  busy: boolean
  sortMode: CommandSortMode
  sortPickIds: string[]
  userCommands: SlashCommand[]
  orderedUserCommands: SlashCommand[]
  builtInTemplates: SlashCommand[]
  orderedBuiltInTemplates: SlashCommand[]
  overriddenBuiltinIds: string[]
  onBeginSort: (mode: Exclude<CommandSortMode, null>) => void
  onCancelSort: () => void
  onSaveSort: (mode: Exclude<CommandSortMode, null>) => void
  onToggleSortPick: (command: SlashCommand) => void
  onNew: () => void
  onEditCustom: (command: SlashCommand) => void
  onViewBuiltin: (command: SlashCommand) => void
  onEditBuiltin: (command: SlashCommand) => void
  onCopyBuiltin: (command: SlashCommand) => void
  onRestore: (commandId: string) => void
  onRestoreMany: (commandIds: string[]) => void
}

export default function CommandManagerCatalog({
  session,
  busy,
  sortMode,
  sortPickIds,
  userCommands,
  orderedUserCommands,
  builtInTemplates,
  orderedBuiltInTemplates,
  overriddenBuiltinIds,
  onBeginSort,
  onCancelSort,
  onSaveSort,
  onToggleSortPick,
  onNew,
  onEditCustom,
  onViewBuiltin,
  onEditBuiltin,
  onCopyBuiltin,
  onRestore,
  onRestoreMany,
}: CommandManagerCatalogProps) {
  return (
    <div className="overflow-y-auto border-r border-ops-surface0 p-4">
      <CustomCommandList
        session={session}
        busy={busy}
        sortMode={sortMode}
        sortPickIds={sortPickIds}
        userCommands={userCommands}
        orderedUserCommands={orderedUserCommands}
        onBeginSort={() => onBeginSort('custom')}
        onCancelSort={onCancelSort}
        onSaveSort={() => onSaveSort('custom')}
        onToggleSortPick={onToggleSortPick}
        onNew={onNew}
        onEdit={onEditCustom}
      />
      <BuiltInCommandList
        busy={busy}
        sortMode={sortMode}
        sortPickIds={sortPickIds}
        builtInTemplates={builtInTemplates}
        orderedBuiltInTemplates={orderedBuiltInTemplates}
        overriddenBuiltinIds={overriddenBuiltinIds}
        onBeginSort={() => onBeginSort('builtin')}
        onCancelSort={onCancelSort}
        onSaveSort={() => onSaveSort('builtin')}
        onToggleSortPick={onToggleSortPick}
        onView={onViewBuiltin}
        onEdit={onEditBuiltin}
        onCopy={onCopyBuiltin}
        onRestore={onRestore}
        onRestoreMany={onRestoreMany}
      />
    </div>
  )
}
