import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Session, SessionToolCatalog, SlashCommand } from '@/types'
import { fetchSessionCommandState } from './sessionCommandService'
import { buildSlashCommands } from './slashCommands'

interface UseSessionCommandStateArgs {
  currentSessionId: string | null
  session: Session | null
  toolCatalog: SessionToolCatalog | null
}

export function useSessionCommandState({
  currentSessionId,
  session,
  toolCatalog,
}: UseSessionCommandStateArgs) {
  const [backendCommands, setBackendCommands] = useState<SlashCommand[]>([])
  const [builtinCommands, setBuiltinCommands] = useState<SlashCommand[]>([])
  const [customCommands, setCustomCommands] = useState<SlashCommand[]>([])

  const applyCommandState = useCallback((state: {
    backendCommands: SlashCommand[]
    builtinCommands: SlashCommand[]
    customCommands: SlashCommand[]
  }) => {
    setBackendCommands(state.backendCommands)
    setBuiltinCommands(state.builtinCommands)
    setCustomCommands(state.customCommands)
  }, [])

  useEffect(() => {
    if (!currentSessionId) {
      setBackendCommands([])
      setBuiltinCommands([])
      setCustomCommands([])
      return
    }

    let cancelled = false
    fetchSessionCommandState(currentSessionId)
      .then((state) => {
        if (!cancelled) applyCommandState(state)
      })
      .catch(() => {
        if (!cancelled) setBackendCommands([])
      })
    return () => {
      cancelled = true
    }
  }, [applyCommandState, currentSessionId, session?.asset_type, session?.protocol])

  const refreshCommands = useCallback(async () => {
    if (!currentSessionId) return
    const state = await fetchSessionCommandState(currentSessionId)
    applyCommandState(state)
  }, [applyCommandState, currentSessionId])

  const slashCommands = useMemo(
    () => backendCommands.length > 0 ? backendCommands : (session ? buildSlashCommands(session, toolCatalog) : []),
    [backendCommands, session, toolCatalog],
  )

  return {
    availableCommands: builtinCommands.length > 0 ? builtinCommands : slashCommands,
    customCommands,
    refreshCommands,
    setCustomCommands,
    slashCommands,
  }
}
