import ConnectionDatabaseDriverStatus from './ConnectionDatabaseDriverStatus'
import ConnectionDatabaseParams from './ConnectionDatabaseParams'
import ConnectionHttpParams from './ConnectionHttpParams'
import ConnectionKubernetesParams from './ConnectionKubernetesParams'
import ConnectionSnmpParams from './ConnectionSnmpParams'
import type { DatabaseDriverCapability, OracleClientConfig } from './connectionModalHelpers'

interface ConnectionDedicatedParamsSectionProps {
  category: string
  currentProtocol: string
  databaseDriverInfo?: DatabaseDriverCapability
  extraArgs: Record<string, unknown>
  isKubernetesAsset: boolean
  oracleClientConfig: OracleClientConfig | null
  port: number
  selectedConnectorLabel: string
  shouldShowGenericHttpParams: boolean
  subType: string
  onExtraArgChange: (field: string, value: unknown) => void
  onExtraArgsChange: (patch: Record<string, unknown>) => void
  oracleThickDefaults: () => Record<string, unknown>
}

export default function ConnectionDedicatedParamsSection({
  category,
  currentProtocol,
  databaseDriverInfo,
  extraArgs,
  isKubernetesAsset,
  oracleClientConfig,
  port,
  selectedConnectorLabel,
  shouldShowGenericHttpParams,
  subType,
  onExtraArgChange,
  onExtraArgsChange,
  oracleThickDefaults,
}: ConnectionDedicatedParamsSectionProps) {
  return (
    <>
      {category === 'db' && (
        <ConnectionDatabaseParams
          extraArgs={extraArgs}
          oracleClientConfig={oracleClientConfig}
          subType={subType}
          onExtraArgChange={onExtraArgChange}
          onExtraArgsChange={onExtraArgsChange}
          oracleThickDefaults={oracleThickDefaults}
        />
      )}

      {category === 'db' && databaseDriverInfo && (
        <ConnectionDatabaseDriverStatus
          driver={databaseDriverInfo}
          isOracle={subType === 'oracle'}
          selectedConnectorLabel={selectedConnectorLabel}
        />
      )}

      {isKubernetesAsset && (
        <ConnectionKubernetesParams
          extraArgs={extraArgs}
          onExtraArgChange={onExtraArgChange}
        />
      )}

      {currentProtocol === 'snmp' && (
        <ConnectionSnmpParams
          extraArgs={extraArgs}
          onExtraArgChange={onExtraArgChange}
        />
      )}

      {shouldShowGenericHttpParams && (
        <ConnectionHttpParams
          extraArgs={extraArgs}
          port={port}
          onExtraArgChange={onExtraArgChange}
        />
      )}
    </>
  )
}
