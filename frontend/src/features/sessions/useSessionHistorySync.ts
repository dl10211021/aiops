import { useEffect, useRef } from 'react'
import { getSessionHistory, resumeChatStream } from '@/api/client'
import { isAbortError } from '@/api/http'
import { useStore } from '@/store'
import type { ChatMessage, Session } from '@/types'
import { applyChatStreamEvent } from './chatStreamEvents'
import { consumeChatStream } from './chatStreamReader'
import { refreshStreamingSessionHistory } from './chatStreamingLifecycle'
import { normalizeHistoryMessages } from './sessionHistory'

const sessionHistoryRestoreLimit = 160
const streamingHistoryRecoveryLimit = 48
const SESSION_HISTORY_FETCH_DELAY_MS = 450
const STREAM_RECOVERY_POLL_MS = 8000
const STREAM_RECOVERY_INITIAL_DELAY_MS = 450
const STREAM_RECOVERY_HIDDEN_POLL_MS = 30000

export function useSessionHistorySync(
  currentSessionId: string | null,
  session: Session | null,
  hasActiveStream: (sessionId: string) => boolean,
) {
  const setSessionMessages = useStore((state) => state.setSessionMessages)
  const appendMessage = useStore((state) => state.appendMessage)
  const updateLastAssistantMessage = useStore((state) => state.updateLastAssistantMessage)
  const removeEmptyAssistantMessages = useStore((state) => state.removeEmptyAssistantMessages)
  const updateSession = useStore((state) => state.updateSession)
  const historyLoadingRef = useRef<Set<string>>(new Set())
  const streamRecoveryControllersRef = useRef<Record<string, AbortController>>({})

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
    if (streamRecoveryControllersRef.current[sessionId]) return
    const recoverySessionId = sessionId

    let cancelled = false
    let inFlight = false
    let timer: ReturnType<typeof window.setTimeout> | null = null
    const controller = new AbortController()
    streamRecoveryControllersRef.current[recoverySessionId] = controller

    function scheduleNext(delay: number) {
      if (cancelled) return
      if (timer) window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        void resumeRunningStream()
      }, delay)
    }

    async function resumeRunningStream() {
      if (cancelled || inFlight) return
      if (document.hidden) {
        scheduleNext(STREAM_RECOVERY_HIDDEN_POLL_MS)
        return
      }
      inFlight = true
      let streamCompleted = false
      let accumulatedMarkdown = ''
      try {
        try {
          const history = await getSessionHistory(recoverySessionId, streamingHistoryRecoveryLimit, { signal: controller.signal })
          if (!cancelled) {
            const messages = (history.data.messages || []).slice(-streamingHistoryRecoveryLimit)
            setSessionMessages(recoverySessionId, normalizeHistoryMessages(recoverySessionId, messages))
          }
        } catch (error) {
          if (isAbortError(error) || controller.signal.aborted) return
        }
        ensureRecoveryAssistantMessage(recoverySessionId, appendMessage)
        updateSession(recoverySessionId, { isStreaming: true, backendStreaming: true })
        const response = await resumeChatStream(recoverySessionId, controller.signal)
        if (!response.ok) {
          scheduleNext(STREAM_RECOVERY_POLL_MS)
          return
        }
        await consumeChatStream(response, (data) => {
          if (data.type === 'chunk') {
            accumulatedMarkdown += typeof data.content === 'string' ? data.content : ''
            updateLastAssistantMessage(recoverySessionId, (message) => ({
              ...message,
              content: accumulatedMarkdown,
            }))
            return false
          }
          const result = applyChatStreamEvent({
            sessionId: recoverySessionId,
            data,
            accumulatedMarkdown,
            updateLastAssistantMessage,
          })
          accumulatedMarkdown = result.accumulatedMarkdown
          if (result.done) streamCompleted = true
          return result.done
        })
        if (!cancelled) {
          removeEmptyAssistantMessages(recoverySessionId)
          await refreshStreamingSessionHistory(recoverySessionId, setSessionMessages)
          updateSession(recoverySessionId, { isStreaming: false, backendStreaming: false, historyLoaded: true })
        }
      } finally {
        inFlight = false
        delete streamRecoveryControllersRef.current[recoverySessionId]
        if (!cancelled && !streamCompleted) {
          scheduleNext(document.hidden ? STREAM_RECOVERY_HIDDEN_POLL_MS : STREAM_RECOVERY_POLL_MS)
        }
      }
    }

    const handleVisibilityChange = () => {
      if (!document.hidden) void resumeRunningStream()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    timer = window.setTimeout(() => {
      void resumeRunningStream()
    }, STREAM_RECOVERY_INITIAL_DELAY_MS)
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      controller.abort()
      delete streamRecoveryControllersRef.current[recoverySessionId]
    }
  }, [appendMessage, currentSessionId, hasActiveStream, removeEmptyAssistantMessages, session?.backendStreaming, setSessionMessages, updateLastAssistantMessage, updateSession])
}

function ensureRecoveryAssistantMessage(
  sessionId: string,
  appendMessage: (sessionId: string, message: ChatMessage) => void,
) {
  const messages = useStore.getState().sessions[sessionId]?.messages || []
  const last = messages[messages.length - 1]
  if (last?.role === 'assistant') return
  appendMessage(sessionId, {
    id: `resume-${sessionId}-${Date.now()}`,
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
    execTrace: [],
    runtimeEvents: [],
  })
}
