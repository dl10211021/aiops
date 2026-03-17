// Zustand store — global state for OpsCore frontend
import { create } from 'zustand'
import type { Session, ChatMessage, ViewId, SkillInfo, Asset } from '@/types'

interface AppState {
  // --- View routing ---
  currentView: ViewId
  setView: (v: ViewId) => void

  // --- Sessions ---
  sessions: Record<string, Session>
  currentSessionId: string | null
  setCurrentSession: (id: string | null) => void
  addSession: (s: Session) => void
  removeSession: (id: string) => void
  updateSession: (id: string, patch: Partial<Session>) => void

  // --- Messages ---
  appendMessage: (sessionId: string, msg: ChatMessage) => void
  updateLastAssistantMessage: (sessionId: string, updater: (msg: ChatMessage) => ChatMessage) => void
  clearMessages: (sessionId: string) => void

  // --- Sidebar ---
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

let toastId = 0

export const useStore = create<AppState>((set, get) => ({
  // View
  currentView: 'chat',
  setView: (v) => set({ currentView: v }),

  // Sessions
  sessions: {},
  currentSessionId: null,
  setCurrentSession: (id) => set({ currentSessionId: id }),
  addSession: (s) => set((st) => ({
    sessions: { ...st.sessions, [s.id]: s },
    currentSessionId: s.id,
  })),
  removeSession: (id) => set((st) => {
    const copy = { ...st.sessions }
    delete copy[id]
    const nextId = st.currentSessionId === id
      ? Object.keys(copy)[0] || null
      : st.currentSessionId
    return { sessions: copy, currentSessionId: nextId }
  }),
  updateSession: (id, patch) => set((st) => {
    const s = st.sessions[id]
    if (!s) return st
    return { sessions: { ...st.sessions, [id]: { ...s, ...patch } } }
  }),

  // Messages
  appendMessage: (sessionId, msg) => set((st) => {
    const s = st.sessions[sessionId]
    if (!s) return st
    return {
      sessions: {
        ...st.sessions,
        [sessionId]: { ...s, messages: [...s.messages, msg] },
      },
    }
  }),
  updateLastAssistantMessage: (sessionId, updater) => set((st) => {
    const s = st.sessions[sessionId]
    if (!s) return st
    const msgs = [...s.messages]
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') {
        msgs[i] = updater(msgs[i])
        break
      }
    }
    return {
      sessions: {
        ...st.sessions,
        [sessionId]: { ...s, messages: msgs },
      },
    }
  }),
  clearMessages: (sessionId) => set((st) => {
    const s = st.sessions[sessionId]
    if (!s) return st
    return {
      sessions: {
        ...st.sessions,
        [sessionId]: { ...s, messages: [] },
      },
    }
  }),

  // Sidebar
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
