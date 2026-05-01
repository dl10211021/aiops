import type { Dispatch, SetStateAction } from 'react'
import {
  CATEGORY_LABELS,
  DEFAULT_FORM,
  SCOPE_OPTIONS,
  SOURCE_OPTIONS,
  SQL_ACTION_OPTIONS,
} from './safetyPolicyShared'
import type { CategoryKey, Decision, DomainDefinition, MatcherType } from './safetyPolicyShared'

type RuleFormState = typeof DEFAULT_FORM

interface RuleFormPanelProps {
  activeCategory: CategoryKey
  activeDomain: DomainDefinition
  form: RuleFormState
  setForm: Dispatch<SetStateAction<RuleFormState>>
  selectedPlatform: string
  isSqlActionMatcher: boolean
  matcherValuePlaceholder: string
  scopePlaceholder: string
  toggleSource: (source: string) => void
  addSimpleRule: () => void
}

export function RuleFormPanel({
  activeCategory,
  activeDomain,
  form,
  setForm,
  selectedPlatform,
  isSqlActionMatcher,
  matcherValuePlaceholder,
  scopePlaceholder,
  toggleSource,
  addSimpleRule,
}: RuleFormPanelProps) {
  return (
    <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-surface0/30 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-ops-text">新增规则</h4>
          <p className="mt-1 text-xs text-ops-subtext">不用写正则也可以加入审批或禁止执行规则；名称、平台和匹配条件会作为结构化规则保存。</p>
        </div>
        <span className="rounded-full border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">
          分类 {CATEGORY_LABELS[activeCategory]}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label>
          <span className="text-xs text-ops-subtext">规则名称</span>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="例如：生产环境禁止删除虚拟机"
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
        </label>
        <label>
          <span className="text-xs text-ops-subtext">平台类型</span>
          <select
            value={selectedPlatform}
            onChange={(e) => setForm({ ...form, platform: e.target.value })}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            {activeDomain.platforms.map((platform) => (
              <option key={platform} value={platform}>{platform}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-ops-subtext">适用对象</span>
          <input
            value={form.resource}
            onChange={(e) => setForm({ ...form, resource: e.target.value })}
            placeholder="例如：虚拟机、Bucket、数据库表、告警规则"
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
        </label>
        <label>
          <span className="text-xs text-ops-subtext">业务动作</span>
          <input
            value={form.action}
            onChange={(e) => setForm({ ...form, action: e.target.value })}
            placeholder="例如：删除、重启、发布、扩缩容"
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
        </label>
        <label>
          <span className="text-xs text-ops-subtext">处理方式</span>
          <select
            value={form.decision}
            onChange={(e) => setForm({ ...form, decision: e.target.value as Decision })}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            <option value="approval">需要审批</option>
            <option value="deny">禁止执行</option>
          </select>
        </label>
        <label>
          <span className="text-xs text-ops-subtext">匹配方式</span>
          <select
            value={form.matcherType}
            onChange={(e) => {
              const nextType = e.target.value as MatcherType
              setForm({
                ...form,
                matcherType: nextType,
                matcherValue: nextType === 'sql_action' ? SQL_ACTION_OPTIONS[0].value : form.matcherValue,
              })
            }}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            {activeCategory === 'sql' && <option value="sql_action">SQL 动作</option>}
            <option value="contains">包含关键词</option>
            <option value="prefix">命令开头</option>
            <option value="equals">完全等于</option>
            <option value="http_method">HTTP 方法</option>
            <option value="platform_action">平台动作</option>
            <option value="regex">正则匹配（高级）</option>
          </select>
        </label>
        <label>
          <span className="text-xs text-ops-subtext">匹配内容</span>
          {isSqlActionMatcher ? (
            <select
              value={form.matcherValue}
              onChange={(e) => setForm({ ...form, matcherValue: e.target.value })}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            >
              {SQL_ACTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label} - {option.hint}</option>
              ))}
            </select>
          ) : (
            <input
              value={form.matcherValue}
              onChange={(e) => setForm({ ...form, matcherValue: e.target.value })}
              placeholder={matcherValuePlaceholder}
              className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
            />
          )}
        </label>
        <label className="col-span-2">
          <span className="text-xs text-ops-subtext">规则说明</span>
          <input
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            placeholder="例如：生产虚拟机删除必须由人工平台操作"
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
        </label>
        <label>
          <span className="text-xs text-ops-subtext">生效范围</span>
          <select
            value={form.scopeType}
            onChange={(e) => setForm({ ...form, scopeType: e.target.value })}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            {SCOPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-ops-subtext">范围值</span>
          <input
            value={form.scopeValue}
            onChange={(e) => setForm({ ...form, scopeValue: e.target.value })}
            disabled={form.scopeType === 'all'}
            placeholder={scopePlaceholder}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-45"
          />
        </label>
        <div className="col-span-2">
          <span className="text-xs text-ops-subtext">操作来源</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {SOURCE_OPTIONS.map((sourceOption) => (
              <label key={sourceOption.value} className="inline-flex items-center gap-2 rounded-full border border-ops-surface1 px-3 py-1 text-xs text-ops-text">
                <input
                  type="checkbox"
                  checked={form.sources.includes(sourceOption.value)}
                  onChange={() => toggleSource(sourceOption.value)}
                  className="accent-ops-accent"
                />
                {sourceOption.label}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
        <p className="text-xs leading-5 text-ops-subtext">
          {form.decision === 'approval'
            ? '审批规则：读写会话进入审批；只读会话会被阻止，避免误执行变更动作。'
            : '禁止执行规则：当前阶段按包含关键词生效，适合放删库、格式化、公开 Bucket、删除虚拟机等明确危险动作。'}
        </p>
        <button
          onClick={addSimpleRule}
          className="shrink-0 rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark transition-colors hover:bg-ops-accent/80"
        >
          加入规则
        </button>
      </div>
    </section>
  )
}
