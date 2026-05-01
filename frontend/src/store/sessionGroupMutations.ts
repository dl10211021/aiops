import {
  DEFAULT_SESSION_GROUP,
  normalizeSessionGroupName,
  sessionPrimaryGroup,
  uniqueSessionGroups,
  withPrimaryGroup,
} from '@/features/sessions/sessionGroups'
import type { Session } from '@/types'
import { writeStoredSessionGroups } from './sessionGroupPersistence'

type SessionGroupStateSnapshot = {
  sessionGroups: string[]
  sessions: Record<string, Session>
}

export function createSessionGroupState(st: SessionGroupStateSnapshot, name: string) {
  const normalized = normalizeSessionGroupName(name)
  if (!normalized) return st
  const nextGroups = uniqueSessionGroups([...st.sessionGroups, normalized])
  writeStoredSessionGroups(nextGroups)
  return { sessionGroups: nextGroups }
}

export function renameSessionGroupState(st: SessionGroupStateSnapshot, oldName: string, newName: string) {
  const oldGroup = normalizeSessionGroupName(oldName)
  const nextGroup = normalizeSessionGroupName(newName)
  if (!oldGroup || !nextGroup || oldGroup === nextGroup) return st
  const sessions = Object.fromEntries(
    Object.entries(st.sessions).map(([id, session]) => [
      id,
      sessionPrimaryGroup(session) === oldGroup
        ? { ...session, tags: withPrimaryGroup(session.tags, nextGroup) }
        : session,
    ]),
  )
  const nextGroups = uniqueSessionGroups(
    st.sessionGroups.map((group) => normalizeSessionGroupName(group) === oldGroup ? nextGroup : group),
  )
  writeStoredSessionGroups(nextGroups)
  return { sessionGroups: nextGroups, sessions }
}

export function deleteSessionGroupState(
  st: SessionGroupStateSnapshot,
  name: string,
  fallbackGroup = DEFAULT_SESSION_GROUP,
) {
  const group = normalizeSessionGroupName(name)
  const fallback = normalizeSessionGroupName(fallbackGroup) || DEFAULT_SESSION_GROUP
  if (!group || group === DEFAULT_SESSION_GROUP) return st
  const sessions = Object.fromEntries(
    Object.entries(st.sessions).map(([id, session]) => [
      id,
      sessionPrimaryGroup(session) === group
        ? { ...session, tags: withPrimaryGroup(session.tags, fallback) }
        : session,
    ]),
  )
  const nextGroups = uniqueSessionGroups(st.sessionGroups.filter((item) => item !== group).concat(fallback))
  writeStoredSessionGroups(nextGroups)
  return { sessionGroups: nextGroups, sessions }
}
