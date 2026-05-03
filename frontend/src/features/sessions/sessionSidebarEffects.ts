import { disconnectSession, updateSessionGroup, updateSessionMetadata } from '@/api/client'
import type { Session } from '@/types'

type AddToast = (message: string, type?: 'success' | 'error' | 'info') => void

export async function syncSessionsGroupToBackend(
  items: Session[],
  groupName: string,
  addToast: AddToast,
) {
  const results = await Promise.allSettled(
    items.map((session) => updateSessionGroup(session.id, groupName)),
  )
  if (results.some((result) => result.status === 'rejected')) {
    addToast('部分会话分组同步到后端失败，刷新后可能需要重试', 'error')
  }
}

export async function disconnectSidebarSession(
  sessionId: string,
  removeSession: (sessionId: string) => void,
) {
  try {
    await disconnectSession(sessionId)
    removeSession(sessionId)
  } catch {
    // Keep disconnect best-effort so a stale backend session does not block UI cleanup.
  }
}

export async function saveSessionGroupToBackend({
  addToast,
  groupName,
  sessionId,
  updateSession,
}: {
  addToast: AddToast
  groupName: string
  sessionId: string
  updateSession: (sessionId: string, patch: Partial<Session>) => void
}) {
  try {
    const response = await updateSessionGroup(sessionId, groupName)
    updateSession(sessionId, {
      tags: response.data.tags,
    })
    addToast(`会话已移动到：${response.data.group_name}`, 'success')
    return response.data
  } catch (error) {
    addToast(operationErrorMessage(error, '会话分组保存失败'), 'error')
    return null
  }
}

export async function saveSessionMetadataToBackend({
  addToast,
  groupName,
  remark,
  sessionId,
  tags,
  updateSession,
}: {
  addToast: AddToast
  groupName: string
  remark: string
  sessionId: string
  tags: string[]
  updateSession: (sessionId: string, patch: Partial<Session>) => void
}) {
  try {
    const response = await updateSessionMetadata(sessionId, {
      remark,
      group_name: groupName,
      tags,
    })
    updateSession(sessionId, {
      remark: response.data.remark,
      tags: response.data.tags,
    })
    addToast('会话信息已更新', 'success')
    return response.data
  } catch (error) {
    addToast(operationErrorMessage(error, '会话信息保存失败'), 'error')
    return null
  }
}

function operationErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return `${fallback}：${error.message}`
  }
  return fallback
}
