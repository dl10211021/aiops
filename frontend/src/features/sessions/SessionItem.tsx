import type { MouseEvent } from 'react'
import type { Session } from '@/types'
import { protocolLabel } from '@/utils/assetDisplay'
import { sessionAttention } from './sessionAttention'

interface SessionItemProps {
  session: Session
  active: boolean
  onSelect: () => void
  onDisconnect: (sid: string, event: MouseEvent<HTMLButtonElement>) => void
}

export default function SessionItem({
  session,
  active,
  onSelect,
  onDisconnect,
}: SessionItemProps) {
  const attention = sessionAttention(session)
  const needsAttention = attention.type !== 'none'
  return (
    <div
      onClick={onSelect}
      className={`group mx-1 flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-3 text-sm transition-all
        ${active
          ? 'border-ops-accent/35 bg-ops-accent/12 text-ops-accent shadow-[0_0_28px_rgba(243,177,90,0.12)]'
          : needsAttention
            ? 'border-yellow-300/25 bg-yellow-300/8 text-ops-text hover:bg-yellow-300/12'
            : 'border-transparent text-ops-subtext hover:bg-ops-surface0/70 hover:text-ops-text'}`}
    >
      <span
        title={`${session.asset_type}/${session.protocol}`}
        className="flex h-9 w-12 shrink-0 items-center justify-center rounded-lg bg-ops-dark/70 px-1 text-center text-[10px] font-bold leading-tight text-ops-text"
      >
        {protocolLabel(session.protocol || session.asset_type)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm font-semibold">
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
          {session.isStreaming && !needsAttention && (
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
          {session.user}@{session.host}
        </div>
      </div>
      {session.heartbeatEnabled && (
        <span className="h-2 w-2 shrink-0 rounded-full bg-ops-success animate-pulse" title="巡检已开启" />
      )}
      <button
        onClick={(event) => onDisconnect(session.id, event)}
        className="hidden rounded-md px-1.5 py-1 text-xs text-ops-alert hover:bg-ops-alert/10 group-hover:block"
        title="断开"
      >
        断开
      </button>
    </div>
  )
}
