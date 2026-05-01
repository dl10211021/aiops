import type { ApprovalRequest } from '@/types'
import { approvalStatusLabel, approvalStatusToneClass } from './approvalDisplay'

export function ApprovalStatusBadge({ status }: { status: ApprovalRequest['status'] }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${approvalStatusToneClass(status)}`}>
      {approvalStatusLabel(status)}
    </span>
  )
}

export function ApprovalInfo({ label, value }: { label: string | number; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-ops-overlay">{label}</span>
      <span className="truncate text-right font-mono text-ops-text">{String(value)}</span>
    </div>
  )
}
