import type { AssetParamDefinition } from '@/types'
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

export function getProtocolForSubType(
  assetSubTypes: Record<string, AssetSubType[]>,
  category: string,
  subType: string,
) {
  return assetSubTypes[category]?.find((item) => item.id === subType)?.asset_type || subType
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
  assetCategories,
  assetSubTypes,
  assetTypeSearch,
  databaseDrivers,
  form,
}: {
  assetCategories: AssetCategoryOption[]
  assetSubTypes: Record<string, AssetSubType[]>
  assetTypeSearch: string
  databaseDrivers: Record<string, DatabaseDriverCapability>
  form: ConnectionFormState
}) {
  const currentProtocol = getProtocolForSubType(assetSubTypes, form.category, form.sub_type)
  const selectedSubInfo = assetSubTypes[form.category]?.find((item) => item.id === form.sub_type)
  const selectedConnectorLabel = selectedSubInfo?.capability?.connector_group?.label || selectedSubInfo?.capability?.connector || currentProtocol
  const selectedConnectorGroup = selectedSubInfo?.capability?.connector_group?.group || '连接方式'
  const selectedMaturity = selectedSubInfo?.capability?.maturity || 'generic'
  const selectedTools = selectedSubInfo?.capability?.tools || selectedSubInfo?.capability?.connector_group?.tools || []
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
  const searchedSubTypeOptions = normalizedAssetTypeSearch
    ? subTypeOptions.filter((item) => {
        const haystack = `${item.id} ${item.label} ${item.asset_type} ${item.capability?.connector_group?.label || ''}`.toLowerCase()
        return haystack.includes(normalizedAssetTypeSearch)
      })
    : subTypeOptions
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
    categoryGroups,
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
  }
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
