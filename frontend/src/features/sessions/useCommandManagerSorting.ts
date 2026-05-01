import { useMemo, useState } from 'react'
import type { SlashCommand } from '@/types'
import {
  commandOrderPreview,
  commandOrderSavePayload,
  commandStableId,
  sortCommandList,
} from './slashCommands'

type CommandSortMode = 'custom' | 'builtin' | null

export function useCommandManagerSorting(
  commands: SlashCommand[],
  availableCommands: SlashCommand[],
  onSaveOrder: (commands: Partial<SlashCommand>[]) => Promise<void> | void,
) {
  const [sortMode, setSortMode] = useState<CommandSortMode>(null)
  const [sortPickIds, setSortPickIds] = useState<string[]>([])
  const builtInTemplates = useMemo(
    () => sortCommandList(availableCommands.filter((command) => command.source !== 'custom')),
    [availableCommands],
  )
  const builtInIds = useMemo(
    () => new Set(builtInTemplates.map((command) => command.builtin_id || command.id)),
    [builtInTemplates],
  )
  const userCommands = useMemo(
    () => sortCommandList(commands.filter((command) => !builtInIds.has(command.id))),
    [builtInIds, commands],
  )
  const orderedUserCommands = sortMode === 'custom'
    ? commandOrderPreview(userCommands, sortPickIds)
    : userCommands
  const orderedBuiltInTemplates = sortMode === 'builtin'
    ? commandOrderPreview(builtInTemplates, sortPickIds)
    : builtInTemplates
  const overriddenBuiltinIds = builtInTemplates
    .filter((command) => command.is_override)
    .map(commandStableId)

  const beginSort = (mode: Exclude<CommandSortMode, null>) => {
    setSortMode((currentMode) => currentMode === mode ? null : mode)
    setSortPickIds([])
  }

  const toggleSortPick = (command: SlashCommand) => {
    const id = commandStableId(command)
    setSortPickIds((ids) => ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id])
  }

  const saveSort = async (mode: Exclude<CommandSortMode, null>) => {
    const source = mode === 'custom' ? userCommands : builtInTemplates
    await onSaveOrder(commandOrderSavePayload(source, sortPickIds))
    setSortMode(null)
    setSortPickIds([])
  }

  const cancelSort = () => {
    setSortMode(null)
    setSortPickIds([])
  }

  return {
    beginSort,
    builtInIds,
    builtInTemplates,
    cancelSort,
    orderedBuiltInTemplates,
    orderedUserCommands,
    overriddenBuiltinIds,
    saveSort,
    sortMode,
    sortPickIds,
    toggleSortPick,
    userCommands,
  }
}
