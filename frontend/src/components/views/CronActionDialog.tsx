import type { CronJob } from '@/types'
import {
  agentProfileLabel,
  channelLabel,
  cronScheduleLabel,
  targetScopeLabel,
} from './cronDisplay'

interface CronActionDialogProps {
  tone: 'accent' | 'alert'
  eyebrow: string
  title: string
  description: string
  job: CronJob
  busy: boolean
  confirmLabel: string
  busyLabel: string
  onClose: () => void
  onConfirm: () => void
}

export function CronActionDialog({
  tone,
  eyebrow,
  title,
  description,
  job,
  busy,
  confirmLabel,
  busyLabel,
  onClose,
  onConfirm,
}: CronActionDialogProps) {
  const toneClass = tone === 'alert' ? 'text-ops-alert' : 'text-ops-accent'
  const buttonClass = tone === 'alert'
    ? 'ops-danger-action'
    : 'ops-primary-action'

  return (
    <div className="ops-modal-backdrop" onClick={() => !busy && onClose()}>
      <section className="ops-modal-surface w-full max-w-lg" onClick={(event) => event.stopPropagation()}>
        <div className="ops-modal-header block">
          <div className={`text-xs font-semibold ${toneClass}`}>{eyebrow}</div>
          <h2 className="mt-1 text-lg font-bold text-ops-text">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-ops-subtext">{description}</p>
        </div>
        <div className="ops-modal-body grid gap-2 p-5 text-sm">
          <div className="ops-data-panel p-3">
            <div className="font-semibold text-ops-text">{job.message || job.id}</div>
            <div className="mt-2 grid gap-1 text-xs text-ops-overlay sm:grid-cols-2">
              <span>计划：{job.id}</span>
              <span>周期：{cronScheduleLabel(job.cron_expr)}</span>
              <span>目标：{job.host || job.target_host || '-'}</span>
              <span>范围：{targetScopeLabel(job.target_scope, job.scope_value)}</span>
              <span>身份：{agentProfileLabel(job.agent_profile)}</span>
              <span>通知：{channelLabel(job.notification_channel)}</span>
            </div>
          </div>
        </div>
        <div className="ops-modal-footer">
          <button
            onClick={onClose}
            disabled={busy}
            className="ops-muted-action px-4 py-2 text-sm disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className={`${buttonClass} px-4 py-2 text-sm disabled:opacity-50`}
          >
            {busy ? busyLabel : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}
