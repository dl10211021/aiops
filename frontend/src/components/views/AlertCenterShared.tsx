import {
  alertSeverityLabel,
  alertSeverityToneClass,
  alertStatusLabel,
  alertStatusToneClass,
} from './alertDisplay'

export function AlertSeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${alertSeverityToneClass(severity)}`}>
      {alertSeverityLabel(severity)}
    </span>
  )
}

export function AlertStatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${alertStatusToneClass(status)}`}>
      {alertStatusLabel(status)}
    </span>
  )
}

export function AlertInfo({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-ops-overlay">{label}</span>
      <span className="truncate text-right font-mono text-ops-text">{String(value)}</span>
    </div>
  )
}
