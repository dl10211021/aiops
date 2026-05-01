import {
  DEFAULT_SESSION_GROUP,
  SESSION_GROUP_STORAGE_KEY,
  uniqueSessionGroups,
} from '@/features/sessions/sessionGroups'

export function readStoredSessionGroups(): string[] {
  try {
    const raw = localStorage.getItem(SESSION_GROUP_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return uniqueSessionGroups(Array.isArray(parsed) ? parsed : [])
  } catch {
    return [DEFAULT_SESSION_GROUP]
  }
}

export function writeStoredSessionGroups(groups: string[]) {
  try {
    localStorage.setItem(SESSION_GROUP_STORAGE_KEY, JSON.stringify(uniqueSessionGroups(groups)))
  } catch {
    // Storage can be unavailable in restricted browser contexts.
  }
}
