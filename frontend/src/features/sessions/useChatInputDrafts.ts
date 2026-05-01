import { useEffect, useState } from 'react'
import type { RefObject } from 'react'

export function useChatInputDrafts(
  currentSessionId: string | null,
  textareaRef: RefObject<HTMLTextAreaElement | null>,
) {
  const [draftsBySession, setDraftsBySession] = useState<Record<string, string>>({})
  const [inputHistory, setInputHistory] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('ops_chat_input_history')
      const parsed = stored ? JSON.parse(stored) : []
      return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
    } catch {
      return []
    }
  })
  const [historyIndex, setHistoryIndex] = useState<number | null>(null)
  const input = currentSessionId ? draftsBySession[currentSessionId] || '' : ''

  useEffect(() => {
    localStorage.setItem('ops_chat_input_history', JSON.stringify(inputHistory.slice(0, 20)))
  }, [inputHistory])

  const setInput = (value: string) => {
    if (!currentSessionId) return
    setDraftsBySession((prev) => ({ ...prev, [currentSessionId]: value }))
  }

  const focusComposer = () => {
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  const moveCursorToEnd = () => {
    requestAnimationFrame(() => {
      const element = textareaRef.current
      if (element) element.selectionStart = element.selectionEnd = element.value.length
    })
  }

  const applySlashCommand = (prompt: string) => {
    setInput(prompt)
    setHistoryIndex(null)
    focusComposer()
  }

  const handleHistoryKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'ArrowUp' && inputHistory.length > 0 && !event.shiftKey) {
      const atStart = event.currentTarget.selectionStart === 0
      if (!input.trim() || atStart) {
        event.preventDefault()
        const nextIndex = historyIndex === null ? 0 : Math.min(historyIndex + 1, inputHistory.length - 1)
        setHistoryIndex(nextIndex)
        setInput(inputHistory[nextIndex])
        moveCursorToEnd()
        return true
      }
    }

    if (event.key === 'ArrowDown' && inputHistory.length > 0 && !event.shiftKey) {
      const atEnd = event.currentTarget.selectionStart === input.length
      if (historyIndex !== null && atEnd) {
        event.preventDefault()
        const nextIndex = historyIndex - 1
        if (nextIndex < 0) {
          setHistoryIndex(null)
          setInput('')
          return true
        }
        setHistoryIndex(nextIndex)
        setInput(inputHistory[nextIndex])
        moveCursorToEnd()
        return true
      }
    }

    return false
  }

  return {
    applySlashCommand,
    draftsBySession,
    handleHistoryKeyDown,
    input,
    inputHistory,
    setDraftsBySession,
    setHistoryIndex,
    setInput,
    setInputHistory,
  }
}
