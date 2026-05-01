interface TraceInfoProps {
  label: string
  value: string
}

export default function TraceInfo({ label, value }: TraceInfoProps) {
  return (
    <div>
      <div className="text-ops-overlay">{label}</div>
      <div className="mt-0.5 font-mono text-ops-text">{value}</div>
    </div>
  )
}
