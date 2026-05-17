import type { ApprovalAuditSummary, ApprovalRequest } from '@/types'
import type {
  SessionModeResolution,
  SessionModeSource,
} from '@/features/sessions/toolPolicyPresentation'
import {
  approvalRiskFilterLabel,
  type ApprovalRiskFilter,
  type ApprovalMetricTone,
  type ApprovalStatusFilter,
} from './approvalDisplay'
import { ApprovalRow } from './ApprovalRow'

const STATUS_OPTIONS: Array<{ id: ApprovalStatusFilter; label: string }> = [
  { id: 'pending', label: '待审批' },
  { id: 'approved', label: '已批准' },
  { id: 'rejected', label: '已拒绝' },
  { id: 'timeout', label: '已超时' },
  { id: 'all', label: '全部' },
]

const RISK_OPTIONS: ApprovalRiskFilter[] = ['all', 'destructive', 'external_effect', 'write', 'skill']

export function ApprovalStatusFilters({
  status,
  onChange,
}: {
  status: ApprovalStatusFilter
  onChange: (status: ApprovalStatusFilter) => void
}) {
  return (
    <div className="ops-data-toolbar mb-5 flex flex-wrap gap-2 p-3">
      {STATUS_OPTIONS.map((item) => (
        <button
          key={item.id}
          onClick={() => onChange(item.id)}
          className={`rounded-full border px-4 py-2 text-sm transition-colors ${
            status === item.id
              ? 'border-ops-accent bg-ops-accent text-ops-dark'
              : 'border-ops-surface1 bg-ops-surface0 text-ops-subtext hover:text-ops-text'
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

export function ApprovalQueueFilters({
  riskFilter,
  search,
  onRiskFilterChange,
  onSearchChange,
}: {
  riskFilter: ApprovalRiskFilter
  search: string
  onRiskFilterChange: (filter: ApprovalRiskFilter) => void
  onSearchChange: (value: string) => void
}) {
  return (
    <div className="ops-data-toolbar mb-5 grid gap-3 p-3 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex flex-wrap gap-2">
        {RISK_OPTIONS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onRiskFilterChange(item)}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              riskFilter === item
                ? 'border-ops-accent bg-ops-accent text-ops-dark'
                : 'border-ops-surface1 bg-ops-surface0 text-ops-subtext hover:text-ops-text'
            }`}
          >
            {approvalRiskFilterLabel(item)}
          </button>
        ))}
      </div>
      <input
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        className="ops-control h-9 w-full px-3 text-sm"
        placeholder="搜索审批 ID、工具、会话、资产"
      />
    </div>
  )
}

export function ApprovalMetric({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: ApprovalMetricTone
}) {
  const toneClass = {
    amber: 'text-ops-accent',
    green: 'text-ops-success',
    red: 'text-ops-alert',
    slate: 'text-ops-subtext',
  }[tone]
  return (
    <div className="ops-data-panel p-4">
      <div className="text-xs text-ops-subtext">{label}</div>
      <div className={`mt-2 font-mono text-2xl font-bold ${toneClass}`}>{value}</div>
    </div>
  )
}

