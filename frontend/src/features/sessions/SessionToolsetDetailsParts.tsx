import type { ToolsetInfo } from '@/types'
import { toolLabel, toolsetLabel } from '@/utils/assetDisplay'

export function ToolsetSummaryPills({
  enabledToolsets,
  primaryToolsets,
}: {
  enabledToolsets: ToolsetInfo[]
  primaryToolsets: ToolsetInfo[]
}) {
  return (
    <div className="mb-2 flex flex-wrap items-center gap-2">
      {primaryToolsets.length > 0 ? primaryToolsets.map((toolset) => (
        <ToolsetPill key={toolset.id} toolset={toolset} />
      )) : (
        <span className="text-xs text-ops-overlay">正在读取当前会话工具集...</span>
      )}
      {enabledToolsets.length > primaryToolsets.length && (
        <span className="rounded-full border border-ops-surface1 bg-ops-dark/50 px-2 py-1 text-xs text-ops-overlay">
          +{enabledToolsets.length - primaryToolsets.length} 类
        </span>
      )}
    </div>
  )
}

export function ContextCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-ops-surface0 bg-ops-dark/35 px-2.5 py-2">
      <div className="text-[11px] text-ops-overlay">{label}</div>
      <div className="mt-1 truncate font-mono text-ops-text">{value}</div>
    </div>
  )
}

export function SafetyBoundaryPanel() {
  return (
    <div className="rounded-lg border border-ops-surface0 bg-ops-dark/35 px-3 py-2 text-xs leading-relaxed text-ops-subtext">
      <div className="font-semibold text-ops-text">安全边界</div>
      <div className="mt-1">
        凭据由资产中心托管注入；高危工具进入审批队列，硬拦截规则会直接拒绝。
      </div>
    </div>
  )
}

function ToolsetPill({ toolset }: { toolset: ToolsetInfo }) {
  const enabledTools = toolset.tools.filter((tool) => tool.enabled)
  const hasInteractiveTool = enabledTools.some((tool) => tool.name === 'clarify' || tool.name === 'request_user_interaction')
  return (
    <details className="group">
      <summary className="cursor-pointer list-none rounded-full border border-ops-surface1 bg-ops-dark/70 px-3 py-1.5 text-xs text-ops-text hover:border-ops-accent/50">
        <span title={toolset.id} className="font-semibold text-ops-accent">{toolsetLabel(toolset.id)}</span>
        {hasInteractiveTool && (
          <span className="ml-2 rounded-full border border-ops-accent/35 bg-ops-accent/10 px-1.5 py-0.5 text-[10px] font-semibold text-ops-accent">
            交互
          </span>
        )}
        <span className="ml-2 text-ops-overlay">{enabledTools.length}</span>
      </summary>
      <div className="absolute z-20 mt-2 w-80 rounded-lg border border-ops-surface1 bg-ops-panel p-3 shadow-2xl">
        <div className="mb-2 text-[10px] text-ops-overlay">可用工具</div>
        <div className="space-y-2">
          {enabledTools.map((tool) => (
            <div key={tool.name} className="rounded-lg bg-ops-dark/70 p-2">
              <div className="flex items-center gap-2">
                <div title={tool.name} className="text-xs font-semibold text-ops-text">{toolLabel(tool.name)}</div>
                <ToolCategoryBadge toolName={tool.name} />
              </div>
              <div className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-ops-subtext">{tool.description}</div>
            </div>
          ))}
        </div>
      </div>
    </details>
  )
}

function ToolCategoryBadge({ toolName }: { toolName: string }) {
  const category = categoryForTool(toolName)
  if (!category) return null
  return (
    <span className="rounded-full border border-ops-surface1/60 bg-ops-panel/45 px-1.5 py-0.5 text-[10px] text-ops-overlay">
      {category}
    </span>
  )
}

function categoryForTool(toolName: string): string {
  if (toolName === 'clarify' || toolName === 'request_user_interaction') return '交互'
  if (toolName === 'todo') return '任务'
  if (toolName === 'image_gen' || toolName === 'vision_analyze' || toolName === 'browser_vision') return '视觉'
  if (toolName === 'web_search' || toolName === 'web_extractor' || toolName === 'web_research') return '联网'
  if (toolName.startsWith('browser_')) return '浏览器'
  return ''
}
