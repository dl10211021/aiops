import type { Session } from '@/types'

export const DEFAULT_SESSION_GROUP = '未分组'
export const SESSION_GROUP_STORAGE_KEY = 'opscore_session_groups'

export function normalizeSessionGroupName(name: string | null | undefined): string {
  return String(name || '').trim().replace(/\s+/g, ' ').slice(0, 80)
}

export function uniqueSessionGroups(groups: Array<string | null | undefined>): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const raw of groups) {
    const name = normalizeSessionGroupName(raw)
    if (!name || seen.has(name)) continue
    seen.add(name)
    result.push(name)
  }
  if (!seen.has(DEFAULT_SESSION_GROUP)) result.unshift(DEFAULT_SESSION_GROUP)
  return result
}

export function sessionPrimaryGroup(session: Pick<Session, 'tags'>): string {
  return normalizeSessionGroupName(session.tags?.[0]) || DEFAULT_SESSION_GROUP
}

export function withPrimaryGroup(tags: string[] | undefined, group: string): string[] {
  const groupName = normalizeSessionGroupName(group) || DEFAULT_SESSION_GROUP
  const rest = (tags || [])
    .slice(1)
    .map((tag) => normalizeSessionGroupName(tag))
    .filter((tag) => tag && tag !== groupName)
  return [groupName, ...rest]
}

export function sessionGroupNames(storedGroups: string[], sessions: Session[]): string[] {
  return uniqueSessionGroups([
    ...storedGroups,
    ...sessions.map((session) => sessionPrimaryGroup(session)),
  ])
}

export function groupSessionsByPrimaryGroup(
  sessions: Session[],
  groups: string[],
): Record<string, Session[]> {
  const grouped: Record<string, Session[]> = Object.fromEntries(
    uniqueSessionGroups(groups).map((group) => [group, [] as Session[]]),
  )
  for (const session of sessions) {
    const group = sessionPrimaryGroup(session)
    if (!grouped[group]) grouped[group] = []
    grouped[group].push(session)
  }
  return grouped
}
