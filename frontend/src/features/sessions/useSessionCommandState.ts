import { useCallback, useEffect, useMemo, useState } from 'react'
import { useStore } from '@/store'
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
  const [commandSessionId, setCommandSessionId] = useState<string | null>(null)

  const applyCommandState = useCallback((sessionId: string, state: {
    backendCommands: SlashCommand[]
    builtinCommands: SlashCommand[]
    customCommands: SlashCommand[]
  }) => {
    setBackendCommands(state.backendCommands)
    setBuiltinCommands(state.builtinCommands)
    setCustomCommands(state.customCommands)
    setCommandSessionId(sessionId)
  }, [])

  useEffect(() => {
    if (!currentSessionId) {
      setBackendCommands([])
      setBuiltinCommands([])
      setCustomCommands([])
      setCommandSessionId(null)
      return
    }

    setBackendCommands([])
    setBuiltinCommands([])
    setCustomCommands([])
    setCommandSessionId(null)
    let cancelled = false
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') return
      fetchSessionCommandState(currentSessionId)
        .then((state) => {
          if (!cancelled) applyCommandState(currentSessionId, state)
        })
        .catch(() => {
          if (!cancelled) {
            setBackendCommands([])
            setBuiltinCommands([])
            setCustomCommands([])
            setCommandSessionId(null)
          }
        })
    }, 800)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [applyCommandState, currentSessionId, session?.asset_type, session?.protocol])

  const refreshCommands = useCallback(async () => {
    if (!currentSessionId) return
    const state = await fetchSessionCommandState(currentSessionId)
    applyCommandState(currentSessionId, state)
  }, [applyCommandState, currentSessionId])

  const hasCurrentBackendCommands = commandSessionId === currentSessionId && backendCommands.length > 0
  const hasCurrentBuiltinCommands = commandSessionId === currentSessionId && builtinCommands.length > 0
  const slashCommands = useMemo(
    () => hasCurrentBackendCommands ? backendCommands : (session ? buildSlashCommands(session, toolCatalog) : []),
    [backendCommands, hasCurrentBackendCommands, session, toolCatalog],
  )

  return {
    availableCommands: hasCurrentBuiltinCommands ? builtinCommands : slashCommands,
    customCommands,
    refreshCommands,
    setCustomCommands,
    slashCommands,
  }
}
