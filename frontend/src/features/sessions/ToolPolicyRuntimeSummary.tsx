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

function policyTone(policy: Record<string, unknown>) {
  const operation = recordValue(policy, 'operation_mode')
  const approval = recordValue(policy, 'approval_policy')
  const destructive = recordValue(policy, 'destructive') === 'true'
  if (destructive || approval === 'always_required' || operation === 'destructive') {
    return {
      label: '强审批',
      className: 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert',
      dotClassName: 'bg-ops-alert',
    }
  }
  if (
    approval === 'guarded_write'
    || operation === 'read_write'
    || operation === 'write'
    || operation === 'external_effect'
  ) {
    return {
      label: '受控执行',
      className: 'border-yellow-300/35 bg-yellow-300/10 text-yellow-100',
      dotClassName: 'bg-yellow-300',
    }
  }
  return {
    label: '只读安全',
    className: 'border-ops-success/35 bg-ops-success/8 text-ops-success',
    dotClassName: 'bg-ops-success',
  }
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
  const tone = policyTone(policy)
  const operation = operationLabel(recordValue(policy, 'operation_mode'))
  const approval = approvalLabel(recordValue(policy, 'approval_policy'))
  const evidence = evidenceLabel(recordValue(policy, 'evidence_family'))
  const timeout = timeoutPolicyLabel(policy) || '未设置超时'
  const retry = retryPolicyLabel(policy) || '不自动重试'
  return (
    <div className="rounded-lg border border-ops-surface1/55 bg-ops-dark/25 p-3 text-xs text-ops-subtext">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tone.className}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${tone.dotClassName}`} />
          {tone.label}
        </span>
        <span className="rounded-full border border-ops-surface1/65 px-2.5 py-1 text-[11px] text-ops-text">
          {operation}
        </span>
        <span className="rounded-full border border-ops-surface1/65 px-2.5 py-1 text-[11px] text-ops-subtext">
          {approval}
        </span>
        <span className="rounded-full border border-ops-surface1/65 px-2.5 py-1 text-[11px] text-ops-subtext">
          {evidence}
        </span>
      </div>
      <div className={`grid gap-2 ${columns}`}>
        {policyRows(policy).map(([label, value]) => (
          <div key={label} className="min-w-0 rounded-md border border-ops-surface0/70 bg-ops-panel/30 px-3 py-2">
            <div className="text-[11px] text-ops-overlay">{label}</div>
            <div className="mt-1 truncate font-mono text-[11px] text-ops-text" title={value}>
              {value}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        <div className="rounded-md border border-ops-surface0/70 bg-ops-panel/30 px-3 py-2">
          <div className="text-[11px] text-ops-overlay">调度边界</div>
          <div className="mt-1 text-[11px] leading-5 text-ops-subtext">
            {recordValue(policy, 'concurrency_safe') === 'true'
              ? '允许只读并发；遇到写入/外发仍按策略收敛。'
              : '串行或受控执行；不会被自动并发放大风险。'}
          </div>
        </div>
        <div className="rounded-md border border-ops-surface0/70 bg-ops-panel/30 px-3 py-2">
          <div className="text-[11px] text-ops-overlay">超时与重试</div>
          <div className="mt-1 text-[11px] leading-5 text-ops-subtext">
            {timeout}，{retry}
          </div>
        </div>
      </div>
    </div>
  )
}

export function ToolPolicyRuntimeChips({ policy }: ToolPolicyRuntimeSummaryProps) {
  if (!policy) return null
  const tone = policyTone(policy)
  const chips = [
    tone.label,
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
