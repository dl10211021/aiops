// Zustand store — global state for OpsCore frontend
import { create } from 'zustand'
import type { ViewId } from '@/types'
import {
  appendMessageState,
  clearMessagesState,
  removeEmptyAssistantMessagesState,
  removeMessageState,
  setSessionMessagesState,
  updateLastAssistantMessageState,
  updateMessageState,
} from './messageMutations'
import { readStoredSessionGroups } from './sessionGroupPersistence'
import {
  createSessionGroupState,
  deleteSessionGroupState,
  renameSessionGroupState,
} from './sessionGroupMutations'
import {
  addSessionState,
  moveSessionToGroupState,
  removeSessionState,
  updateSessionState,
} from './sessionMutations'
import type { AppState } from './types'

let toastId = 0
const VIEW_IDS = new Set<ViewId>([
  'dashboard',
  'bigscreen',
  'chat',
  'assets',
  'canvas',
  'cron',
  'alerts',
  'approvals',
  'skills',
  'knowledge',
  'config',
])

export function viewFromLocationHash(): ViewId {
  if (typeof window === 'undefined') return 'chat'
  const raw = window.location.hash.replace(/^#\/?/, '').split(/[/?&]/)[0]
  return VIEW_IDS.has(raw as ViewId) ? raw as ViewId : 'chat'
}

function syncViewHash(view: ViewId) {
  if (typeof window === 'undefined') return
  if (viewFromLocationHash() === view) return
  window.history.pushState(null, '', `${window.location.pathname}${window.location.search}#/${view}`)
}

export const useStore = create<AppState>((set, get) => ({
  // View
  currentView: viewFromLocationHash(),
  setView: (v) => {
    syncViewHash(v)
    set({ currentView: v })
  },

  // Sessions
  sessions: {},
  currentSessionId: null,
  setCurrentSession: (id) => set({ currentSessionId: id }),
  addSession: (session, activate = true) => set((state) => addSessionState(state, session, activate)),
  removeSession: (id) => set((state) => removeSessionState(state, id)),
  updateSession: (id, patch) => set((state) => updateSessionState(state, id, patch)),
  moveSessionToGroup: (id, groupName) => set((state) => moveSessionToGroupState(state, id, groupName)),

  // Messages
  appendMessage: (sessionId, message) => set((state) => appendMessageState(state, sessionId, message)),
  setSessionMessages: (sessionId, messages) => set((state) => setSessionMessagesState(state, sessionId, messages)),
  removeMessage: (sessionId, messageId) => set((state) => removeMessageState(state, sessionId, messageId)),
  updateMessage: (sessionId, messageId, updater) => set((state) => updateMessageState(state, sessionId, messageId, updater)),
  updateLastAssistantMessage: (sessionId, updater) => set((state) => updateLastAssistantMessageState(state, sessionId, updater)),
  removeEmptyAssistantMessages: (sessionId) => set((state) => removeEmptyAssistantMessagesState(state, sessionId)),
  clearMessages: (sessionId) => set((state) => clearMessagesState(state, sessionId)),

  // Sidebar
  sessionGroups: readStoredSessionGroups(),
  createSessionGroup: (name) => set((state) => createSessionGroupState(state, name)),
  renameSessionGroup: (oldName, newName) => set((state) => renameSessionGroupState(state, oldName, newName)),
  deleteSessionGroup: (name, fallbackGroup) => set((state) => deleteSessionGroupState(state, name, fallbackGroup)),
  collapsedGroups: new Set<string>(),
  toggleGroup: (name) => set((st) => {
    const next = new Set(st.collapsedGroups)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    return { collapsedGroups: next }
  }),
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // Modals
  activeModal: null,
  openModal: (id) => set({ activeModal: id }),
  closeModal: () => set({ activeModal: null }),

  // Skills
  skillRegistry: [],
  setSkillRegistry: (skills) => set({ skillRegistry: skills }),

  // Assets
  assets: [],
  setAssets: (assets) => set({ assets }),

  // Streaming
  chatController: null,
  setChatController: (c) => set({ chatController: c }),

  // Toast
  toasts: [],
  addToast: (message, type = 'info') => {
    const id = ++toastId
    set((st) => ({ toasts: [...st.toasts, { id, message, type }] }))
    setTimeout(() => get().removeToast(id), 4000)
  },
  removeToast: (id) => set((st) => ({
    toasts: st.toasts.filter((t) => t.id !== id),
  })),
}))
