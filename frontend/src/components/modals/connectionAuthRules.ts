import type { AssetSubType } from './connectionModalTypes'
import { NO_AUTH_PROTOCOLS } from './connectionParamDefinitions'

export const authModeFor = (id: string, protocol?: string, capability?: AssetSubType['capability']): AssetSubType['authMode'] => {
  const connector = capability?.connector
  const credentialFields = capability?.credential_fields || []
  if (['object_storage_api', 'kubernetes_api', 'ai_platform_api'].includes(connector || '')) return 'none'
  if (connector === 'native_kv') {
    if (credentialFields.includes('password') && !credentialFields.includes('username')) return 'password_only'
    if (!credentialFields.includes('username') && !credentialFields.includes('password')) return 'none'
  }
  if (id === 'redis') return 'password_only'
  if (protocol === 'snmp' || id === 'snmp') return 'custom_snmp'
  if (protocol && NO_AUTH_PROTOCOLS.has(protocol)) return 'none'
  return 'basic'
}

export const getAuthVisibility = (
  subTypes: Record<string, AssetSubType[]>,
  subType: string,
  category: string,
) => {
  const currentSubInfo = subTypes[category]?.find((item) => item.id === subType)
  const authMode = currentSubInfo?.authMode || 'basic'

  if (authMode === 'password_only') return { showUser: false, showPass: true }
  if (authMode === 'custom_snmp') return { showUser: false, showPass: false }
  if (authMode === 'none') return { showUser: false, showPass: false }
  return { showUser: true, showPass: true }
}

const DEFAULT_USERNAMES = new Set([
  '',
  'root',
  'admin',
  'administrator',
  'system',
  'postgres',
  'sa',
  'sysdba',
  'db2inst1',
])

const defaultUsernameFor = (category: string, subInfo: AssetSubType) => {
  if (subInfo.id === 'windows' || subInfo.asset_type === 'winrm') return 'Administrator'
  if (subInfo.id === 'oracle') return 'system'
  if (['dameng', 'dm', 'xugu'].includes(subInfo.id)) return 'SYSDBA'
  if (subInfo.id === 'db2') return 'db2inst1'
  if (subInfo.id === 'ipmi') return 'admin'
  if (subInfo.id === 'postgresql') return 'postgres'
  if (subInfo.id === 'mssql') return 'sa'
  if (subInfo.id === 'ldap') return ''
  if (['redis', 'memcached', 'snmp'].includes(subInfo.id) || subInfo.asset_type === 'snmp') return ''
  if (['http_api', 'redfish', 'k8s'].includes(subInfo.asset_type)) return ''
  if (category === 'db') return 'root'
  if (category === 'network') return 'admin'
  return 'root'
}

export const usernameForSelection = (currentUsername: string, category: string, subInfo: AssetSubType) =>
  DEFAULT_USERNAMES.has(String(currentUsername || '').trim().toLowerCase())
    ? defaultUsernameFor(category, subInfo)
    : currentUsername
