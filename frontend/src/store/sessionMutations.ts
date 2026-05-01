import {
  normalizeSessionGroupName,
  sessionPrimaryGroup,
  uniqueSessionGroups,
  withPrimaryGroup,
} from '@/features/sessions/sessionGroups'
import type { Session } from '@/types'
import { writeStoredSessionGroups } from './sessionGroupPersistence'

type SessionStateSnapshot = {
  currentSessionId: string | null
  sessionGroups: string[]
  sessions: Record<string, Session>
}

export function addSessionState(st: SessionStateSnapshot, session: Session, activate: boolean) {
  const nextGroups = uniqueSessionGroups([...st.sessionGroups, sessionPrimaryGroup(session)])
  writeStoredSessionGroups(nextGroups)
  return {
    sessions: { ...st.sessions, [session.id]: session },
    sessionGroups: nextGroups,
    currentSessionId: activate ? session.id : st.currentSessionId,
  }
}

export function removeSessionState(st: SessionStateSnapshot, id: string) {
  const sessions = { ...st.sessions }
  delete sessions[id]
  const currentSessionId = st.currentSessionId === id
    ? Object.keys(sessions)[0] || null
    : st.currentSessionId
  return { sessions, currentSessionId }
}

export function updateSessionState(st: SessionStateSnapshot, id: string, patch: Partial<Session>) {
  const session = st.sessions[id]
  if (!session) return st
  return { sessions: { ...st.sessions, [id]: { ...session, ...patch } } }
}

export function moveSessionToGroupState(st: SessionStateSnapshot, id: string, groupName: string) {
  const session = st.sessions[id]
  if (!session) return st
  const normalized = normalizeSessionGroupName(groupName)
  if (!normalized) return st
  const nextGroups = uniqueSessionGroups([...st.sessionGroups, normalized])
  writeStoredSessionGroups(nextGroups)
  return {
    sessionGroups: nextGroups,
    sessions: {
      ...st.sessions,
      [id]: { ...session, tags: withPrimaryGroup(session.tags, normalized) },
    },
  }
}
