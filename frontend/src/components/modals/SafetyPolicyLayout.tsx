import type { SafetyPolicy } from '@/types'
import { SAFETY_POLICY_DOMAINS } from './safetyPolicyDomains'
import { categoryCount } from './safetyPolicyLogic'
import { CATEGORY_LABELS, POLICY_PANELS } from './safetyPolicyShared'
import type { DomainDefinition, PolicyPanel } from './safetyPolicyShared'

interface SafetyPolicyTotals {
  action: number
  advanced: number
  networkEnabled: boolean
}

interface SafetyPolicySidebarProps {
  activeDomainId: string
  policy: SafetyPolicy | null
  totals: SafetyPolicyTotals
  onClose: () => void
  onSwitchDomain: (domainId: string) => void
}

export function SafetyPolicySidebar({
  activeDomainId,
  policy,
  totals,
  onClose,
  onSwitchDomain,
}: SafetyPolicySidebarProps) {
  return (
    <aside className="flex w-72 flex-col border-r border-ops-surface0 bg-ops-dark">
      <div className="border-b border-ops-surface0 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-ops-text">安全策略</h2>
            <p className="mt-1 text-[11px] text-ops-subtext">以动作权限为主，网络边界和高级字段兜底</p>
          </div>
          <button onClick={onClose} className="text-xl text-ops-subtext hover:text-ops-text">&times;</button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 border-b border-ops-surface0 p-3 text-center">
        <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-2 py-2">
          <div className="text-lg font-bold text-emerald-200">{totals.action}</div>
          <div className="text-[10px] text-ops-subtext">动作策略</div>
        </div>
        <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-2 py-2">
          <div className="text-lg font-bold text-cyan-200">{totals.networkEnabled ? '开' : '关'}</div>
          <div className="text-[10px] text-ops-subtext">网络边界</div>
        </div>
        <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-2 py-2">
          <div className="text-lg font-bold text-yellow-200">{totals.advanced}</div>
          <div className="text-[10px] text-ops-subtext">高级兜底</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {SAFETY_POLICY_DOMAINS.map((domain) => (
          <button
            key={domain.id}
            onClick={() => onSwitchDomain(domain.id)}
            className={`mb-1 flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left transition-colors ${
              activeDomainId === domain.id ? 'bg-ops-surface1 text-ops-text' : 'text-ops-subtext hover:bg-ops-surface0'
            }`}
          >
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-ops-surface1 bg-ops-panel text-xs font-bold">
              {domain.icon}
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium">{domain.label}</span>
              <span className="block truncate text-[10px] text-ops-overlay">
                {CATEGORY_LABELS[domain.category]} · {categoryCount(policy?.categories?.[domain.category])} 条
              </span>
            </span>
          </button>
        ))}
      </div>
    </aside>
  )
}

interface SafetyPolicyHeaderProps {
  activeDomain: DomainDefinition
  activePanel: PolicyPanel
  selectedPlatform: string
  onPanelChange: (panel: PolicyPanel) => void
  onPlatformChange: (platform: string) => void
}

export function SafetyPolicyHeader({
  activeDomain,
  activePanel,
  selectedPlatform,
  onPanelChange,
  onPlatformChange,
}: SafetyPolicyHeaderProps) {
  return (
    <header className="border-b border-ops-surface0 px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-ops-accent/15 text-sm font-bold text-ops-accent">
              {activeDomain.icon}
            </span>
            <div>
              <h3 className="text-base font-semibold text-ops-text">{activeDomain.label}</h3>
              <p className="text-xs text-ops-subtext">{activeDomain.hint}</p>
            </div>
          </div>
        </div>
        <label className="w-52 shrink-0">
          <span className="text-xs text-ops-subtext">当前平台</span>
          <select
            value={selectedPlatform}
            onChange={(e) => onPlatformChange(e.target.value)}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            {activeDomain.platforms.map((platform) => (
              <option key={platform} value={platform}>{platform}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-4">
        {POLICY_PANELS.map((panel) => (
          <button
            key={panel.id}
            onClick={() => onPanelChange(panel.id)}
            className={`rounded-lg border px-3 py-2 text-left transition-colors ${
              activePanel === panel.id
                ? 'border-ops-accent bg-ops-accent/12 text-ops-text'
                : 'border-ops-surface0 bg-ops-dark/35 text-ops-subtext hover:border-ops-surface1 hover:text-ops-text'
            }`}
          >
            <span className="block text-sm font-semibold">{panel.label}</span>
            <span className="mt-0.5 block text-[11px] text-ops-overlay">{panel.hint}</span>
          </button>
        ))}
      </div>
    </header>
  )
}

export function SafetyPolicyDecisionGuide() {
  return (
    <>
      <section className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3">
          <div className="text-sm font-semibold text-emerald-200">允许执行</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">只读巡检、状态查询、日志查看默认允许，不需要单独拦截。</p>
        </div>
        <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 p-3">
          <div className="text-sm font-semibold text-yellow-200">需要审批</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">读写会话进入审批；只读会话阻止执行并提示切换读写。</p>
        </div>
        <div className="rounded-lg border border-red-400/20 bg-red-400/10 p-3">
          <div className="text-sm font-semibold text-red-200">禁止执行</div>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">无论只读或读写，命中后直接拒绝，不进入审批。</p>
        </div>
      </section>

      <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-ops-text">判定优先级</span>
          {[
            '网络边界',
            '高级禁止兜底',
            '动作权限',
            '高级审批/只读兜底',
            '默认放行',
          ].map((label, index) => (
            <span key={label} className="flex items-center gap-2">
              <span className="rounded-full border border-ops-surface1 bg-ops-panel px-2 py-1 text-ops-subtext">
                {index + 1}. {label}
              </span>
              {index < 4 && <span className="text-ops-overlay">→</span>}
            </span>
          ))}
        </div>
        <p className="mt-2 text-xs leading-5 text-ops-subtext">
          动作权限是日常主配置；高级设置只做更严格的禁止兜底，或在系统没有识别出动作时补充审批和只读保护。
        </p>
      </section>
    </>
  )
}
