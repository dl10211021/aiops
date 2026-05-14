import type { ExecTraceItem } from '@/types'
import { parseJsonRecord } from './jsonRecords'

export function recordValue(record: Record<string, unknown> | null, key: string) {
  const value = record?.[key]
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
    ? String(value)
    : ''
}

export function objectRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

export function toolPolicyFromResult(result: Record<string, unknown> | null) {
  return objectRecord(result?.tool_policy)
}

export function toolPolicyFromTrace(trace: ExecTraceItem): Record<string, unknown> | null {
  const metaPolicy = objectRecord(trace.resultMeta?.tool_policy)
  if (metaPolicy) return metaPolicy
  const evidenceMeta = objectRecord(trace.evidence?.result_meta)
  const evidencePolicy = objectRecord(evidenceMeta?.tool_policy)
  if (evidencePolicy) return evidencePolicy
  const parsed = parseJsonRecord(trace.result || '')
  return toolPolicyFromResult(parsed)
}

export function operationLabel(mode: string) {
  return {
    read: '只读',
    write: '写入',
    read_write: '读写受控',
    destructive: '破坏性',
    external_effect: '外发',
    interactive: '人工交互',
  }[mode] || mode || '未知'
}

export function approvalLabel(policy: string) {
  return {
    none: '无需审批',
    guarded_write: '写入受控',
    always_required: '强制审批',
  }[policy] || policy || '未知'
}

export function evidenceLabel(family: string) {
  return {
    database: '数据库证据',
    host_cli: '主机命令证据',
    http_api: 'HTTP/API 证据',
    observability: '可观测证据',
    network: '网络证据',
    storage: '存储证据',
    virtualization: '虚拟化证据',
    container: '容器证据',
    knowledge: '知识证据',
    notification: '通知审计',
    memory: '记忆审计',
    human_interaction: '人工输入',
    local_runtime: '本地运行时',
    platform: '平台证据',
  }[family] || family || '未知'
}

export function toolPolicySearchText(policy: Record<string, unknown> | null) {
  if (!policy) return ''
  const operation = recordValue(policy, 'operation_mode')
  const approval = recordValue(policy, 'approval_policy')
  const evidence = recordValue(policy, 'evidence_family')
  return [
    recordValue(policy, 'name'),
    operation,
    operationLabel(operation),
    approval,
    approvalLabel(approval),
    evidence,
    evidenceLabel(evidence),
    recordValue(policy, 'safety_category'),
    recordValue(policy, 'toolset'),
  ].filter(Boolean).join(' ')
}
