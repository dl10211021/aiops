import {
  ASSET_TYPE_LABELS,
  CATEGORY_LABELS,
  PROTOCOL_LABELS,
  STATUS_LABELS,
  TOOL_LABELS,
  TOOLSET_LABELS,
} from './assetDisplayMaps'

function normalizeDisplayKey(value?: string) {
  return String(value || '').trim().toLowerCase()
}

export function toolLabel(tool: string) {
  return TOOL_LABELS[tool] || tool
}

export function statusLabel(status: string) {
  return STATUS_LABELS[status] || status
}

export function protocolLabel(protocol?: string) {
  const key = normalizeDisplayKey(protocol)
  return PROTOCOL_LABELS[key] || (key ? key.toUpperCase() : '-')
}

export function assetTypeLabel(assetType?: string) {
  const key = normalizeDisplayKey(assetType)
  return ASSET_TYPE_LABELS[key] || (assetType || '-')
}

export function toolsetLabel(toolset?: string) {
  const key = normalizeDisplayKey(toolset)
  return TOOLSET_LABELS[key] || (toolset || '-')
}

export function categoryLabel(category?: string) {
  const key = normalizeDisplayKey(category)
  return CATEGORY_LABELS[key] || (category || '-')
}
