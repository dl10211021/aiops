import type { SlashCommand } from '@/types'
import {
  BuiltInCommandCard,
  BuiltInCommandHeader,
  BuiltInSortHint,
} from './BuiltInCommandListParts'
import { commandStableId } from './slashCommands'

type CommandSortMode = 'custom' | 'builtin' | null

interface BuiltInCommandListProps {
  busy: boolean
  sortMode: CommandSortMode
  sortPickIds: string[]
  builtInTemplates: SlashCommand[]
  orderedBuiltInTemplates: SlashCommand[]
  overriddenBuiltinIds: string[]
  onBeginSort: () => void
  onCancelSort: () => void
  onSaveSort: () => void
  onToggleSortPick: (command: SlashCommand) => void
  onView: (command: SlashCommand) => void
  onEdit: (command: SlashCommand) => void
  onCopy: (command: SlashCommand) => void
  onRestore: (commandId: string) => void
  onRestoreMany: (commandIds: string[]) => void
}

export default function BuiltInCommandList({
  busy,
  sortMode,
  sortPickIds,
  builtInTemplates,
  orderedBuiltInTemplates,
  overriddenBuiltinIds,
  onBeginSort,
  onCancelSort,
  onSaveSort,
  onToggleSortPick,
  onView,
  onEdit,
  onCopy,
  onRestore,
  onRestoreMany,
}: BuiltInCommandListProps) {
  if (builtInTemplates.length === 0) return null

  return (
    <div className="mt-5 border-t border-ops-surface0 pt-4">
      <BuiltInCommandHeader
        busy={busy}
        overriddenBuiltinIds={overriddenBuiltinIds}
        sortMode={sortMode}
        onBeginSort={onBeginSort}
        onCancelSort={onCancelSort}
        onRestoreMany={onRestoreMany}
        onSaveSort={onSaveSort}
      />
      {sortMode === 'builtin' && <BuiltInSortHint />}
      <div className="space-y-2">
        {orderedBuiltInTemplates.map((command) => {
          const pickedOrder = sortPickIds.indexOf(commandStableId(command)) + 1
          return (
            <BuiltInCommandCard
              key={command.id}
              command={command}
              pickedOrder={pickedOrder}
              sortMode={sortMode}
              onCopy={onCopy}
              onEdit={onEdit}
              onRestore={onRestore}
              onToggleSortPick={onToggleSortPick}
              onView={onView}
            />
          )
        })}
      </div>
    </div>
  )
}
