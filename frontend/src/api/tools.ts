import type { SessionToolCatalog, SlashCommand, ToolCenterCatalog } from '@/types'
import { request } from './http'

export async function getToolCatalog() {
  return request<SessionToolCatalog>('/tools/catalog')
}

export async function getToolCenterCatalog() {
  return request<ToolCenterCatalog>('/tools/center')
}

export async function getSessionCommands(sessionId: string, options?: RequestInit) {
  return request<{ commands: SlashCommand[]; builtin_commands: SlashCommand[]; custom_commands: SlashCommand[]; context: Record<string, unknown> }>(
    `/session/${sessionId}/commands`,
    options,
  )
}

export async function listCustomCommands() {
  return request<{ commands: SlashCommand[] }>('/commands/custom')
}

export async function saveCustomCommand(command: Partial<SlashCommand>) {
  const payload = {
    ...command,
    prompt_template: command.prompt_template || command.prompt || '',
  }
  if (command.id) {
    return request<{ command: SlashCommand }>(`/commands/custom/${encodeURIComponent(command.id)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }
  return request<{ command: SlashCommand }>('/commands/custom', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function deleteCustomCommand(commandId: string) {
  return request(`/commands/custom/${encodeURIComponent(commandId)}`, { method: 'DELETE' })
}
