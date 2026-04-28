import { useStore } from '@/store'
import { disconnectSession } from '@/api/client'
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

  // Group sessions by tags[0]
  const grouped: Record<string, Session[]> = {}
  Object.values(sessions).forEach((s) => {
    const g = (s.tags && s.tags[0]) || '未分组'
    if (!grouped[g]) grouped[g] = []
    grouped[g].push(s)
  })

  const handleDisconnect = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await disconnectSession(sid)
      removeSession(sid)
    } catch {
      // ignore
    }
  }

  const protocolIcon = (p: string) => {
    switch (p) {
      case 'ssh': return 'SSH'
      case 'mysql':
      case 'oracle':
      case 'postgresql':
      case 'mssql':
      case 'database': return 'DB'
      case 'http_api':
      case 'api': return 'API'
      case 'winrm': return 'WIN'
      case 'snmp': return 'SN'
      default: return 'IO'
    }
  }

  return (
    <aside className="w-72 bg-ops-sidebar/82 border-r border-ops-surface0/80 flex flex-col shrink-0 overflow-hidden backdrop-blur-xl">
      {/* Header */}
      <div className="p-4 border-b border-ops-surface0/80 flex items-center justify-between">
        <div>
          <span className="block text-sm font-semibold text-ops-text">活跃会话</span>
          <span className="text-[10px] uppercase tracking-[0.18em] text-ops-overlay">asset linked agents</span>
        </div>
        <button
          onClick={() => openModal('connect')}
          className="text-xs bg-ops-accent text-ops-dark px-3 py-1.5 rounded-full font-semibold hover:bg-ops-accent/85 transition-colors"
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
              <span className="ml-auto flex items-center gap-1.5 text-ops-overlay">
                {items.some((s) => s.isStreaming) && (
                  <span className="inline-flex items-center gap-1 text-ops-accent" title="有会话正在执行">
                    <span className="h-1.5 w-1.5 rounded-full bg-ops-accent animate-pulse" />
                    {items.filter((s) => s.isStreaming).length}
                  </span>
                )}
                <span>{items.length}</span>
              </span>
            </button>

            {/* Group items */}
            {!collapsedGroups.has(group) && items.map((s) => (
              <div
                key={s.id}
                onClick={() => { setCurrentSession(s.id); setView('chat') }}
                className={`group flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer text-sm transition-all border
                  ${s.id === currentSessionId
                    ? 'border-ops-accent/35 bg-ops-accent/12 text-ops-accent shadow-[0_0_28px_rgba(243,177,90,0.12)]'
                    : 'border-transparent text-ops-subtext hover:bg-ops-surface0/70 hover:text-ops-text'}`}
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ops-dark/70 font-mono text-[10px] font-bold tracking-[0.08em]">{protocolIcon(s.protocol || s.asset_type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-semibold">
                      {s.remark || s.host}
                    </span>
                    {s.isStreaming && (
                      <span
                        className="inline-flex shrink-0 items-center gap-1 rounded-full border border-ops-accent/35 bg-ops-accent/10 px-1.5 py-0.5 text-[10px] font-semibold text-ops-accent"
                        title="AI 正在执行"
                        aria-label="AI 正在执行"
                      >
                        <span className="h-2 w-2 rounded-full border border-ops-accent/35 border-t-ops-accent animate-spin" />
                        执行中
                      </span>
                    )}
                  </div>
                  <div className="truncate font-mono text-[10px] text-ops-overlay">
                    {s.user}@{s.host}
                  </div>
                </div>
                {/* Status indicators */}
                <div className="flex items-center gap-1 shrink-0">
                  {s.heartbeatEnabled && <span className="w-1.5 h-1.5 rounded-full bg-ops-success animate-pulse" title="心跳中" />}
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
