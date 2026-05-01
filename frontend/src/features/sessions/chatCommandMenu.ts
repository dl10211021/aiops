import type { SlashCommand } from '@/types'

export function buildQuickCommands(commands: SlashCommand[]) {
  const pinnedCommands = commands.filter((command) => command.pinned)
  return [
    ...pinnedCommands,
    ...commands.filter((command) => !command.pinned),
  ]
}

export function visibleSlashCommandsForInput(input: string, commands: SlashCommand[]) {
  if (!input.startsWith('/')) return []
  const query = input.slice(1).toLowerCase()
  return commands
    .filter((command) => command.id.includes(query) || command.label.toLowerCase().includes(query))
    .slice(0, 20)
}
