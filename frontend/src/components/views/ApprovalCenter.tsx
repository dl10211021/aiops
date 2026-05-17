import { useCallback } from 'react'
import PageHeader from '@/components/layout/PageHeader'
import {
  resolveSessionModeWithSource,
  type SessionModeResolution,
  type SessionModeSource,
} from '@/features/sessions/toolPolicyPresentation'
import type { ApprovalRequest } from '@/types'
import { useStore } from '@/store'
import { ApprovalDecisionModal } from './ApprovalDecisionModal'
import {
  ApprovalAuditSummaryPanel,
  ApprovalEmptyState,
  ApprovalList,
  ApprovalMetric,
  ApprovalQueueFilters,
  ApprovalStatusFilters,
} from './ApprovalCenterParts'
import { useApprovalCenterData } from './useApprovalCenterData'

export default function ApprovalCenter() {
  const sessions = useStore((state) => state.sessions)
  const {
    approvals,
    approvalSearch,
    approvalTotal,
    auditSummary,
    busyId,
    counts,
    decisionNote,
    decisionTarget,
    error,
    handleExecute,
    load,
    loading,
    openDecision,
    operator,
    riskFilter,
    setApprovalSearch,
    setDecisionNote,
    setDecisionTarget,
    setOperator,
    setRiskFilter,
    setStatus,
    status,
    submitDecision,
  } = useApprovalCenterData()

  const resolveSessionModeWithSourceForList = useCallback((approval: ApprovalRequest): SessionModeResolution => {
    const context = approval.context as Record<string, unknown>
    const contextMode = [context.session_mode, context.mode, context.allow_modifications, context.execution_mode]
      .find((value) => value !== undefined && value !== null)
    const sourceSession = approval.session_id ? sessions[approval.session_id] : null
    return resolveSessionModeWithSource(contextMode, sourceSession ? Boolean(sourceSession.isReadWriteMode) : undefined)
  }, [sessions])

  const sourceLabelByMode = useCallback((source: SessionModeSource) => {
    return {
      context: '来源：会话上下文',
      session_snapshot: '来源：会话快照',
      inferred_unknown: '来源：未识别',
    }[source]
  }, [])

  return (
    <div className="ops-page">
      <div className="ops-page-inner">
        <PageHeader
          eyebrow="风险审批队列"
          title="审批中心"
          description="所有命中后端审批策略的高危工具调用都会进入这里，可查询、批准、拒绝和审计。"
          actions={(
            <button
              onClick={() => void load()}
              className="ops-control rounded-lg px-4 py-2 text-sm font-semibold"
            >
              刷新
            </button>
          )}
        />

        <ApprovalStatusFilters status={status} onChange={setStatus} />
        <ApprovalQueueFilters
          riskFilter={riskFilter}
          search={approvalSearch}
          onRiskFilterChange={setRiskFilter}
          onSearchChange={setApprovalSearch}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-ops-alert/35 bg-ops-alert/10 px-4 py-3 text-sm text-ops-alert">
            {error}
          </div>
        )}

        <div className="mb-5 grid gap-3 md:grid-cols-4">
          <ApprovalMetric label="待审批" value={counts.pending} tone="amber" />
          <ApprovalMetric label="已批准" value={counts.approved} tone="green" />
          <ApprovalMetric label="已拒绝" value={counts.rejected} tone="red" />
          <ApprovalMetric label="已超时" value={counts.timeout} tone="slate" />
        </div>

        <ApprovalAuditSummaryPanel auditSummary={auditSummary} />

        {loading || approvals.length > 0 ? (
          <ApprovalList
            approvals={approvals}
            totalCount={approvalTotal}
            loading={loading}
            busyId={busyId}
            resolveSessionMode={resolveSessionModeWithSourceForList}
            resolveSessionModeSourceLabel={sourceLabelByMode}
            onApprove={(approval) => openDecision(approval, true)}
            onReject={(approval) => openDecision(approval, false)}
            onExecute={(approval) => void handleExecute(approval)}
          />
        ) : (
          <ApprovalEmptyState
            status={status}
            onShowPending={() => setStatus('pending')}
            onRefresh={() => void load()}
          />
        )}

        {decisionTarget && (
          <ApprovalDecisionModal
            approval={decisionTarget.approval}
            approved={decisionTarget.approved}
            sessionModeResolution={resolveSessionModeWithSourceForList(decisionTarget.approval)}
            sessionModeSourceLabel={
              sourceLabelByMode(resolveSessionModeWithSourceForList(decisionTarget.approval).source)
            }
            operator={operator}
            note={decisionNote}
            busy={busyId === decisionTarget.approval.id}
            onOperatorChange={setOperator}
            onNoteChange={setDecisionNote}
            onClose={() => setDecisionTarget(null)}
            onSubmit={() => void submitDecision()}
          />
        )}
      </div>
    </div>
  )
}
