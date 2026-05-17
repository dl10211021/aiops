interface EvidenceReferenceChipProps {
  kind: 'evidence' | 'approval'
  label?: string
  value: string
  title: string
  onClick: () => void
  className?: string
}

export function EvidenceReferenceChip({
  kind,
  label,
  value,
  title,
  onClick,
  className = '',
}: EvidenceReferenceChipProps) {
  const tone = kind === 'approval'
    ? 'border-amber-400/35 bg-amber-400/10 text-amber-100 hover:bg-amber-400/15'
    : 'border-ops-surface1 bg-ops-dark/20 text-ops-overlay hover:border-ops-accent/45 hover:text-ops-accent'
  return (
    <button
      type="button"
      onClick={onClick}
      className={`max-w-full truncate rounded-full border px-2 py-0.5 font-mono text-[10px] ${tone} ${className}`}
      title={title}
    >
      {label || (kind === 'approval' ? '审批' : '证据')}：{value}
    </button>
  )
}
