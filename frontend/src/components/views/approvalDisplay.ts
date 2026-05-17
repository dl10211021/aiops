import type { ApprovalRequest } from '@/types'

export type ApprovalStatusFilter = ApprovalRequest['status'] | 'all'
export type ApprovalRiskFilter = 'all' | 'destructive' | 'external_effect' | 'write' | 'skill'
export type ApprovalMetricTone = 'amber' | 'green' | 'red' | 'slate'

export function approvalStatusLabel(status: ApprovalRequest['status']) {
  return {
    pending: '待审批',
    approved: '已批准',
    rejected: '已拒绝',
    timeout: '已超时',
  }[status]
}

export function approvalStatusToneClass(status: ApprovalRequest['status']) {
  return {
    pending: 'border-ops-accent/40 bg-ops-accent/10 text-ops-accent',
    approved: 'border-ops-success/40 bg-ops-success/10 text-ops-success',
    rejected: 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert',
    timeout: 'border-ops-surface1 bg-ops-surface0 text-ops-subtext',
  }[status]
}

export function approvalPolicyActionTone(severity?: string) {
  if (severity === 'critical') return 'border-ops-alert/45 bg-ops-alert/10 text-ops-alert'
  if (severity === 'high') return 'border-yellow-300/35 bg-yellow-300/10 text-yellow-100'
  if (severity === 'medium') return 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
  return 'border-ops-success/30 bg-ops-success/10 text-ops-success'
}

export function approvalRiskFilterLabel(filter: ApprovalRiskFilter) {
  return {
    all: '全部风险',
    destructive: '破坏性',
    external_effect: '外发/通知',
    write: '写入变更',
    skill: '技能变更',
  }[filter]
}
