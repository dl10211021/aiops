import type { AssistantModelConfig } from '@/api/config'

interface ModelOption {
  id: string
  name: string
  providerName: string
}

interface LLMAssistantModelPanelProps {
  config: AssistantModelConfig
  modelOptions: ModelOption[]
  saving: boolean
  onChange: (patch: Partial<AssistantModelConfig>) => void
  onTaskChange: (task: string, enabled: boolean) => void
  onSave: () => void
}

const taskLabels = [
  ['memory_compression', '成功经验与长期记忆压缩'],
  ['asset_profile_prompt', '资产画像生成并注入提示词'],
  ['trace_review', '思维链执行审查'],
  ['risk_advice', '风险与后续建议'],
  ['completion_check', '任务完成度检查'],
] as const

export default function LLMAssistantModelPanel({
  config,
  modelOptions,
  saving,
  onChange,
  onTaskChange,
  onSave,
}: LLMAssistantModelPanelProps) {
  const mainModelValue = config.main_model_id || ''
  const assistantModelValue = config.model_id || ''

  return (
    <section className="rounded-lg border border-ops-surface0 bg-ops-dark/35 p-4">
      <div className="mb-3">
        <div className="text-sm font-semibold text-ops-text">主模型 / 辅助思维模型</div>
        <p className="mt-1 text-[11px] leading-5 text-ops-subtext">
          主模型负责正常会话和工具调度；辅助思维模型负责画像、记忆压缩、思维链审查和成功经验沉淀。未配置辅助模型时会自动使用主模型。
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs text-ops-subtext">
          主模型
          <select
            value={mainModelValue}
            onChange={(event) => onChange({ main_model_id: event.target.value })}
            className="mt-1 w-full rounded border border-ops-surface1 bg-ops-panel px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            <option value="">默认第一个可用模型</option>
            {modelOptions.map((model) => (
              <option key={model.id} value={model.id}>
                {model.providerName} / {model.name}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs text-ops-subtext">
          辅助思维模型
          <select
            value={assistantModelValue}
            onChange={(event) => onChange({ model_id: event.target.value })}
            disabled={!config.enabled}
            className="mt-1 w-full rounded border border-ops-surface1 bg-ops-panel px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">未指定，使用主模型</option>
            {modelOptions.map((model) => (
              <option key={model.id} value={model.id}>
                {model.providerName} / {model.name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm text-ops-subtext">
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(event) => onChange({ enabled: event.target.checked })}
            className="accent-ops-accent"
          />
          启用辅助思维模型
        </label>

        <label className="text-xs text-ops-subtext">
          思考强度
          <select
            value={config.thinking_mode || 'high'}
            onChange={(event) => onChange({ thinking_mode: event.target.value })}
            className="mt-1 w-full rounded border border-ops-surface1 bg-ops-panel px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            <option value="off">关闭思考</option>
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="enabled">自动启用</option>
          </select>
        </label>
      </div>

      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {taskLabels.map(([task, label]) => (
          <label key={task} className="flex items-center gap-2 rounded-md border border-ops-surface0 bg-ops-panel/45 px-3 py-2 text-xs text-ops-subtext">
            <input
              type="checkbox"
              checked={config.tasks?.[task] !== false}
              onChange={(event) => onTaskChange(task, event.target.checked)}
              className="accent-ops-accent"
            />
            {label}
          </label>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-[11px] text-ops-overlay">
          当前规则：配置辅助模型则辅助任务使用它；未配置则使用主模型。
        </span>
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="rounded-md bg-ops-accent px-3 py-1.5 text-xs font-semibold text-ops-dark disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存模型角色'}
        </button>
      </div>
    </section>
  )
}
