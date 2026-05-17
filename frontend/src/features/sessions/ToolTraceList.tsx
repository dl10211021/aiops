import type { ExecTraceItem, SafetyPolicyAction, SafetyPolicyDecision } from '@/types'
import { toolLabel } from '@/utils/assetDisplay'
import { parseJsonRecord } from './jsonRecords'
import {
  DatabaseResultSummary,
  PolicyBlockedSummary,
  ToolErrorSummary,
  TracePrimaryActionNotice,
} from './ToolTraceSummaries'
import {
  extractPrimaryAction,
  isPolicyBlockedResult,
  isToolErrorResult,
  traceExecutionText,
} from './traceUtils'
import {
  commandActionFromTrace,
  evidenceLabel,
  evidenceToneClass,
  httpActionFromTrace,
  operationLabel,
  operationToneClass,
  recordValue,
  runtimeExecutionLabels,
  runtimePolicyLabels,
  parseSessionMode,
  sessionModePolicyLabel,
  sessionModePolicyToneClass,
  sqlActionFromTrace,
  toolPolicyFromTrace,
} from './toolPolicyPresentation'

interface ToolTraceListProps {
  items: ExecTraceItem[]
  onTraceActionRule?: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
  sessionMode?: 'readonly' | 'readwrite'
  sessionModeSource?: 'context' | 'session_snapshot' | 'inferred_unknown'
}

export default function ToolTraceList({
  items,
  onTraceActionRule,
  policyRuleBusy,
  sessionMode,
  sessionModeSource,
}: ToolTraceListProps) {
  const traceSource = sessionModeSource || (sessionMode ? 'session_snapshot' : 'inferred_unknown')
  return (
    <div className="mt-2 space-y-2">
      {items.map((item, index) => {
        const traceSession = resolveTraceSessionMode(item, sessionMode, traceSource)
        return (
        <ToolTraceCard
          key={index}
          item={item}
          onTraceActionRule={onTraceActionRule}
          policyRuleBusy={policyRuleBusy}
          sessionMode={traceSession.mode ?? sessionMode}
          sessionModeSource={traceSession.source}
        />
        )
      })}
    </div>
  )
}

type SessionModeResolution = {
  mode?: 'readonly' | 'readwrite'
  source: 'context' | 'session_snapshot' | 'inferred_unknown'
}

function resolveTraceSessionMode(
  item: ExecTraceItem,
  fallbackMode?: 'readonly' | 'readwrite',
  fallbackSource: 'context' | 'session_snapshot' | 'inferred_unknown' = 'inferred_unknown',
): SessionModeResolution {
  const meta = item.resultMeta || {}
  const modeInMeta = parseSessionMode(meta?.session_mode)
  if (modeInMeta) {
    return { mode: modeInMeta, source: 'context' }
  }
  const metaContext = parseSessionMode(meta?.context_mode)
  if (metaContext) return { mode: metaContext, source: 'context' }
  if (fallbackMode) return { mode: fallbackMode, source: fallbackSource }
  return { mode: undefined, source: fallbackSource }
}

