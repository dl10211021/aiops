import type { ExecTraceItem } from '@/types'
import { parseJsonRecord } from './jsonRecords'

export type SessionMode = 'readonly' | 'readwrite'
export type SessionModeSource = 'context' | 'session_snapshot' | 'inferred_unknown'

export interface SessionModeResolution {
  mode?: SessionMode
  source: SessionModeSource
}

export function parseSessionMode(value: unknown): SessionMode | undefined {
  if (typeof value === 'boolean') return value ? 'readwrite' : 'readonly'
  if (typeof value === 'number') {
    if (value === 1) return 'readwrite'
    if (value === 0) return 'readonly'
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (['1', 'true', 'yes', 'on', 'rw', 'readwrite', 'r+w', 'write'].includes(normalized)) {
      return 'readwrite'
    }
    if (['0', 'false', 'no', 'off', 'ro', 'readonly'].includes(normalized)) {
      return 'readonly'
    }
    if (normalized.startsWith('read_only') || normalized.startsWith('read-only')) {
      return 'readonly'
    }
    if (normalized.includes('read') && normalized.includes('write')) {
      return 'readwrite'
    }
  }
  return undefined
}

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

function numberValue(record: Record<string, unknown> | null, key: string) {
  const raw = record?.[key]
  const value = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN
  return Number.isFinite(value) ? value : null
}

function secondsText(value: number) {
  if (value <= 0) return ''
  return value >= 10 ? `${Math.round(value)}s` : `${Number(value.toFixed(2))}s`
}

export function toolPolicyFromResult(result: Record<string, unknown> | null) {
  return meaningfulToolPolicy(objectRecord(result?.tool_policy))
}

export function toolPolicyFromTrace(trace: ExecTraceItem): Record<string, unknown> | null {
  const metaPolicy = objectRecord(trace.resultMeta?.tool_policy)
  if (meaningfulToolPolicy(metaPolicy)) return metaPolicy
  const evidenceMeta = objectRecord(trace.evidence?.result_meta)
  const evidencePolicy = objectRecord(evidenceMeta?.tool_policy)
  if (meaningfulToolPolicy(evidencePolicy)) return evidencePolicy
  const parsed = parseJsonRecord(trace.result || '')
  return toolPolicyFromResult(parsed)
}

export function meaningfulToolPolicy(policy: Record<string, unknown> | null) {
  if (!policy) return null
  return ['operation_mode', 'approval_policy', 'evidence_family'].some((key) => recordValue(policy, key))
    ? policy
    : null
}

export function operationLabel(mode: string) {
  return {
    read: '只读',
    write: '写入能力',
    read_write: '可读写',
    destructive: '破坏性',
    external_effect: '外发',
    interactive: '人工交互',
  }[mode] || mode || '未知'
}

export function approvalLabel(policy: string) {
  return {
    none: '无需审批',
    guarded_write: '写入需审批',
    always_required: '强制审批',
  }[policy] || policy || '未知'
}

export function operationToneClass(mode: string) {
  return {
    read: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-100',
    write: 'border-amber-400/35 bg-amber-400/10 text-amber-100',
    read_write: 'border-cyan-400/35 bg-cyan-400/10 text-cyan-100',
    destructive: 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert',
    external_effect: 'border-fuchsia-400/35 bg-fuchsia-400/10 text-fuchsia-100',
    interactive: 'border-sky-400/35 bg-sky-400/10 text-sky-100',
  }[mode] || 'border-ops-surface1/65 bg-ops-dark/35 text-ops-subtext'
}

export function approvalToneClass(policy: string) {
  return {
    none: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-100',
    guarded_write: 'border-amber-400/40 bg-amber-400/10 text-amber-100',
    always_required: 'border-ops-alert/45 bg-ops-alert/10 text-ops-alert',
  }[policy] || 'border-ops-surface1/65 bg-ops-dark/35 text-ops-subtext'
}

export function sessionModePolicyToneClass(
  operationMode: string,
  approvalPolicy: string,
  sessionMode?: SessionMode,
  sessionModeSource: SessionModeSource = 'inferred_unknown',
) {
  const writeCapable = ['write', 'read_write', 'destructive', 'external_effect'].includes(operationMode)
  const requiresWriteGate = approvalPolicy === 'guarded_write' || writeCapable
  if (!sessionMode && requiresWriteGate) {
    return 'border-amber-300/45 bg-amber-300/10 text-amber-100'
  }
  if (sessionMode === 'readonly' && requiresWriteGate) {
    return 'border-ops-alert/45 bg-ops-alert/10 text-ops-alert'
  }
  if (sessionMode === 'readwrite' && requiresWriteGate) {
    return 'border-emerald-300/45 bg-emerald-300/10 text-emerald-100'
  }
  return approvalToneClass(approvalPolicy)
}

