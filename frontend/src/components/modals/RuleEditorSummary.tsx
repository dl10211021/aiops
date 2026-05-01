import type { SafetyPolicyRule } from '@/types'
import { DECISION_LABELS, MATCHER_LABELS, SCOPE_OPTIONS, SOURCE_OPTIONS } from './safetyPolicyShared'
import type { Decision, DomainDefinition, MatcherType, OperationPreset } from './safetyPolicyShared'

type RuleTemplateSummary = {
  id: string
  name: string
  description: string
  rules: unknown[]
}

interface RuleEditorSummaryProps {
  activeDomain: DomainDefinition
  templates: RuleTemplateSummary[]
  visibleDecision: Decision
  visibleRules: SafetyPolicyRule[]
  visibleOperationPresets: OperationPreset[]
  applyTemplate: (templateId: string) => void
  applyOperationPreset: (preset: OperationPreset) => void
  updateSemanticRule: (ruleId: string, patch: Partial<SafetyPolicyRule>) => void
  removeSemanticRule: (ruleId: string) => void
}

function semanticMatcherType(type: MatcherType) {
  if (type === 'prefix') return 'command_prefix'
  if (type === 'equals') return 'equals'
  if (type === 'http_method') return 'http_method'
  if (type === 'platform_action') return 'platform_action'
  if (type === 'sql_action') return 'sql_action'
  return type
}

function scopeLabel(type?: string, value?: string) {
  const option = SCOPE_OPTIONS.find((item) => item.value === type)
  if (!type || type === 'all') return '全部资产'
  return `${option?.label || type}: ${value || '未填写'}`
}

function sourceLabel(source: string) {
  return SOURCE_OPTIONS.find((item) => item.value === source)?.label || source
}

function matcherLabel(type: string, value: string) {
  return `${MATCHER_LABELS[type] || type}：${value}`
}

