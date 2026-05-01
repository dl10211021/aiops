import type { SafetyPolicyAction, SafetyPolicyDecision } from '@/types'
import { policyActionTone } from './policyTones'
import TraceInfo from './TraceInfo'
import TracePolicyDecisionButtons from './TracePolicyDecisionButtons'
import {
  policyDecisionLabel,
  resultReason,
  stringValue,
  toolErrorTitle,
} from './traceUtils'

export function ToolErrorSummary({ result }: { result: Record<string, unknown> }) {
  const title = toolErrorTitle(result)
  const message = stringValue(result.error || result.message || result.reason) || '工具返回了失败状态。'
  const hint = stringValue(result.hint)
  const rawError = stringValue(result.raw_error || result.stderr)
  const exitStatus = result.exit_status === undefined || result.exit_status === null ? '' : String(result.exit_status)

  return (
    <div className="mb-2 rounded-lg border border-ops-alert/35 bg-ops-alert/10 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-ops-alert/40 bg-ops-dark/45 px-2 py-0.5 text-[11px] font-semibold text-ops-alert">
          {title}
        </span>
        {exitStatus && (
          <span className="rounded-full border border-ops-surface0 bg-ops-panel/45 px-2 py-0.5 font-mono text-[10px] text-ops-overlay">
            exit {exitStatus}
          </span>
        )}
      </div>
      <p className="mt-2 text-xs leading-5 text-ops-text">{message}</p>
      {hint && (
        <div className="mt-2 rounded-md border border-ops-accent/25 bg-ops-accent/10 px-3 py-2 text-[11px] leading-5 text-ops-subtext">
          <span className="font-semibold text-ops-accent">处理建议：</span>{hint}
        </div>
      )}
      {rawError && (
        <details className="mt-2 rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
          <summary className="cursor-pointer text-[11px] text-ops-overlay">错误详情</summary>
          <pre className="mt-2 max-h-28 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
            {rawError.substring(0, 1200)}
          </pre>
        </details>
      )}
    </div>
  )
}

export function PolicyBlockedSummary({
  result,
  primaryAction,
  onTraceActionRule,
  policyRuleBusy,
}: {
  result: Record<string, unknown> | null
  primaryAction: SafetyPolicyAction | null
  onTraceActionRule?: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
}) {
  const decision = String(result?.policy_decision || '')
  return (
    <div className="mb-2 rounded-lg border border-ops-alert/35 bg-ops-alert/10 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-ops-alert/40 bg-ops-dark/45 px-2 py-0.5 text-[11px] font-semibold text-ops-alert">
          {policyDecisionLabel(decision)}
        </span>
        {primaryAction && (
          <span className={`rounded-full border px-2 py-0.5 text-[11px] ${policyActionTone(primaryAction.severity)}`}>
            {primaryAction.label}
          </span>
        )}
      </div>
      <p className="mt-2 text-xs leading-5 text-ops-text">{resultReason(result)}</p>
      {primaryAction && (
        <div className="mt-3 rounded-md border border-ops-surface0 bg-ops-dark/35 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-semibold text-ops-text">{primaryAction.label}</span>
            <span className="font-mono text-[10px] text-ops-overlay">{primaryAction.id}</span>
          </div>
          {primaryAction.description && (
            <p className="mt-1 text-[11px] leading-4 text-ops-subtext">{primaryAction.description}</p>
          )}
          {onTraceActionRule && (
            <TracePolicyDecisionButtons
              action={primaryAction}
              onTraceActionRule={onTraceActionRule}
              policyRuleBusy={policyRuleBusy}
            />
          )}
        </div>
      )}
    </div>
  )
}

export function TracePrimaryActionNotice({
  action,
  onTraceActionRule,
  policyRuleBusy,
}: {
  action: SafetyPolicyAction
  onTraceActionRule?: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
}) {
  return (
    <div className="mb-2 rounded-md border border-yellow-300/25 bg-yellow-300/10 px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-yellow-100">{action.label}</span>
        <span className="font-mono text-[10px] text-yellow-100/70">{action.id}</span>
      </div>
      {action.description && (
        <p className="mt-1 text-[11px] leading-4 text-yellow-100/80">{action.description}</p>
      )}
      {onTraceActionRule && (
        <TracePolicyDecisionButtons
          action={action}
          onTraceActionRule={onTraceActionRule}
          policyRuleBusy={policyRuleBusy}
        />
      )}
    </div>
  )
}

export function DatabaseResultSummary({ result }: { result: Record<string, unknown> }) {
  if (!('statement_type' in result) && !('has_result_set' in result) && !('affected_rows' in result)) return null
  const statementType = String(result.statement_type || '-').toUpperCase()
  const hasResultSet = Boolean(result.has_result_set)
  const committed = Boolean(result.committed)
  const count = result.affected_rows ?? result.count ?? '-'
  const message = typeof result.message === 'string' ? result.message : ''
  return (
    <div className="mb-2 rounded-md border border-ops-surface0 bg-ops-dark/45 p-2">
      <div className="grid gap-2 text-[11px] md:grid-cols-4">
        <TraceInfo label="SQL 类型" value={statementType} />
        <TraceInfo label="结果集" value={hasResultSet ? '有' : '无'} />
        <TraceInfo label="已提交" value={committed ? '是' : '否'} />
        <TraceInfo label={result.affected_rows !== undefined ? '影响行数' : '返回行数'} value={String(count)} />
      </div>
      {message && <div className="mt-2 text-[11px] text-ops-subtext">{message}</div>}
    </div>
  )
}
