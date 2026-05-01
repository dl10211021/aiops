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
  if (typeof sql === 'string' && sql.trim()) rows.push({ label: 'SQL', value: sql.trim(), wide: true })
  if (typeof command === 'string' && command.trim()) rows.push({ label: '命令', value: command.trim(), wide: true })
  if (typeof method === 'string' && method.trim()) rows.push({ label: 'HTTP 方法', value: method.trim() })
  if (typeof path === 'string' && path.trim()) rows.push({ label: 'API 路径', value: path.trim(), wide: true })
  for (const key of ['host', 'port', 'database', 'db_type', 'operation', 'asset_id']) {
    const value = parsed[key]
    if (value !== undefined && value !== null && String(value).trim()) {
      rows.push({ label: approvalArgLabel(key), value: String(value) })
    }
  }
  return rows.slice(0, 8)
}

function approvalArgLabel(key: string) {
  return {
    host: '目标',
    port: '端口',
    database: '数据库',
    db_type: '数据库类型',
    operation: '操作',
    asset_id: '资产 ID',
  }[key] || key
}