export function sessionModePolicyLabel(operationMode: string, approvalPolicy: string, sessionMode?: SessionMode) {
  const writeCapable = ['write', 'read_write', 'destructive', 'external_effect'].includes(operationMode)
  const requiresWriteGate = approvalPolicy === 'guarded_write' || writeCapable
  if (sessionMode === 'readonly' && requiresWriteGate) return '只读限制'
  if (sessionMode === 'readwrite' && requiresWriteGate) return '读写通过'
  if (requiresWriteGate) return '待识别会话'
  return approvalLabel(approvalPolicy)
}

export function resolveSessionModeWithSource(
  contextMode: unknown,
  sessionMode: SessionMode | boolean | undefined | null,
): SessionModeResolution {
  const mode = parseSessionMode(contextMode)
  if (mode) return { mode, source: 'context' }
  const normalizedMode = parseSessionMode(sessionMode)
  if (normalizedMode) return { mode: normalizedMode, source: 'session_snapshot' }
  return { mode: undefined, source: 'inferred_unknown' }
}

export function sessionModeLabel(mode?: SessionMode) {
  if (mode === 'readonly') return '会话模式：只读'
  if (mode === 'readwrite') return '会话模式：读写'
  return '会话模式：未识别'
}

export function sessionModeSourceLabel(source: SessionModeSource) {
  return {
    context: '来源：会话上下文',
    session_snapshot: '来源：会话快照',
    inferred_unknown: '来源：未识别',
  }[source]
}

