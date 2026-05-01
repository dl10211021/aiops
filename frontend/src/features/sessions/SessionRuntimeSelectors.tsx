import type { ModelGroup } from '@/api/client'

export function ModelSelector({
  availableModels,
  modelName,
  onModelChange,
}: {
  availableModels: ModelGroup[]
  modelName: string
  onModelChange: (value: string) => void
}) {
  return (
    <div className="flex h-9 min-w-0 items-center gap-1.5 rounded-lg border border-ops-surface1/70 bg-ops-panel/45 px-2">
      <span className="text-[10px] text-ops-overlay">模型</span>
      <select
        value={modelName}
        onChange={(event) => onModelChange(event.target.value)}
        className="w-44 bg-transparent text-xs text-ops-text outline-none lg:w-56"
        title="模型"
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
