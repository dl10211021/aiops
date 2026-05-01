import { useEffect, useRef } from 'react'
import { getActiveSessions, getSessionHistory } from '@/api/client'
import { useStore } from '@/store'
import type { Session } from '@/types'
import { normalizeHistoryMessages } from './sessionHistory'

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
    if (!sessionId || !session || session.historyLoaded || historyLoadingRef.current.has(sessionId)) return

    historyLoadingRef.current.add(sessionId)
    getSessionHistory(sessionId)
      .then((history) => {
        const messages = history.data.messages || []
        const current = useStore.getState().sessions[sessionId]
        if (!current) return
        if ((current.messages || []).length === 0) {
          setSessionMessages(sessionId, normalizeHistoryMessages(sessionId, messages))
        }
        updateSession(sessionId, { historyLoaded: true })
      })
      .catch(() => {
        updateSession(sessionId, { historyLoaded: true })
      })
      .finally(() => {
        historyLoadingRef.current.delete(sessionId)
      })
  }, [currentSessionId, session, session?.historyLoaded, setSessionMessages, updateSession])

  useEffect(() => {
    const sessionId = currentSessionId
    if (!sessionId || !session?.backendStreaming) return
    if (hasActiveStream(sessionId)) return

    let cancelled = false
    const refreshHistory = async () => {
      try {
        const history = await getSessionHistory(sessionId)
        if (!cancelled) {
          setSessionMessages(sessionId, normalizeHistoryMessages(sessionId, history.data.messages || []))
        }
      } catch {
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
    }
  }, [currentSessionId, hasActiveStream, session?.backendStreaming, setSessionMessages, updateSession])
}
