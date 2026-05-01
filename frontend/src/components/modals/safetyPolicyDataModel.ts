import type { SafetyPolicy } from '@/types'
import {
  ACTION_RULE_DOMAIN_OPTIONS,
  DEFAULT_NETWORK_BOUNDARY,
  type CategoryKey,
  type DomainDefinition,
  type PolicyPanel,
} from './safetyPolicyShared'
import type {
  DEFAULT_CUSTOM_ACTION_RULE,
  DEFAULT_TEST_FORM,
} from './safetyPolicyShared'
import {
  actionPolicyForCategory,
  builtinActionIds,
  resolveToolName,
} from './safetyPolicyLogic'

type CustomActionRule = typeof DEFAULT_CUSTOM_ACTION_RULE
type TestForm = typeof DEFAULT_TEST_FORM

export function buildSafetyPolicyDataViewModel({
  activeCategory,
  activeDomain,
  activePanel,
  customActionRule,
  policy,
  selectedPlatform,
}: {
  activeCategory: CategoryKey
  activeDomain: DomainDefinition
  activePanel: PolicyPanel
  customActionRule: CustomActionRule
  policy: SafetyPolicy | null
  selectedPlatform: string
}) {
  const category = policy?.categories?.[activeCategory] || {}
  const showActionPanel = activePanel === 'actions'
  const showNetworkBoundaryPanel = activePanel === 'network-boundary'
  const showTestPanel = activePanel === 'test'
  const showAdvancedPanel = activePanel === 'advanced'
  const actionPolicy = actionPolicyForCategory(activeCategory, selectedPlatform, activeDomain.id)
  const customActionDomain = customActionRule.domain || actionPolicy?.domain || (activeCategory === 'http' ? 'http' : activeCategory)
  const customActionPlaceholder = ACTION_RULE_DOMAIN_OPTIONS.find((item) => item.value === customActionDomain)?.placeholder || 's3.download_object'
  const customActionRows = Object.entries(policy?.action_rules?.[customActionDomain] || {})
    .filter(([actionId]) => !builtinActionIds(customActionDomain).has(actionId))
    .sort(([left], [right]) => left.localeCompare(right))
  const boundary: NonNullable<SafetyPolicy['network_boundary']> = {
    ...DEFAULT_NETWORK_BOUNDARY,
    ...(policy?.network_boundary || {}),
  }

  return {
    actionPolicy,
    boundary,
    category,
    customActionDomain,
    customActionPlaceholder,
    customActionRows,
    showActionPanel,
    showAdvancedPanel,
    showNetworkBoundaryPanel,
    showTestPanel,
  }
}

export function buildSafetyPolicyTestPayload({
  activeCategory,
  activeDomain,
  selectedPlatform,
  testForm,
}: {
  activeCategory: CategoryKey
  activeDomain: DomainDefinition
  selectedPlatform: string
  testForm: TestForm
}) {
  const input = testForm.input.trim()
  return {
    tool_name: resolveToolName(activeDomain, selectedPlatform),
    command: input,
    sql: activeCategory === 'sql' ? input : undefined,
    method: activeCategory === 'http' ? testForm.method : undefined,
    path: activeCategory === 'http' ? input : undefined,
    allow_modifications: testForm.mode === 'readwrite',
    asset_type: selectedPlatform,
    host: '172.17.8.150',
    protocol: activeCategory === 'http'
      ? 'http_api'
      : activeCategory === 'sql'
        ? selectedPlatform.toLowerCase().replace(/\s+/g, '_')
        : undefined,
    trigger_source: 'chat',
  }
}
