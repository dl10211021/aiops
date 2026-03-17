import { useEffect, useRef } from 'react'
import { useStore } from '@/store'
import LeftNav from '@/components/layout/LeftNav'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import ToastContainer from '@/components/layout/ToastContainer'
import ChatWindow from '@/components/chat/ChatWindow'
import AssetVault from '@/components/views/AssetVault'
import SkillMarket from '@/components/views/SkillMarket'
import KnowledgeBase from '@/components/views/KnowledgeBase'
import CronManager from '@/components/views/CronManager'
import ConnectionModal from '@/components/modals/ConnectionModal'
import LLMConfigModal from '@/components/modals/LLMConfigModal'
import NotificationsModal from '@/components/modals/NotificationsModal'
import DynamicSkillsModal from '@/components/modals/DynamicSkillsModal'
import SessionActionsModal from '@/components/modals/SessionActionsModal'
import { getActiveSessions, pollAllSessions, getSessionHistory } from '@/api/client'
import type { ChatMessage } from '@/types'

function ViewRouter() {
  const currentView = useStore((s) => s.currentView)
  switch (currentView) {
    case 'chat': return <ChatWindow />
    case 'assets': return <AssetVault />
    case 'skills': return <SkillMarket />
    case 'knowledge': return <KnowledgeBase />
    case 'cron': return <CronManager />
    default: return <ChatWindow />
  }
}

function ModalRouter() {
  const activeModal = useStore((s) => s.activeModal)
  switch (activeModal) {
    case 'connect': return <ConnectionModal />
    case 'llm-config': return <LLMConfigModal />
    case 'notifications': return <NotificationsModal />
    case 'dynamic-skills': return <DynamicSkillsModal />
    case 'session-actions': return <SessionActionsModal />
    default: return null
  }
}

export default function App() {
  const addSession = useStore((s) => s.addSession)
  const setCurrentSession = useStore((s) => s.setCurrentSession)
  const appendMessage = useStore((s) => s.appendMessage)
  const sessions = useStore((s) => s.sessions)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Restore sessions from backend on mount
  useEffect(() => {
    const restore = async () => {
      try {
        const res = await getActiveSessions()
        const serverSessions = res.data.sessions || {}
        let firstId: string | null = null

        for (const [sid, sinfo] of Object.entries(serverSessions)) {
          if (!firstId) firstId = sid
          addSession({
            id: sid,
            host: sinfo.host,
            remark: sinfo.remark || '',
            isReadWriteMode: sinfo.isReadWriteMode,
            skills: sinfo.skills || [],
            agentProfile: sinfo.agentProfile || 'default',
            user: sinfo.user || '',
            protocol: sinfo.protocol || 'ssh',
            extra_args: sinfo.extra_args || {},
            heartbeatEnabled: sinfo.heartbeatEnabled || false,
            group_name: sinfo.group_name || '未分组',
            messages: [],
            isStreaming: false,
          })

          // Load chat history
          try {
            const hist = await getSessionHistory(sid)
            const msgs = hist.data.messages || []
            msgs.forEach((m, i) => {
              appendMessage(sid, {
                id: `hist-${sid}-${i}`,
                role: m.role as 'user' | 'assistant',
                content: m.content,
                timestamp: Date.now() - (msgs.length - i) * 1000,
              })
            })
          } catch { /* ignore */ }
        }

        if (firstId) setCurrentSession(firstId)
      } catch { /* backend not ready */ }
    }
    restore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Heartbeat polling
  useEffect(() => {
    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await pollAllSessions()
        const updates = res.data.updates || {}
        for (const [sid, msgs] of Object.entries(updates)) {
          if (!sessions[sid]) continue
          msgs.forEach((m) => {
            const msg: ChatMessage = {
              id: `hb-${Date.now()}-${Math.random()}`,
              role: m.role as 'user' | 'assistant',
              content: m.content,
              timestamp: Date.now(),
            }
            appendMessage(sid, msg)
          })
        }
      } catch { /* ignore */ }
    }, 5000)

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [sessions, appendMessage])

  return (
    <div className="h-screen flex bg-ops-dark overflow-hidden">
      {/* Left icon nav */}
      <LeftNav />

      {/* Sidebar with sessions */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <ViewRouter />
      </div>

      {/* Modals */}
      <ModalRouter />

      {/* Toast notifications */}
      <ToastContainer />
    </div>
  )
}
