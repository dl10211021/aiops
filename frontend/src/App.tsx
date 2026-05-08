import { Component, lazy, Suspense, useEffect, useRef, type ComponentType, type ErrorInfo, type ReactNode } from 'react'
import { useStore, viewFromLocationHash } from '@/store'
import LeftNav from '@/components/layout/LeftNav'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import ToastContainer from '@/components/layout/ToastContainer'
import { getActiveSessions, pollAllSessions } from '@/api/client'
import type { ChatMessage } from '@/types'

const CHUNK_RELOAD_KEY = 'opscore:chunk-reload-once'

function isChunkLoadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error || '')
  return /Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk|ChunkLoadError/i.test(message)
}

function lazyWithChunkRecovery<T extends { default: ComponentType<unknown> }>(factory: () => Promise<T>) {
  return lazy(() => factory().catch((error) => {
    if (isChunkLoadError(error) && !window.sessionStorage.getItem(CHUNK_RELOAD_KEY)) {
      window.sessionStorage.setItem(CHUNK_RELOAD_KEY, '1')
      window.location.reload()
      return new Promise<T>(() => undefined)
    }
    throw error
  }))
}

class ChunkErrorBoundary extends Component<
  { area: string; children: ReactNode },
  { hasError: boolean; message: string }
> {
  state = { hasError: false, message: '' }

  static getDerivedStateFromError(error: unknown) {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : '视图加载失败',
    }
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error('OpsCore view load failed', error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center bg-ops-dark p-6">
        <div className="ops-card max-w-lg p-6 text-center">
          <div className="text-sm font-black text-ops-alert">{this.props.area}加载失败</div>
          <p className="mt-3 text-sm leading-6 text-ops-subtext">
            当前页面资源可能已经更新，浏览器仍在使用旧版本缓存。请重新加载页面获取最新前端资源。
          </p>
          <pre className="ops-data-panel mt-4 max-h-32 overflow-auto p-3 text-left text-xs text-ops-overlay">
            {this.state.message}
          </pre>
          <button
            className="ops-primary-action mt-5 px-4 py-2 text-sm"
            onClick={() => {
              window.sessionStorage.removeItem(CHUNK_RELOAD_KEY)
              window.location.reload()
            }}
          >
            重新加载
          </button>
        </div>
      </div>
    )
  }
}

const ChatWindow = lazyWithChunkRecovery(() => import('@/components/chat/ChatWindow'))
const Dashboard = lazyWithChunkRecovery(() => import('@/components/views/Dashboard'))
const AssetVault = lazyWithChunkRecovery(() => import('@/components/views/AssetVault'))
const ApprovalCenter = lazyWithChunkRecovery(() => import('@/components/views/ApprovalCenter'))
const SkillMarket = lazyWithChunkRecovery(() => import('@/components/views/SkillMarket'))
const KnowledgeBase = lazyWithChunkRecovery(() => import('@/components/views/KnowledgeBase'))
const CronManager = lazyWithChunkRecovery(() => import('@/components/views/CronManager'))
const AlertCenter = lazyWithChunkRecovery(() => import('@/components/views/AlertCenter'))
const RealtimeCanvas = lazyWithChunkRecovery(() => import('@/components/views/RealtimeCanvas'))
const ConnectionModal = lazyWithChunkRecovery(() => import('@/components/modals/ConnectionModal'))
const LLMConfigModal = lazyWithChunkRecovery(() => import('@/components/modals/LLMConfigModal'))
const NotificationsModal = lazyWithChunkRecovery(() => import('@/components/modals/NotificationsModal'))
const DynamicSkillsModal = lazyWithChunkRecovery(() => import('@/components/modals/DynamicSkillsModal'))
const SessionActionsModal = lazyWithChunkRecovery(() => import('@/components/modals/SessionActionsModal'))
const SafetyPolicyModal = lazyWithChunkRecovery(() => import('@/components/modals/SafetyPolicyModal'))

function ViewFallback() {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center bg-ops-dark text-sm text-ops-subtext">
      加载视图...
    </div>
  )
}

function ModalFallback() {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/55 text-sm text-ops-subtext">
      加载中...
    </div>
  )
}