export function evidenceToneClass(family: string) {
  return {
    database: 'border-sky-400/35 bg-sky-400/10 text-sky-100',
    host_cli: 'border-lime-400/35 bg-lime-400/10 text-lime-100',
    http_api: 'border-indigo-300/35 bg-indigo-400/10 text-indigo-100',
    observability: 'border-teal-300/35 bg-teal-400/10 text-teal-100',
    network: 'border-cyan-300/35 bg-cyan-400/10 text-cyan-100',
    storage: 'border-violet-300/35 bg-violet-400/10 text-violet-100',
    virtualization: 'border-purple-300/35 bg-purple-400/10 text-purple-100',
    container: 'border-blue-300/35 bg-blue-400/10 text-blue-100',
    knowledge: 'border-stone-300/35 bg-stone-400/10 text-stone-100',
    notification: 'border-fuchsia-300/35 bg-fuchsia-400/10 text-fuchsia-100',
    memory: 'border-orange-300/35 bg-orange-400/10 text-orange-100',
    human_interaction: 'border-sky-300/35 bg-sky-400/10 text-sky-100',
    local_runtime: 'border-zinc-300/35 bg-zinc-400/10 text-zinc-100',
    platform: 'border-slate-300/35 bg-slate-400/10 text-slate-100',
  }[family] || 'border-ops-surface1/65 bg-ops-dark/35 text-ops-subtext'
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

export function timeoutPolicyLabel(policy: Record<string, unknown> | null) {
  const timeoutPolicy = objectRecord(policy?.timeout_policy)
  const defaultSeconds = numberValue(timeoutPolicy, 'default_seconds')
  const maxSeconds = numberValue(timeoutPolicy, 'max_seconds')
  if (!defaultSeconds || defaultSeconds <= 0) return ''
  const defaultText = secondsText(defaultSeconds)
  const maxText = maxSeconds && maxSeconds > 0 ? secondsText(maxSeconds) : ''
  return maxText ? `超时 ${defaultText}/${maxText}` : `超时 ${defaultText}`
}

export function retryPolicyLabel(policy: Record<string, unknown> | null) {
  const retryPolicy = objectRecord(policy?.retry_policy)
  const maxAttempts = numberValue(retryPolicy, 'max_attempts')
  if (!maxAttempts || maxAttempts <= 1) return ''
  const delaySeconds = numberValue(retryPolicy, 'delay_seconds')
  const delayText = delaySeconds && delaySeconds > 0 ? ` · 间隔 ${secondsText(delaySeconds)}` : ''
  return `重试 ${Math.round(maxAttempts)} 次${delayText}`
}

export function runtimePolicyLabels(policy: Record<string, unknown> | null) {
  return [
    timeoutPolicyLabel(policy),
    retryPolicyLabel(policy),
    recordValue(policy, 'concurrency_safe') === 'true' ? '可并发' : '',
  ].filter(Boolean)
}

function runtimeExecutionFromTrace(trace: ExecTraceItem) {
  const resultRuntimeExecution = objectRecord(trace.resultMeta?.runtime_execution)
  if (resultRuntimeExecution) return { execution: resultRuntimeExecution, kind: 'runtime_execution' }
  const resultRuntimePolicy = objectRecord(trace.resultMeta?.runtime_policy)
  if (resultRuntimePolicy) return { execution: resultRuntimePolicy, kind: 'runtime_policy' }
  const evidenceMeta = objectRecord(trace.evidence?.result_meta)
  const evidenceRuntimeExecution = objectRecord(evidenceMeta?.runtime_execution)
  if (evidenceRuntimeExecution) return { execution: evidenceRuntimeExecution, kind: 'runtime_execution' }
  const evidenceRuntimePolicy = objectRecord(evidenceMeta?.runtime_policy)
  if (evidenceRuntimePolicy) return { execution: evidenceRuntimePolicy, kind: 'runtime_policy' }
  return { execution: null, kind: '' }
}

export function runtimeExecutionLabels(trace: ExecTraceItem) {
  const { execution, kind } = runtimeExecutionFromTrace(trace)
  const attempts = numberValue(execution, 'attempts')
  const maxAttempts = numberValue(execution, 'max_attempts')
  const retried = recordValue(execution, 'retried') === 'true'
  const finalStatus = recordValue(execution, 'final_status')
  const errorType = recordValue(execution, 'error_type')
  const timeoutSeconds = numberValue(execution, 'timeout_seconds')
  const labels: string[] = []
  if (finalStatus === 'error') {
    labels.push(errorType === 'tool_timeout' && timeoutSeconds ? `实际超时 ${secondsText(timeoutSeconds)}` : '实际执行失败')
  }
  if (!attempts || attempts <= 1) return labels
  if (kind === 'runtime_execution' && !retried) return labels
  const totalText = maxAttempts && maxAttempts > 0 ? `/${Math.round(maxAttempts)}` : ''
  labels.push(`实际重试 ${Math.round(attempts)}${totalText} 次`)
  return labels
}

const sqlReadTypes = new Set(['select', 'show', 'describe', 'desc', 'explain', 'with'])
const sqlWriteTypes = new Set([
  'alter',
  'analyze',
  'call',
  'create',
  'delete',
  'drop',
  'grant',
  'insert',
  'merge',
  'replace',
  'revoke',
  'truncate',
  'update',
])

function sqlStatementTypeFromTrace(trace: ExecTraceItem) {
  const resultMeta = objectRecord(trace.resultMeta)
  const evidenceMeta = objectRecord(trace.evidence?.result_meta)
  const parsed = parseJsonRecord(trace.result || '')
  const fromMeta = recordValue(resultMeta, 'statement_type') || recordValue(evidenceMeta, 'statement_type') || recordValue(parsed, 'statement_type')
  if (fromMeta) return fromMeta.trim().toLowerCase()
  const text = [trace.args, trace.evidence?.input_summary, trace.evidence?.redacted_input]
    .filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    .join('\n')
  const firstToken = text
    .replace(/^\s*(--.*\n|\/\*[\s\S]*?\*\/\s*)+/g, '')
    .trim()
    .match(/^[a-zA-Z_]+/)
  return firstToken?.[0]?.toLowerCase() || ''
}

export function sqlActionFromTrace(trace: ExecTraceItem) {
  if (trace.tool !== 'db_execute_query') return null
  const statementType = sqlStatementTypeFromTrace(trace)
  if (!statementType) return null
  if (sqlReadTypes.has(statementType)) {
    return {
      label: `SQL：只读查询 (${statementType.toUpperCase()})`,
      className: 'border-emerald-400/35 bg-emerald-400/10 text-emerald-100',
      searchText: `sql readonly read ${statementType} 只读查询`,
    }
  }
  if (sqlWriteTypes.has(statementType)) {
    return {
      label: `SQL：写入/DDL (${statementType.toUpperCase()})`,
      className: 'border-ops-alert/40 bg-ops-alert/10 text-ops-alert',
      searchText: `sql write ddl ${statementType} 写入 变更`,
    }
  }
  return {
    label: `SQL：待识别 (${statementType.toUpperCase()})`,
    className: 'border-amber-300/45 bg-amber-300/10 text-amber-100',
    searchText: `sql unknown ${statementType} 待识别`,
  }
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
    timeoutPolicyLabel(policy),
    retryPolicyLabel(policy),
  ].filter(Boolean).join(' ')
}
