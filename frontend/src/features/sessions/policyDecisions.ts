import type { SafetyPolicyDecision } from '@/types'

export const TRACE_RULE_DECISION_LABELS: Record<SafetyPolicyDecision, string> = {
  allow: '允许执行',
  approval: '需要审批',
  deny: '禁止执行',
}
