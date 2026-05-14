import { useEffect, useMemo, useState } from 'react'
import { getAlertEvents, getAlertPolicy, testAlertPolicy, updateAlertPolicy } from '@/api/client'
import { useStore } from '@/store'
import type {
  AlertAutomationAction,
  AlertAutomationPolicy,
  AlertAutomationPolicyTestResult,
  AlertAutomationRule,
  AlertAutomationRuleConditions,
  AlertEvent,
} from '@/types'

const ACTION_OPTIONS: Array<{ id: AlertAutomationAction; label: string }> = [
  { id: 'analyze', label: '触发 AI 分析' },
  { id: 'record_only', label: '仅记录' },
  { id: 'dedupe_escalate', label: '重复升级分析' },
  { id: 'suppress', label: '抑制' },
  { id: 'close', label: '恢复闭环' },
]

const CHANNEL_OPTIONS = [
  { id: 'wechat', label: '企微' },
  { id: 'dingtalk', label: '钉钉' },
  { id: 'email', label: '邮件' },
]

const REMEDIATION_MODE_OPTIONS = [
  { id: 'disabled', label: '关闭：只分析建议' },
  { id: 'suggest', label: '建议：生成修复方案' },
  { id: 'approval', label: '审批：确认后执行' },
  { id: 'auto_low_risk', label: '低风险自动修复' },
]

const EMPTY_POLICY: AlertAutomationPolicy = { version: 1, rules: [] }
type ConditionListKey = Exclude<keyof AlertAutomationRuleConditions, 'min_repeat_count' | 'recovery'>
type PolicyEditorMode = 'simple' | 'advanced'
type QuickHandlingMode = 'record_only' | 'readonly_notify' | 'suggest' | 'approval' | 'auto_low_risk'

type PolicyOptionSet = {
  alertClasses: string[]
  alertNames: string[]
  hosts: string[]
  labelContains: string[]
  priorities: string[]
  severities: string[]
  sourceFamilies: string[]
}

type QuickPolicyConfig = {
  alertClass: string
  alertName: string
  cooldownMinutes: number
  handling: QuickHandlingMode
  host: string
  severity: string
  sourceFamily: string
}

function listToText(value?: string[]) {
  return (value || []).join(', ')
}

function textToList(value: string) {
  return value.split(/[,，\n]/).map((item) => item.trim().toLowerCase()).filter(Boolean)
}

function newRule(): AlertAutomationRule {
  const stamp = Date.now().toString(36)
  return {
    id: `custom-${stamp}`,
    name: '自定义告警策略',
    enabled: true,
    conditions: {},
    action: 'analyze',
    notify: true,
    channels: ['wechat'],
    remediation_mode: 'suggest',
    allowed_remediation_actions: [],
    cooldown_minutes: 30,
    reason: '命中自定义告警策略。',
  }
}

const QUICK_HANDLING_OPTIONS: Array<{ id: QuickHandlingMode; label: string; description: string }> = [
  { id: 'readonly_notify', label: '只读分析并通知', description: '默认流程：AI 查监控和资产会话，只读排查后通知。' },
  { id: 'record_only', label: '只记录/转发', description: '不触发 AI，适合低价值或噪声告警。' },
  { id: 'suggest', label: '建议修复', description: 'AI 给修复建议，不执行命令。' },
  { id: 'approval', label: '确认后修复', description: 'AI 生成动作，人工确认后执行。' },
  { id: 'auto_low_risk', label: '低风险自动处理', description: '只允许白名单低风险动作自动执行。' },
]

function quickRuleName(config: QuickPolicyConfig) {
  const scope = [config.sourceFamily, config.severity, config.alertClass, config.host, config.alertName].filter(Boolean).join(' / ')
  const action = QUICK_HANDLING_OPTIONS.find((item) => item.id === config.handling)?.label || '快速策略'
  return scope ? `${scope} - ${action}` : `默认快速策略 - ${action}`
}

function ruleMatchKey(rule: AlertAutomationRule) {
  const conditions = rule.conditions || {}
  return JSON.stringify({
    action: rule.action,
    alert_classes: conditions.alert_classes || [],
    channels: rule.channels || [],
    cooldown_minutes: rule.cooldown_minutes || 30,
    host_contains: conditions.host_contains || [],
    name_contains: conditions.name_contains || [],
    remediation_mode: rule.remediation_mode || 'disabled',
    severities: conditions.severities || [],
    source_families: conditions.source_families || [],
  })
}

