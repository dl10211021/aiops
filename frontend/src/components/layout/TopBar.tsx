import { useStore } from '@/store'

export default function TopBar() {
  const currentSessionId = useStore((s) => s.currentSessionId)
  const sessions = useStore((s) => s.sessions)
  const updateSession = useStore((s) => s.updateSession)
  const openModal = useStore((s) => s.openModal)
  const sidebarOpen = useStore((s) => s.sidebarOpen)
  const setSidebarOpen = useStore((s) => s.setSidebarOpen)
  const addToast = useStore((s) => s.addToast)

  const session = currentSessionId ? sessions[currentSessionId] : null

  const togglePermission = async () => {
    if (!session) return
    try {
      const { updatePermission } = await import('@/api/client')
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
      const { updateHeartbeat } = await import('@/api/client')
      const newState = !session.heartbeatEnabled
      await updateHeartbeat(session.id, newState)
      updateSession(session.id, { heartbeatEnabled: newState })
      addToast(newState ? '心跳巡检已开启' : '心跳巡检已关闭', 'info')
    } catch {
      addToast('心跳切换失败', 'error')
    }
  }

  return (
    <header className="h-12 bg-ops-panel border-b border-ops-surface0 flex items-center px-3 gap-3 shrink-0">
      {/* Sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="text-ops-subtext hover:text-ops-text text-lg"
        title="切换侧栏"
      >
        ☰
      </button>

      {session ? (
        <>
          {/* Session info */}
          <div className="flex items-center gap-2 text-sm min-w-0">
            <span className="font-medium text-ops-text truncate">
              {session.remark || session.host}
            </span>
            <span className="text-ops-overlay text-xs">
              {session.user}@{session.host} ({session.protocol})
            </span>
          </div>

          <div className="flex-1" />

          {/* Action buttons */}
          <button
            onClick={togglePermission}
            className={`text-xs px-2.5 py-1 rounded transition-colors ${
              session.isReadWriteMode
                ? 'bg-ops-alert/20 text-ops-alert'
                : 'bg-ops-surface0 text-ops-subtext'
            }`}
            title={session.isReadWriteMode ? '当前: 读写模式' : '当前: 只读模式'}
          >
            {session.isReadWriteMode ? '🔓 读写' : '🔒 只读'}
          </button>

          <button
            onClick={toggleHeartbeat}
            className={`text-xs px-2.5 py-1 rounded transition-colors ${
              session.heartbeatEnabled
                ? 'bg-ops-success/20 text-ops-success'
                : 'bg-ops-surface0 text-ops-subtext'
            }`}
          >
            {session.heartbeatEnabled ? '💓 巡检中' : '💤 巡检关'}
          </button>

          <button
            onClick={() => openModal('dynamic-skills')}
            className="text-xs px-2.5 py-1 rounded bg-ops-surface0 text-ops-subtext hover:text-ops-text transition-colors"
          >
            🧩 技能
          </button>

          <button
            onClick={() => openModal('session-actions')}
            className="text-ops-subtext hover:text-ops-text text-sm"
            title="更多操作"
          >
            ⋯
          </button>
        </>
      ) : (
        <>
          <span className="text-sm text-ops-subtext">请选择或新建一个会话</span>
          <div className="flex-1" />
        </>
      )}
    </header>
  )
}
