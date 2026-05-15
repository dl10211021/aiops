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
  evidenceLabel,
  evidenceToneClass,
  operationLabel,
  operationToneClass,
  recordValue,
  runtimeExecutionLabels,
  runtimePolicyLabels,
  sessionModePolicyLabel,
  sessionModePolicyToneClass,
  toolPolicyFromTrace,
} from './toolPolicyPresentation'

interface ToolTraceListProps {
  items: ExecTraceItem[]
  onTraceActionRule?: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
  sessionMode?: 'readonly' | 'readwrite'
}

export default function ToolTraceList({ items, onTraceActionRule, policyRuleBusy, sessionMode }: ToolTraceListProps) {
  return (
    <div className="mt-2 space-y-2">
      {items.map((item, index) => (
        <ToolTraceCard
          key={index}
          item={item}
          onTraceActionRule={onTraceActionRule}
          policyRuleBusy={policyRuleBusy}
          sessionMode={sessionMode}
        />
      ))}
    </div>
  )
}

function ToolTraceCard({
  item,
  onTraceActionRule,
  policyRuleBusy,
  sessionMode,
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
  const primaryAction = extractPrimaryAction(parsedResult)
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
            <span
              className={`rounded border px-2 py-0.5 font-semibold ${sessionModePolicyToneClass(operationMode, approvalPolicy, sessionMode)}`}
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
