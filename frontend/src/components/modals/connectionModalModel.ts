import type { AssetAccessProtocol, AssetParamDefinition } from '@/types'
import type {
  AssetCategoryOption,
  AssetSubType,
  DatabaseDriverCapability,
} from './connectionModalHelpers'
import {
  CORE_ASSET_PARAM_FIELDS,
  DATABASE_DEDICATED_PARAM_FIELDS,
  DEDICATED_HTTP_CONNECTORS,
  ENDPOINT_BACKED_CONNECTORS,
  HTTP_BACKED_PROTOCOLS,
  HTTP_DEDICATED_PARAM_FIELDS,
  K8S_DEDICATED_PARAM_FIELDS,
  SNMP_DEDICATED_PARAM_FIELDS,
  connectionHintFor,
  getAuthVisibility,
  groupOptions,
  groupParamDefinitions,
  parseHostFromUrl,
} from './connectionModalHelpers'
import type { ConnectionFormState } from './connectionModalState'

const COMMON_ASSET_TYPE_IDS = new Set([
  'linux',
  'windows',
  'mysql',
  'oracle',
  'postgresql',
  'redis',
  'mongodb',
  'elasticsearch',
  'docker',
  'k8s',
  'nginx',
  'tomcat',
  'kafka',
  'vmware',
  'zstack',
  'switch',
  'firewall',
  'ceph',
  'nas',
  's3',
  'prometheus',
  'grafana',
  'zabbix',
  'elastic_stack',
  'graylog',
  'loki',
  'website',
  'port',
  'ping',
])

export function getProtocolForSubType(
  assetSubTypes: Record<string, AssetSubType[]>,
  category: string,
  subType: string,
) {
  return assetSubTypes[category]?.find((item) => item.id === subType)?.asset_type || subType
}

export function operationAccessProtocols(subInfo?: AssetSubType): AssetAccessProtocol[] {
  const protocols = (subInfo?.access_protocols || []).filter((item) => (item.purpose || 'operation') === 'operation')
  if (protocols.length > 0) return protocols
  if (!subInfo) return []
  return [{
    protocol: subInfo.asset_type,
    label: subInfo.asset_type.toUpperCase(),
    purpose: 'operation',
    purpose_label: '运维接入',
    role: 'default',
    role_label: '默认',
    source: '资产类型默认协议',
    default_port: subInfo.defaultPort,
    is_default: true,
    supported: true,
  }]
}

function resolveCurrentProtocol(subInfo: AssetSubType | undefined, requestedProtocol: string) {
  const protocols = operationAccessProtocols(subInfo)
  if (requestedProtocol && protocols.some((item) => item.protocol === requestedProtocol)) {
    return requestedProtocol
  }
  return protocols.find((item) => item.is_default)?.protocol || subInfo?.asset_type || requestedProtocol
}

export function buildConnectionExtraArgs(
  category: string,
  subInfo: AssetSubType,
  oracleThickDefaults: () => Record<string, unknown>,
) {
  return {
    ...defaultsFromParams(subInfo.params || []),
    category,
    sub_type: subInfo.id,
    ...(category === 'db' ? { db_type: subInfo.id } : {}),
    ...(subInfo.id === 'oracle' ? { oracle_connect_type: 'sid', ...oracleThickDefaults() } : {}),
  }
}

