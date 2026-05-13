import { memo, useEffect, useState } from 'react'
import type { KeyboardEvent, MouseEvent } from 'react'
import type { Session } from '@/types'
import SessionItem from './SessionItem'
import { DEFAULT_SESSION_GROUP } from './sessionGroups'
import { summarizeSessions } from './sessionMetrics'

const DEFAULT_GROUP_SESSION_LIMIT = 50
const GROUP_SESSION_LIMIT_STEP = 50

interface SessionGroupListProps {
  collapsedGroups: Set<string>
  currentSessionId: string | null
  grouped: Record<string, Session[]>
  groupNames: string[]
  selectedGroup: string
  sessionList: Session[]
  onDisconnect: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
  onEdit: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
  onOpenTerminal: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
  onDeleteGroup: (group: string) => void
  onRenameGroup: (oldName: string, newName: string) => boolean
  onSelectGroup: (group: string) => void
  onSelectSession: (sessionId: string, group: string) => void
  onToggleGroup: (group: string) => void
  searching?: boolean
}

function SessionGroupList({
  collapsedGroups,
  currentSessionId,
  grouped,
  groupNames,
  selectedGroup,
  sessionList,
  onDisconnect,
  onEdit,
  onOpenTerminal,
  onDeleteGroup,
  onRenameGroup,
  onSelectGroup,
  onSelectSession,
  onToggleGroup,
  searching = false,
}: SessionGroupListProps) {
  const [renamingGroup, setRenamingGroup] = useState<string | null>(null)
  const [renameDraft, setRenameDraft] = useState('')
  const [expandedLimits, setExpandedLimits] = useState<Record<string, number>>({})

  useEffect(() => {
    if (renamingGroup && !groupNames.includes(renamingGroup)) {
      setRenamingGroup(null)
      setRenameDraft('')
    }
  }, [groupNames, renamingGroup])

  useEffect(() => {
    setExpandedLimits((current) => {
      const visible = new Set(groupNames)
      const next = Object.fromEntries(Object.entries(current).filter(([group]) => visible.has(group)))
      return Object.keys(next).length === Object.keys(current).length ? current : next
    })
  }, [groupNames])

  const startRename = (group: string) => {
    setRenamingGroup(group)
    setRenameDraft(group)
    onSelectGroup(group)
  }

  const cancelRename = () => {
    setRenamingGroup(null)
    setRenameDraft('')
  }

  const submitRename = () => {
    if (!renamingGroup) return
    const saved = onRenameGroup(renamingGroup, renameDraft)
    if (saved) cancelRename()
  }

  const handleRenameKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') submitRename()
    if (event.key === 'Escape') cancelRename()
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-2">
      {sessionList.length === 0 && (
        <div className="mt-8 rounded-lg border border-ops-surface1/70 bg-ops-surface0/50 px-3 py-5 text-center text-xs leading-5 text-ops-subtext">
          {searching ? '没有匹配的会话' : '暂无活跃会话'}
          <br />
          {searching ? '调整搜索关键词后再试' : '点击上方「+ 新建」连接资产'}
        </div>
      )}

      {groupNames.map((group) => {
        const items = grouped[group] || []
        const limit = expandedLimits[group] || DEFAULT_GROUP_SESSION_LIMIT
        const visibleItems = visibleGroupSessions(items, limit, currentSessionId)
        const hiddenCount = Math.max(0, items.length - visibleItems.length)
        const selected = group === selectedGroup
        const isDefaultGroup = group === DEFAULT_SESSION_GROUP
        const renaming = renamingGroup === group
        return (
          <section
            key={group}
            className="group/session mb-3"
          >
            <div className={`flex items-center gap-1 rounded-lg px-1 py-1 transition-colors ${
              selected ? 'bg-ops-accent/8 text-ops-text' : 'text-ops-subtext hover:bg-ops-surface0/42 hover:text-ops-text'
            }`}>
              <button
                onClick={() => onToggleGroup(group)}
                className="grid h-7 w-5 shrink-0 place-items-center rounded-md text-[10px] hover:bg-ops-surface0 hover:text-ops-text"
                title={collapsedGroups.has(group) ? '展开组' : '折叠组'}
              >
                {collapsedGroups.has(group) ? '▶' : '▼'}
              </button>
              {renaming ? (
                <div className="grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_36px_36px] gap-1">
                  <input
                    autoFocus
                    value={renameDraft}
                    onChange={(event) => setRenameDraft(event.target.value)}
                    onKeyDown={handleRenameKeyDown}
                    className="h-7 min-w-0 rounded-md border border-ops-accent/60 bg-ops-dark/55 px-2 text-xs font-semibold text-ops-text outline-none"
                    aria-label={`重命名会话组 ${group}`}
                  />
                  <button
                    onClick={submitRename}
                    className="rounded-md border border-ops-accent/45 bg-ops-accent/12 text-[11px] font-bold text-ops-accent hover:bg-ops-accent/18"
                    title="保存组名称"
                  >
                    保存
                  </button>
                  <button
                    onClick={cancelRename}
                    className="rounded-md border border-ops-surface1 bg-ops-surface0/60 text-[11px] font-semibold text-ops-subtext hover:text-ops-text"
                    title="取消重命名"
                  >
                    取消
                  </button>
                </div>
              ) : (
                <>
                  <button
                    onClick={() => onSelectGroup(group)}
                    className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 py-1 text-left text-xs transition-colors hover:text-ops-text"
                    title={group}
                  >
                    <span className="truncate text-sm font-black text-ops-text">{group}</span>
                    <GroupMetrics sessions={items} />
                  </button>
                  {!isDefaultGroup && (
                    <div className={`flex shrink-0 items-center gap-1 transition-opacity ${
                      selected ? 'opacity-90' : 'opacity-0 group-hover/session:opacity-80'
                    }`}>
                      <button
                        onClick={() => startRename(group)}
                        className="rounded-md border border-ops-surface1/70 bg-ops-dark/45 px-1.5 py-0.5 text-[11px] font-semibold text-ops-subtext transition-colors hover:border-ops-accent hover:text-ops-text"
                        title={`重命名 ${group}`}
                      >
                        改名
                      </button>
                      <button
                        onClick={() => onDeleteGroup(group)}
                        className="rounded-md border border-ops-alert/35 bg-ops-alert/8 px-1.5 py-0.5 text-[11px] font-semibold text-ops-alert transition-colors hover:bg-ops-alert/14"
                        title={`删除 ${group}`}
                      >
                        删除
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {!collapsedGroups.has(group) && (
              <div className="grid gap-1.5 pt-1.5">
                {items.length === 0 ? (
                  <div className="rounded-md border border-dashed border-ops-surface1/70 px-3 py-2 text-[11px] text-ops-overlay">
                    暂无会话
                  </div>
                ) : (
                  <>
                    {visibleItems.map((session) => (
                      <SessionItem
                        key={session.id}
                        session={session}
                        active={session.id === currentSessionId}
                        group={group}
                        onSelectSession={onSelectSession}
                        onDisconnect={onDisconnect}
                        onEdit={onEdit}
                        onOpenTerminal={onOpenTerminal}
                      />
                    ))}
                    {hiddenCount > 0 && (
                      <button
                        type="button"
                        onClick={() => {
                          setExpandedLimits((current) => ({
                            ...current,
                            [group]: (current[group] || DEFAULT_GROUP_SESSION_LIMIT) + GROUP_SESSION_LIMIT_STEP,
                          }))
                        }}
                        className="rounded-lg border border-ops-surface1/70 bg-ops-surface0/55 px-3 py-2 text-xs font-semibold text-ops-subtext transition-colors hover:border-ops-accent/45 hover:text-ops-text"
                      >
                        还有 {hiddenCount} 个{searching ? '匹配' : ''}会话，继续显示
                      </button>
                    )}
                  </>
                )}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}

export default memo(SessionGroupList, areSessionGroupListPropsEqual)

function visibleGroupSessions(items: Session[], limit: number, currentSessionId: string | null) {
  const visibleItems = items.slice(0, limit)
  if (!currentSessionId || visibleItems.some((session) => session.id === currentSessionId)) {
    return visibleItems
  }
  const activeSession = items.find((session) => session.id === currentSessionId)
  if (!activeSession) return visibleItems
  return [activeSession, ...visibleItems.slice(0, Math.max(0, limit - 1))]
}

function areSessionGroupListPropsEqual(prev: SessionGroupListProps, next: SessionGroupListProps) {
  return prev.collapsedGroups === next.collapsedGroups
    && prev.currentSessionId === next.currentSessionId
    && prev.grouped === next.grouped
    && prev.groupNames === next.groupNames
    && prev.selectedGroup === next.selectedGroup
    && prev.sessionList === next.sessionList
    && prev.onDisconnect === next.onDisconnect
    && prev.onEdit === next.onEdit
    && prev.onOpenTerminal === next.onOpenTerminal
    && prev.onDeleteGroup === next.onDeleteGroup
    && prev.onRenameGroup === next.onRenameGroup
    && prev.onSelectGroup === next.onSelectGroup
    && prev.onSelectSession === next.onSelectSession
    && prev.onToggleGroup === next.onToggleGroup
    && prev.searching === next.searching
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
