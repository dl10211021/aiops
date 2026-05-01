import {
  deleteCustomCommand,
  getSessionCommands,
  listCustomCommands,
  saveCustomCommand,
} from '@/api/tools'
import type { SlashCommand } from '@/types'

export interface SessionCommandState {
  backendCommands: SlashCommand[]
  builtinCommands: SlashCommand[]
  customCommands: SlashCommand[]
}

export async function fetchSessionCommandState(sessionId: string): Promise<SessionCommandState> {
  const res = await getSessionCommands(sessionId)
  return {
    backendCommands: res.data.commands || [],
    builtinCommands: res.data.builtin_commands || [],
    customCommands: res.data.custom_commands || [],
  }
}

export async function fetchCustomCommands() {
  const res = await listCustomCommands()
  return res.data.commands || []
}

export async function persistCommandDraft(command: Partial<SlashCommand>) {
  await saveCustomCommand(command)
}

export async function removeCommand(commandId: string) {
  await deleteCustomCommand(commandId)
}

export async function restoreCommandOverrides(commandIds: string[]) {
  await Promise.all(commandIds.map((commandId) => deleteCustomCommand(commandId).catch(() => null)))
}

export async function persistCommandOrder(commands: Partial<SlashCommand>[]) {
  await Promise.all(commands.map((command) => saveCustomCommand(command)))
}
