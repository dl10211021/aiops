import { useEffect, useRef } from 'react'
import { getSessionHistory, getSessionStatus } from '@/api/client'
import { isAbortError } from '@/api/http'
import { useStore } from '@/store'
import type { Session } from '@/types'
import { normalizeHistoryMessages } from './sessionHistory'

const sessionHistoryRestoreLimit = 160
const SESSION_HISTORY_FETCH_DELAY_MS = 120
const STREAM_RECOVERY_POLL_MS = 8000
const STREAM_RECOVERY_HIDDEN_POLL_MS = 30000
const STREAM_STATUS_CACHE_TTL_MS = STREAM_RECOVERY_POLL_MS

const streamStatusCache = new Map<string, { checkedAt: number; isStreaming: boolean }>()

function readFreshStreamStatus(sessionId: string) {
  const cached = streamStatusCache.get(sessionId)
  if (!cached || Date.now() - cached.checkedAt > STREAM_STATUS_CACHE_TTL_MS) return null
  return cached.isStreaming
}

function rememberStreamStatus(sessionId: string, isStreaming: boolean) {
  streamStatusCache.set(sessionId, { checkedAt: Date.now(), isStreaming })
}

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
      || session.backendStreaming
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
          const messages = (history.data.messages || []).slice(-sessionHistoryRestoreLimit)
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
    const recoverySessionId = sessionId

    let cancelled = false
    let inFlight = false
    let timer: ReturnType<typeof window.setTimeout> | null = null
    const controller = new AbortController()

    function scheduleNext(delay: number) {
      if (cancelled) return
      if (timer) window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        void refreshHistory()
      }, delay)
    }

    async function refreshHistory() {
      if (cancelled || inFlight) return
      if (hasActiveStream(recoverySessionId)) {
        updateSession(recoverySessionId, { isStreaming: true, backendStreaming: true })
        return
      }
      if (document.hidden) {
        scheduleNext(STREAM_RECOVERY_HIDDEN_POLL_MS)
        return
      }
      inFlight = true
      let shouldContinue = true
      try {
        let running = true
        let statusKnown = false
        const cachedRunning = readFreshStreamStatus(recoverySessionId)
        if (cachedRunning !== null) {
          running = cachedRunning
          statusKnown = true
          shouldContinue = running
          updateSession(recoverySessionId, { isStreaming: running, backendStreaming: running })
        } else {
          try {
            const active = await getSessionStatus(recoverySessionId, { signal: controller.signal })
            if (cancelled) return
            running = Boolean(active.data.isStreaming)
            statusKnown = true
            shouldContinue = running
            rememberStreamStatus(recoverySessionId, running)
            updateSession(recoverySessionId, { isStreaming: running, backendStreaming: running })
          } catch {
            // Keep the current running indicator if the status check is transiently unavailable.
          }
        }

        const current = useStore.getState().sessions[recoverySessionId]
        const shouldSyncHistory = !current?.historyLoaded || (statusKnown && !running)
        if (shouldSyncHistory) {
          try {
            const history = await getSessionHistory(recoverySessionId, sessionHistoryRestoreLimit, { signal: controller.signal })
            if (!cancelled) {
              const messages = (history.data.messages || []).slice(-sessionHistoryRestoreLimit)
              setSessionMessages(recoverySessionId, normalizeHistoryMessages(recoverySessionId, messages))
              updateSession(recoverySessionId, { historyLoaded: true })
            }
          } catch (error) {
            if (isAbortError(error) || controller.signal.aborted) return
            // This is only reconnect recovery; keep current transcript on transient failures.
          }
        }
      } finally {
        inFlight = false
        if (!cancelled && shouldContinue) {
          scheduleNext(document.hidden ? STREAM_RECOVERY_HIDDEN_POLL_MS : STREAM_RECOVERY_POLL_MS)
        }
      }
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) void refreshHistory()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    void refreshHistory()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      controller.abort()
    }
  }, [currentSessionId, hasActiveStream, session?.backendStreaming, setSessionMessages, updateSession])
}
