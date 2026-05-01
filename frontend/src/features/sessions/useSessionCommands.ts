import { useCallback, useState } from 'react'
import type { Session, SessionToolCatalog, SlashCommand } from '@/types'
import {
  fetchCustomCommands,
  persistCommandDraft,
  persistCommandOrder,
  removeCommand,
  restoreCommandOverrides,
} from './sessionCommandService'
import { useSessionCommandState } from './useSessionCommandState'
import {
  commandDraftForBuiltin,
  commandDraftForSession,
  commandDraftFromCommand,
} from './slashCommands'

interface UseSessionCommandsArgs {
  currentSessionId: string | null
  session: Session | null
  toolCatalog: SessionToolCatalog | null
}

export function useSessionCommands({
  currentSessionId,
  session,
  toolCatalog,
}: UseSessionCommandsArgs) {
  const {
    availableCommands,
    customCommands,
    refreshCommands,
    setCustomCommands,
    slashCommands,
  } = useSessionCommandState({
    currentSessionId,
    session,
    toolCatalog,
  })
  const [managerOpen, setManagerOpen] = useState(false)
  const [draft, setDraft] = useState<Partial<SlashCommand> | null>(null)
  const [readonlyDraft, setReadonlyDraft] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const openManager = useCallback(async () => {
    setManagerOpen(true)
    setError('')
    setDraft(commandDraftForSession(session))
    setReadonlyDraft(false)
    try {
      setCustomCommands(await fetchCustomCommands())
    } catch (err) {
      setError(err instanceof Error ? err.message : '快捷命令加载失败')
    }
  }, [session])

  const closeManager = useCallback(() => {
    setManagerOpen(false)
  }, [])

  const newCommand = useCallback(() => {
    setReadonlyDraft(false)
    setDraft(commandDraftForSession(session))
  }, [session])

  const editCustomCommand = useCallback((command: SlashCommand) => {
    setError('')
    setReadonlyDraft(false)
    setDraft({
      ...command,
      prompt_template: command.prompt_template || command.prompt,
    })
  }, [])

  const editBuiltinCommand = useCallback((command: SlashCommand) => {
    setError('')
    setReadonlyDraft(false)
    setDraft(commandDraftForBuiltin(command))
  }, [])

  const viewBuiltinCommand = useCallback((command: SlashCommand) => {
    setError('')
    setReadonlyDraft(true)
    setDraft(commandDraftForBuiltin(command))
  }, [])

  const copyCommand = useCallback((command: SlashCommand) => {
    setReadonlyDraft(false)
    setDraft(commandDraftFromCommand(command, session))
  }, [session])

  const beginEdit = useCallback(() => {
    setReadonlyDraft(false)
  }, [])

  const saveDraft = useCallback(async () => {
    if (!draft) return
    setBusy(true)
    setError('')
    try {
      await persistCommandDraft(draft)
      setDraft(commandDraftForSession(session))
      setReadonlyDraft(false)
      await refreshCommands()
    } catch (err) {
      setError(err instanceof Error ? err.message : '快捷命令保存失败')
    } finally {
      setBusy(false)
    }
  }, [draft, refreshCommands, session])

  const removeCustomCommand = useCallback(async (commandId: string) => {
    if (!window.confirm('确定删除这个快捷命令吗？')) return
    setBusy(true)
    setError('')
    try {
      await removeCommand(commandId)
      if (draft?.id === commandId) setDraft(commandDraftForSession(session))
      await refreshCommands()
    } catch (err) {
      setError(err instanceof Error ? err.message : '快捷命令删除失败')
    } finally {
      setBusy(false)
    }
  }, [draft?.id, refreshCommands, session])

  const restoreBuiltinCommand = useCallback(async (commandId: string) => {
    setBusy(true)
    setError('')
    try {
      await restoreCommandOverrides([commandId])
      setDraft(commandDraftForSession(session))
      setReadonlyDraft(false)
      await refreshCommands()
    } catch (err) {
      setError(err instanceof Error ? err.message : '内置模板恢复失败')
    } finally {
      setBusy(false)
    }
  }, [refreshCommands, session])

  const restoreBuiltinCommands = useCallback(async (commandIds: string[]) => {
    const uniqueIds = Array.from(new Set(commandIds.filter(Boolean)))
    if (uniqueIds.length === 0) return
    if (!window.confirm(`确定恢复 ${uniqueIds.length} 个内置模板为默认配置吗？`)) return
    setBusy(true)
    setError('')
    try {
      await restoreCommandOverrides(uniqueIds)
      setDraft(commandDraftForSession(session))
      setReadonlyDraft(false)
      await refreshCommands()
    } catch (err) {
      setError(err instanceof Error ? err.message : '内置模板恢复失败')
    } finally {
      setBusy(false)
    }
  }, [refreshCommands, session])

  const saveOrder = useCallback(async (commandsToSave: Partial<SlashCommand>[]) => {
    if (commandsToSave.length === 0) return
    setBusy(true)
    setError('')
    try {
      await persistCommandOrder(commandsToSave)
      setDraft(commandDraftForSession(session))
      setReadonlyDraft(false)
      await refreshCommands()
    } catch (err) {
      setError(err instanceof Error ? err.message : '快捷命令排序保存失败')
    } finally {
      setBusy(false)
    }
  }, [refreshCommands, session])

  return {
    availableCommands,
    busy,
    closeManager,
    copyCommand,
    customCommands,
    draft,
    editBuiltinCommand,
    editCustomCommand,
    error,
    managerOpen,
    newCommand,
    openManager,
    readonlyDraft,
    removeCustomCommand,
    restoreBuiltinCommand,
    restoreBuiltinCommands,
    saveDraft,
    saveOrder,
    setDraft,
    slashCommands,
    beginEdit,
    viewBuiltinCommand,
  }
}
