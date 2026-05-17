import type { ApprovalRequest } from '@/types'
import { request } from './http'

export async function getApprovals(status?: string, limit = 100) {
  const params = new URLSearchParams()
  if (status && status !== 'all') params.set('status', status)
  params.set('limit', String(limit))
  return request<{ approvals: ApprovalRequest[] }>(`/approvals?${params.toString()}`)
}

export async function getApproval(approvalId: string) {
  return request<{ approval: ApprovalRequest }>(`/approvals/${approvalId}`)
}

export async function decideApproval(
  approvalId: string,
  approved: boolean,
  operator = 'ops-admin',
  note = ''
) {
  return request<{ approval: ApprovalRequest }>(`/approvals/${approvalId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ approved, operator, note }),
  })
}

export async function executeApproval(approvalId: string) {
  return request<{ approval: ApprovalRequest; result: Record<string, unknown> }>(
    `/approvals/${approvalId}/execute`,
    { method: 'POST' }
  )
}
