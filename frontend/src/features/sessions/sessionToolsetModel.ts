import type { Session, SessionToolCatalog } from '@/types'
import { assetTypeLabel, protocolLabel } from '@/utils/assetDisplay'

export function buildSessionToolsetModel(session: Session, catalog: SessionToolCatalog | null) {
  const enabledToolsets = (catalog?.toolsets || []).filter((toolset) => toolset.enabled)
  const activeTools = catalog?.active_tools || enabledToolsets.flatMap((toolset) => (
    toolset.tools.filter((tool) => tool.enabled).map((tool) => tool.name)
  ))
  const primaryToolsets = enabledToolsets.slice(0, 3)
  const scope = session.target_scope || catalog?.context?.target_scope || 'asset'
  const scopeValue = session.scope_value || catalog?.context?.host || session.host
  const targetLabel = session.remark || session.host || '-'
  const assetText = assetTypeLabel(session.asset_type)
  const protocolText = protocolLabel(session.protocol)
  const pendingApprovalCount = session.messages.filter((message) => message.toolApproval && !message.toolApproval.resolved).length
  const pendingInteractionCount = session.messages.filter((message) => message.userInteraction && !message.userInteraction.resolved).length
  const pendingCount = pendingApprovalCount + pendingInteractionCount
  const capabilityItems = [
    `工具 ${activeTools.length || '...'}`,
    `技能 ${session.skills.length}`,
    pendingCount > 0 ? `待确认 ${pendingCount}` : '',
  ].filter(Boolean)

  return {
    activeTools,
    assetText,
    capabilityItems,
    enabledToolsets,
    pendingApprovalCount,
    pendingCount,
    pendingInteractionCount,
    primaryToolsets,
    protocolText,
    scope,
    scopeValue,
    targetLabel,
  }
}