export function buildConnectionModalModel({
  assetCatalogMode,
  assetCategories,
  assetSubTypes,
  assetTypeSearch,
  databaseDrivers,
  form,
}: {
  assetCatalogMode: 'common' | 'all'
  assetCategories: AssetCategoryOption[]
  assetSubTypes: Record<string, AssetSubType[]>
  assetTypeSearch: string
  databaseDrivers: Record<string, DatabaseDriverCapability>
  form: ConnectionFormState
}) {
  const selectedSubInfo = assetSubTypes[form.category]?.find((item) => item.id === form.sub_type)
  const accessProtocolOptions = operationAccessProtocols(selectedSubInfo)
  const currentProtocol = resolveCurrentProtocol(selectedSubInfo, form.protocol)
  const currentAccessProtocol = accessProtocolOptions.find((item) => item.protocol === currentProtocol)
  const selectedConnectorLabel = currentAccessProtocol?.label || selectedSubInfo?.capability?.connector_group?.label || selectedSubInfo?.capability?.connector || currentProtocol
  const selectedConnectorGroup = currentAccessProtocol?.purpose_label || selectedSubInfo?.capability?.connector_group?.group || '连接方式'
  const selectedMaturity = selectedSubInfo?.capability?.maturity || 'generic'
  const selectedTools = toolsForCurrentProtocol(form.category, currentProtocol, selectedSubInfo)
  const selectedToolDetails = selectedSubInfo?.capability?.tool_details?.length
    ? selectedSubInfo.capability.tool_details
    : selectedTools.map((name) => ({ name }))
  const selectedConnector = selectedSubInfo?.capability?.connector || ''
  const selectedConnectionHint = connectionHintFor(selectedSubInfo, currentProtocol)
  const isEndpointBackedAsset = ENDPOINT_BACKED_CONNECTORS.has(selectedConnector)
  const shouldShowGenericHttpParams =
    (['http_api', 'redfish'].includes(currentProtocol) || HTTP_BACKED_PROTOCOLS.has(currentProtocol))
    && !DEDICATED_HTTP_CONNECTORS.has(selectedConnector)
  const inferredHostFromEndpoint = parseHostFromUrl(
    form.extra_args.endpoint_url || form.extra_args.base_url || form.extra_args.cluster_url
  )
  const resolveAssetHost = (isGlobal = false) => {
    if (isGlobal) return 'global'
    return String(form.host || '').trim() || (isEndpointBackedAsset ? inferredHostFromEndpoint : '')
  }
  const missingHostMessage = isEndpointBackedAsset
    ? '请输入主机地址，或在连接参数中填写 Endpoint/Base URL'
    : '请输入主机地址'
  const isKubernetesAsset = ['k8s', 'kubernetes'].includes(form.sub_type) || currentProtocol === 'k8s'
  const categoryGroups = groupOptions(assetCategories, (item) => item.group || '其它')
  const subTypeOptions = assetSubTypes[form.category] || []
  const normalizedAssetTypeSearch = assetTypeSearch.trim().toLowerCase()
  const commonSubTypeOptions = subTypeOptions.filter((item) => COMMON_ASSET_TYPE_IDS.has(item.id))
  const catalogModeSubTypeOptions =
    assetCatalogMode === 'common' && commonSubTypeOptions.length > 0
      ? commonSubTypeOptions
      : subTypeOptions
  const searchSourceOptions = normalizedAssetTypeSearch ? subTypeOptions : catalogModeSubTypeOptions
  const searchedSubTypeOptions = normalizedAssetTypeSearch
    ? searchSourceOptions.filter((item) => {
        const accessText = (item.access_protocols || []).map((protocol) => `${protocol.protocol} ${protocol.label}`).join(' ')
        const haystack = `${item.id} ${item.label} ${item.asset_type} ${accessText} ${item.capability?.connector_group?.label || ''}`.toLowerCase()
        return haystack.includes(normalizedAssetTypeSearch)
      })
    : searchSourceOptions
  const filteredSubTypeOptions = selectedSubInfo && !searchedSubTypeOptions.some((item) => item.id === selectedSubInfo.id)
    ? [selectedSubInfo, ...searchedSubTypeOptions]
    : searchedSubTypeOptions
  const subTypeGroups = groupOptions(filteredSubTypeOptions, (item) => item.capability?.connector_group?.label || item.asset_type.toUpperCase())
  const databaseDriverInfo = form.category === 'db' ? databaseDrivers[databaseDriverKey(form, currentProtocol)] : undefined
  const authVisibility = getAuthVisibility(assetSubTypes, form.sub_type, form.category)
  const extensionParams = (selectedSubInfo?.params || []).filter((param) => {
    if (CORE_ASSET_PARAM_FIELDS.has(param.field)) return false
    if (form.category === 'db' && DATABASE_DEDICATED_PARAM_FIELDS.has(param.field)) return false
    if (isKubernetesAsset && K8S_DEDICATED_PARAM_FIELDS.has(param.field)) return false
    if (currentProtocol === 'snmp' && SNMP_DEDICATED_PARAM_FIELDS.has(param.field)) return false
    if (shouldShowGenericHttpParams && HTTP_DEDICATED_PARAM_FIELDS.has(param.field)) return false
    return true
  })
  const visibleExtensionParams = extensionParams.filter((param) => shouldShowParam(param, form.extra_args))
  const extensionParamGroups = groupParamDefinitions(visibleExtensionParams)

  return {
    authVisibility,
    accessProtocolOptions,
    categoryGroups,
    currentAccessProtocol,
    currentProtocol,
    databaseDriverInfo,
    extensionParamGroups,
    filteredSubTypeOptions,
    inferredHostFromEndpoint,
    isEndpointBackedAsset,
    isKubernetesAsset,
    missingHostMessage,
    normalizedAssetTypeSearch,
    resolveAssetHost,
    searchedSubTypeOptions,
    selectedConnectionHint,
    selectedConnectorGroup,
    selectedConnectorLabel,
    selectedMaturity,
    selectedSubInfo,
    selectedToolDetails,
    selectedTools,
    shouldShowGenericHttpParams,
    subTypeGroups,
    subTypeOptions,
    catalogModeSubTypeOptions,
  }
}

