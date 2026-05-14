import type { ToolApproval } from '@/types'
import { toolLabel } from '@/utils/assetDisplay'
import { ApprovalSourceSummary } from './ApprovalSourceSummary'
import TraceInfo from './TraceInfo'
import { policyActionTone } from './policyTones'
import { ToolPolicyRuntimeChips, ToolPolicyRuntimeGrid } from './ToolPolicyRuntimeSummary'

type ApprovalAction = NonNullable<ToolApproval['actions']>[number]
type ApprovalRow = { label: string; value: string; wide?: boolean }

export function getToolApprovalDisplay(approval: ToolApproval) {
  const approved = approval.decision === 'approved'
  const rejected = approval.decision === 'rejected'
  const timedOut = approval.decision === 'timeout'
  const resolvedTone = approved
    ? 'border-ops-success/35 bg-ops-success/6'
    : rejected || timedOut
      ? 'border-ops-alert/35 bg-ops-alert/6'
      : 'border-yellow-300/35 bg-yellow-300/8'
  const statusTone = approved
    ? 'text-ops-success'
    : rejected || timedOut ? 'text-ops-alert' : 'text-yellow-200'
  const decisionLabel = approved
    ? approval.autoAll ? '已批准，本会话自动放行' : '已批准，继续执行'
    : timedOut ? '审批超时，已取消执行' : rejected ? '已拒绝，已拦截执行' : '等待人工审批'
  const decisionText = approval.decidedAt
    ? new Date(approval.decidedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : ''

  return { decisionLabel, decisionText, resolvedTone, statusTone }
}

export function ToolApprovalCardHeader({
  approval,
  decisionLabel,
  statusTone,
}: {
  approval: ToolApproval
  decisionLabel: string
  statusTone: string
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-ops-surface0/70 px-4 py-3">
      <div>
        <div className={`text-xs font-semibold ${statusTone}`}>
          {decisionLabel}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span title={approval.toolName} className="text-sm font-semibold text-ops-text">{toolLabel(approval.toolName)}</span>
          <span className="rounded-full border border-yellow-300/25 px-2 py-0.5 text-[11px] text-yellow-100">
            {approval.primaryAction?.label || '敏感操作'}
          </span>
          <ToolPolicyRuntimeChips policy={approval.toolPolicy} />
        </div>
      </div>
      <span className="font-mono text-[11px] text-ops-overlay">{approval.toolCallId}</span>
    </div>
  )
}

export function ToolApprovalPolicySummary({ approval }: { approval: ToolApproval }) {
  return <ToolPolicyRuntimeGrid policy={approval.toolPolicy} columns="md:grid-cols-4" />
}

export function ToolApprovalReason({ reason }: { reason?: string }) {
  if (!reason) return null
  return (
    <div className="rounded-lg border border-yellow-300/20 bg-ops-dark/35 px-3 py-2 text-yellow-100">
      {reason}
    </div>
  )
}

export function ToolApprovalSource({ approval }: { approval: ToolApproval }) {
  return <ApprovalSourceSummary source={approval.approvalSource || null} reason={approval.reason} />
}

export function ToolApprovalResolution({
  approval,
  decisionLabel,
  decisionText,
}: {
  approval: ToolApproval
  decisionLabel: string
  decisionText: string
}) {
  if (!approval.resolved) return null
  return (
    <div className="grid gap-2 md:grid-cols-3">
      <TraceInfo label="处理人" value={approval.operator || '-'} />
      <TraceInfo label="处理时间" value={decisionText || '-'} />
      <TraceInfo label="处理结论" value={decisionLabel} />
      {approval.note && (
        <div className="md:col-span-3">
          <div className="text-ops-overlay">处理原因</div>
          <div className="mt-1 rounded-md border border-ops-surface0 bg-ops-dark/45 px-3 py-2 text-ops-text">
            {approval.note}
          </div>
        </div>
      )}
    </div>
  )
}

export function ToolApprovalActions({ actions }: { actions: ApprovalAction[] }) {
  if (actions.length === 0) return null
  return (
    <div className="grid gap-2 md:grid-cols-2">
      {actions.map((action) => (
        <div key={action.id} className={`rounded-md border px-3 py-2 ${policyActionTone(action.severity)}`}>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold">{action.label}</span>
            <span className="font-mono text-[10px] opacity-75">{action.id}</span>
          </div>
          {action.description && <p className="mt-1 text-[11px] leading-4 opacity-85">{action.description}</p>}
        </div>
      ))}
    </div>
  )
}

export function ToolApprovalPayload({
  args,
  rows,
}: {
  args: string
  rows: ApprovalRow[]
}) {
  if (rows.length === 0) {
    return (
      <pre className="max-h-28 overflow-auto whitespace-pre-wrap break-all rounded-md border border-ops-surface0 bg-ops-dark/45 px-3 py-2 font-mono text-[11px]">
        {args.substring(0, 600)}
      </pre>
    )
  }

  return (
    <div className="grid gap-2 md:grid-cols-2">
      {rows.map((row) => (
        <div key={row.label} className={row.wide ? 'md:col-span-2' : ''}>
          <div className="text-[11px] text-ops-overlay">{row.label}</div>
          <div className="mt-1 rounded-md border border-ops-surface0 bg-ops-dark/45 px-3 py-2 font-mono text-[11px] leading-relaxed text-ops-text">
            {row.value}
          </div>
        </div>
      ))}
    </div>
  )
}

export function ToolApprovalDecisionActions({
  approval,
  onApproval,
}: {
  approval: ToolApproval
  onApproval: (approval: ToolApproval, approved: boolean, autoAll?: boolean) => void
}) {
  if (approval.resolved) return null
  return (
    <div className="flex flex-wrap gap-2 border-t border-yellow-300/20 px-4 py-3">
      <button
        onClick={() => onApproval(approval, true)}
        className="rounded-md bg-ops-success px-3 py-1.5 text-xs font-semibold text-ops-dark transition-colors hover:bg-ops-success/85"
      >
        批准
      </button>
      <button
        onClick={() => onApproval(approval, false)}
        className="rounded-md bg-ops-alert px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-ops-alert/85"
      >
        拒绝
      </button>
      <button
        onClick={() => onApproval(approval, true, true)}
        className="rounded-md border border-ops-surface1 px-3 py-1.5 text-xs text-ops-subtext transition-colors hover:text-ops-text"
      >
        本会话自动批准
      </button>
    </div>
  )
}
