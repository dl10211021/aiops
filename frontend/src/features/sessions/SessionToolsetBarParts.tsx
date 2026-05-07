import type { ModelGroup } from '@/api/client'
import type { Session, ToolsetInfo } from '@/types'
import { ModelSelector, ThinkingModeSelector } from './SessionRuntimeSelectors'
import { ContextCell, SafetyBoundaryPanel, ToolsetSummaryPills } from './SessionToolsetDetailsParts'

export function SessionIdentityStrip({
  session,
  assetText,
  protocolText,
  capabilityItems,
}: {
  session: Session
  assetText: string
  protocolText: string
  capabilityItems: string[]
}) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <span
        title={`${session.asset_type}/${session.protocol}`}
        className="shrink-0 rounded-full border border-ops-accent/30 bg-ops-accent/10 px-2.5 py-1 text-[11px] font-semibold text-ops-accent"
      >
        {assetText} / {protocolText}
      </span>
      <span className="min-w-0 truncate font-mono text-[11px] text-ops-overlay">
        {session.user || '-'}@{session.host}
      </span>
      <span className="hidden h-5 items-center rounded-full border border-ops-surface1/45 bg-ops-panel/35 px-2 text-[11px] text-ops-subtext md:inline-flex">
        {capabilityItems.join(' / ')}
      </span>
      <span className="hidden min-w-0 truncate text-[11px] text-ops-overlay 2xl:inline">
        凭据托管注入，高危动作进入审批
      </span>
    </div>
  )
}

export function SessionRuntimeControls({
  availableModels,
  modelName,
  orchestrationMode,
  thinkingMode,
  capabilityItems,
  detailsOpen,
  onModelChange,
  onOrchestrationModeChange,
  onThinkingModeChange,
  onToggleDetails,
}: {
  availableModels: ModelGroup[]
  modelName: string
  orchestrationMode: 'single' | 'split'
  thinkingMode: string
  capabilityItems: string[]
  detailsOpen: boolean
  onModelChange: (value: string) => void
  onOrchestrationModeChange: (mode: 'single' | 'split') => void
  onThinkingModeChange: (value: string) => void
  onToggleDetails: () => void
}) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2 xl:justify-end">
      <ModelSelector
        availableModels={availableModels}
        modelName={modelName}
        onModelChange={onModelChange}
      />
      <ThinkingModeSelector
        thinkingMode={thinkingMode}
        onThinkingModeChange={onThinkingModeChange}
      />
      <div className="inline-flex h-9 overflow-hidden rounded-lg border border-ops-surface1/70 bg-ops-panel/45 p-0.5" title="切换本次会话的模型协作策略">
        <button
          type="button"
          onClick={() => onOrchestrationModeChange('single')}
          className={`rounded-md px-2.5 text-[11px] font-semibold transition-colors ${
            orchestrationMode === 'single'
              ? 'bg-ops-accent/18 text-ops-accent'
              : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'
          }`}
          title="原始单模型流程：主模型自己规划、选工具、执行后回复"
        >
          原始
        </button>
        <button
          type="button"
          onClick={() => onOrchestrationModeChange('split')}
          className={`rounded-md px-2.5 text-[11px] font-semibold transition-colors ${
            orchestrationMode === 'split'
              ? 'bg-ops-accent/18 text-ops-accent'
              : 'text-ops-subtext hover:bg-ops-surface0 hover:text-ops-text'
          }`}
          title="主副模型流程：主模型定目标和兜底，辅助模型选工具和整理回复"
        >
          主副
        </button>
      </div>
      <span className="inline-flex h-9 rounded-lg border border-ops-surface1/60 bg-ops-panel/35 px-2.5 text-right text-[11px] text-ops-subtext sm:hidden">
        <span className="self-center">{capabilityItems.join(' / ')}</span>
      </span>
      <button
        type="button"
        onClick={onToggleDetails}
        className="h-9 rounded-lg border border-ops-surface1/70 bg-ops-panel/45 px-3 text-xs font-semibold text-ops-subtext transition-colors hover:border-ops-accent/50 hover:text-ops-text"
        aria-expanded={detailsOpen}
      >
        {detailsOpen ? '收起' : '详情'}
      </button>
    </div>
  )
}

export function SessionToolsetDetails({
  enabledToolsets,
  primaryToolsets,
  scope,
  scopeValue,
  session,
  targetLabel,
}: {
  enabledToolsets: ToolsetInfo[]
  primaryToolsets: ToolsetInfo[]
  scope: string
  scopeValue: string
  session: Session
  targetLabel: string
}) {
  return (
    <div className="mt-2 grid gap-2 border-t border-ops-surface0/80 pt-2 lg:grid-cols-[1fr_340px]">
      <div className="min-w-0">
        <ToolsetSummaryPills
          enabledToolsets={enabledToolsets}
          primaryToolsets={primaryToolsets}
        />
        <div className="grid gap-2 text-[11px] text-ops-subtext md:grid-cols-2 xl:grid-cols-4">
          <ContextCell label="目标" value={targetLabel} />
          <ContextCell label="账号" value={session.user || '-'} />
          <ContextCell label="范围" value={`${scope}${scopeValue ? ` / ${scopeValue}` : ''}`} />
          <ContextCell label="标签" value={(session.tags || []).slice(0, 3).join(', ') || '-'} />
        </div>
      </div>
      <SafetyBoundaryPanel />
    </div>
  )
}
