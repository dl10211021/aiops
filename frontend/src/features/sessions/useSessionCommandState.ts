import { useCallback, useEffect, useMemo, useState } from 'react'
import { isAbortError } from '@/api/http'
import { useStore } from '@/store'
import type { Session, SessionToolCatalog, SlashCommand } from '@/types'
import { fetchSessionCommandState } from './sessionCommandService'
import { buildSlashCommands } from './slashCommands'

const SESSION_COMMAND_CACHE_TTL_MS = 5 * 60 * 1000
const SESSION_COMMAND_FETCH_DELAY_MS = 450

interface UseSessionCommandStateArgs {
  currentSessionId: string | null
  session: Session | null
  toolCatalog: SessionToolCatalog | null
}

type CommandStateCacheValue = {
  backendCommands: SlashCommand[]
  builtinCommands: SlashCommand[]
  customCommands: SlashCommand[]
}

const sessionCommandStateCache = new Map<string, { state: CommandStateCacheValue; cachedAt: number }>()

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

    const cacheKey = sessionCommandCacheKey(currentSessionId, session?.asset_type, session?.protocol)
    const cached = sessionCommandStateCache.get(cacheKey)
    if (cached && Date.now() - cached.cachedAt < SESSION_COMMAND_CACHE_TTL_MS) {
      applyCommandState(currentSessionId, cached.state)
      return
    }

    let cancelled = false
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') return
      fetchSessionCommandState(currentSessionId, { signal: controller.signal })
        .then((state) => {
          sessionCommandStateCache.set(cacheKey, { state, cachedAt: Date.now() })
          if (!cancelled) applyCommandState(currentSessionId, state)
        })
        .catch((error) => {
          if (isAbortError(error) || controller.signal.aborted) return
          if (!cancelled) {
            setBackendCommands([])
            setBuiltinCommands([])
            setCustomCommands([])
            setCommandSessionId(null)
          }
        })
    }, SESSION_COMMAND_FETCH_DELAY_MS)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [applyCommandState, currentSessionId, session?.asset_type, session?.protocol])

  const refreshCommands = useCallback(async () => {
    if (!currentSessionId) return
    const state = await fetchSessionCommandState(currentSessionId)
    sessionCommandStateCache.set(
      sessionCommandCacheKey(currentSessionId, session?.asset_type, session?.protocol),
      { state, cachedAt: Date.now() },
    )
    applyCommandState(currentSessionId, state)
  }, [applyCommandState, currentSessionId, session?.asset_type, session?.protocol])

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

function sessionCommandCacheKey(sessionId: string, assetType?: string, protocol?: string) {
  return [sessionId, assetType || '', protocol || ''].join('|')
}
