interface ConnectionPermissionSectionProps {
  allowModifications: boolean
  onChange: (allowModifications: boolean) => void
}

export default function ConnectionPermissionSection({
  allowModifications,
  onChange,
}: ConnectionPermissionSectionProps) {
  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3">
      <div className="mb-2 text-xs font-semibold text-ops-text">会话权限</div>
      <div className="grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onChange(false)}
          className={`rounded-lg border px-3 py-2 text-left transition-colors ${
            !allowModifications
              ? 'border-ops-success/45 bg-ops-success/10 text-ops-text'
              : 'border-ops-surface1 bg-ops-panel/40 text-ops-subtext hover:text-ops-text'
          }`}
        >
          <div className="text-sm font-semibold">只读模式</div>
          <div className="mt-1 text-[11px] leading-4 text-ops-overlay">
            默认模式，仅查询和分析，不主动修改目标系统。
          </div>
        </button>
        <button
          type="button"
          onClick={() => onChange(true)}
          className={`rounded-lg border px-3 py-2 text-left transition-colors ${
            allowModifications
              ? 'border-ops-alert/45 bg-ops-alert/10 text-ops-text'
              : 'border-ops-surface1 bg-ops-panel/40 text-ops-subtext hover:text-ops-text'
          }`}
        >
          <div className="text-sm font-semibold">允许变更</div>
          <div className="mt-1 text-[11px] leading-4 text-ops-overlay">
            可执行修改动作，高危命令仍会进入审批或被硬拦截。
          </div>
        </button>
      </div>
    </section>
  )
}
