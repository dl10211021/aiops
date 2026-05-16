import {
  approvalLabel,
  evidenceToneClass,
  evidenceLabel,
  operationLabel,
  operationToneClass,
  recordValue,
  retryPolicyLabel,
  runtimePolicyLabels,
  sessionModeSourceLabel,
  sessionModePolicyLabel,
  sessionModePolicyToneClass,
  timeoutPolicyLabel,
} from './toolPolicyPresentation'

interface ToolPolicyRuntimeSummaryProps {
  policy?: Record<string, unknown> | null
  columns?: string
  sessionMode?: 'readonly' | 'readwrite'
  sessionModeSource?: 'context' | 'session_snapshot' | 'inferred_unknown'
}

function requiresWriteGate(operation: string, approval: string) {
  return (
    approval === 'guarded_write'
    || ['write', 'read_write', 'destructive', 'external_effect'].includes(operation)
  )
}

function policyTone(policy: Record<string, unknown>, sessionMode?: 'readonly' | 'readwrite') {
  const operation = recordValue(policy, 'operation_mode')
  const approval = recordValue(policy, 'approval_policy')
  const destructive = recordValue(policy, 'destructive') === 'true'
  if (requiresWriteGate(operation, approval)) {
    if (sessionMode === 'readonly') {
      return {
        label: '只读限制',
        className: 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert',
        dotClassName: 'bg-ops-alert',
      }
    }
    if (sessionMode === 'readwrite') {
      return {
        label: destructive || approval === 'always_required' || operation === 'destructive' ? '读写强审批' : '读写已开启',
        className: 'border-ops-success/35 bg-ops-success/8 text-ops-success',
        dotClassName: 'bg-ops-success',
      }
    }
  }
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
  sessionMode,
  sessionModeSource,
}: ToolPolicyRuntimeSummaryProps) {
  if (!policy) return null
  const tone = policyTone(policy, sessionMode)
  const operationMode = recordValue(policy, 'operation_mode')
  const approvalPolicy = recordValue(policy, 'approval_policy')
  const evidenceFamily = recordValue(policy, 'evidence_family')
  const operation = operationLabel(operationMode)
  const approval = sessionModePolicyLabel(operationMode, approvalPolicy, sessionMode)
  const evidence = evidenceLabel(evidenceFamily)
  const timeout = timeoutPolicyLabel(policy) || '未设置超时'
  const retry = retryPolicyLabel(policy) || '不自动重试'
  return (
    <div className="rounded-lg border border-ops-surface1/55 bg-ops-dark/25 p-3 text-xs text-ops-subtext">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tone.className}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${tone.dotClassName}`} />
          {tone.label}
        </span>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${operationToneClass(operationMode)}`}>
          模式：{operation}
        </span>
        <span
          className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${sessionModePolicyToneClass(
            operationMode,
            approvalPolicy,
            sessionMode,
            sessionModeSource,
          )}`}
        >
          门禁：{approval}
          {sessionModeSource ? ` (${sessionModeSource === 'context' ? '上下文' : sessionModeSource === 'session_snapshot' ? '快照' : '待识别'})` : ''}
        </span>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${evidenceToneClass(evidenceFamily)}`}>
          证据：{evidence}
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

export function ToolPolicyRuntimeChips({ policy, sessionMode, sessionModeSource }: ToolPolicyRuntimeSummaryProps) {
  if (!policy) return null
  const tone = policyTone(policy, sessionMode)
  const operationMode = recordValue(policy, 'operation_mode')
  const approvalPolicy = recordValue(policy, 'approval_policy')
  const evidenceFamily = recordValue(policy, 'evidence_family')
  const runtimeChips = [
    ...runtimePolicyLabels(policy),
    recordValue(policy, 'destructive') === 'true' ? '破坏性' : '',
  ].filter(Boolean)
  return (
    <>
      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${tone.className}`}>{tone.label}</span>
      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${operationToneClass(operationMode)}`}>
        模式：{operationLabel(operationMode)}
      </span>
      <span
        className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${sessionModePolicyToneClass(
            operationMode,
            approvalPolicy,
            sessionMode,
            sessionModeSource,
          )}`}
        >
          门禁：{sessionModePolicyLabel(operationMode, approvalPolicy, sessionMode)}
          {sessionModeSource ? ` (${sessionModeSourceLabel(sessionModeSource)})` : ''}
        </span>
      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${evidenceToneClass(evidenceFamily)}`}>
        证据：{evidenceLabel(evidenceFamily)}
      </span>
      {runtimeChips.map((label) => (
        <span key={label} className="rounded-full border border-ops-surface1/65 px-2 py-0.5 text-[11px] text-ops-subtext">{label}</span>
      ))}
    </>
  )
}
