import type { MouseEvent } from 'react'
import type { Session } from '@/types'
import { protocolLabel } from '@/utils/assetDisplay'
import { sessionAttention } from './sessionAttention'
import { isSessionRunning } from './sessionMetrics'

interface SessionItemProps {
  session: Session
  active: boolean
  onSelect: () => void
  onDisconnect: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
  onEdit: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
}

export default function SessionItem({
  session,
  active,
  onSelect,
  onDisconnect,
  onEdit,
}: SessionItemProps) {
  const attention = sessionAttention(session)
  const needsAttention = attention.type !== 'none'
  const running = isSessionRunning(session)
  const protocolText = protocolLabel(session.protocol || session.asset_type)
  const messageCount = session.messages?.length || 0
  const skillCount = session.skills?.length || 0
  const assetText = session.asset_type || session.protocol || 'asset'
  return (
    <div
      onClick={onSelect}
      className={`group relative grid min-h-[72px] cursor-pointer grid-cols-[44px_minmax(0,1fr)] gap-2.5 overflow-hidden rounded-xl border px-2.5 py-2.5 text-sm transition-colors duration-150
        ${active
          ? 'border-ops-accent/60 bg-[linear-gradient(135deg,rgba(40,208,168,0.16),rgba(15,36,56,0.76))] text-ops-accent shadow-[inset_0_0_0_1px_rgba(40,208,168,0.08)]'
          : needsAttention
            ? 'border-yellow-300/30 bg-[linear-gradient(135deg,rgba(253,224,71,0.12),rgba(18,32,49,0.72))] text-ops-text hover:border-yellow-300/45'
            : 'border-ops-surface1/45 bg-[linear-gradient(135deg,rgba(23,35,53,0.64),rgba(9,20,35,0.82))] text-ops-subtext hover:border-ops-accent/30 hover:text-ops-text'}`}
    >
      <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-ops-accent/28 to-transparent" />
      <span
        title={`${session.asset_type}/${session.protocol}`}
        className="relative grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-ops-surface1/65 bg-ops-dark/78 px-1 text-center text-[10px] font-black leading-tight text-ops-text shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
      >
        <span
          className={`absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border border-ops-panel ${
            running
              ? 'bg-ops-accent shadow-[0_0_10px_rgba(40,208,168,0.85)] animate-pulse'
              : 'bg-ops-success shadow-[0_0_8px_rgba(90,214,125,0.6)]'
          }`}
          title={running ? '会话执行中' : '会话已连接'}
          aria-label={running ? '会话执行中' : '会话已连接'}
        />
        {protocolText}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-start gap-2">
          <span className="min-w-0 flex-1 truncate text-sm font-black text-ops-text">
            {session.remark || session.host}
          </span>
          {needsAttention && (
            <span
              className="inline-flex shrink-0 items-center gap-1 rounded-full border border-yellow-300/35 bg-yellow-300/10 px-1.5 py-0.5 text-[10px] font-semibold text-yellow-100"
              title={attention.label}
              aria-label={attention.label}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-yellow-300 animate-pulse" />
              {attention.label}
            </span>
          )}
          {running && !needsAttention && (
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
        <div className="mt-1 truncate font-mono text-[10px] text-ops-overlay">
          {session.user}@{session.host}
        </div>
        <div className="mt-2 flex min-w-0 flex-wrap items-center gap-1.5">
          <span className="rounded-full border border-ops-surface1/60 bg-ops-dark/35 px-2 py-0.5 text-[10px] font-semibold text-ops-overlay">
            {assetText}
          </span>
          <span className="rounded-full border border-ops-surface1/60 bg-ops-dark/35 px-2 py-0.5 text-[10px] font-semibold text-ops-overlay">
            消息 {messageCount}
          </span>
          {skillCount > 0 && (
            <span className="rounded-full border border-ops-accent/30 bg-ops-accent/10 px-2 py-0.5 text-[10px] font-semibold text-ops-accent">
              技能 {skillCount}
            </span>
          )}
          {session.heartbeatEnabled && (
            <span className="inline-flex items-center gap-1 rounded-full border border-ops-success/30 bg-ops-success/10 px-2 py-0.5 text-[10px] font-semibold text-ops-success" title="巡检已开启">
              <span className="h-1.5 w-1.5 rounded-full bg-ops-success animate-pulse" />
              巡检
            </span>
          )}
        </div>
        <div className="absolute bottom-2 right-2 hidden items-center gap-1 group-hover:flex">
          <button
            onClick={(event) => onEdit(session.id, event)}
            className="rounded-lg border border-ops-surface1/70 bg-ops-dark/45 px-2 py-1 text-[11px] font-semibold text-ops-subtext hover:border-ops-accent/40 hover:text-ops-text"
            title="编辑"
          >
            编辑
          </button>
          <button
            onClick={(event) => onDisconnect(session.id, event)}
            className="rounded-lg border border-ops-alert/35 bg-ops-alert/8 px-2 py-1 text-[11px] font-semibold text-ops-alert hover:bg-ops-alert/12"
            title="断开"
          >
            断开
          </button>
        </div>
      </div>
    </div>
  )
}
