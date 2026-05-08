import type { AssetParamDefinition } from '@/types'
import ConnectionExtensionParam from './ConnectionExtensionParam'
import { MATURITY_LABELS } from './connectionModalHelpers'

interface ConnectionParamGroup {
  group: string
  items: AssetParamDefinition[]
}

interface ConnectionAdvancedParamsSectionProps {
  connectorLabel?: string
  extraArgs: Record<string, unknown>
  maturity?: string
  paramGroups: ConnectionParamGroup[]
  onParamChange: (field: string, value: unknown) => void
}

export default function ConnectionAdvancedParamsSection({
  connectorLabel,
  extraArgs,
  maturity,
  paramGroups,
  onParamChange,
}: ConnectionAdvancedParamsSectionProps) {
  if (paramGroups.length === 0) {
    return null
  }

  const maturityLabel = maturity ? MATURITY_LABELS[maturity] || maturity : ''

  return (
    <div className="ops-data-panel p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-ops-text">连接参数</div>
        {connectorLabel && (
          <div className="text-[10px] text-ops-subtext">
            {connectorLabel}
            {maturityLabel && ` · ${maturityLabel}`}
          </div>
        )}
      </div>
      <div className="space-y-3">
        {paramGroups.map((group) => (
          <div key={group.group} className="ops-data-panel p-3">
            <div className="mb-2 text-[11px] font-semibold text-ops-subtext">{group.group}</div>
            <div className="grid grid-cols-2 gap-3">
              {group.items.map((param) => (
                <ConnectionExtensionParam
                  key={param.field}
                  param={param}
                  value={extraArgs[param.field]}
                  onChange={onParamChange}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
