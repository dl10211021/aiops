import { Component, lazy, Suspense, useEffect, useRef, useState, type ComponentType, type ErrorInfo, type ReactNode } from 'react'
import { useStore, viewFromLocationHash } from '@/store'
import LeftNav from '@/components/layout/LeftNav'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import ToastContainer from '@/components/layout/ToastContainer'
import { getActiveSessions, pollAllSessions } from '@/api/client'
import type { ChatMessage, Session, ViewId } from '@/types'

const CHUNK_RELOAD_KEY = 'opscore:chunk-reload-at'
const CHUNK_RELOAD_COOLDOWN_MS = 15000

function isChunkLoadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error || '')
  return /Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk|ChunkLoadError/i.test(message)
}

function lazyWithChunkRecovery<T extends { default: ComponentType<unknown> }>(factory: () => Promise<T>) {
  return lazy(() => factory().then((module) => {
    window.sessionStorage.removeItem(CHUNK_RELOAD_KEY)
    return module
  }).catch((error) => {
    const lastReload = Number(window.sessionStorage.getItem(CHUNK_RELOAD_KEY) || '0')
    const canReload = !Number.isFinite(lastReload) || Date.now() - lastReload > CHUNK_RELOAD_COOLDOWN_MS
    if (isChunkLoadError(error) && canReload) {
      window.sessionStorage.setItem(CHUNK_RELOAD_KEY, String(Date.now()))
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

const loadChatWindow = () => import('@/components/chat/ChatWindow')
const loadDashboard = () => import('@/components/views/Dashboard')
const loadAssetVault = () => import('@/components/views/AssetVault')
const loadApprovalCenter = () => import('@/components/views/ApprovalCenter')
const loadSkillMarket = () => import('@/components/views/SkillMarket')
const loadToolCenter = () => import('@/components/views/ToolCenter')
const loadKnowledgeBase = () => import('@/components/views/KnowledgeBase')
const loadCronManager = () => import('@/components/views/CronManager')
const loadAlertCenter = () => import('@/components/views/AlertCenter')
const loadRealtimeCanvas = () => import('@/components/views/RealtimeCanvas')
const loadObservabilityCenter = () => import('@/components/views/ObservabilityCenter')
const loadSystemConfigCenter = () => import('@/components/views/SystemConfigCenter')
const loadConnectionModal = () => import('@/components/modals/ConnectionModal')
const loadLLMConfigModal = () => import('@/components/modals/LLMConfigModal')
const loadNotificationsModal = () => import('@/components/modals/NotificationsModal')
const loadSessionRetentionConfigModal = () => import('@/components/modals/SessionRetentionConfigModal')
const loadDynamicSkillsModal = () => import('@/components/modals/DynamicSkillsModal')
const loadSessionActionsModal = () => import('@/components/modals/SessionActionsModal')
const loadSafetyPolicyModal = () => import('@/components/modals/SafetyPolicyModal')

const ChatWindow = lazyWithChunkRecovery(loadChatWindow)
const Dashboard = lazyWithChunkRecovery(loadDashboard)
const AssetVault = lazyWithChunkRecovery(loadAssetVault)
const ApprovalCenter = lazyWithChunkRecovery(loadApprovalCenter)
const SkillMarket = lazyWithChunkRecovery(loadSkillMarket)
const ToolCenter = lazyWithChunkRecovery(loadToolCenter)
const KnowledgeBase = lazyWithChunkRecovery(loadKnowledgeBase)
const CronManager = lazyWithChunkRecovery(loadCronManager)
const AlertCenter = lazyWithChunkRecovery(loadAlertCenter)
const RealtimeCanvas = lazyWithChunkRecovery(loadRealtimeCanvas)
const ObservabilityCenter = lazyWithChunkRecovery(loadObservabilityCenter)
const SystemConfigCenter = lazyWithChunkRecovery(loadSystemConfigCenter)
const ConnectionModal = lazyWithChunkRecovery(loadConnectionModal)
const LLMConfigModal = lazyWithChunkRecovery(loadLLMConfigModal)
const NotificationsModal = lazyWithChunkRecovery(loadNotificationsModal)
const SessionRetentionConfigModal = lazyWithChunkRecovery(loadSessionRetentionConfigModal)
const DynamicSkillsModal = lazyWithChunkRecovery(loadDynamicSkillsModal)
const SessionActionsModal = lazyWithChunkRecovery(loadSessionActionsModal)
const SafetyPolicyModal = lazyWithChunkRecovery(loadSafetyPolicyModal)

const ROUTE_PRELOADERS: Partial<Record<ViewId, () => Promise<unknown>>> = {
  dashboard: loadDashboard,
  chat: loadChatWindow,
  observability: loadObservabilityCenter,
  assets: loadAssetVault,
  canvas: loadRealtimeCanvas,
  skills: loadSkillMarket,
  tools: loadToolCenter,
  knowledge: loadKnowledgeBase,
  cron: loadCronManager,
  alerts: loadAlertCenter,
  approvals: loadApprovalCenter,
  config: loadSystemConfigCenter,
}

function preloadViewChunk(view: ViewId) {
  void ROUTE_PRELOADERS[view]?.().catch(() => undefined)
}

const BACKGROUND_ROUTE_PRELOADERS = [
  loadKnowledgeBase,
  loadSkillMarket,
  loadToolCenter,
  loadAssetVault,
  loadSystemConfigCenter,
  loadDashboard,
]
const BACKGROUND_PRELOAD_START_DELAY_MS = 5000
const BACKGROUND_PRELOAD_STEP_DELAY_MS = 1400
const CHAT_INITIAL_RENDER_DELAY_MS = 180
const NON_CHAT_SESSION_RESTORE_DELAY_MS = 1200
const SESSION_POLL_INTERVAL_MS = 5000
const IDLE_SESSION_POLL_INTERVAL_MS = 15000
const HIDDEN_SESSION_POLL_INTERVAL_MS = 30000

function ViewFallback() {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center bg-ops-dark/82 p-6 text-sm text-ops-subtext">
      <div className="ops-data-panel flex min-w-[240px] items-center gap-3 rounded-2xl px-4 py-3">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-ops-accent shadow-[0_0_16px_rgba(40,208,168,0.45)]" />
        <span>加载视图...</span>
      </div>
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

function DeferredChatWindow() {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setReady(true), CHAT_INITIAL_RENDER_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [])
  return ready ? <ChatWindow /> : <ViewFallback />
}

function ViewRouter() {
  const currentView = useStore((s) => s.currentView)
  return (
    <ChunkErrorBoundary key={currentView} area="视图">
      <Suspense fallback={<ViewFallback />}>
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'bigscreen' && <Dashboard />}
        {currentView === 'chat' && <DeferredChatWindow />}
        {currentView === 'observability' && <ObservabilityCenter />}
        {currentView === 'assets' && <AssetVault />}
        {currentView === 'canvas' && <RealtimeCanvas />}
        {currentView === 'skills' && <SkillMarket />}
        {currentView === 'tools' && <ToolCenter />}
        {currentView === 'knowledge' && <KnowledgeBase />}
        {currentView === 'cron' && <CronManager />}
        {currentView === 'alerts' && <AlertCenter />}
        {currentView === 'approvals' && <ApprovalCenter />}
        {currentView === 'config' && <SystemConfigCenter />}
        {!['dashboard', 'bigscreen', 'chat', 'observability', 'assets', 'canvas', 'skills', 'tools', 'knowledge', 'cron', 'alerts', 'approvals', 'config'].includes(currentView) && <DeferredChatWindow />}
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
        {activeModal === 'session-retention' && <SessionRetentionConfigModal />}
        {activeModal === 'safety-policy' && <SafetyPolicyModal />}
        {activeModal === 'dynamic-skills' && <DynamicSkillsModal />}
        {activeModal === 'session-actions' && <SessionActionsModal />}
      </Suspense>
    </ChunkErrorBoundary>
  )
}

export default function App() {
  const restoreSessions = useStore((s) => s.restoreSessions)
  const setView = useStore((s) => s.setView)
  const appendMessage = useStore((s) => s.appendMessage)
  const currentView = useStore((s) => s.currentView)
  const sidebarOpen = useStore((s) => s.sidebarOpen)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const restoreStartedRef = useRef(false)

  useEffect(() => {
    const handleHashChange = () => setView(viewFromLocationHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [setView])

  // Restore sessions from backend on mount
  useEffect(() => {
    if (restoreStartedRef.current) return

    const restore = async () => {
      if (restoreStartedRef.current) return
      restoreStartedRef.current = true
      try {
        const res = await getActiveSessions()
        const serverSessions = res.data.sessions || {}
        let firstId: string | null = null
        const restoredSessions: Session[] = []

        for (const [sid, sinfo] of Object.entries(serverSessions)) {
          if (!firstId) firstId = sid
          restoredSessions.push({
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
          })
        }

        restoreSessions(restoredSessions, firstId)
      } catch { /* backend not ready */ }
    }

    const delay = currentView === 'chat' ? 0 : NON_CHAT_SESSION_RESTORE_DELAY_MS
    const timer = window.setTimeout(() => void restore(), delay)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentView, restoreSessions])

  useEffect(() => {
    if (currentView === 'chat') return

    let cancelled = false
    const timeoutIds = new Set<ReturnType<typeof window.setTimeout>>()
    const idleIds = new Set<number>()
    const requestIdle = window.requestIdleCallback || ((callback) => window.setTimeout(callback, 1200))
    const cancelIdle = window.cancelIdleCallback || window.clearTimeout

    const schedulePreload = (index: number) => {
      if (cancelled || index >= BACKGROUND_ROUTE_PRELOADERS.length) return
      const delay = index === 0 ? BACKGROUND_PRELOAD_START_DELAY_MS : BACKGROUND_PRELOAD_STEP_DELAY_MS
      const timeoutId = window.setTimeout(() => {
        timeoutIds.delete(timeoutId)
        if (cancelled) return
        const idleId = requestIdle(() => {
          idleIds.delete(Number(idleId))
          if (cancelled) return
          void BACKGROUND_ROUTE_PRELOADERS[index]().catch(() => undefined).finally(() => schedulePreload(index + 1))
        })
        idleIds.add(Number(idleId))
      }, delay)
      timeoutIds.add(timeoutId)
    }

    const pausePreloadingForInteraction = () => {
      if (cancelled) return
      timeoutIds.forEach((id) => window.clearTimeout(id))
      timeoutIds.clear()
      idleIds.forEach((id) => cancelIdle(id))
      idleIds.clear()
    }

    schedulePreload(0)
    window.addEventListener('pointerdown', pausePreloadingForInteraction, { once: true, capture: true })
    window.addEventListener('keydown', pausePreloadingForInteraction, { once: true, capture: true })
    return () => {
      cancelled = true
      window.removeEventListener('pointerdown', pausePreloadingForInteraction, { capture: true })
      window.removeEventListener('keydown', pausePreloadingForInteraction, { capture: true })
      timeoutIds.forEach((id) => window.clearTimeout(id))
      idleIds.forEach((id) => cancelIdle(id))
    }
  }, [currentView])

  // Heartbeat polling
  useEffect(() => {
    let cancelled = false
    let inFlight = false

    const schedulePoll = (delay: number) => {
      if (cancelled) return
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current)
      pollTimerRef.current = window.setTimeout(() => void poll(), delay)
    }

    const poll = async () => {
      if (document.visibilityState === 'hidden') {
        schedulePoll(HIDDEN_SESSION_POLL_INTERVAL_MS)
        return
      }
      if (inFlight) {
        schedulePoll(SESSION_POLL_INTERVAL_MS)
        return
      }
      const sessions = useStore.getState().sessions
      if (Object.keys(sessions).length === 0) {
        schedulePoll(IDLE_SESSION_POLL_INTERVAL_MS)
        return
      }
      inFlight = true
      try {
        const res = await pollAllSessions()
        const updates = res.data.updates || {}
        const latestSessions = useStore.getState().sessions
        for (const [sid, msgs] of Object.entries(updates)) {
          if (!latestSessions[sid]) continue
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
      finally {
        inFlight = false
        schedulePoll(SESSION_POLL_INTERVAL_MS)
      }
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState !== 'visible') return
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current)
      void poll()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    schedulePoll(SESSION_POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (pollTimerRef.current) window.clearTimeout(pollTimerRef.current)
    }
  }, [appendMessage])

  const isChatView = currentView === 'chat'

  return (
    <div className="ops-shell grid h-screen grid-cols-[104px_minmax(0,1fr)] grid-rows-[56px_minmax(0,1fr)] overflow-hidden bg-ops-dark">
      {/* Global command bar */}
      <TopBar />

      {/* Left product nav */}
      <LeftNav onPreloadView={preloadViewChunk} />

      {/* Main product workspace */}
      <main className="min-h-0 min-w-0 overflow-hidden p-2 lg:p-3">
        {isChatView ? (
          <div
            className={`ops-chat-workspace grid h-full min-h-0 gap-3 ${
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
