import { disconnectSession, updateSessionGroup } from '@/api/client'
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

export async function moveSessionGroupToBackend({
  addToast,
  groupName,
  moveSessionToGroup,
  sessionId,
}: {
  addToast: AddToast
  groupName: string
  moveSessionToGroup: (sessionId: string, groupName: string) => void
  sessionId: string
}) {
  try {
    await updateSessionGroup(sessionId, groupName)
    moveSessionToGroup(sessionId, groupName)
    addToast(`当前会话已移动到：${groupName}`, 'success')
  } catch {
    addToast('会话分组同步失败', 'error')
  }
}