export function RuleEditorSummary({
  activeDomain,
  templates,
  visibleDecision,
  visibleRules,
  visibleOperationPresets,
  applyTemplate,
  applyOperationPreset,
  updateSemanticRule,
  removeSemanticRule,
}: RuleEditorSummaryProps) {
  return (
    <>
      <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45">
        <div className="grid grid-cols-[1.2fr_1fr_1fr_1.8fr] border-b border-ops-surface0 px-4 py-2 text-[11px] font-semibold text-ops-overlay">
          <span>动作</span>
          <span>建议策略</span>
          <span>平台对象</span>
          <span>示例</span>
        </div>
        {activeDomain.examples.map((item) => (
          <div key={`${item.action}-${item.example}`} className="grid grid-cols-[1.2fr_1fr_1fr_1.8fr] items-center border-b border-ops-surface0/70 px-4 py-3 last:border-b-0">
            <span className="text-sm font-medium text-ops-text">{item.action}</span>
            <span>
              <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${DECISION_LABELS[item.decision].className}`}>
                {DECISION_LABELS[item.decision].label}
              </span>
            </span>
            <span className="text-xs text-ops-subtext">{activeDomain.objects}</span>
            <span className="truncate font-mono text-xs text-ops-overlay">{item.example}</span>
          </div>
        ))}
      </section>

      <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-ops-text">策略模板</h4>
            <p className="mt-1 text-xs text-ops-subtext">一键加入常用规则组合，保存后生效，可继续单条启停或删除。</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {templates.map((template) => (
            <button
              key={template.id}
              onClick={() => applyTemplate(template.id)}
              className="rounded-lg border border-ops-surface1 bg-ops-panel/50 p-3 text-left transition-colors hover:border-ops-accent/60 hover:bg-ops-surface0/60"
            >
              <span className="block text-sm font-semibold text-ops-text">{template.name}</span>
              <span className="mt-1 block text-xs leading-5 text-ops-subtext">{template.description}</span>
              <span className="mt-2 block text-[11px] text-ops-overlay">{template.rules.length} 条规则</span>
            </button>
          ))}
        </div>
      </section>

      <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45">
        <div className="flex items-center justify-between border-b border-ops-surface0 px-4 py-3">
          <div>
            <h4 className="text-sm font-semibold text-ops-text">已配置{DECISION_LABELS[visibleDecision].label}</h4>
            <p className="mt-1 text-xs text-ops-subtext">这里只展示当前类型的结构化规则，可直接启停或删除。</p>
          </div>
          <span className="text-xs text-ops-overlay">{visibleRules.length} 条</span>
        </div>
        {visibleRules.length === 0 ? (
          <div className="px-4 py-5 text-sm text-ops-subtext">当前资源域还没有结构化规则，可以在下方新增。</div>
        ) : (
          <div className="divide-y divide-ops-surface0">
            {visibleRules.map((rule) => (
              <div key={rule.id} className="grid grid-cols-[1.3fr_1fr_1fr_auto] items-center gap-3 px-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${DECISION_LABELS[rule.decision].className}`}>
                      {DECISION_LABELS[rule.decision].label}
                    </span>
                    <span className="truncate text-sm font-medium text-ops-text">{rule.name}</span>
                  </div>
                  <p className="mt-1 truncate text-xs text-ops-subtext">{rule.description || '无说明'}</p>
                  <p className="mt-1 truncate text-[11px] text-ops-overlay">
                    范围：{scopeLabel(rule.scope?.type, rule.scope?.value)} · 来源：{rule.sources?.length ? rule.sources.map(sourceLabel).join(' / ') : '全部来源'}
                  </p>
                </div>
                <span className="text-xs text-ops-subtext">{rule.platform || '-'}</span>
                <span className="truncate text-xs text-ops-overlay" title={rule.matchers?.map((matcher) => matcherLabel(matcher.type, matcher.value)).join(' / ')}>
                  {rule.matchers?.map((matcher) => matcherLabel(matcher.type, matcher.value)).join(' / ')}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => updateSemanticRule(rule.id, { enabled: !rule.enabled })}
                    className={`rounded-md border px-2 py-1 text-xs ${
                      rule.enabled === false
                        ? 'border-ops-surface1 text-ops-subtext hover:text-ops-text'
                        : 'border-emerald-400/30 text-emerald-200 hover:bg-emerald-400/10'
                    }`}
                  >
                    {rule.enabled === false ? '已停用' : '启用中'}
                  </button>
                  <button
                    onClick={() => removeSemanticRule(rule.id)}
                    className="rounded-md border border-red-400/30 px-2 py-1 text-xs text-red-200 hover:bg-red-400/10"
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {visibleOperationPresets.length > 0 && (
        <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-ops-text">常见动作快速填入</h4>
              <p className="mt-1 text-xs text-ops-subtext">选择业务动作后，系统会自动填好平台、对象、处理方式和匹配内容，你只需要调整范围并保存。</p>
            </div>
            <span className="rounded-lg border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">{visibleOperationPresets.length} 个动作</span>
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            {visibleOperationPresets.map((preset) => (
              <button
                key={`${preset.platform}-${preset.name}`}
                onClick={() => applyOperationPreset(preset)}
                className="rounded-lg border border-ops-surface1 bg-ops-panel/50 p-3 text-left transition-colors hover:border-ops-accent/60 hover:bg-ops-surface0/60"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-ops-text">{preset.name}</span>
                  <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${DECISION_LABELS[preset.decision].className}`}>
                    {DECISION_LABELS[preset.decision].label}
                  </span>
                </div>
                <div className="mt-2 text-[11px] text-ops-subtext">{preset.platform} · {preset.resource} · {preset.action}</div>
                <div className="mt-1 truncate text-[11px] text-ops-overlay">{matcherLabel(semanticMatcherType(preset.matcherType), preset.matcherValue)}</div>
              </button>
            ))}
          </div>
        </section>
      )}
    </>
  )
}
