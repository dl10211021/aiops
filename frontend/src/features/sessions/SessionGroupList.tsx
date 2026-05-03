import type { MouseEvent } from 'react'
import type { Session } from '@/types'
import SessionItem from './SessionItem'
import { summarizeSessions } from './sessionMetrics'

interface SessionGroupListProps {
  collapsedGroups: Set<string>
  currentSessionId: string | null
  grouped: Record<string, Session[]>
  groupNames: string[]
  selectedGroup: string
  sessionList: Session[]
  onDisconnect: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
  onSelectGroup: (group: string) => void
  onSelectSession: (sessionId: string, group: string) => void
  onToggleGroup: (group: string) => void
}

export default function SessionGroupList({
  collapsedGroups,
  currentSessionId,
  grouped,
  groupNames,
  selectedGroup,
  sessionList,
  onDisconnect,
  onSelectGroup,
  onSelectSession,
  onToggleGroup,
}: SessionGroupListProps) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-2">
      {sessionList.length === 0 && (
        <div className="mt-8 rounded-lg border border-ops-surface1/70 bg-ops-surface0/50 px-3 py-5 text-center text-xs leading-5 text-ops-subtext">
          暂无活跃会话
          <br />
          点击上方「+ 新建」连接资产
        </div>
      )}

      {groupNames.map((group) => {
        const items = grouped[group] || []
        const selected = group === selectedGroup
        return (
          <section
            key={group}
            className={`mb-2 rounded-lg border bg-ops-panel transition-colors ${
              selected ? 'border-ops-accent/55 shadow-[0_0_0_1px_rgba(40,208,168,0.14)]' : 'border-ops-surface1/70'
            }`}
          >
            <div className="flex items-center gap-1 px-1.5 py-1">
              <button
                onClick={() => onToggleGroup(group)}
                className="grid h-8 w-7 shrink-0 place-items-center rounded-md text-[10px] text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text"
                title={collapsedGroups.has(group) ? '展开组' : '折叠组'}
              >
                {collapsedGroups.has(group) ? '▶' : '▼'}
              </button>
              <button
                onClick={() => onSelectGroup(group)}
                className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 py-1.5 text-left text-xs text-ops-subtext transition-colors hover:text-ops-text"
                title={group}
              >
                <span className="truncate font-semibold">{group}</span>
                <GroupMetrics sessions={items} />
              </button>
            </div>

            {!collapsedGroups.has(group) && (
              <div className="grid gap-1 px-1.5 pb-1.5">
                {items.length === 0 ? (
                  <div className="rounded-md border border-dashed border-ops-surface1/70 px-3 py-2 text-[11px] text-ops-overlay">
                    暂无会话
                  </div>
                ) : items.map((session) => (
                  <SessionItem
                    key={session.id}
                    session={session}
                    active={session.id === currentSessionId}
                    onSelect={() => onSelectSession(session.id, group)}
                    onDisconnect={onDisconnect}
                  />
                ))}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}

function GroupMetrics({ sessions }: { sessions: Session[] }) {
  const metrics = summarizeSessions(sessions)
  return (
    <span className="ml-auto flex items-center gap-1.5 text-ops-overlay">
      {metrics.needsAttention > 0 && (
        <span className="inline-flex items-center gap-1 text-yellow-100" title="有会话等待处理">
          <span className="h-1.5 w-1.5 rounded-full bg-yellow-300 animate-pulse" />
          {metrics.needsAttention}
        </span>
      )}
      {metrics.running > 0 && (
        <span className="inline-flex items-center gap-1 text-ops-accent" title="有会话正在执行">
          <span className="h-1.5 w-1.5 rounded-full bg-ops-accent animate-pulse" />
          {metrics.running}
        </span>
      )}
      <span>{metrics.total}</span>
    </span>
  )
}
