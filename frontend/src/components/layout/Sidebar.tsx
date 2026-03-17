import { useStore } from '@/store'
import type { Session } from '@/types'

export default function Sidebar() {
  const sessions = useStore((s) => s.sessions)
  const currentSessionId = useStore((s) => s.currentSessionId)
  const setCurrentSession = useStore((s) => s.setCurrentSession)
  const collapsedGroups = useStore((s) => s.collapsedGroups)
  const toggleGroup = useStore((s) => s.toggleGroup)
  const sidebarOpen = useStore((s) => s.sidebarOpen)
  const openModal = useStore((s) => s.openModal)
  const removeSession = useStore((s) => s.removeSession)
  const setView = useStore((s) => s.setView)

  if (!sidebarOpen) return null

  // Group sessions by group_name
  const grouped: Record<string, Session[]> = {}
  Object.values(sessions).forEach((s) => {
    const g = s.group_name || '未分组'
    if (!grouped[g]) grouped[g] = []
    grouped[g].push(s)
  })

  const handleDisconnect = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const { disconnectSession } = await import('@/api/client')
      await disconnectSession(sid)
      removeSession(sid)
    } catch {
      // ignore
    }
  }

  const protocolIcon = (p: string) => {
    switch (p) {
      case 'ssh': return '🖥️'
      case 'database': return '🗄️'
      case 'api': return '🌐'
      case 'winrm': return '🪟'
      default: return '📡'
    }
  }

  return (
    <aside className="w-60 bg-ops-sidebar border-r border-ops-surface0 flex flex-col shrink-0 overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-ops-surface0 flex items-center justify-between">
        <span className="text-sm font-semibold text-ops-text">活跃会话</span>
        <button
          onClick={() => openModal('connect')}
          className="text-xs bg-ops-accent/20 text-ops-accent px-2 py-1 rounded hover:bg-ops-accent/30 transition-colors"
        >
          + 新建
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {Object.keys(grouped).length === 0 && (
          <div className="text-xs text-ops-subtext text-center mt-8 px-2">
            暂无活跃会话<br />
            点击上方「+ 新建」开始连接
          </div>
        )}

        {Object.entries(grouped).map(([group, items]) => (
          <div key={group}>
            {/* Group header */}
            <button
              onClick={() => toggleGroup(group)}
              className="w-full flex items-center gap-1 px-2 py-1.5 text-xs text-ops-subtext hover:text-ops-text transition-colors"
            >
              <span className="text-[10px]">{collapsedGroups.has(group) ? '▶' : '▼'}</span>
              <span>{group}</span>
              <span className="ml-auto text-ops-overlay">{items.length}</span>
            </button>

            {/* Group items */}
            {!collapsedGroups.has(group) && items.map((s) => (
              <div
                key={s.id}
                onClick={() => { setCurrentSession(s.id); setView('chat') }}
                className={`group flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-sm transition-colors
                  ${s.id === currentSessionId
                    ? 'bg-ops-accent/15 text-ops-accent'
                    : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'}`}
              >
                <span className="text-sm shrink-0">{protocolIcon(s.protocol)}</span>
                <div className="flex-1 min-w-0">
                  <div className="truncate text-xs font-medium">
                    {s.remark || s.host}
                  </div>
                  <div className="truncate text-[10px] text-ops-overlay">
                    {s.user}@{s.host}
                  </div>
                </div>
                {/* Status indicators */}
                <div className="flex items-center gap-1 shrink-0">
                  {s.heartbeatEnabled && <span className="w-1.5 h-1.5 rounded-full bg-ops-success animate-pulse" title="心跳中" />}
                  {s.isReadWriteMode && <span className="text-[9px] text-ops-alert" title="读写模式">RW</span>}
                </div>
                {/* Disconnect button */}
                <button
                  onClick={(e) => handleDisconnect(s.id, e)}
                  className="hidden group-hover:block text-ops-alert text-xs hover:text-red-400"
                  title="断开"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
    </aside>
  )
}
