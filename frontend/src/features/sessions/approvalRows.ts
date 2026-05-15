import type { ToolApproval } from '@/types'
import { parseJsonRecord } from './jsonRecords'

export interface ApprovalArgumentRow {
  label: string
  value: string
  wide?: boolean
}

export function approvalArgumentRows(approval: ToolApproval): ApprovalArgumentRow[] {
  const parsed = parseJsonRecord(approval.args)
  if (!parsed) return []
  const rows: ApprovalArgumentRow[] = []
  const sql = parsed.sql
  const command = parsed.command
  const method = parsed.method
  const path = parsed.path
  const url = parsed.url
  const endpoint = parsed.endpoint
  const body = parsed.body
  const params = parsed.params
  const headers = parsed.headers
  if (typeof sql === 'string' && sql.trim()) rows.push({ label: 'SQL', value: sql.trim(), wide: true })
  if (typeof command === 'string' && command.trim()) rows.push({ label: '命令', value: command.trim(), wide: true })
  if (typeof method === 'string' && method.trim()) rows.push({ label: 'HTTP 方法', value: method.trim() })
  if (typeof path === 'string' && path.trim()) rows.push({ label: 'API 路径', value: path.trim(), wide: true })
  if (typeof url === 'string' && url.trim()) rows.push({ label: 'URL', value: url.trim(), wide: true })
  if (typeof endpoint === 'string' && endpoint.trim()) rows.push({ label: '接口', value: endpoint.trim(), wide: true })
  if (body !== undefined && body !== null && String(body).trim()) rows.push({ label: '请求体', value: formatApprovalArgValue(body), wide: true })
  if (params !== undefined && params !== null && String(params).trim()) rows.push({ label: '参数', value: formatApprovalArgValue(params), wide: true })
  if (headers !== undefined && headers !== null && String(headers).trim()) rows.push({ label: '请求头', value: formatApprovalArgValue(headers), wide: true })
  for (const key of ['host', 'port', 'database', 'db_type', 'operation', 'asset_id', 'asset_name', 'target', 'channel', 'title']) {
    const value = parsed[key]
    if (value !== undefined && value !== null && String(value).trim()) {
      rows.push({ label: approvalArgLabel(key), value: formatApprovalArgValue(value) })
    }
  }
  return rows.slice(0, 12)
}

function formatApprovalArgValue(value: unknown) {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function approvalArgLabel(key: string) {
  return {
    host: '目标',
    port: '端口',
    database: '数据库',
    db_type: '数据库类型',
    operation: '操作',
    asset_id: '资产 ID',
    asset_name: '资产',
    target: '目标',
    channel: '通知渠道',
    title: '标题',
  }[key] || key
}
