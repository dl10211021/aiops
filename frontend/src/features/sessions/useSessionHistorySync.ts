import { useEffect, useRef } from 'react'
import { getActiveSessions, getSessionHistory } from '@/api/client'
import { isAbortError } from '@/api/http'
import { useStore } from '@/store'
import type { Session } from '@/types'
import { normalizeHistoryMessages } from './sessionHistory'

const sessionHistoryRestoreLimit = 160
const SESSION_HISTORY_FETCH_DELAY_MS = 120

export function useSessionHistorySync(
  currentSessionId: string | null,
  session: Session | null,
  hasActiveStream: (sessionId: string) => boolean,
) {
  const setSessionMessages = useStore((state) => state.setSessionMessages)
  const updateSession = useStore((state) => state.updateSession)
  const historyLoadingRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    const sessionId = currentSessionId
    if (
      !sessionId
      || !session
      || session.historyLoaded
      || historyLoadingRef.current.has(sessionId)
      || hasActiveStream(sessionId)
    ) return

    historyLoadingRef.current.add(sessionId)
    let cancelled = false
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      if (useStore.getState().currentView !== 'chat') {
        historyLoadingRef.current.delete(sessionId)
        return
      }
      getSessionHistory(sessionId, sessionHistoryRestoreLimit, { signal: controller.signal })
        .then((history) => {
          if (cancelled) return
          const messages = history.data.messages || []
          const current = useStore.getState().sessions[sessionId]
          if (!current) return
          setSessionMessages(sessionId, normalizeHistoryMessages(sessionId, messages))
          updateSession(sessionId, { historyLoaded: true })
        })
        .catch((error) => {
          if (isAbortError(error) || controller.signal.aborted) return
          if (!cancelled) updateSession(sessionId, { historyLoaded: true })
        })
        .finally(() => {
          historyLoadingRef.current.delete(sessionId)
        })
    }, SESSION_HISTORY_FETCH_DELAY_MS)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller.abort()
      historyLoadingRef.current.delete(sessionId)
    }
  }, [currentSessionId, hasActiveStream, session, session?.historyLoaded, setSessionMessages, updateSession])

  useEffect(() => {
    const sessionId = currentSessionId
    if (!sessionId || !session?.backendStreaming) return
    if (hasActiveStream(sessionId)) return

    let cancelled = false
    const controller = new AbortController()
    const refreshHistory = async () => {
      try {
        const history = await getSessionHistory(sessionId, sessionHistoryRestoreLimit, { signal: controller.signal })
        if (!cancelled) {
          setSessionMessages(sessionId, normalizeHistoryMessages(sessionId, history.data.messages || []))
        }
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) return
        // This is only reconnect recovery; keep current transcript on transient failures.
      }
      try {
        const active = await getActiveSessions()
        if (cancelled) return
        const running = Boolean(active.data.sessions?.[sessionId]?.isStreaming)
        updateSession(sessionId, { isStreaming: running, backendStreaming: running })
      } catch {
        // Keep the current running indicator if the status check is transiently unavailable.
      }
    }
    void refreshHistory()
    const timer = window.setInterval(refreshHistory, 5000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      controller.abort()
    }
  }, [currentSessionId, hasActiveStream, session?.backendStreaming, setSessionMessages, updateSession])
}
