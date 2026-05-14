import {
  approvalLabel,
  evidenceLabel,
  operationLabel,
  recordValue,
  retryPolicyLabel,
  runtimePolicyLabels,
  timeoutPolicyLabel,
} from './toolPolicyPresentation'

interface ToolPolicyRuntimeSummaryProps {
  policy?: Record<string, unknown> | null
  columns?: string
}

function policyRows(policy: Record<string, unknown>) {
  return [
    ['工具模式', operationLabel(recordValue(policy, 'operation_mode'))],
    ['审批策略', approvalLabel(recordValue(policy, 'approval_policy'))],
    ['证据类型', evidenceLabel(recordValue(policy, 'evidence_family'))],
    ['结果策略', recordValue(policy, 'result_store_policy') || '-'],
    ['超时策略', timeoutPolicyLabel(policy) || '-'],
    ['重试策略', retryPolicyLabel(policy) || '不自动重试'],
    ['并发执行', recordValue(policy, 'concurrency_safe') === 'true' ? '允许' : '串行/受控'],
    ['破坏性', recordValue(policy, 'destructive') === 'true' ? '是' : '否'],
  ]
}

export function ToolPolicyRuntimeGrid({
  policy,
  columns = 'md:grid-cols-4',
}: ToolPolicyRuntimeSummaryProps) {
  if (!policy) return null
  return (
    <div className={`grid gap-2 rounded-lg border border-ops-surface1/55 bg-ops-dark/25 p-3 text-xs text-ops-subtext ${columns}`}>
      {policyRows(policy).map(([label, value]) => (
        <div key={label} className="flex min-w-0 items-center justify-between gap-3">
          <span className="shrink-0 text-ops-overlay">{label}</span>
          <span className="truncate text-right font-mono text-ops-text">{value}</span>
        </div>
      ))}
    </div>
  )
}

export function ToolPolicyRuntimeChips({ policy }: ToolPolicyRuntimeSummaryProps) {
  if (!policy) return null
  const chips = [
    operationLabel(recordValue(policy, 'operation_mode')),
    approvalLabel(recordValue(policy, 'approval_policy')),
    evidenceLabel(recordValue(policy, 'evidence_family')),
    ...runtimePolicyLabels(policy),
    recordValue(policy, 'destructive') === 'true' ? '破坏性' : '',
  ].filter(Boolean)
  return (
    <>
      {chips.map((label) => (
        <span key={label} className="rounded-full border border-ops-surface1/65 px-2 py-0.5 text-[11px] text-ops-subtext">
          {label}
        </span>
      ))}
    </>
  )
}
