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

interface ToolTraceListProps {
  items: ExecTraceItem[]
  onTraceActionRule?: (action: SafetyPolicyAction, decision: SafetyPolicyDecision) => void
  policyRuleBusy?: string | null
}

export default function ToolTraceList({ items, onTraceActionRule, policyRuleBusy }: ToolTraceListProps) {
  return (
    <div className="mt-2 space-y-2">
      {items.map((item, index) => (
        <ToolTraceCard
          key={index}
          item={item}
          onTraceActionRule={onTraceActionRule}
          policyRuleBusy={policyRuleBusy}
        />
      ))}
    </div>
  )
}

function ToolTraceCard({
  item,
  onTraceActionRule,
  policyRuleBusy,
}: Omit<ToolTraceListProps, 'items'> & { item: ExecTraceItem }) {
  const status = item.status || (item.type === 'tool_start' ? 'running' : 'done')
  const parsedResult = item.resultMeta || parseJsonRecord(item.result || '')
  const primaryAction = extractPrimaryAction(parsedResult)
  const isPolicyBlocked = isPolicyBlockedResult(parsedResult)
  const isToolError = !isPolicyBlocked && isToolErrorResult(parsedResult)
  const executionText = traceExecutionText(item)
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
        {elapsed && <span className="ml-auto font-mono text-[10px] text-ops-overlay">{elapsed}</span>}
      </div>
      {executionText && (
        <div className="border-t border-ops-surface0/80 px-3 py-2">
          <div className="mb-1 text-[11px] text-ops-overlay">执行内容</div>
          <pre className="max-h-24 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-ops-subtext">
            {executionText.substring(0, 600)}
          </pre>
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
