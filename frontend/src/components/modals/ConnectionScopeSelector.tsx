const TARGET_SCOPE_OPTIONS = [
  { value: 'asset', label: '单台资产', desc: '保存到资产中心并打开会话' },
  { value: 'group', label: '资产组别', desc: '作为批量任务或会话入口' },
  { value: 'global', label: '全局会话', desc: '不绑定具体资产' },
]

interface ConnectionScopeSelectorProps {
  value: string
  onChange: (value: string) => void
}

export default function ConnectionScopeSelector({
  value,
  onChange,
}: ConnectionScopeSelectorProps) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/25 p-3">
      <div className="mb-2 text-xs font-semibold text-ops-text">连接范围</div>
      <div className="grid gap-2 sm:grid-cols-3">
        {TARGET_SCOPE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded-lg border px-3 py-2 text-left transition-colors ${
              value === option.value
                ? 'border-ops-accent bg-ops-accent/15 text-ops-text'
                : 'border-ops-surface1 bg-ops-panel/40 text-ops-subtext hover:text-ops-text'
            }`}
          >
            <div className="text-sm font-semibold">{option.label}</div>
            <div className="mt-1 text-[11px] leading-4 text-ops-overlay">{option.desc}</div>
          </button>
        ))}
      </div>
    </section>
  )
}
