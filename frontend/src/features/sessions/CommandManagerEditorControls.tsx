export function CommandTextField({
  className = '',
  disabled,
  label,
  placeholder,
  value,
  onChange,
}: {
  className?: string
  disabled: boolean
  label: string
  placeholder: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <label className={`text-sm ${className}`}>
      <span className="text-ops-subtext">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-ops-text outline-none focus:border-ops-accent disabled:cursor-default disabled:opacity-75"
        placeholder={placeholder}
      />
    </label>
  )
}

export function CommandSelectField({
  disabled,
  label,
  options,
  value,
  onChange,
}: {
  disabled: boolean
  label: string
  options: Array<{ label: string; value: string }>
  value: string
  onChange: (value: string) => void
}) {
  return (
    <label className="text-sm">
      <span className="text-ops-subtext">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-ops-text outline-none focus:border-ops-accent disabled:cursor-default disabled:opacity-75"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  )
}

export function CommandOrderField({
  busy,
  readonlyDraft,
  sortOrder,
  onStepOrder,
}: {
  busy: boolean
  readonlyDraft: boolean
  sortOrder: number
  onStepOrder: (delta: number) => void
}) {
  return (
    <label className="text-sm">
      <span className="text-ops-subtext">显示顺序</span>
      <div className="mt-1 flex items-center gap-2">
        <button
          type="button"
          onClick={() => onStepOrder(-1)}
          disabled={readonlyDraft || busy || sortOrder <= 1}
          className="rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-subtext hover:border-ops-accent/45 hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-40"
        >
          上移
        </button>
        <span className="min-w-16 rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-center font-mono text-sm text-ops-text">
          {sortOrder}
        </span>
        <button
          type="button"
          onClick={() => onStepOrder(1)}
          disabled={readonlyDraft || busy || sortOrder >= 100}
          className="rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-subtext hover:border-ops-accent/45 hover:text-ops-text disabled:cursor-not-allowed disabled:opacity-40"
        >
          下移
        </button>
      </div>
    </label>
  )
}

export function CommandCheckbox({
  checked,
  disabled,
  label,
  onChange,
}: {
  checked: boolean
  disabled: boolean
  label: string
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="accent-ops-accent disabled:opacity-50"
      />
      {label}
    </label>
  )
}