function quickRuleFromConfig(config: QuickPolicyConfig): AlertAutomationRule {
  const stamp = Date.now().toString(36)
  const runAi = config.handling !== 'record_only'
  const notify = config.handling !== 'record_only'
  const conditions: AlertAutomationRuleConditions = {}
  if (config.sourceFamily) conditions.source_families = [config.sourceFamily]
  if (config.severity) conditions.severities = [config.severity]
  if (config.alertClass) conditions.alert_classes = [config.alertClass]
  if (config.host) conditions.host_contains = [config.host]
  if (config.alertName) conditions.name_contains = [config.alertName]
  return {
    id: `quick-${stamp}`,
    name: quickRuleName(config),
    enabled: true,
    conditions,
    action: runAi ? 'analyze' : 'record_only',
    notify,
    channels: notify ? ['wechat', 'dingtalk', 'email'] : [],
    remediation_mode: config.handling === 'auto_low_risk' ? 'auto_low_risk' : config.handling === 'approval' ? 'approval' : config.handling === 'suggest' ? 'suggest' : 'disabled',
    allowed_remediation_actions: config.handling === 'auto_low_risk' ? ['cleanup_temp_files', 'rotate_logs'] : [],
    cooldown_minutes: Math.max(1, Math.min(Number(config.cooldownMinutes) || 30, 1440)),
    reason: runAi
      ? '命中流程策略：首次触发 AI 只读分析；同类重复告警进入降噪窗口后只转发通知。'
      : '命中流程策略，仅记录告警事件。',
  }
}

function quickNotificationText(mode: QuickHandlingMode) {
  return mode === 'record_only' ? '不通知或按外部平台转发' : '企业微信、钉钉、邮件'
}

function quickRemediationText(mode: QuickHandlingMode) {
  if (mode === 'auto_low_risk') return '低风险自动修复'
  if (mode === 'approval') return '生成方案，人工确认后执行'
  if (mode === 'suggest') return '只给建议'
  if (mode === 'readonly_notify') return '只读排查，不改系统'
  return '不修复'
}

function actionLabel(action?: string) {
  return ACTION_OPTIONS.find((item) => item.id === action)?.label || action || '-'
}

function compactOptions(values: Array<string | null | undefined>, limit = 18) {
  return Array.from(new Set(values.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean))).sort().slice(0, limit)
}

function alertLabelOptions(alerts: AlertEvent[]) {
  const values: string[] = []
  alerts.forEach((alert) => {
    ;[alert.labels, alert.annotations].forEach((source) => {
      if (!source || typeof source !== 'object') return
      Object.entries(source).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') return
        values.push(`${key}=${String(value)}`)
      })
    })
  })
  return compactOptions(values, 24)
}

function buildPolicyOptionSet(alerts: AlertEvent[]): PolicyOptionSet {
  return {
    alertClasses: compactOptions(alerts.map((alert) => alert.alert_class)),
    alertNames: compactOptions(alerts.map((alert) => alert.alert_name), 24),
    hosts: compactOptions(alerts.map((alert) => alert.host), 24),
    labelContains: alertLabelOptions(alerts),
    priorities: compactOptions(alerts.map((alert) => alert.priority)),
    severities: compactOptions(alerts.map((alert) => alert.severity)),
    sourceFamilies: compactOptions(alerts.map((alert) => alert.source_family || alert.source_type || alert.source)),
  }
}

function toggleListValue(values: string[] | undefined, value: string) {
  const normalized = value.trim().toLowerCase()
  if (!normalized) return values || []
  const current = new Set(values || [])
  if (current.has(normalized)) current.delete(normalized)
  else current.add(normalized)
  return Array.from(current)
}

function normalizeChannels(rule: AlertAutomationRule, channel: string, checked: boolean): string[] {
  const next = new Set(rule.channels || [])
  if (checked) next.add(channel)
  else next.delete(channel)
  return Array.from(next)
}

