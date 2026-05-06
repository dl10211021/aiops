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

const SQL_DATABASE_SUB_TYPES = new Set([
  'mysql',
  'oracle',
  'postgresql',
  'mssql',
  'sqlserver',
  'tidb',
  'oceanbase',
  'kingbase',
  'dameng',
  'dm',
  'db2',
  'doris_fe',
  'greenplum',
  'greptime',
  'hive',
  'iotdb',
  'mariadb',
  'opengauss',
  'starrocks_fe',
  'vastbase',
  'xugu',
])

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
  const shouldShowSqlDatabaseParams = category === 'db' && SQL_DATABASE_SUB_TYPES.has(subType)

  return (
    <>
      {shouldShowSqlDatabaseParams && (
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
