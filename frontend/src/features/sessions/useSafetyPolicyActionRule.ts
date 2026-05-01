import { useState } from 'react'
import { getSafetyPolicy, updateSafetyPolicy } from '@/api/client'
import { useStore } from '@/store'
import type { SafetyPolicyAction, SafetyPolicyDecision } from '@/types'
import type { LatestPolicyBlock } from './chatAttention'
import { policyBlockKey } from './chatAttention'
import { TRACE_RULE_DECISION_LABELS } from './policyDecisions'
import { actionRuleDomain } from './traceUtils'

export function useSafetyPolicyActionRule(
  latestPolicyBlock: LatestPolicyBlock | null,
  onDismissPolicyBlock: (key: string) => void,
) {
  const addToast = useStore((state) => state.addToast)
  const [busyKey, setBusyKey] = useState<string | null>(null)

  const saveActionRule = async (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => {
    if (!action.id) return
    const nextBusyKey = `${action.id}:${decision}`
    setBusyKey(nextBusyKey)
    try {
      const response = await getSafetyPolicy()
      const policy = response.data.policy
      const domain = actionRuleDomain(action.id)
      const nextPolicy = {
        ...policy,
        action_rules: {
          ...(policy.action_rules || {}),
          [domain]: {
            ...((policy.action_rules || {})[domain] || {}),
            [action.id]: decision,
          },
        },
      }
      await updateSafetyPolicy(nextPolicy)
      if (latestPolicyBlock && latestPolicyBlock.action.id === action.id) {
        onDismissPolicyBlock(policyBlockKey(latestPolicyBlock))
      }
      addToast(
        `已将「${action.label || action.id}」设置为${TRACE_RULE_DECISION_LABELS[decision]}。本次已被拒绝的工具不会自动重放，重新发送后按新策略执行。`,
        'success',
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : '安全策略保存失败'
      addToast(message, 'error')
    } finally {
      setBusyKey(null)
    }
  }

  return {
    busyKey,
    saveActionRule,
  }
}
