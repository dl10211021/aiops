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
  const statusTitle = running ? '会话执行中' : needsAttention ? attention.label : '会话已连接'
  return (
    <div
      onClick={onSelect}
      className={`group relative grid min-h-[58px] cursor-pointer grid-cols-[46px_minmax(0,1fr)_14px] items-center gap-3 overflow-hidden rounded-lg border px-2.5 py-2 text-sm transition-colors duration-150
        ${active
          ? 'border-ops-accent/60 bg-[linear-gradient(135deg,rgba(40,208,168,0.16),rgba(15,36,56,0.76))] text-ops-accent shadow-[inset_0_0_0_1px_rgba(40,208,168,0.08)]'
          : needsAttention
            ? 'border-yellow-300/30 bg-[linear-gradient(135deg,rgba(253,224,71,0.12),rgba(18,32,49,0.72))] text-ops-text hover:border-yellow-300/45'
            : 'border-ops-surface1/45 bg-[linear-gradient(135deg,rgba(23,35,53,0.64),rgba(9,20,35,0.82))] text-ops-subtext hover:border-ops-accent/30 hover:text-ops-text'}`}
    >
      <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-ops-accent/28 to-transparent" />
      <span
        title={`${session.asset_type}/${session.protocol}`}
        className="grid h-9 w-11 shrink-0 place-items-center rounded-md border border-ops-surface1/65 bg-ops-dark/82 px-1 text-center text-[10px] font-black leading-tight text-ops-text shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
      >
        {protocolText}
      </span>
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-[15px] font-black leading-5 text-ops-text">
            {session.remark || session.host}
          </span>
        </div>
        <div className="mt-0.5 truncate font-mono text-[10px] font-semibold text-ops-overlay">
          {session.user}@{session.host}
        </div>
        <div className="pointer-events-none absolute right-7 top-2 flex gap-1 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
          <button
            onClick={(event) => {
              event.stopPropagation()
              onEdit(session.id, event)
            }}
            className="rounded border border-ops-surface1/70 bg-ops-dark/80 px-1.5 py-0.5 text-[10px] font-semibold text-ops-subtext hover:border-ops-accent/45 hover:text-ops-text"
            title="编辑"
          >
            编辑
          </button>
          <button
            onClick={(event) => {
              event.stopPropagation()
              onDisconnect(session.id, event)
            }}
            className="rounded border border-ops-alert/35 bg-ops-dark/80 px-1.5 py-0.5 text-[10px] font-semibold text-ops-alert hover:bg-ops-alert/12"
            title="断开"
          >
            断开
          </button>
        </div>
      </div>
      <span
        className={`h-2.5 w-2.5 rounded-full border border-ops-panel ${
          running
            ? 'bg-ops-accent shadow-[0_0_10px_rgba(40,208,168,0.85)] animate-pulse'
            : needsAttention
              ? 'bg-yellow-300 shadow-[0_0_10px_rgba(253,224,71,0.58)]'
              : 'bg-ops-success shadow-[0_0_9px_rgba(90,214,125,0.7)]'
        }`}
        title={statusTitle}
        aria-label={statusTitle}
      />
    </div>
  )
}
