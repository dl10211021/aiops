import type { AgentRuntimeConfig } from '@/api/client'

interface RuntimeDraft {
  chat_max_steps: number
  headless_max_steps: number
}

interface LLMRuntimeConfigPanelProps {
  runtimeConfig: AgentRuntimeConfig | null
  runtimeDraft: RuntimeDraft
  runtimeSaving: boolean
  onDraftChange: (patch: Partial<RuntimeDraft>) => void
  onSave: () => void
}

export default function LLMRuntimeConfigPanel({
  runtimeConfig,
  runtimeDraft,
  runtimeSaving,
  onDraftChange,
  onSave,
}: LLMRuntimeConfigPanelProps) {
  return (
    <div className="ops-data-panel mb-4 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-ops-text">Agent 执行保护</h3>
          <p className="mt-1 text-xs leading-5 text-ops-subtext">
            控制单次任务最多允许模型连续思考和调用工具的轮数。达到上限后，系统会停止工具调用并输出阶段性运维报告。
          </p>
        </div>
        {runtimeConfig && (
          <span className="ops-control px-2 py-1 text-[10px] text-ops-overlay">
            范围 {runtimeConfig.min_steps}-{runtimeConfig.max_steps}
          </span>
        )}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs text-ops-subtext">前台会话上限</span>
          <input
            type="number"
            min={runtimeConfig?.min_steps ?? 10}
            max={runtimeConfig?.max_steps ?? 200}
            value={runtimeDraft.chat_max_steps}
            onChange={(e) => onDraftChange({ chat_max_steps: Number(e.target.value) })}
            className="ops-control mt-1 w-full px-3 py-2 text-sm"
          />
          <span className="mt-1 block text-[11px] text-ops-overlay">普通 AI 会话使用，默认 80。</span>
        </label>
        <label className="block">
          <span className="text-xs text-ops-subtext">后台任务上限</span>
          <input
            type="number"
            min={runtimeConfig?.min_steps ?? 10}
            max={runtimeConfig?.max_steps ?? 200}
            value={runtimeDraft.headless_max_steps}
            onChange={(e) => onDraftChange({ headless_max_steps: Number(e.target.value) })}
            className="ops-control mt-1 w-full px-3 py-2 text-sm"
          />
          <span className="mt-1 block text-[11px] text-ops-overlay">巡检、定时任务、后台自治使用，默认 60。</span>
        </label>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="text-[11px] text-ops-overlay">
          保存后立即生效，并写入环境配置，重启后仍保留。
        </div>
        <button
          onClick={onSave}
          disabled={runtimeSaving}
          className="ops-muted-action px-3 py-1.5 text-xs disabled:opacity-50"
        >
          {runtimeSaving ? '保存中...' : '保存执行保护'}
        </button>
      </div>
    </div>
  )
}