function toolsForCurrentProtocol(category: string, currentProtocol: string, subInfo?: AssetSubType) {
  const defaultTools = subInfo?.capability?.tools || subInfo?.capability?.connector_group?.tools || []
  if (currentProtocol === subInfo?.asset_type) return defaultTools
  if (currentProtocol === 'ssh') {
    if (category === 'network') return ['network_cli_execute_command']
    if (category === 'storage') return ['storage_execute_command']
    if (category === 'middleware') return ['middleware_execute_command']
    if (category === 'container') return ['container_execute_command']
    return ['linux_execute_command']
  }
  if (currentProtocol === 'http_api') {
    if (category === 'network') return ['network_api_request']
    if (category === 'monitor') return ['monitoring_api_query']
    if (category === 'log') return ['monitoring_api_query']
    if (category === 'container') return ['container_api_request']
    if (category === 'middleware') return ['middleware_api_request']
    if (category === 'bigdata') return ['bigdata_api_request']
    if (category === 'security') return ['security_api_request']
    if (category === 'oob') return ['oob_api_request']
    if (category === 'discovery') return ['discovery_api_request']
    if (category === 'ai') return ['ai_platform_api_request']
    if (category === 'cicd') return ['cicd_api_request']
    return ['http_api_request']
  }
  return defaultTools
}

function defaultsFromParams(params: AssetParamDefinition[] = []) {
  const defaults: Record<string, unknown> = {}
  params.forEach((param) => {
    if (CORE_ASSET_PARAM_FIELDS.has(param.field)) return
    if (param.defaultValue !== undefined) {
      defaults[param.field] = param.defaultValue
    } else if (param.required && param.options?.length) {
      defaults[param.field] = param.options[0].value
    } else if (param.required && param.type === 'boolean') {
      defaults[param.field] = false
    }
  })
  return defaults
}

function databaseDriverKey(form: ConnectionFormState, currentProtocol: string) {
  const key = String(form.extra_args.db_type || form.sub_type || currentProtocol).toLowerCase()
  if (['tidb', 'oceanbase'].includes(key)) return 'mysql'
  if (['doris_fe', 'starrocks_fe', 'greptime'].includes(key)) return 'mysql'
  if (['kingbase', 'pg'].includes(key)) return 'postgresql'
  if (['sqlserver', 'sql_server'].includes(key)) return 'mssql'
  return key
}

function shouldShowParam(param: AssetParamDefinition, extraArgs: Record<string, unknown>) {
  if (!param.depend) return true
  return Object.entries(param.depend).every(([field, allowed]) => {
    const current = extraArgs[field]
    return allowed.map(String).includes(String(current))
  })
}
