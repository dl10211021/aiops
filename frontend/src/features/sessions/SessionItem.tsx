import type { MouseEvent } from 'react'
import type { Session } from '@/types'
import { protocolLabel } from '@/utils/assetDisplay'
import { sessionAttention } from './sessionAttention'
import { isSessionRunning } from './sessionMetrics'

function protocolBadgeClass(session: Session) {
  const raw = `${session.protocol || ''} ${session.asset_type || ''}`.toLowerCase()
  if (raw.includes('oracle')) return 'border-amber-400/25 bg-amber-400/8 text-amber-300'
  if (raw.includes('postgres') || raw.includes('pgsql')) return 'border-violet-400/25 bg-violet-400/10 text-violet-200'
  if (raw.includes('mysql') || raw.includes('tidb') || raw.includes('mariadb')) return 'border-sky-400/25 bg-sky-400/10 text-sky-200'
  if (raw.includes('win') || raw.includes('rdp')) return 'border-slate-400/25 bg-slate-400/10 text-slate-200'
  if (raw.includes('ssh') || raw.includes('linux') || raw.includes('unix') || raw.includes('esxi')) return 'border-blue-400/25 bg-blue-400/10 text-blue-200'
  if (raw.includes('snmp') || raw.includes('switch') || raw.includes('network')) return 'border-emerald-400/25 bg-emerald-400/10 text-emerald-200'
  return 'border-ops-surface1/65 bg-ops-dark/82 text-ops-text'
}

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
      className={`group relative grid min-h-[58px] cursor-pointer grid-cols-[46px_minmax(0,1fr)_54px] items-center gap-3 overflow-hidden rounded-lg border px-2.5 py-2 text-sm transition-colors duration-150
        ${active
          ? 'border-ops-accent/60 bg-[linear-gradient(135deg,rgba(40,208,168,0.16),rgba(15,36,56,0.76))] text-ops-accent shadow-[inset_0_0_0_1px_rgba(40,208,168,0.08)]'
          : needsAttention
            ? 'border-yellow-300/30 bg-[linear-gradient(135deg,rgba(253,224,71,0.12),rgba(18,32,49,0.72))] text-ops-text hover:border-yellow-300/45'
            : 'border-ops-surface1/45 bg-[linear-gradient(135deg,rgba(20,31,45,0.72),rgba(9,19,32,0.92))] text-ops-subtext hover:border-ops-accent/32 hover:bg-[linear-gradient(135deg,rgba(26,42,60,0.74),rgba(10,23,38,0.94))] hover:text-ops-text'}`}
    >
      <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-ops-accent/18 to-transparent" />
      <span
        title={`${session.asset_type}/${session.protocol}`}
        className={`grid h-9 w-11 shrink-0 place-items-center rounded-md border px-1 text-center text-[10px] font-black leading-tight shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${protocolBadgeClass(session)}`}
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
      </div>
      <div className="flex items-center justify-end gap-1">
        <div className={`flex items-center gap-1 transition-opacity ${
          active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
        }`}>
          <button
            type="button"
            onClick={(event) => onEdit(session.id, event)}
            className="grid h-6 w-6 place-items-center rounded-md border border-ops-surface1/65 bg-ops-dark/45 text-[12px] font-black text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text"
            title="编辑单个会话：名称、分组、标签"
            aria-label="编辑单个会话"
          >
            ✎
          </button>
          <button
            type="button"
            onClick={(event) => onDisconnect(session.id, event)}
            className="grid h-6 w-6 place-items-center rounded-md border border-ops-alert/35 bg-ops-alert/8 text-[12px] font-black text-ops-alert transition-colors hover:bg-ops-alert/14"
            title="断开会话"
            aria-label="断开会话"
          >
            ⏻
          </button>
        </div>
        <span
          className={`h-2.5 w-2.5 shrink-0 rounded-full border border-ops-panel ${
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
    </div>
  )
}
