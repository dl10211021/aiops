import type { SafetyPolicyAction, SafetyPolicyDecision } from '@/types'
import { TRACE_RULE_DECISION_LABELS } from './policyDecisions'

export default function TracePolicyDecisionButtons({
  action,
  onTraceActionRule,
  policyRuleBusy,
}: {
  action: SafetyPolicyAction
  onTraceActionRule: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
}) {
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {(['allow', 'approval', 'deny'] as SafetyPolicyDecision[]).map((decision) => {
        const busyKey = `${action.id}:${decision}`
        const isBusy = policyRuleBusy === busyKey
        const tone = decision === 'allow'
          ? 'border-ops-success/40 text-ops-success hover:bg-ops-success/10'
          : decision === 'approval'
            ? 'border-yellow-300/35 text-yellow-100 hover:bg-yellow-300/10'
            : 'border-ops-alert/45 text-ops-alert hover:bg-ops-alert/10'
        return (
          <button
            key={decision}
            type="button"
            disabled={Boolean(policyRuleBusy)}
            onClick={() => onTraceActionRule(action, decision)}
            className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${tone}`}
          >
            {isBusy ? '保存中' : TRACE_RULE_DECISION_LABELS[decision]}
          </button>
        )
      })}
    </div>
  )
}
