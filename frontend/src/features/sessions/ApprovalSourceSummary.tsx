interface ApprovalSourceSummaryProps {
  source?: Record<string, unknown> | null
  sources?: Array<Record<string, unknown> | null> | null
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

export function ApprovalSourceSummary({ source, sources, reason }: ApprovalSourceSummaryProps) {
  const normalizedSources = (sources && sources.length > 0
    ? sources
    : source
      ? [source]
      : []
  ).filter((item): item is Record<string, unknown> => Boolean(item))

  if (normalizedSources.length === 0 && !reason) return null

  return (
    <div className="grid gap-2">
      {normalizedSources.map((item, index) => {
        const layer = sourceText(item, 'layer')
        const label = sourceText(item, 'label') || '安全策略'
        const detail = sourceText(item, 'detail')
        const sourceReason = sourceText(item, 'reason')
        return (
          <div key={`${layer || 'source'}-${index}`} className={`rounded-lg border px-3 py-2 text-xs leading-5 ${sourceTone(layer)}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">策略来源：{label}</span>
              {detail && <span className="font-mono text-[11px] opacity-80">{detail}</span>}
            </div>
            {sourceReason && <div className="mt-1 opacity-90">{sourceReason}</div>}
          </div>
        )
      })}
      {normalizedSources.length === 0 && reason && (
        <div className={`rounded-lg border px-3 py-2 text-xs leading-5 ${sourceTone('')}`}>
          <div className="mt-1 opacity-90">{reason}</div>
        </div>
      )}
    </div>
  )
}
