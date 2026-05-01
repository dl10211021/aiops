import type { ExecTraceItem, SafetyPolicyAction } from '@/types'
import { parseJsonRecord } from './jsonRecords'

export function extractPrimaryAction(result: Record<string, unknown> | null): SafetyPolicyAction | null {
  const action = result?.primary_action
  if (!action || typeof action !== 'object' || Array.isArray(action)) return null
  const record = action as Record<string, unknown>
  const id = String(record.id || '')
  const label = String(record.label || '')
  if (!id || !label) return null
  return {
    id,
    label,
    description: typeof record.description === 'string' ? record.description : undefined,
    severity: typeof record.severity === 'string' ? record.severity : undefined,
  }
}

export function isPolicyBlockedResult(result: Record<string, unknown> | null): boolean {
  if (!result) return false
  const status = String(result.status || '').toUpperCase()
  const decision = String(result.policy_decision || '')
  return status === 'BLOCKED' || decision === 'readonly_block' || decision === 'deny'
}

const TOOL_ERROR_LABELS: Record<string, string> = {
  approval_rejected: '审批已拒绝',
  approval_timeout: '审批已超时',
  permission_denied: '权限不足',
  powershell_syntax: 'PowerShell 语法错误',
  powershell_execution_policy: 'PowerShell 执行策略限制',
  tool_arguments_invalid: '工具参数错误',
  winrm_authentication: 'WinRM 认证失败',
  winrm_connection: 'WinRM 连接异常',
  winrm_command_failed: 'WinRM 命令失败',
  winrm_error: 'WinRM 执行失败',
}

export function isToolErrorResult(result: Record<string, unknown> | null): boolean {
  if (!result) return false
  const status = String(result.status || '').toUpperCase()
  return Boolean(
    status === 'ERROR' ||
    status === 'FAILED' ||
    result.success === false ||
    result.has_error === true ||
    result.error ||
    result.error_type,
  )
}

export function toolErrorTitle(result: Record<string, unknown>): string {
  const errorType = typeof result.error_type === 'string' ? result.error_type : ''
  if (errorType && TOOL_ERROR_LABELS[errorType]) return TOOL_ERROR_LABELS[errorType]
  if (errorType) return errorType.split('_').join(' ')
  return '工具执行失败'
}

export function stringValue(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (value === undefined || value === null) return ''
  return String(value).trim()
}

export function policyDecisionLabel(decision: unknown): string {
  if (decision === 'readonly_block') return '只读保护'
  if (decision === 'deny') return '禁止执行'
  if (decision === 'approval') return '需要审批'
  if (decision === 'allow') return '允许执行'
  return '策略拦截'
}

export function resultReason(result: Record<string, unknown> | null): string {
  const reason = result?.reason
  if (typeof reason === 'string' && reason.trim()) return reason.trim()
  const error = result?.error
  if (typeof error === 'string' && error.trim()) return error.trim()
  return '该工具调用被安全策略阻止。'
}

export function traceTargetLabel(trace: ExecTraceItem): string {
  const parsedArgs = parseJsonRecord(trace.args || '')
  if (parsedArgs) {
    const command = parsedArgs.command
    const sql = parsedArgs.sql
    const method = parsedArgs.method
    const path = parsedArgs.path || parsedArgs.url || parsedArgs.endpoint
    const action = parsedArgs.action || parsedArgs.operation
    if (typeof command === 'string' && command.trim()) return command.trim()
    if (typeof sql === 'string' && sql.trim()) return sql.trim()
    if (typeof method === 'string' && typeof path === 'string') return `${method.toUpperCase()} ${path}`
    if (typeof action === 'string' && action.trim()) return action.trim()
  }
  if (trace.args?.trim()) return trace.args.trim().slice(0, 240)
  return trace.tool || ''
}

export function actionRuleDomain(actionId: string): string {
  const domain = actionId.split('.', 1)[0]
  if (['linux', 'windows', 'sql', 'redis', 'http', 'network', 'local', 'skill_change'].includes(domain)) {
    return domain
  }
  return 'http'
}

export function completeLastTrace(items: ExecTraceItem[], data: Record<string, unknown>): ExecTraceItem[] {
  const result = String(data.result || '')
  const dataStatus = data.result_status === 'error' || data.result_status === 'done'
    ? data.result_status
    : null
  const status = dataStatus || toolResultStatus(result)
  const resultMeta = data.result_meta && typeof data.result_meta === 'object' && !Array.isArray(data.result_meta)
    ? data.result_meta as Record<string, unknown>
    : undefined
  const next = [...items]
  for (let i = next.length - 1; i >= 0; i--) {
    if (next[i].type === 'tool_start' && next[i].status === 'running') {
      next[i] = {
        ...next[i],
        type: 'tool_end',
        result,
        resultMeta,
        status,
        completedAt: Date.now(),
      }
      return next
    }
  }
  next.push({
    type: 'tool_end',
    tool: String(data.tool || 'unknown'),
    result,
    resultMeta,
    status,
    completedAt: Date.now(),
  })
  return next
}

function toolResultStatus(result: string): 'done' | 'error' {
  const parsed = parseJsonRecord(result)
  if (parsed) {
    const status = String(parsed.status || '').toUpperCase()
    if (status === 'ERROR' || status === 'FAILED' || status === 'BLOCKED') return 'error'
    if (parsed.success === false || parsed.has_error === true || parsed.error || parsed.reason) return 'error'
  }
  return result.includes('"BLOCKED"') || result.includes('"ERROR"') || result.includes('错误：') ? 'error' : 'done'
}
