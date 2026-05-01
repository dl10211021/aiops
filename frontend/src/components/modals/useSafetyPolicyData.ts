import { useEffect, useMemo, useState } from 'react'
import { getSafetyPolicy, testSafetyPolicy, updateSafetyPolicy } from '@/api/safety'
import { useStore } from '@/store'
import type { SafetyPolicy, SafetyPolicyCategory, SafetyPolicyDecision, SafetyPolicyTestResult } from '@/types'
import { SAFETY_POLICY_DOMAINS } from './safetyPolicyDomains'
import { actionRuleDomain, calculatePolicyTotals, resolveCategory } from './safetyPolicyLogic'
import {
  DECISION_LABELS,
  DEFAULT_CUSTOM_ACTION_RULE,
  DEFAULT_TEST_FORM,
} from './safetyPolicyShared'
import type { CategoryKey, PolicyPanel } from './safetyPolicyShared'
import {
  buildSafetyPolicyDataViewModel,
  buildSafetyPolicyTestPayload,
} from './safetyPolicyDataModel'
import {
  patchSafetyPolicy,
  patchSafetyPolicyCategory,
  patchSafetyPolicyNetworkBoundary,
  removeSafetyPolicyActionRule,
  setSafetyPolicyActionRule,
} from './safetyPolicyMutations'

export function useSafetyPolicyData() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)
  const [policy, setPolicy] = useState<SafetyPolicy | null>(null)
  const [activeDomainId, setActiveDomainId] = useState('os')
  const [activePanel, setActivePanel] = useState<PolicyPanel>('actions')
  const [saving, setSaving] = useState(false)
  const [testForm, setTestForm] = useState(DEFAULT_TEST_FORM)
  const [selectedPlatforms, setSelectedPlatforms] = useState<Record<string, string>>({})
  const [customActionRule, setCustomActionRule] = useState(DEFAULT_CUSTOM_ACTION_RULE)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<SafetyPolicyTestResult | null>(null)

  useEffect(() => {
    getSafetyPolicy()
      .then((res) => setPolicy(res.data.policy))
      .catch(() => addToast('加载安全策略失败', 'error'))
  }, [addToast])

  const activeDomain = SAFETY_POLICY_DOMAINS.find((domain) => domain.id === activeDomainId) || SAFETY_POLICY_DOMAINS[0]
  const selectedPlatform = activeDomain.platforms.includes(selectedPlatforms[activeDomain.id])
    ? selectedPlatforms[activeDomain.id]
    : activeDomain.platforms[0]
  const activeCategory = resolveCategory(activeDomain, selectedPlatform)
  const {
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
  } = buildSafetyPolicyDataViewModel({
    activeCategory,
    activeDomain,
    activePanel,
    customActionRule,
    policy,
    selectedPlatform,
  })

  const totals = useMemo(() => calculatePolicyTotals(policy), [policy])

  const updatePolicy = (patch: Partial<SafetyPolicy>) => {
    if (!policy) return
    setPolicy(patchSafetyPolicy(policy, patch))
  }

  const updateCategory = (categoryKey: CategoryKey, patch: Partial<SafetyPolicyCategory>) => {
    if (!policy) return
    setPolicy(patchSafetyPolicyCategory(policy, categoryKey, patch))
  }

  const updateActionRule = (domain: string, actionId: string, decision: SafetyPolicyDecision) => {
    if (!policy) return
    setPolicy(setSafetyPolicyActionRule(policy, domain, actionId, decision))
  }

  const removeActionRule = (domain: string, actionId: string) => {
    if (!policy) return
    setPolicy(removeSafetyPolicyActionRule(policy, domain, actionId))
  }

  const addCustomActionRule = () => {
    const actionId = customActionRule.actionId.trim()
    if (!actionId) {
      addToast('请填写动作 ID', 'error')
      return
    }
    if (!/^[a-zA-Z0-9_.:-]+$/.test(actionId)) {
      addToast('动作 ID 只能包含字母、数字、点号、下划线、冒号和短横线', 'error')
      return
    }
    updateActionRule(customActionDomain, actionId, customActionRule.decision)
    setCustomActionRule({ ...customActionRule, domain: customActionDomain, actionId: '' })
    addToast(`已加入自定义动作策略：${actionId}，保存后生效`, 'success')
  }

  const updateNetworkBoundary = (patch: Partial<NonNullable<SafetyPolicy['network_boundary']>>) => {
    if (!policy) return
    setPolicy(patchSafetyPolicyNetworkBoundary(policy, patch))
  }

  const applyTestActionRule = (decision: SafetyPolicyDecision) => {
    const action = testResult?.primary_action || testResult?.actions?.[0]
    if (!action) {
      addToast('当前测试结果没有识别到可配置的动作', 'error')
      return
    }
    const domain = actionRuleDomain(action.id, activeCategory)
    updateActionRule(domain, action.id, decision)
    if (domain === 'linux') setActivePanel('actions')
    addToast(`已将「${action.label}」设置为${DECISION_LABELS[decision].label}，保存后生效`, 'success')
  }

  const switchPanel = (panel: PolicyPanel) => {
    setActivePanel(panel)
  }

  const switchDomain = (domainId: string) => {
    setActiveDomainId(domainId)
    setCustomActionRule({ ...customActionRule, domain: '', actionId: '' })
    setTestResult(null)
  }

  const updateSelectedPlatform = (platform: string) => {
    setSelectedPlatforms({ ...selectedPlatforms, [activeDomain.id]: platform })
    setCustomActionRule({ ...customActionRule, domain: '', actionId: '' })
    setTestResult(null)
  }

  const runPolicyTest = async () => {
    const input = testForm.input.trim()
    if (!input) {
      addToast('请填写要测试的命令、SQL 或 API 路径', 'error')
      return
    }
    const payload = buildSafetyPolicyTestPayload({
      activeCategory,
      activeDomain,
      selectedPlatform,
      testForm,
    })

    setTesting(true)
    try {
      const res = await testSafetyPolicy(payload)
      setTestResult(res.data.result)
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '测试安全策略失败', 'error')
    } finally {
      setTesting(false)
    }
  }

  const save = async () => {
    if (!policy) return
    setSaving(true)
    try {
      const res = await updateSafetyPolicy(policy)
      setPolicy(res.data.policy)
      addToast('安全策略已保存', 'success')
      closeModal()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存安全策略失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  return {
    activeCategory,
    activeDomain,
    activePanel,
    actionPolicy,
    addCustomActionRule,
    applyTestActionRule,
    boundary,
    category,
    closeModal,
    customActionDomain,
    customActionPlaceholder,
    customActionRows,
    customActionRule,
    policy,
    removeActionRule,
    runPolicyTest,
    save,
    saving,
    selectedPlatform,
    setCustomActionRule,
    setTestForm,
    showActionPanel,
    showAdvancedPanel,
    showNetworkBoundaryPanel,
    showTestPanel,
    switchDomain,
    switchPanel,
    testForm,
    testing,
    testResult,
    totals,
    updateActionRule,
    updateCategory,
    updateNetworkBoundary,
    updatePolicy,
    updateSelectedPlatform,
  }
}
