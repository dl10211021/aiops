import type { SafetyPolicy, SafetyPolicyCategory, SafetyPolicyDecision } from '@/types'
import { DEFAULT_NETWORK_BOUNDARY } from './safetyPolicyShared'
import type { CategoryKey } from './safetyPolicyShared'

export function patchSafetyPolicy(policy: SafetyPolicy, patch: Partial<SafetyPolicy>) {
  return { ...policy, ...patch }
}

export function patchSafetyPolicyCategory(
  policy: SafetyPolicy,
  categoryKey: CategoryKey,
  patch: Partial<SafetyPolicyCategory>,
) {
  return {
    ...policy,
    categories: {
      ...policy.categories,
      [categoryKey]: { ...(policy.categories[categoryKey] || {}), ...patch },
    },
  }
}

export function setSafetyPolicyActionRule(
  policy: SafetyPolicy,
  domain: string,
  actionId: string,
  decision: SafetyPolicyDecision,
) {
  return {
    ...policy,
    action_rules: {
      ...(policy.action_rules || {}),
      [domain]: {
        ...((policy.action_rules || {})[domain] || {}),
        [actionId]: decision,
      },
    },
  }
}

export function removeSafetyPolicyActionRule(
  policy: SafetyPolicy,
  domain: string,
  actionId: string,
) {
  const nextDomainRules = { ...((policy.action_rules || {})[domain] || {}) }
  delete nextDomainRules[actionId]
  return {
    ...policy,
    action_rules: {
      ...(policy.action_rules || {}),
      [domain]: nextDomainRules,
    },
  }
}

export function patchSafetyPolicyNetworkBoundary(
  policy: SafetyPolicy,
  patch: Partial<NonNullable<SafetyPolicy['network_boundary']>>,
) {
  return {
    ...policy,
    network_boundary: {
      ...DEFAULT_NETWORK_BOUNDARY,
      ...(policy.network_boundary || {}),
      ...patch,
    },
  }
}