function ToolTraceCard({
  item,
  onTraceActionRule,
  policyRuleBusy,
  sessionMode,
  sessionModeSource,
}: Omit<ToolTraceListProps, 'items'> & { item: ExecTraceItem }) {
  const status = item.status || (item.type === 'tool_start' ? 'running' : 'done')
  const parsedResult = item.resultMeta || parseJsonRecord(item.result || '')
  const toolPolicy = toolPolicyFromTrace(item)
  const operationMode = recordValue(toolPolicy, 'operation_mode')
  const approvalPolicy = recordValue(toolPolicy, 'approval_policy')
  const evidenceFamily = recordValue(toolPolicy, 'evidence_family')
  const gateLabel = sessionModePolicyLabel(operationMode, approvalPolicy, sessionMode)
  const runtimeLabels = runtimePolicyLabels(toolPolicy)
  const executionLabels = runtimeExecutionLabels(item)
  const sqlAction = sqlActionFromTrace(item)
  const httpAction = httpActionFromTrace(item)
  const commandAction = commandActionFromTrace(item)
  const primaryAction = extractPrimaryAction(parsedResult)
  const dispatchItems = dispatchResultItems(parsedResult)
  const isPolicyBlocked = isPolicyBlockedResult(parsedResult)
  const isToolError = !isPolicyBlocked && isToolErrorResult(parsedResult)
  const executionText = traceExecutionText(item)
  const evidence = item.evidence
  const evidenceId = item.evidenceId || evidence?.evidence_id || ''
  const evidenceInput = evidence?.input_summary || evidence?.redacted_input || ''
  const evidenceOutput = evidence?.output_preview || ''
  const elapsed = item.startedAt && item.completedAt
    ? `${Math.max(0, ((item.completedAt - item.startedAt) / 1000)).toFixed(1)}s`
    : item.startedAt
      ? '执行中'
      : ''
  const tone = status === 'error'
    ? 'border-ops-alert/45 bg-ops-alert/5 text-ops-alert'
    : status === 'running'
      ? 'border-ops-accent/45 bg-ops-accent/5 text-ops-accent'
      : 'border-ops-success/30 bg-ops-success/5 text-ops-success'

  return (
    <div className={`overflow-hidden rounded-lg border ${tone}`}>
      <div className="flex items-center gap-2 px-3 py-2 text-xs">
        <span className={`h-2 w-2 rounded-full ${status === 'running' ? 'bg-ops-accent animate-pulse' : status === 'error' ? 'bg-ops-alert' : 'bg-ops-success'}`} />
        <span title={item.tool} className="font-semibold text-ops-text">{toolLabel(item.tool)}</span>
        {evidence?.tool_family && (
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5 font-mono text-[10px] text-ops-overlay">
            {evidence.tool_family}
          </span>
        )}
        {item.toolCallId && (
          <span className="rounded-full border border-ops-surface1 px-2 py-0.5 font-mono text-[10px] text-ops-overlay">
            {item.toolCallId}
          </span>
        )}
        {elapsed && <span className="ml-auto font-mono text-[10px] text-ops-overlay">{elapsed}</span>}
      </div>
      {evidenceId && (
        <div className="border-t border-ops-surface0/80 px-3 py-1.5 font-mono text-[10px] text-ops-overlay">
          evidence: {evidenceId}
        </div>
      )}
      {toolPolicy && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[11px] text-ops-overlay">工具策略</div>
          <div className="flex flex-wrap gap-1.5 text-[11px]">
            <span
              className={`rounded border px-2 py-0.5 font-semibold ${operationToneClass(operationMode)}`}
              title="工具自身能力边界：只读、可读写、外发或破坏性。"
            >
              模式：{operationLabel(operationMode)}
            </span>
            {sqlAction && (
              <span
                className={`rounded border px-2 py-0.5 font-semibold ${sqlAction.className}`}
                title="本次 SQL 的实际动作类型，和工具自身可读写能力分开显示。"
              >
                {sqlAction.label}
              </span>
            )}
            {httpAction && (
              <span
                className={`rounded border px-2 py-0.5 font-semibold ${httpAction.className}`}
                title="本次 HTTP/API 请求的实际方法，和工具自身可读写能力分开显示。"
              >
                {httpAction.label}
              </span>
            )}
            {commandAction && (
              <span
                className={`rounded border px-2 py-0.5 font-semibold ${commandAction.className}`}
                title="本次命令的实际动作，和工具自身可读写能力分开显示。"
              >
                {commandAction.label}
              </span>
            )}
            <span
              className={`rounded border px-2 py-0.5 font-semibold ${sessionModePolicyToneClass(
                operationMode,
                approvalPolicy,
                sessionMode,
                sessionModeSource,
              )}`}
              title="当前执行门禁：是否可直接运行，还是写入/高危动作需要审批。"
            >
              门禁：{gateLabel}
            </span>
            <span
              className={`rounded border px-2 py-0.5 font-semibold ${evidenceToneClass(evidenceFamily)}`}
              title="结果会归档到哪类证据链，用于审计、报告和追踪。"
            >
              证据：{evidenceLabel(evidenceFamily)}
            </span>
            {recordValue(toolPolicy, 'destructive') === 'true' && (
              <span className="rounded border border-ops-alert/35 bg-ops-alert/10 px-2 py-0.5 font-semibold text-ops-alert">
                破坏性
              </span>
            )}
            {runtimeLabels.map((label) => (
              <span key={label} className="rounded border border-ops-surface1/65 bg-ops-dark/35 px-2 py-0.5 font-semibold text-ops-subtext">
                {label}
              </span>
            ))}
            {executionLabels.map((label) => (
              <span key={label} className="rounded border border-amber-400/35 bg-amber-400/10 px-2 py-0.5 font-semibold text-amber-100">
                {label}
              </span>
            ))}
          </div>
        </div>
      )}
      {executionText && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[11px] text-ops-overlay">执行内容</div>
          <pre className="max-h-24 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
            {executionText.substring(0, 600)}
          </pre>
        </div>
      )}
      {(evidenceInput || evidenceOutput) && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[11px] text-ops-overlay">证据摘要</div>
          {evidenceInput && (
            <pre className="max-h-24 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
              {evidenceInput.substring(0, 600)}
            </pre>
          )}
          {evidenceOutput && evidenceOutput !== item.result && (
            <pre className="mt-2 max-h-24 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
              {evidenceOutput.substring(0, 600)}
            </pre>
          )}
        </div>
      )}
      {item.result && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[11px] text-ops-overlay">结果</div>
          {isPolicyBlocked && (
            <PolicyBlockedSummary
              result={parsedResult}
              primaryAction={primaryAction}
              onTraceActionRule={onTraceActionRule}
              policyRuleBusy={policyRuleBusy}
            />
          )}
          {parsedResult && isToolError && <ToolErrorSummary result={parsedResult} />}
          {parsedResult && !isPolicyBlocked && !isToolError && <DatabaseResultSummary result={parsedResult} />}
          {dispatchItems.length > 0 && (
            <div className="mb-2 rounded-md border border-ops-surface0 bg-ops-panel/35 px-3 py-2">
              <div className="mb-1 text-[11px] text-ops-overlay">协同子任务</div>
              <div className="space-y-1.5 text-[11px]">
                {dispatchItems.slice(0, 8).map((child, index) => {
                  const preview = dispatchResultPreview(child)
                  return (
                    <div
                      key={`${recordValue(child, 'session_id') || index}`}
                      className="flex min-w-0 flex-wrap items-center gap-1.5 rounded border border-ops-surface1/60 bg-ops-dark/35 px-2 py-1"
                    >
                      <span className="min-w-0 truncate font-mono text-ops-subtext" title={recordValue(child, 'session_id') || ''}>
                        {recordValue(child, 'session_id') || `#${index + 1}`}
                      </span>
                      <span className="rounded border border-ops-surface1/65 px-1.5 py-0.5 font-semibold text-ops-subtext">
                        {recordValue(child, 'status') || '-'}
                      </span>
                      <span className={`rounded border px-1.5 py-0.5 font-semibold ${dispatchResultModeToneClass(child)}`}>
                        模式：{dispatchResultModeLabel(child)}
                      </span>
                      {preview && (
                        <span className="min-w-0 flex-1 truncate text-ops-overlay" title={preview}>
                          {preview}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          {primaryAction && !isPolicyBlocked && (
            <TracePrimaryActionNotice
              action={primaryAction}
              onTraceActionRule={onTraceActionRule}
              policyRuleBusy={policyRuleBusy}
            />
          )}
          {isPolicyBlocked || isToolError ? (
            <details className="rounded-md border border-ops-surface0 bg-ops-panel/35 px-3 py-2">
              <summary className="cursor-pointer text-[11px] text-ops-overlay">原始返回</summary>
              <pre className="mt-2 max-h-36 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
                {item.result.substring(0, 1200)}
              </pre>
            </details>
          ) : (
            <pre className="max-h-44 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
              {item.result.substring(0, 1200)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

function dispatchResultItems(result: Record<string, unknown> | null): Record<string, unknown>[] {
  if (recordValue(result, 'status') !== 'BATCH_COMPLETE') return []
  const items = result?.results
  if (!Array.isArray(items)) return []
  return items.filter((item): item is Record<string, unknown> => {
    return Boolean(item && typeof item === 'object' && !Array.isArray(item))
  })
}

function dispatchResultModeLabel(item: Record<string, unknown>): string {
  const mode = parseSessionMode(item.session_mode ?? item.allow_modifications)
  if (mode === 'readwrite') return '读写'
  if (mode === 'readonly') return '只读'
  return '未识别'
}

function dispatchResultModeToneClass(item: Record<string, unknown>): string {
  const mode = parseSessionMode(item.session_mode ?? item.allow_modifications)
  if (mode === 'readwrite') return 'border-ops-success/35 bg-ops-success/10 text-ops-success'
  if (mode === 'readonly') return 'border-amber-400/35 bg-amber-400/10 text-amber-100'
  return 'border-ops-surface1/65 bg-ops-dark/35 text-ops-subtext'
}

function dispatchResultPreview(item: Record<string, unknown>): string {
  return recordValue(item, 'error') || recordValue(item, 'report') || ''
}
