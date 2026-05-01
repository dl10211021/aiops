import { respondUserInteraction } from '@/api/client'
import { useStore } from '@/store'
import type { ChatMessage, Session } from '@/types'
import { findInteractionMessageId } from './chatAttention'

export function useUserInteractionResponse(
  currentSessionId: string | null,
  sessions: Record<string, Session>,
) {
  const updateMessage = useStore((state) => state.updateMessage)
  const updateLastAssistantMessage = useStore((state) => state.updateLastAssistantMessage)
  const addToast = useStore((state) => state.addToast)

  const respond = async (requestId: string, value: string, label = '') => {
    const sessionId = currentSessionId
    if (!sessionId) return
    const targetMessages = sessions[sessionId]?.messages || []
    const targetMessageId = findInteractionMessageId(targetMessages, requestId)
    try {
      await respondUserInteraction(sessionId, requestId, value, label)
      const updater = (message: ChatMessage) => {
        const interaction = message.userInteraction
        const displayValue = interaction?.inputType === 'password' && value ? '******' : value
        return {
          ...message,
          userInteraction: interaction
            ? { ...interaction, resolved: true, status: 'submitted', value: displayValue, label }
            : undefined,
        }
      }
      if (targetMessageId) updateMessage(sessionId, targetMessageId, updater)
      else updateLastAssistantMessage(sessionId, updater)
    } catch {
      addToast('交互输入提交失败，可能已超时', 'error')
    }
  }

  return {
    respond,
  }
}
