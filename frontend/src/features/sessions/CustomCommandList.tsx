import type { Session, SlashCommand } from '@/types'
import {
  CustomCommandCard,
  CustomCommandEmptyState,
  CustomCommandListHeader,
  CustomSortHint,
  customCommandPickedOrder,
} from './CustomCommandListParts'

type CommandSortMode = 'custom' | 'builtin' | null

interface CustomCommandListProps {
  session: Session | null
  busy: boolean
  sortMode: CommandSortMode
  sortPickIds: string[]
  userCommands: SlashCommand[]
  orderedUserCommands: SlashCommand[]
  onBeginSort: () => void
  onCancelSort: () => void
  onSaveSort: () => void
  onToggleSortPick: (command: SlashCommand) => void
  onNew: () => void
  onEdit: (command: SlashCommand) => void
}

export default function CustomCommandList({
  session,
  busy,
  sortMode,
  sortPickIds,
  userCommands,
  orderedUserCommands,
  onBeginSort,
  onCancelSort,
  onSaveSort,
  onToggleSortPick,
  onNew,
  onEdit,
}: CustomCommandListProps) {
  return (
    <>
      <CustomCommandListHeader
        busy={busy}
        sortMode={sortMode}
        userCommandCount={userCommands.length}
        onBeginSort={onBeginSort}
        onCancelSort={onCancelSort}
        onNew={onNew}
        onSaveSort={onSaveSort}
      />
      {sortMode === 'custom' && <CustomSortHint />}
      <div className="space-y-2">
        {userCommands.length === 0 ? (
          <CustomCommandEmptyState session={session} />
        ) : orderedUserCommands.map((command) => {
          const pickedOrder = customCommandPickedOrder(command, sortPickIds)
          return (
            <CustomCommandCard
              key={command.id}
              command={command}
              pickedOrder={pickedOrder}
              sortMode={sortMode}
              onEdit={onEdit}
              onToggleSortPick={onToggleSortPick}
            />
          )
        })}
      </div>
    </>
  )
}
