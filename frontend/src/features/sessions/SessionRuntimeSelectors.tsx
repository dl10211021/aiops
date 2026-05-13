import type { ModelGroup } from '@/api/client'

export function ModelSelector({
  availableModels,
  configuredMainModel,
  modelName,
  onModelChange,
}: {
  availableModels: ModelGroup[]
  configuredMainModel: string
  modelName: string
  onModelChange: (value: string) => void
}) {
  const configuredMainModelLabel = availableModels
    .flatMap((group) => group.models)
    .find((model) => model.id === configuredMainModel)?.name || configuredMainModel
  const followsGlobalModel = Boolean(configuredMainModel && modelName === configuredMainModel)
  const modelStateLabel = configuredMainModel
    ? (followsGlobalModel ? '跟随全局' : '会话覆盖')
    : '后端默认'

  return (
    <div className="flex h-9 min-w-0 items-center gap-1.5 rounded-lg border border-ops-surface1/70 bg-ops-panel/45 px-2">
      <span className="text-[10px] text-ops-overlay">会话模型</span>
      <span
        className={`hidden rounded border px-1.5 py-0.5 text-[10px] font-semibold 2xl:inline-flex ${
          followsGlobalModel
            ? 'border-ops-accent/30 bg-ops-accent/10 text-ops-accent'
            : configuredMainModel
              ? 'border-ops-warning/35 bg-ops-warning/10 text-ops-warning'
              : 'border-ops-surface1/60 bg-ops-panel/45 text-ops-overlay'
        }`}
        title={configuredMainModel ? `全局主模型：${configuredMainModelLabel}` : '尚未配置全局主模型'}
      >
        {modelStateLabel}
      </span>
      <select
        value={modelName}
        onChange={(event) => onModelChange(event.target.value)}
        className="w-40 bg-transparent text-xs text-ops-text outline-none lg:w-52"
        title={configuredMainModel ? `会话模型，可临时覆盖全局主模型：${configuredMainModelLabel}` : '会话模型，可临时覆盖全局主模型'}
      >
        {availableModels.length > 0 ? (
          availableModels.map((group) => (
            <optgroup key={group.provider_id} label={group.provider_name}>
              {group.models.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}
            </optgroup>
          ))
        ) : (
          <option value={modelName}>{modelName || '使用后端默认模型'}</option>
        )}
      </select>
      {configuredMainModel && !followsGlobalModel && (
        <button
          type="button"
          onClick={() => onModelChange(configuredMainModel)}
          className="hidden rounded border border-ops-surface1/60 px-1.5 py-0.5 text-[10px] font-semibold text-ops-subtext hover:border-ops-accent/40 hover:text-ops-accent xl:inline-flex"
          title={`切回全局主模型：${configuredMainModelLabel}`}
        >
          跟随
        </button>
      )}
    </div>
  )
}

export function ThinkingModeSelector({
  thinkingMode,
  onThinkingModeChange,
}: {
  thinkingMode: string
  onThinkingModeChange: (value: string) => void
}) {
  return (
    <div className="flex h-9 items-center gap-1.5 rounded-lg border border-ops-surface1/70 bg-ops-panel/45 px-2">
      <span className="text-[10px] text-ops-overlay">思考</span>
      <select
        value={thinkingMode}
        onChange={(event) => onThinkingModeChange(event.target.value)}
        className="w-24 bg-transparent text-xs text-ops-text outline-none"
        title="思考模式"
      >
        <option value="off">关闭</option>
        <option value="enabled">开启</option>
        <option value="low">低度</option>
        <option value="medium">中度</option>
        <option value="high">高度</option>
      </select>
    </div>
  )
}