export function ApprovalAuditSummaryPanel({
  auditSummary,
}: {
  auditSummary: ApprovalAuditSummary | null
}) {
  const layers = topEntries(auditSummary?.by_layer)
  const risks = topEntries(auditSummary?.by_risk)
  const recent = auditSummary?.recent?.slice(0, 4) || []
  return (
    <section className="ops-data-panel mb-5 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-ops-text">审批策略审计聚合</h2>
          <p className="mt-1 text-xs text-ops-subtext">按策略层、风险类型和最近审批记录汇总，便于确认哪些 gate 正在生效。</p>
        </div>
        <span className="ops-control px-3 py-1 text-xs text-ops-subtext">
          样本 {auditSummary?.total || 0}/{auditSummary?.limit || 500}
        </span>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <ApprovalSummaryBlock title="策略层" items={layers} labelFor={approvalLayerLabel} />
        <ApprovalSummaryBlock title="风险类型" items={risks} labelFor={approvalRiskSummaryLabel} />
        <div className="rounded-lg border border-ops-surface1 bg-ops-surface0/45 p-3">
          <div className="text-xs font-semibold text-ops-subtext">最近审批</div>
          <div className="mt-3 space-y-2">
            {recent.length > 0 ? recent.map((item) => (
              <div key={item.id || `${item.tool_name}-${item.requested_at}`} className="min-w-0 text-xs">
                <div className="truncate font-mono text-ops-text">{item.tool_name || '-'}</div>
                <div className="mt-0.5 truncate text-ops-subtext">
                  {approvalStatusLabel(item.status)} · {item.session_id || '-'} · {item.reason || '-'}
                </div>
              </div>
            )) : (
              <div className="text-xs text-ops-subtext">暂无审批记录</div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export function ApprovalList({
  approvals,
  loading,
  busyId,
  onApprove,
  onReject,
  onExecute,
  resolveSessionMode,
  resolveSessionModeSourceLabel,
  totalCount,
}: {
  approvals: ApprovalRequest[]
  totalCount: number
  loading: boolean
  busyId: string | null
  onApprove: (approval: ApprovalRequest) => void
  onReject: (approval: ApprovalRequest) => void
  onExecute: (approval: ApprovalRequest) => void
  resolveSessionMode: (approval: ApprovalRequest) => SessionModeResolution
  resolveSessionModeSourceLabel: (source: SessionModeSource) => string
}) {
  return (
    <section className="ops-data-panel overflow-hidden">
      <div className="ops-data-toolbar m-3 mb-0 px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-ops-text">工具调用审批记录</h2>
            <p className="mt-1 text-xs text-ops-subtext">参数和上下文已由后端脱敏，审批动作会写入审计状态。</p>
          </div>
          <span className="ops-control px-3 py-1 text-xs text-ops-accent">
            当前 {approvals.length}/{totalCount} 条
          </span>
        </div>
      </div>
      <div className="divide-y divide-ops-surface0">
        {loading && <div className="p-8 text-center text-sm text-ops-subtext">正在加载审批队列...</div>}
        {!loading && approvals.map((approval) => (
          <ApprovalRow
            key={approval.id}
            approval={approval}
            busy={busyId === approval.id}
            sessionModeResolution={resolveSessionMode(approval)}
            sessionModeSourceLabel={resolveSessionModeSourceLabel(resolveSessionMode(approval).source)}
            onApprove={() => onApprove(approval)}
            onReject={() => onReject(approval)}
            onExecute={() => onExecute(approval)}
          />
        ))}
      </div>
    </section>
  )
}

function ApprovalSummaryBlock({
  title,
  items,
  labelFor,
}: {
  title: string
  items: Array<[string, number]>
  labelFor: (value: string) => string
}) {
  return (
    <div className="rounded-lg border border-ops-surface1 bg-ops-surface0/45 p-3">
      <div className="text-xs font-semibold text-ops-subtext">{title}</div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map(([key, count]) => (
          <div key={key} className="flex items-center justify-between gap-3 text-xs">
            <span className="truncate text-ops-text">{labelFor(key)}</span>
            <span className="font-mono font-semibold text-ops-accent">{count}</span>
          </div>
        )) : (
          <div className="text-xs text-ops-subtext">暂无数据</div>
        )}
      </div>
    </div>
  )
}

function topEntries(values?: Record<string, number>) {
  return Object.entries(values || {})
    .filter(([, count]) => count > 0)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
}

function approvalLayerLabel(value: string) {
  return {
    runtime_policy: '运行策略',
    safety_policy: '安全策略',
    action_policy: '动作策略',
    unknown: '未识别',
  }[value] || value
}

function approvalRiskSummaryLabel(value: string) {
  return {
    destructive: '高危/破坏性',
    write_or_external: '写入/外发',
    skill_change: '技能变更',
    policy_only: '策略审批',
  }[value] || value
}

function approvalStatusLabel(value?: string) {
  return {
    pending: '待审批',
    approved: '已批准',
    rejected: '已拒绝',
    timeout: '已超时',
  }[value || ''] || '未知'
}

export function ApprovalEmptyState({
  status,
  onShowPending,
  onRefresh,
}: {
  status: ApprovalStatusFilter
  onShowPending: () => void
  onRefresh: () => void
}) {
  return (
    <section className="ops-data-panel p-6">
      <div className="text-sm font-semibold text-ops-text">当前筛选条件下暂无审批记录</div>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-ops-subtext">
        审批中心只展示命中高风险策略的工具调用。普通只读巡检不会进入审批队列，读写变更、实例管理、技能演进等动作会在这里等待人工处理。
      </p>
      <div className="mt-5 flex flex-wrap gap-2">
        {status !== 'pending' && (
          <button
            onClick={onShowPending}
            className="ops-muted-action px-3 py-1.5 text-sm"
          >
            查看待审批
          </button>
        )}
        <button
          onClick={onRefresh}
          className="ops-primary-action px-3 py-1.5 text-sm"
        >
          刷新队列
        </button>
      </div>
    </section>
  )
}
