import type { Asset, ChatMessage, Session, SkillInfo, ViewId } from '@/types'

export interface AppState {
  // --- View routing ---
  currentView: ViewId
  setView: (v: ViewId) => void

  // --- Sessions ---
  sessions: Record<string, Session>
  currentSessionId: string | null
  setCurrentSession: (id: string | null) => void
  addSession: (s: Session, activate?: boolean) => void
  removeSession: (id: string) => void
  updateSession: (id: string, patch: Partial<Session>) => void
  moveSessionToGroup: (id: string, groupName: string) => void

  // --- Messages ---
  appendMessage: (sessionId: string, msg: ChatMessage) => void
  setSessionMessages: (sessionId: string, messages: ChatMessage[]) => void
  removeMessage: (sessionId: string, messageId: string) => void
  updateMessage: (sessionId: string, messageId: string, updater: (msg: ChatMessage) => ChatMessage) => void
  updateLastAssistantMessage: (sessionId: string, updater: (msg: ChatMessage) => ChatMessage) => void
  removeEmptyAssistantMessages: (sessionId: string) => void
  clearMessages: (sessionId: string) => void

  // --- Sidebar ---
  sessionGroups: string[]
  createSessionGroup: (name: string) => void
  renameSessionGroup: (oldName: string, newName: string) => void
  deleteSessionGroup: (name: string, fallbackGroup?: string) => void
  collapsedGroups: Set<string>
  toggleGroup: (name: string) => void
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void

  // --- Modals ---
  activeModal: string | null
  openModal: (id: string) => void
  closeModal: () => void

  // --- Skills cache ---
  skillRegistry: SkillInfo[]
  setSkillRegistry: (skills: SkillInfo[]) => void

  // --- Assets cache ---
  assets: Asset[]
  setAssets: (assets: Asset[]) => void

  // --- Streaming ---
  chatController: AbortController | null
  setChatController: (c: AbortController | null) => void

  // --- Toast ---
  toasts: Array<{ id: number; message: string; type: 'success' | 'error' | 'info' }>
  addToast: (message: string, type?: 'success' | 'error' | 'info') => void
  removeToast: (id: number) => void
}