function ViewRouter() {
  const currentView = useStore((s) => s.currentView)
  return (
    <ChunkErrorBoundary key={currentView} area="视图">
      <Suspense fallback={<ViewFallback />}>
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'bigscreen' && <Dashboard />}
        {currentView === 'chat' && <ChatWindow />}
        {currentView === 'assets' && <AssetVault />}
        {currentView === 'canvas' && <RealtimeCanvas />}
        {currentView === 'skills' && <SkillMarket />}
        {currentView === 'knowledge' && <KnowledgeBase />}
        {currentView === 'cron' && <CronManager />}
        {currentView === 'alerts' && <AlertCenter />}
        {currentView === 'approvals' && <ApprovalCenter />}
        {!['dashboard', 'bigscreen', 'chat', 'assets', 'canvas', 'skills', 'knowledge', 'cron', 'alerts', 'approvals'].includes(currentView) && <ChatWindow />}
      </Suspense>
    </ChunkErrorBoundary>
  )
}

function ModalRouter() {
  const activeModal = useStore((s) => s.activeModal)
  if (!activeModal) return null
  return (
    <ChunkErrorBoundary key={activeModal} area="弹窗">
      <Suspense fallback={<ModalFallback />}>
        {activeModal === 'connect' && <ConnectionModal />}
        {activeModal === 'llm-config' && <LLMConfigModal />}
        {activeModal === 'notifications' && <NotificationsModal />}
        {activeModal === 'safety-policy' && <SafetyPolicyModal />}
        {activeModal === 'dynamic-skills' && <DynamicSkillsModal />}
        {activeModal === 'session-actions' && <SessionActionsModal />}
      </Suspense>
    </ChunkErrorBoundary>
  )
}

export default function App() {
  const addSession = useStore((s) => s.addSession)
  const setCurrentSession = useStore((s) => s.setCurrentSession)
  const setView = useStore((s) => s.setView)
  const appendMessage = useStore((s) => s.appendMessage)
  const sessions = useStore((s) => s.sessions)
  const currentView = useStore((s) => s.currentView)
  const sidebarOpen = useStore((s) => s.sidebarOpen)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const restoreStartedRef = useRef(false)

  useEffect(() => {
    const handleHashChange = () => setView(viewFromLocationHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [setView])

  // Restore sessions from backend on mount
  useEffect(() => {
    if (restoreStartedRef.current) return
    restoreStartedRef.current = true

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
            asset_type: sinfo.asset_type || sinfo.protocol || 'ssh',
            protocol: sinfo.protocol || 'ssh',
            extra_args: sinfo.extra_args || {},
            heartbeatEnabled: sinfo.heartbeatEnabled || false,
            tags: sinfo.tags || ['未分组'],
            target_scope: sinfo.target_scope || 'asset',
            scope_value: sinfo.scope_value || null,
            messages: [],
            isStreaming: Boolean(sinfo.isStreaming),
            backendStreaming: Boolean(sinfo.isStreaming),
            historyLoaded: false,
          }, false)
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
            if (!m.content || !m.content.trim()) return
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

  const isChatView = currentView === 'chat'

  return (
    <div className="ops-shell grid h-screen grid-cols-[104px_minmax(0,1fr)] grid-rows-[56px_minmax(0,1fr)] overflow-hidden bg-ops-dark">
      {/* Global command bar */}
      <TopBar />

      {/* Left product nav */}
      <LeftNav />

      {/* Main product workspace */}
      <main className="min-h-0 min-w-0 overflow-hidden p-2 lg:p-3">
        {isChatView ? (
          <div
            className={`grid h-full min-h-0 gap-3 ${
              sidebarOpen
                ? 'grid-cols-[minmax(300px,320px)_minmax(0,1fr)]'
                : 'grid-cols-[minmax(0,1fr)]'
            }`}
          >
            <Sidebar />
            <ViewRouter />
          </div>
        ) : (
          <div className="h-full min-h-0 overflow-auto">
            <ViewRouter />
          </div>
        )}
      </main>

      {/* Modals */}
      <ModalRouter />

      {/* Toast notifications */}
      <ToastContainer />
    </div>
  )
}
