interface ApprovalSourceSummaryProps {
  source?: Record<string, unknown> | null
  reason?: string
}

function sourceText(source?: Record<string, unknown> | null, key?: string) {
  if (!source || !key) return ''
  const value = source[key]
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
    ? String(value)
    : ''
}

function sourceTone(layer: string) {
  if (layer === 'runtime_policy') return 'border-sky-300/30 bg-sky-300/10 text-sky-100'
  if (layer === 'action_policy') return 'border-yellow-300/30 bg-yellow-300/10 text-yellow-100'
  return 'border-ops-surface1/65 bg-ops-dark/35 text-ops-subtext'
}

export function ApprovalSourceSummary({ source, reason }: ApprovalSourceSummaryProps) {
  if (!source && !reason) return null
  const layer = sourceText(source, 'layer')
  const label = sourceText(source, 'label') || '安全策略'
  const detail = sourceText(source, 'detail')
  const sourceReason = sourceText(source, 'reason') || reason || ''
  return (
    <div className={`rounded-lg border px-3 py-2 text-xs leading-5 ${sourceTone(layer)}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">策略来源：{label}</span>
        {detail && <span className="font-mono text-[11px] opacity-80">{detail}</span>}
      </div>
      {sourceReason && <div className="mt-1 opacity-90">{sourceReason}</div>}
    </div>
  )
}
