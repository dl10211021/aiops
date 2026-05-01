import PageHeader from '@/components/layout/PageHeader'
import { ApprovalDecisionModal } from './ApprovalDecisionModal'
import {
  ApprovalEmptyState,
  ApprovalList,
  ApprovalMetric,
  ApprovalStatusFilters,
} from './ApprovalCenterParts'
import { useApprovalCenterData } from './useApprovalCenterData'

export default function ApprovalCenter() {
  const {
    approvals,
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
    setDecisionNote,
    setDecisionTarget,
    setOperator,
    setStatus,
    status,
    submitDecision,
  } = useApprovalCenterData()

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-5">
      <div className="w-full max-w-none">
        <PageHeader
          eyebrow="风险审批队列"
          title="审批中心"
          description="所有命中后端审批策略的高危工具调用都会进入这里，可查询、批准、拒绝和审计。"
          actions={(
            <button
              onClick={() => void load()}
              className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-4 py-2 text-sm text-ops-text transition-colors hover:border-ops-accent/60"
            >
              刷新
            </button>
          )}
        />

        <ApprovalStatusFilters status={status} onChange={setStatus} />

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

        {loading || approvals.length > 0 ? (
          <ApprovalList
            approvals={approvals}
            loading={loading}
            busyId={busyId}
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
