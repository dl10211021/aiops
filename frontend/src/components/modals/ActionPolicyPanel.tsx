import type { Dispatch, SetStateAction } from 'react'
import type { SafetyPolicy, SafetyPolicyDecision } from '@/types'
import {
  ACTION_RULE_DOMAIN_OPTIONS,
  DECISION_LABELS,
} from './safetyPolicyShared'
import type { ActionRuleOption, DomainDefinition } from './safetyPolicyShared'

type ActionPolicy = {
  domain: string
  title: string
  description: string
  options: ActionRuleOption[]
} | null

type CustomActionRule = {
  domain: string
  actionId: string
  decision: SafetyPolicyDecision
}

interface ActionPolicyPanelProps {
  policy: SafetyPolicy
  activeDomain: DomainDefinition
  actionPolicy: ActionPolicy
  customActionDomain: string
  customActionPlaceholder: string
  customActionRule: CustomActionRule
  customActionRows: Array<[string, SafetyPolicyDecision]>
  setCustomActionRule: Dispatch<SetStateAction<CustomActionRule>>
  updateActionRule: (domain: string, actionId: string, decision: SafetyPolicyDecision) => void
  removeActionRule: (domain: string, actionId: string) => void
  addCustomActionRule: () => void
}

export function ActionPolicyPanel({
  policy,
  activeDomain,
  actionPolicy,
  customActionDomain,
  customActionPlaceholder,
  customActionRule,
  customActionRows,
  setCustomActionRule,
  updateActionRule,
  removeActionRule,
  addCustomActionRule,
}: ActionPolicyPanelProps) {
  return (
    <>
      {actionPolicy ? (
        <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45">
          <div className="flex items-center justify-between gap-3 border-b border-ops-surface0 px-4 py-3">
            <div>
              <h4 className="text-sm font-semibold text-ops-text">{actionPolicy.title}</h4>
              <p className="mt-1 text-xs leading-5 text-ops-subtext">
                {actionPolicy.description}
              </p>
            </div>
            <span className="rounded-lg border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">
              {actionPolicy.options.length} 个动作
            </span>
          </div>

          <div className="divide-y divide-ops-surface0">
            {actionPolicy.options.map((action) => {
              const decision = policy.action_rules?.[actionPolicy.domain]?.[action.id] || action.defaultDecision
              return (
                <div key={action.id} className="grid grid-cols-[1.2fr_1.4fr_150px] items-center gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ops-text">{action.label}</span>
                      <span className="font-mono text-[10px] text-ops-overlay">{action.id}</span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-ops-subtext">{action.description}</p>
                  </div>
                  <div className="min-w-0 rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2">
                    <div className="text-[10px] text-ops-overlay">示例</div>
                    <div className="truncate font-mono text-xs text-ops-subtext" title={action.example}>{action.example}</div>
                  </div>
                  <label>
                    <span className="sr-only">{action.label}处理方式</span>
                    <select
                      value={decision}
                      onChange={(e) => updateActionRule(actionPolicy.domain, action.id, e.target.value as SafetyPolicyDecision)}
                      className={`w-full rounded-lg border px-3 py-2 text-sm outline-none ${DECISION_LABELS[decision].className} bg-ops-dark focus:border-ops-accent`}
                    >
                      <option value="allow">允许执行</option>
                      <option value="approval">需要审批</option>
                      <option value="deny">禁止执行</option>
                    </select>
                  </label>
                </div>
              )
            })}
          </div>
        </section>
      ) : (
        <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
          <div>
            <h4 className="text-sm font-semibold text-ops-text">当前平台使用自定义动作</h4>
            <p className="mt-1 text-xs leading-5 text-ops-subtext">
              {activeDomain.label} 的动作通常来自平台 API、设备命令或业务语义。请在下方“自定义动作策略”中录入系统识别出的动作 ID，
              并直接设置为允许执行、需要审批或禁止执行。
            </p>
          </div>
        </section>
      )}

      <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
        <div className="mb-3 flex items-start justify-between gap-4">
          <div>
            <h4 className="text-sm font-semibold text-ops-text">自定义动作策略</h4>
            <p className="mt-1 text-xs leading-5 text-ops-subtext">
              适合把测试器或会话轨迹里识别出的动作 ID 手动加入策略。只有系统能识别出的动作 ID 会生效；
              临时关键词或正则兜底能力已移到“高级设置”，普通配置优先使用动作 ID。
            </p>
          </div>
          <span className="shrink-0 rounded-lg border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">
            {ACTION_RULE_DOMAIN_OPTIONS.find((item) => item.value === customActionDomain)?.label || customActionDomain}
          </span>
        </div>

        <div className="grid gap-3 md:grid-cols-[180px_1fr_150px_auto]">
          <label>
            <span className="text-xs text-ops-subtext">策略域</span>
            <select
              value={customActionDomain}
              onChange={(e) => setCustomActionRule({ ...customActionRule, domain: e.target.value })}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              {ACTION_RULE_DOMAIN_OPTIONS.map((domain) => (
                <option key={domain.value} value={domain.value}>{domain.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span className="text-xs text-ops-subtext">动作 ID</span>
            <input
              value={customActionRule.actionId}
              onChange={(e) => setCustomActionRule({ ...customActionRule, actionId: e.target.value })}
              placeholder={customActionPlaceholder}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-sm text-ops-text outline-none focus:border-ops-accent"
            />
          </label>
          <label>
            <span className="text-xs text-ops-subtext">处理方式</span>
            <select
              value={customActionRule.decision}
              onChange={(e) => setCustomActionRule({ ...customActionRule, decision: e.target.value as SafetyPolicyDecision })}
              className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm outline-none ${DECISION_LABELS[customActionRule.decision].className} bg-ops-dark focus:border-ops-accent`}
            >
              <option value="allow">允许执行</option>
              <option value="approval">需要审批</option>
              <option value="deny">禁止执行</option>
            </select>
          </label>
          <button
            type="button"
            onClick={addCustomActionRule}
            className="self-end rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark transition-colors hover:bg-ops-accent/80"
          >
            加入
          </button>
        </div>

        <div className="mt-4 rounded-lg border border-ops-surface0 bg-ops-panel/35">
          <div className="flex items-center justify-between border-b border-ops-surface0 px-3 py-2">
            <span className="text-xs font-semibold text-ops-text">当前域的自定义动作</span>
            <span className="text-[11px] text-ops-overlay">{customActionRows.length} 条</span>
          </div>
          {customActionRows.length === 0 ? (
            <div className="px-3 py-3 text-xs text-ops-subtext">当前策略域还没有额外自定义动作。</div>
          ) : (
            <div className="divide-y divide-ops-surface0">
              {customActionRows.map(([actionId, decision]) => (
                <div key={actionId} className="flex items-center gap-3 px-3 py-2">
                  <span className="min-w-0 flex-1 truncate font-mono text-xs text-ops-text">{actionId}</span>
                  <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${DECISION_LABELS[decision].className}`}>
                    {DECISION_LABELS[decision].label}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeActionRule(customActionDomain, actionId)}
                    className="shrink-0 rounded-md border border-red-400/30 px-2 py-1 text-xs text-red-200 hover:bg-red-400/10"
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  )
}
