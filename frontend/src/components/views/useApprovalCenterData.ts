import { useCallback, useEffect, useMemo, useState } from 'react'
import { decideApproval, executeApproval, getApprovals, getApprovalSummary } from '@/api/approvals'
import { useStore } from '@/store'
import type { ApprovalAuditSummary, ApprovalRequest } from '@/types'
import type { ApprovalRiskFilter, ApprovalStatusFilter } from './approvalDisplay'

export function useApprovalCenterData() {
  const addToast = useStore((s) => s.addToast)
  const [status, setStatus] = useState<ApprovalStatusFilter>('pending')
  const [riskFilter, setRiskFilter] = useState<ApprovalRiskFilter>('all')
  const [approvalSearch, setApprovalSearch] = useState('')
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [allApprovals, setAllApprovals] = useState<ApprovalRequest[]>([])
  const [auditSummary, setAuditSummary] = useState<ApprovalAuditSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [decisionTarget, setDecisionTarget] = useState<{ approval: ApprovalRequest; approved: boolean } | null>(null)
  const [operator, setOperator] = useState(() => localStorage.getItem('OPSCORE_OPERATOR') || 'user')
  const [decisionNote, setDecisionNote] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [filteredRes, allRes, summaryRes] = await Promise.all([
        getApprovals(status, 200),
        getApprovals('all', 500),
        getApprovalSummary(500),
      ])
      setApprovals(filteredRes.data.approvals || [])
      setAllApprovals(allRes.data.approvals || [])
      setAuditSummary(summaryRes.data.summary || null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载审批队列失败')
    } finally {
      setLoading(false)
    }
  }, [status])

  useEffect(() => {
    void load()
  }, [load])

  const counts = useMemo(() => {
    const next = { pending: 0, approved: 0, rejected: 0, timeout: 0 }
    for (const item of allApprovals) {
      if (item.status in next) next[item.status as keyof typeof next] += 1
    }
    return next
  }, [allApprovals])

  const visibleApprovals = useMemo(() => {
    const query = approvalSearch.trim().toLowerCase()
    return approvals.filter((item) => (
      approvalMatchesRiskFilter(item, riskFilter)
      && (!query || approvalSearchText(item).includes(query))
    ))
  }, [approvalSearch, approvals, riskFilter])

  const openDecision = (approval: ApprovalRequest, approved: boolean) => {
    setDecisionTarget({ approval, approved })
    setDecisionNote('')
  }

  const submitDecision = async () => {
    if (!decisionTarget) return
    const { approval, approved } = decisionTarget
    const action = approved ? '批准' : '拒绝'
    if (!operator.trim()) {
      addToast('操作人不能为空', 'error')
      return
    }
    if (approved && !decisionNote.trim()) {
      addToast('批准敏感操作必须填写原因', 'error')
      return
    }
    localStorage.setItem('OPSCORE_OPERATOR', operator.trim())
    setBusyId(approval.id)
    try {
      await decideApproval(approval.id, approved, operator.trim(), decisionNote.trim())
      addToast(`审批已${action}`, 'success')
      setDecisionTarget(null)
      setDecisionNote('')
      await load()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '审批处理失败', 'error')
    } finally {
      setBusyId(null)
    }
  }

  const handleExecute = async (approval: ApprovalRequest) => {
    setBusyId(approval.id)
    try {
      await executeApproval(approval.id)
      addToast('审批动作已执行', 'success')
      await load()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '审批执行失败', 'error')
    } finally {
      setBusyId(null)
    }
  }

  return {
    approvals: visibleApprovals,
    approvalSearch,
    approvalTotal: approvals.length,
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
  }
}

function approvalMatchesRiskFilter(approval: ApprovalRequest, filter: ApprovalRiskFilter) {
  if (filter === 'all') return true
  const policy = approval.metadata?.tool_policy
  const operationMode = String(policy?.operation_mode || '')
  if (filter === 'destructive') return Boolean(policy?.destructive) || operationMode === 'destructive'
  if (filter === 'external_effect') return operationMode === 'external_effect'
  if (filter === 'write') {
    return ['write', 'read_write'].includes(operationMode)
      || policy?.approval_policy === 'guarded_write'
  }
  if (filter === 'skill') {
    return Boolean(approval.metadata?.skill_change || approval.metadata?.skill_rollback)
      || approval.tool_name.includes('skill')
  }
  return true
}

function approvalSearchText(approval: ApprovalRequest) {
  const context = approval.context || {}
  const requestedAction = approval.metadata?.requested_action
  return [
    approval.id,
    approval.tool_call_id,
    approval.session_id,
    approval.tool_name,
    approval.reason,
    context.host,
    context.remark,
    context.asset_type,
    context.protocol,
    requestedAction?.label,
    requestedAction?.kind,
  ].filter(Boolean).join(' ').toLowerCase()
}
