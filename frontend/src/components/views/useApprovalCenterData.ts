import { useCallback, useEffect, useMemo, useState } from 'react'
import { decideApproval, executeApproval, getApprovals } from '@/api/approvals'
import { useStore } from '@/store'
import type { ApprovalRequest } from '@/types'
import type { ApprovalStatusFilter } from './approvalDisplay'

export function useApprovalCenterData() {
  const addToast = useStore((s) => s.addToast)
  const [status, setStatus] = useState<ApprovalStatusFilter>('pending')
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [allApprovals, setAllApprovals] = useState<ApprovalRequest[]>([])
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
      const [filteredRes, allRes] = await Promise.all([
        getApprovals(status, 200),
        getApprovals('all', 500),
      ])
      setApprovals(filteredRes.data.approvals || [])
      setAllApprovals(allRes.data.approvals || [])
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
  }
}
