import type { SafetyPolicy } from '@/types'

interface PolicyRuntimeSettingsProps {
  policy: SafetyPolicy
  updatePolicy: (patch: Partial<SafetyPolicy>) => void
}

export function PolicyRuntimeSettings({ policy, updatePolicy }: PolicyRuntimeSettingsProps) {
  return (
    <section className="ops-data-panel mb-4 grid grid-cols-2 gap-4 p-4">
      <label>
        <span className="text-xs text-ops-subtext">审批等待超时（秒）</span>
        <input
          type="number"
          min={30}
          max={1800}
          value={policy.approval_timeout_seconds}
          onChange={(e) => updatePolicy({ approval_timeout_seconds: Number(e.target.value) || 300 })}
          className="ops-control mt-1 w-full px-3 py-2 text-sm"
        />
      </label>
      <label className="flex items-center gap-2 pt-6 text-sm text-ops-text">
        <input
          type="checkbox"
          checked={policy.readwrite_chat_warning_enabled}
          onChange={(e) => updatePolicy({ readwrite_chat_warning_enabled: e.target.checked })}
          className="accent-ops-accent"
        />
        读写会话聊天前弹窗提醒
      </label>
    </section>
  )
}
