import type { ReactNode } from 'react'

export const notificationInputClass = 'w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none transition-colors focus:border-ops-accent'

export function ChannelSection({
  title,
  description,
  enabled,
  testing,
  onEnabledChange,
  onTest,
  children,
}: {
  title: string
  description: string
  enabled: boolean
  testing: boolean
  onEnabledChange: (enabled: boolean) => void
  onTest: () => void
  children: ReactNode
}) {
  return (
    <section className={`rounded-lg border p-4 transition-colors ${enabled ? 'border-ops-surface1 bg-ops-dark/35' : 'border-ops-surface0 bg-ops-dark/20 opacity-80'}`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <label className="flex min-w-0 items-start gap-3">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onEnabledChange(e.target.checked)}
            className="mt-1 accent-ops-accent"
          />
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-ops-text">{title}</span>
            <span className="mt-1 block text-xs leading-5 text-ops-subtext">{description}</span>
          </span>
        </label>
        <button
          onClick={onTest}
          disabled={testing || !enabled}
          className="rounded-lg border border-ops-surface1 bg-ops-surface0 px-3 py-1.5 text-xs text-ops-subtext transition-colors hover:text-ops-text disabled:opacity-45"
        >
          {testing ? '测试中...' : '测试通道'}
        </button>
      </div>
      <div className="grid gap-3">
        {children}
      </div>
    </section>
  )
}

export function Field({
  label,
  value,
  onChange,
  className,
  placeholder,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (value: string) => void
  className: string
  placeholder?: string
  type?: string
}) {
  return (
    <label>
      <span className="text-xs text-ops-subtext">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`mt-1 ${className}`}
        placeholder={placeholder}
      />
    </label>
  )
}