function DynamicConditionInput({
  label,
  options,
  placeholder,
  value,
  onChange,
}: {
  label: string
  options: string[]
  placeholder: string
  value?: string[]
  onChange: (value: string[]) => void
}) {
  const selected = value || []
  return (
    <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold text-ops-text">{label}</div>
        <div className="text-[10px] text-ops-overlay">{options.length ? `样本 ${options.length} 项` : '暂无样本'}</div>
      </div>
      <input
        value={listToText(selected)}
        onChange={(event) => onChange(textToList(event.target.value))}
        placeholder={placeholder}
        className="ops-control mt-2 w-full px-3 py-2 text-xs"
      />
      <div className="mt-2 flex max-h-20 flex-wrap gap-1.5 overflow-y-auto">
        {options.length === 0 ? (
          <span className="text-[11px] leading-5 text-ops-overlay">接收告警后这里会出现可点选值，也可以先手填。</span>
        ) : options.map((option) => {
          const active = selected.includes(option)
          return (
            <button
              key={option}
              type="button"
              onClick={() => onChange(toggleListValue(selected, option))}
              className={`rounded border px-2 py-1 text-[11px] transition-colors ${
                active
                  ? 'border-ops-accent bg-ops-accent text-ops-dark'
                  : 'border-ops-surface1 bg-ops-surface0 text-ops-subtext hover:text-ops-text'
              }`}
            >
              {option}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function AlertPolicyDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const addToast = useStore((s) => s.addToast)
  const [editorMode, setEditorMode] = useState<PolicyEditorMode>('simple')
  const [policy, setPolicy] = useState<AlertAutomationPolicy>(EMPTY_POLICY)
  const [activeRuleIndex, setActiveRuleIndex] = useState(0)
  const [quickConfig, setQuickConfig] = useState<QuickPolicyConfig>({
    alertClass: '',
    alertName: '',
    cooldownMinutes: 30,
    handling: 'readonly_notify',
    host: '',
    severity: '',
    sourceFamily: '',
  })
  const [sampleAlerts, setSampleAlerts] = useState<AlertEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testPayload, setTestPayload] = useState(
    JSON.stringify(
      {
        source: 'zabbix',
        host: 'db.local',
        alert_name: 'DiskFull',
        severity: 'critical',
        description: 'disk usage above 95%',
        labels: { service: 'database' },
      },
      null,
      2
    )
  )
  const [testResult, setTestResult] = useState<AlertAutomationPolicyTestResult | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    Promise.allSettled([
      getAlertPolicy(),
      getAlertEvents({ status: 'all', limit: 500 }),
    ])
      .then(([policyResult, alertResult]) => {
        if (cancelled) return
        if (policyResult.status === 'fulfilled') {
          setPolicy(policyResult.value.data.policy || EMPTY_POLICY)
          setActiveRuleIndex(0)
        } else {
          addToast(policyResult.reason instanceof Error ? policyResult.reason.message : '加载告警策略失败', 'error')
        }
        if (alertResult.status === 'fulfilled') {
          setSampleAlerts(alertResult.value.data.alerts || [])
        } else {
          setSampleAlerts([])
          addToast('最近告警样本加载失败，策略条件仍可手填', 'info')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [addToast, open])

  const enabledCount = useMemo(() => policy.rules.filter((rule) => rule.enabled).length, [policy.rules])
  const optionSet = useMemo(() => buildPolicyOptionSet(sampleAlerts), [sampleAlerts])
  const activeRule = policy.rules[activeRuleIndex] || null

  useEffect(() => {
    if (!open || policy.rules.length === 0) return
    if (activeRuleIndex >= policy.rules.length) {
      setActiveRuleIndex(policy.rules.length - 1)
    }
  }, [activeRuleIndex, open, policy.rules.length])

  if (!open) return null

  const updateRule = (index: number, patch: Partial<AlertAutomationRule>) => {
    setPolicy((current) => ({
      ...current,
      rules: current.rules.map((rule, itemIndex) => itemIndex === index ? { ...rule, ...patch } : rule),
    }))
  }

  const updateCondition = (index: number, key: keyof AlertAutomationRule['conditions'], value: unknown) => {
    setPolicy((current) => ({
      ...current,
      rules: current.rules.map((rule, itemIndex) => itemIndex === index
        ? { ...rule, conditions: { ...(rule.conditions || {}), [key]: value } }
        : rule),
    }))
  }

  const updateConditionList = (index: number, key: ConditionListKey, value: string[]) => {
    updateCondition(index, key, value)
  }

  const removeRule = (index: number) => {
    setPolicy((current) => ({ ...current, rules: current.rules.filter((_, itemIndex) => itemIndex !== index) }))
    setActiveRuleIndex((current) => Math.max(0, Math.min(current > index ? current - 1 : current, policy.rules.length - 2)))
  }

  const deleteRuleAndSave = async (index: number) => {
    const rule = policy.rules[index]
    if (!rule) return
    if (!window.confirm(`删除规则「${rule.name}」？`)) return
    const nextPolicy = { ...policy, rules: policy.rules.filter((_, itemIndex) => itemIndex !== index) }
    setSaving(true)
    try {
      const res = await updateAlertPolicy(nextPolicy)
      setPolicy(res.data.policy)
      setActiveRuleIndex(0)
      addToast('规则已删除', 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '删除规则失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  const moveRule = (index: number, direction: -1 | 1) => {
    setPolicy((current) => {
      const target = index + direction
      if (target < 0 || target >= current.rules.length) return current
      const rules = current.rules.slice()
      const [item] = rules.splice(index, 1)
      rules.splice(target, 0, item)
      return { ...current, rules }
    })
    setActiveRuleIndex(index + direction)
  }

  const addRule = () => {
    const rule = newRule()
    setPolicy((current) => ({ ...current, rules: [...current.rules, rule] }))
    setActiveRuleIndex(policy.rules.length)
    setEditorMode('advanced')
  }

  const saveQuickRule = async () => {
    const rule = quickRuleFromConfig(quickConfig)
    const key = ruleMatchKey(rule)
    const existingIndex = policy.rules.findIndex((item) => ruleMatchKey(item) === key || item.name === rule.name)
    const nextRules = existingIndex >= 0
      ? policy.rules.map((item, index) => index === existingIndex ? { ...rule, id: item.id } : item)
      : [rule, ...policy.rules]
    const nextPolicy = { ...policy, rules: nextRules }
    setSaving(true)
    try {
      const res = await updateAlertPolicy(nextPolicy)
      setPolicy(res.data.policy)
      setActiveRuleIndex(0)
      addToast(existingIndex >= 0 ? '已有规则已更新' : '规则已保存并启用', 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '保存规则失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  const save = async () => {
    setSaving(true)
    try {
      const res = await updateAlertPolicy(policy)
      setPolicy(res.data.policy)
      addToast('告警策略已保存', 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '保存告警策略失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  const runTest = async () => {
    setTesting(true)
    try {
      const payload = JSON.parse(testPayload) as Record<string, unknown>
      const res = await testAlertPolicy(payload)
      setTestResult(res.data.result)
      addToast('策略测试完成', 'success')
    } catch (error: unknown) {
      addToast(error instanceof Error ? error.message : '策略测试失败，请检查 JSON', 'error')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[90] bg-ops-dark/70 backdrop-blur-sm">
      <aside className="ops-modal-surface ml-auto flex h-full w-full max-w-[1180px] flex-col rounded-none border-l border-ops-surface1">
        <header className="border-b border-ops-surface0 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-base font-bold text-ops-text">配置告警处理流程</div>
              <div className="mt-1 text-xs text-ops-subtext">
                先选告警范围，再选处理方式。默认只读分析和通知，自动修复必须单独选择。当前 {policy.rules.length} 条规则，启用 {enabledCount} 条。
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <div className="flex rounded-lg border border-ops-surface1 bg-ops-dark/30 p-1">
                <button
                  onClick={() => setEditorMode('simple')}
                  className={`rounded-md px-3 py-1.5 text-xs font-semibold ${editorMode === 'simple' ? 'bg-ops-accent text-ops-dark' : 'text-ops-subtext hover:text-ops-text'}`}
                >
                  简单流程
                </button>
                <button
                  onClick={() => setEditorMode('advanced')}
                  className={`rounded-md px-3 py-1.5 text-xs font-semibold ${editorMode === 'advanced' ? 'bg-ops-accent text-ops-dark' : 'text-ops-subtext hover:text-ops-text'}`}
                >
                  精细规则
                </button>
              </div>
              <button onClick={addRule} className="ops-muted-action px-3 py-2 text-xs">
                添加精细规则
              </button>
              <button onClick={save} disabled={saving || loading} className="ops-primary-action px-4 py-2 text-xs disabled:opacity-50">
                {saving ? '保存中...' : '保存全部'}
              </button>
              <button onClick={onClose} className="ops-muted-action px-3 py-2 text-xs">关闭</button>
            </div>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="ops-data-panel p-8 text-center text-sm text-ops-subtext">正在加载告警策略...</div>
          ) : editorMode === 'simple' ? (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
              <section className="ops-data-panel overflow-hidden">
                <div className="border-b border-ops-surface0 bg-ops-dark/20 px-5 py-4">
                  <div className="text-base font-bold text-ops-text">按真实处理流程配置</div>
                  <div className="mt-1 text-xs leading-5 text-ops-subtext">
                    选中一类告警，决定它只读分析、人工确认修复，还是低风险自动处理。保存后立即生效。
                  </div>
                </div>
                <div className="grid gap-4 p-5">
                  <section className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
                    <div className="flex items-start gap-3">
                      <span className="grid h-7 w-7 shrink-0 place-items-center rounded bg-ops-accent text-xs font-black text-ops-dark">1</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-ops-text">这条规则管哪些告警</div>
                        <p className="mt-1 text-xs leading-5 text-ops-subtext">可以从已接收到的 Prometheus/Zabbix 字段里选，也可以手填。</p>
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          <label className="text-xs text-ops-subtext">
                            告警平台
                            <select value={quickConfig.sourceFamily} onChange={(event) => setQuickConfig((current) => ({ ...current, sourceFamily: event.target.value }))} className="ops-control mt-1 w-full px-3 py-2 text-sm">
                              <option value="">全部平台</option>
                              {optionSet.sourceFamilies.map((item) => <option key={item} value={item}>{item}</option>)}
                            </select>
                          </label>
                          <label className="text-xs text-ops-subtext">
                            主机 / IP
                            <input list="alert-policy-hosts" value={quickConfig.host} onChange={(event) => setQuickConfig((current) => ({ ...current, host: event.target.value }))} placeholder="例如 172.17.8.151" className="ops-control mt-1 w-full px-3 py-2 text-sm" />
                            <datalist id="alert-policy-hosts">
                              {optionSet.hosts.map((item) => <option key={item} value={item} />)}
                            </datalist>
                          </label>
                          <label className="text-xs text-ops-subtext">
                            告警类型
                            <select value={quickConfig.alertClass} onChange={(event) => setQuickConfig((current) => ({ ...current, alertClass: event.target.value }))} className="ops-control mt-1 w-full px-3 py-2 text-sm">
                              <option value="">全部类型</option>
                              {optionSet.alertClasses.map((item) => <option key={item} value={item}>{item}</option>)}
                            </select>
                          </label>
                          <label className="text-xs text-ops-subtext">
                            告警名包含
                            <input list="alert-policy-names" value={quickConfig.alertName} onChange={(event) => setQuickConfig((current) => ({ ...current, alertName: event.target.value }))} placeholder="例如 DiskFull、HostDown" className="ops-control mt-1 w-full px-3 py-2 text-sm" />
                            <datalist id="alert-policy-names">
                              {optionSet.alertNames.map((item) => <option key={item} value={item} />)}
                            </datalist>
                          </label>
                          <label className="text-xs text-ops-subtext md:col-span-2">
                            严重级别
                            <select value={quickConfig.severity} onChange={(event) => setQuickConfig((current) => ({ ...current, severity: event.target.value }))} className="ops-control mt-1 w-full px-3 py-2 text-sm">
                              <option value="">全部级别</option>
                              {optionSet.severities.map((item) => <option key={item} value={item}>{item}</option>)}
                            </select>
                          </label>
                        </div>
                      </div>
                    </div>
                  </section>

                  <section className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
                    <div className="flex items-start gap-3">
                      <span className="grid h-7 w-7 shrink-0 place-items-center rounded bg-ops-accent text-xs font-black text-ops-dark">2</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-ops-text">选择处理流程</div>
                        <p className="mt-1 text-xs leading-5 text-ops-subtext">默认是 AI 只读分析：先查监控，再联动资产会话，只输出建议并通知。</p>
                        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
                          {QUICK_HANDLING_OPTIONS.map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => setQuickConfig((current) => ({ ...current, handling: item.id }))}
                              className={`rounded-lg border p-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ops-accent/70 ${
                                quickConfig.handling === item.id
                                  ? 'border-ops-accent bg-ops-accent/12'
                                  : 'border-ops-surface0 bg-ops-panel/40 hover:border-ops-surface1'
                              }`}
                            >
                              <div className="text-sm font-semibold text-ops-text">{item.label}</div>
                              <div className="mt-1 text-[11px] leading-5 text-ops-subtext">{item.description}</div>
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </section>

                  <section className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-4">
                    <div className="flex items-start gap-3">
                      <span className="grid h-7 w-7 shrink-0 place-items-center rounded bg-ops-accent text-xs font-black text-ops-dark">3</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-ops-text">降噪和通知</div>
                        <p className="mt-1 text-xs leading-5 text-ops-subtext">同一主机同一类告警应合并为事件。首次走 AI；重复告警只更新事件和通知，避免 AI 被刷屏。</p>
                        <div className="mt-3 grid gap-3 md:grid-cols-3">
                          <div className="rounded border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
                            <label className="text-[11px] text-ops-overlay">
                              AI 冷却窗口
                              <input
                                type="number"
                                min={1}
                                max={1440}
                                value={quickConfig.cooldownMinutes}
                                onChange={(event) => setQuickConfig((current) => ({ ...current, cooldownMinutes: Number(event.target.value) || 30 }))}
                                className="ops-control mt-1 w-full px-2 py-1.5 text-sm font-semibold text-ops-text"
                              />
                            </label>
                            <div className="mt-1 text-[10px] text-ops-overlay">单位：分钟，建议 10-60。</div>
                          </div>
                          <div className="rounded border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
                            <div className="text-[11px] text-ops-overlay">重复告警</div>
                            <div className="mt-1 text-sm font-semibold text-ops-text">只转发通知</div>
                          </div>
                          <div className="rounded border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
                            <div className="text-[11px] text-ops-overlay">通知通道</div>
                            <div className="mt-1 text-sm font-semibold text-ops-text">{quickNotificationText(quickConfig.handling)}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </section>

                  <section className="rounded-lg border border-ops-accent/35 bg-ops-accent/8 p-4">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-ops-text">保存后会生成这条规则</div>
                        <div className="mt-2 text-xs leading-6 text-ops-subtext">
                          <span className="font-semibold text-ops-text">{quickRuleName(quickConfig)}</span>
                          <br />
                          修复策略：{quickRemediationText(quickConfig.handling)}；AI 冷却：{quickConfig.cooldownMinutes || 30} 分钟；通知：{quickNotificationText(quickConfig.handling)}。
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={saveQuickRule}
                        disabled={saving || loading}
                        className="ops-primary-action shrink-0 px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
                      >
                        {saving ? '保存中...' : '保存并启用规则'}
                      </button>
                    </div>
                  </section>
                </div>
              </section>

              <aside className="space-y-3">
                <div className="ops-data-panel p-4">
                  <div className="text-sm font-semibold text-ops-text">现在怎么跑</div>
                  <div className="mt-3 space-y-3 text-xs leading-5 text-ops-subtext">
                    <div><span className="font-semibold text-ops-text">接入：</span>外部平台把告警推到 Webhook 或 API。</div>
                    <div><span className="font-semibold text-ops-text">分析：</span>首次命中规则时 AI 查监控和资产会话。</div>
                    <div><span className="font-semibold text-ops-text">降噪：</span>同类重复告警不重复拉 AI。</div>
                    <div><span className="font-semibold text-ops-text">通知：</span>只读建议、人工确认或自动修复后统一通知。</div>
                  </div>
                </div>
                <div className="ops-data-panel p-4">
                  <div className="text-sm font-semibold text-ops-text">规则状态</div>
                  <div className="mt-3 grid gap-2 text-xs text-ops-subtext">
                    <div className="flex justify-between gap-3"><span>规则总数</span><span className="font-mono text-ops-text">{policy.rules.length}</span></div>
                    <div className="flex justify-between gap-3"><span>启用规则</span><span className="font-mono text-ops-text">{enabledCount}</span></div>
                    <div className="flex justify-between gap-3"><span>可选样本</span><span className="font-mono text-ops-text">{sampleAlerts.length}</span></div>
                  </div>
                </div>
                <div className="ops-data-panel p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-ops-text">已有规则</div>
                    <button type="button" onClick={() => setEditorMode('advanced')} className="ops-muted-action px-2 py-1 text-[11px]">
                      精细编辑
                    </button>
                  </div>
                  <div className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
                    {policy.rules.length === 0 ? (
                      <div className="rounded border border-ops-surface0 bg-ops-dark/20 px-3 py-3 text-xs text-ops-overlay">暂无规则</div>
                    ) : policy.rules.map((rule, index) => (
                      <div key={rule.id} className="rounded-lg border border-ops-surface0 bg-ops-dark/20 px-3 py-2">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate text-xs font-semibold text-ops-text">{rule.name}</div>
                            <div className="mt-1 text-[11px] text-ops-overlay">{actionLabel(rule.action)} / {rule.enabled ? '启用' : '停用'}</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => void deleteRuleAndSave(index)}
                            disabled={saving}
                            className="ops-muted-action shrink-0 px-2 py-1 text-[11px] text-ops-alert disabled:opacity-50"
                          >
                            删除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="ops-data-panel p-4">
                  <div className="text-sm font-semibold text-ops-text">需要细调时</div>
                  <div className="mt-2 text-xs leading-6 text-ops-subtext">
                    进入精细规则可以调整顺序、标签匹配、通知通道和自动修复白名单。
                  </div>
                </div>
              </aside>
            </div>
          ) : (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
              <section className="grid min-h-[620px] gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
                <div className="ops-data-panel overflow-hidden">
                  <div className="border-b border-ops-surface0 px-3 py-2">
                    <div className="text-sm font-semibold text-ops-text">规则顺序</div>
                    <div className="mt-1 text-[11px] text-ops-overlay">从上到下命中，第一条生效。</div>
                  </div>
                  <div className="max-h-[calc(100vh-15rem)] overflow-y-auto p-2">
                    {policy.rules.map((rule, index) => (
                      <button
                        key={rule.id}
                        type="button"
                        onClick={() => setActiveRuleIndex(index)}
                        className={`mb-2 w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                          activeRuleIndex === index
                            ? 'border-ops-accent bg-ops-accent/12'
                            : 'border-ops-surface0 bg-ops-dark/25 hover:border-ops-surface1'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-xs font-semibold text-ops-text">{index + 1}. {rule.name}</span>
                          <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] ${rule.enabled ? 'border-ops-success/40 text-ops-success' : 'border-ops-surface1 text-ops-overlay'}`}>
                            {rule.enabled ? '启用' : '停用'}
                          </span>
                        </div>
                        <div className="mt-1 truncate text-[11px] text-ops-subtext">{actionLabel(rule.action)}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {activeRule ? (
                  <div className="ops-data-panel overflow-hidden">
                    <div className="border-b border-ops-surface0 bg-ops-dark/20 px-4 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <label className="inline-flex items-center gap-2 text-sm font-semibold text-ops-text">
                          <input
                            type="checkbox"
                            checked={activeRule.enabled}
                            onChange={(event) => updateRule(activeRuleIndex, { enabled: event.target.checked })}
                            className="accent-ops-accent"
                          />
                          规则 {activeRuleIndex + 1}
                        </label>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <button onClick={() => moveRule(activeRuleIndex, -1)} disabled={activeRuleIndex === 0} className="ops-muted-action px-2 py-1 disabled:opacity-40">上移</button>
                          <button onClick={() => moveRule(activeRuleIndex, 1)} disabled={activeRuleIndex === policy.rules.length - 1} className="ops-muted-action px-2 py-1 disabled:opacity-40">下移</button>
                          <button onClick={() => removeRule(activeRuleIndex)} className="ops-muted-action px-2 py-1 text-ops-alert">删除</button>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_220px_220px]">
                        <label className="text-xs text-ops-subtext">
                          规则名称
                          <input value={activeRule.name} onChange={(event) => updateRule(activeRuleIndex, { name: event.target.value })} className="ops-control mt-1 w-full px-3 py-2 text-sm" />
                        </label>
                        <label className="text-xs text-ops-subtext">
                          动作
                          <select value={activeRule.action} onChange={(event) => updateRule(activeRuleIndex, { action: event.target.value as AlertAutomationAction })} className="ops-control mt-1 w-full px-3 py-2 text-sm">
                            {ACTION_OPTIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                          </select>
                        </label>
                        <label className="text-xs text-ops-subtext">
                          自动修复模式
                          <select value={activeRule.remediation_mode || 'disabled'} onChange={(event) => updateRule(activeRuleIndex, { remediation_mode: event.target.value })} className="ops-control mt-1 w-full px-3 py-2 text-sm">
                            {REMEDIATION_MODE_OPTIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                          </select>
                        </label>
                      </div>
                    </div>

                    <div className="max-h-[calc(100vh-15rem)] overflow-y-auto p-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <div>
                          <div className="text-xs font-semibold text-ops-text">匹配条件</div>
                          <div className="mt-1 text-[11px] text-ops-overlay">点击样本值快速加入；输入框仍可补充未出现的新值。</div>
                        </div>
                        <span className="rounded border border-ops-surface1 bg-ops-surface0 px-2 py-1 text-[10px] text-ops-subtext">
                          {activeRule.enabled ? '启用' : '停用'}
                        </span>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        <DynamicConditionInput label="来源平台" value={activeRule.conditions.source_families} options={optionSet.sourceFamilies} placeholder="zabbix, prometheus" onChange={(value) => updateConditionList(activeRuleIndex, 'source_families', value)} />
                        <DynamicConditionInput label="严重级别" value={activeRule.conditions.severities} options={optionSet.severities} placeholder="critical, warning" onChange={(value) => updateConditionList(activeRuleIndex, 'severities', value)} />
                        <DynamicConditionInput label="告警类型" value={activeRule.conditions.alert_classes} options={optionSet.alertClasses} placeholder="network, database" onChange={(value) => updateConditionList(activeRuleIndex, 'alert_classes', value)} />
                        <DynamicConditionInput label="优先级" value={activeRule.conditions.priorities} options={optionSet.priorities} placeholder="p0, p1, p2" onChange={(value) => updateConditionList(activeRuleIndex, 'priorities', value)} />
                        <DynamicConditionInput label="主机包含" value={activeRule.conditions.host_contains} options={optionSet.hosts} placeholder="db, 172.17" onChange={(value) => updateConditionList(activeRuleIndex, 'host_contains', value)} />
                        <DynamicConditionInput label="告警名包含" value={activeRule.conditions.name_contains} options={optionSet.alertNames} placeholder="disk, linkdown" onChange={(value) => updateConditionList(activeRuleIndex, 'name_contains', value)} />
                        <DynamicConditionInput label="标签/注解包含" value={activeRule.conditions.label_contains} options={optionSet.labelContains} placeholder="service=database" onChange={(value) => updateConditionList(activeRuleIndex, 'label_contains', value)} />
                        <label className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3 text-xs text-ops-subtext">
                          重复次数至少
                          <input type="number" min={1} value={activeRule.conditions.min_repeat_count || ''} onChange={(event) => updateCondition(activeRuleIndex, 'min_repeat_count', event.target.value ? Number(event.target.value) : undefined)} className="ops-control mt-2 w-full px-3 py-2 text-sm" />
                        </label>
                        <label className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3 text-xs text-ops-subtext">
                          AI 冷却窗口（分钟）
                          <input type="number" min={1} max={1440} value={activeRule.cooldown_minutes || 30} onChange={(event) => updateRule(activeRuleIndex, { cooldown_minutes: Number(event.target.value) || 30 })} className="ops-control mt-2 w-full px-3 py-2 text-sm" />
                        </label>
                        <label className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3 text-xs text-ops-subtext">
                          允许的低风险修复动作
                          <input value={listToText(activeRule.allowed_remediation_actions)} onChange={(event) => updateRule(activeRuleIndex, { allowed_remediation_actions: textToList(event.target.value) })} placeholder="cleanup_temp_files, rotate_logs" className="ops-control mt-2 w-full px-3 py-2 text-sm" />
                        </label>
                      </div>

                      <div className="mt-3 grid gap-3 border-t border-ops-surface0 pt-3 md:grid-cols-[220px_1fr]">
                        <label className="inline-flex items-center gap-2 text-xs text-ops-subtext">
                          <input type="checkbox" checked={activeRule.notify} onChange={(event) => updateRule(activeRuleIndex, { notify: event.target.checked })} className="accent-ops-accent" />
                          AI 分析完成后通知
                        </label>
                        <div className="flex flex-wrap gap-3 text-xs text-ops-subtext">
                          {CHANNEL_OPTIONS.map((channel) => (
                            <label key={channel.id} className="inline-flex items-center gap-1.5">
                              <input
                                type="checkbox"
                                checked={(activeRule.channels || []).includes(channel.id)}
                                onChange={(event) => updateRule(activeRuleIndex, { channels: normalizeChannels(activeRule, channel.id, event.target.checked) })}
                                className="accent-ops-accent"
                              />
                              {channel.label}
                            </label>
                          ))}
                        </div>
                      </div>
                      <label className="mt-3 block text-xs text-ops-subtext">
                        策略原因
                        <textarea value={activeRule.reason} onChange={(event) => updateRule(activeRuleIndex, { reason: event.target.value })} rows={2} className="ops-control mt-1 w-full resize-y px-3 py-2 text-sm" />
                      </label>
                    </div>
                  </div>
                ) : (
                  <div className="ops-data-panel p-8 text-center text-sm text-ops-subtext">暂无规则，点击右上角添加。</div>
                )}
              </section>

              <section className="space-y-3">
                <div className="ops-data-panel p-4">
                  <div className="text-sm font-semibold text-ops-text">策略测试</div>
                  <p className="mt-1 text-xs leading-5 text-ops-subtext">粘贴任意监控告警 payload，直接查看会命中的规则和动作。</p>
                  <textarea value={testPayload} onChange={(event) => setTestPayload(event.target.value)} rows={13} className="ops-control mt-3 w-full resize-y px-3 py-2 font-mono text-xs leading-5" />
                  <button onClick={runTest} disabled={testing} className="ops-primary-action mt-3 w-full px-3 py-2 text-xs disabled:opacity-50">
                    {testing ? '测试中...' : '测试命中策略'}
                  </button>
                </div>
                {testResult && (
                  <div className="ops-data-panel p-4 text-xs text-ops-subtext">
                    <div className="mb-2 text-sm font-semibold text-ops-text">测试结果</div>
                    <div className="grid gap-2">
                      <div className="flex justify-between gap-3"><span>来源分类</span><span className="font-mono text-ops-text">{testResult.policy.source_family || '-'}</span></div>
                      <div className="flex justify-between gap-3"><span>告警类型</span><span className="font-mono text-ops-text">{testResult.policy.alert_class || '-'}</span></div>
                      <div className="flex justify-between gap-3"><span>优先级</span><span className="font-mono text-ops-text">{testResult.policy.priority || '-'}</span></div>
                      <div className="flex justify-between gap-3"><span>命中规则</span><span className="text-right font-mono text-ops-text">{testResult.policy.automation_decision?.rule_name || '-'}</span></div>
                      <div className="flex justify-between gap-3"><span>动作</span><span className="text-right text-ops-text">{actionLabel(testResult.policy.noise_action)}</span></div>
                      <div className="flex justify-between gap-3"><span>AI 分析</span><span className="text-ops-text">{testResult.policy.automation_decision?.run_ai ? '会触发' : '不触发'}</span></div>
                      <div className="flex justify-between gap-3"><span>通知</span><span className="text-ops-text">{testResult.policy.automation_decision?.notify ? (testResult.policy.notification_plan?.targets || []).join(', ') || 'auto' : '不通知'}</span></div>
                      <div className="flex justify-between gap-3"><span>修复模式</span><span className="text-ops-text">{testResult.policy.automation_decision?.remediation_mode || 'disabled'}</span></div>
                    </div>
                    <div className="mt-3 rounded border border-ops-surface0 bg-ops-dark/30 p-3 leading-5">
                      {testResult.policy.automation_decision?.reason || '-'}
                    </div>
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
