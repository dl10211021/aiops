import { useStore } from '@/store'
import { updateHeartbeat, updatePermission } from '@/api/client'
import type { ViewId } from '@/types'

const VIEW_LABELS: Record<ViewId, string> = {
  dashboard: '总览大屏',
  bigscreen: '总览大屏',
  chat: 'AI 会话',
  assets: '资产中心',
  cron: '自动化巡检',
  alerts: '告警事件',
  approvals: '审批中心',
  skills: '技能市场',
  knowledge: '知识库',
}

export default function TopBar() {
  const currentSessionId = useStore((s) => s.currentSessionId)
  const currentView = useStore((s) => s.currentView)
  const sessions = useStore((s) => s.sessions)
  const updateSession = useStore((s) => s.updateSession)
  const openModal = useStore((s) => s.openModal)
  const sidebarOpen = useStore((s) => s.sidebarOpen)
  const setSidebarOpen = useStore((s) => s.setSidebarOpen)
  const addToast = useStore((s) => s.addToast)

  const session = currentSessionId ? sessions[currentSessionId] : null
  const isChatView = currentView === 'chat'

  const togglePermission = async () => {
    if (!session) return
    try {
      const newMode = !session.isReadWriteMode
      await updatePermission(session.id, newMode)
      updateSession(session.id, { isReadWriteMode: newMode })
      addToast(newMode ? '已切换为读写模式' : '已切换为只读模式', 'info')
    } catch {
      addToast('权限切换失败', 'error')
    }
  }

  const toggleHeartbeat = async () => {
    if (!session) return
    try {
      const newState = !session.heartbeatEnabled
      await updateHeartbeat(session.id, newState)
      updateSession(session.id, { heartbeatEnabled: newState })
      addToast(newState ? '心跳巡检已开启' : '心跳巡检已关闭', 'info')
    } catch {
      addToast('心跳切换失败', 'error')
    }
  }

  return (
    <header className="h-14 bg-ops-panel/82 border-b border-ops-surface0/80 flex items-center px-4 gap-3 shrink-0 backdrop-blur-xl">
      {/* Sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="text-ops-subtext hover:text-ops-text text-lg rounded-lg px-2 py-1 hover:bg-ops-surface0/70"
        title="切换侧栏"
      >
        ☰
      </button>

      {session && isChatView ? (
        <>
          {/* Session info */}
          <div className="flex min-w-0 items-center gap-3 text-sm">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-ops-success shadow-[0_0_18px_rgba(79,209,177,0.65)]" />
            <span className="font-semibold text-ops-text truncate">
              {session.remark || session.host}
            </span>
            <span className="rounded-full border border-ops-surface1/70 bg-ops-dark/50 px-2 py-0.5 font-mono text-[11px] text-ops-subtext">
              {session.user}@{session.host} ({session.asset_type}/{session.protocol})
            </span>
          </div>

          <div className="flex-1" />

          {/* Action buttons */}
          <button
            onClick={togglePermission}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              session.isReadWriteMode
                ? 'border-ops-alert/40 bg-ops-alert/15 text-ops-alert'
                : 'border-ops-surface1/60 bg-ops-surface0/70 text-ops-subtext'
            }`}
            title={session.isReadWriteMode ? '当前: 读写模式' : '当前: 只读模式'}
          >
            {session.isReadWriteMode ? '🔓 读写' : '🔒 只读'}
          </button>

          <button
            onClick={toggleHeartbeat}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              session.heartbeatEnabled
                ? 'border-ops-success/40 bg-ops-success/15 text-ops-success'
                : 'border-ops-surface1/60 bg-ops-surface0/70 text-ops-subtext'
            }`}
          >
            {session.heartbeatEnabled ? '💓 巡检中' : '💤 巡检关'}
          </button>

          <button
            onClick={() => openModal('dynamic-skills')}
            className="text-xs px-3 py-1.5 rounded-full border border-ops-surface1/60 bg-ops-surface0/70 text-ops-subtext hover:text-ops-text transition-colors"
          >
            🧩 技能
          </button>

          <button
            onClick={() => openModal('session-actions')}
            className="text-ops-subtext hover:text-ops-text text-sm rounded-lg px-2 py-1 hover:bg-ops-surface0/70"
            title="更多操作"
          >
            ⋯
          </button>
        </>
      ) : (
        <>
          <div className="flex min-w-0 items-center gap-3 text-sm">
            <span className="font-semibold text-ops-text">{VIEW_LABELS[currentView] || 'OpsCore'}</span>
            {currentView === 'chat' && <span className="text-sm text-ops-subtext">请选择或新建一个会话</span>}
          </div>
          <div className="flex-1" />
        </>
      )}
    </header>
  )
}
