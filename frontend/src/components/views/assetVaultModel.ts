import type { Asset } from '@/types'
import type { AssetTypeDefinition } from '@/api/client'

export const CATEGORY_ORDER = [
  'os',
  'db',
  'container',
  'middleware',
  'bigdata',
  'monitor',
  'virtualization',
  'network',
  'storage',
  'oob',
  'service',
  'discovery',
  'security',
  'ai',
  'cicd',
  'custom',
  'other',
]

export const CONNECTOR_FALLBACK_ORDER = [
  'native_sql',
  'native_kv',
  'native_document',
  'database_http',
  'database_driver',
  'container_shell',
  'ssh_shell',
  'middleware_shell',
  'storage_shell',
  'virtualization_shell',
  'ai_compute_shell',
  'ssh_network_cli',
  'winrm_powershell',
  'http_api',
  'custom_api',
  'container_api',
  'middleware_api',
  'bigdata_api',
  'monitoring_api',
  'kubernetes_api',
  'virtualization_api',
  'network_api',
  'storage_api',
  'security_api',
  'redfish_api',
  'oob_api',
  'discovery_api',
  'service_probe',
  'ai_platform_api',
  'cicd_api',
  'snmp',
  'object_storage_api',
  'unknown',
]

const PROTOCOL_CONNECTOR_FALLBACK: Record<string, string> = {
  oracle: 'native_sql',
  mysql: 'native_sql',
  postgresql: 'native_sql',
  mssql: 'native_sql',
  db2: 'database_jdbc',
  dameng: 'database_jdbc',
  xugu: 'database_jdbc',
  hive: 'database_jdbc',
  iotdb: 'database_jdbc',
  clickhouse: 'database_http',
  elasticsearch: 'database_http',
  nebula_graph: 'database_http',
  redis: 'native_kv',
  memcached: 'native_kv',
  mongodb: 'native_document',
  ssh: 'ssh_shell',
  winrm: 'winrm_powershell',
  http_api: 'http_api',
  http: 'service_probe',
  tls: 'service_probe',
  websocket: 'service_probe',
  tcp: 'service_probe',
  udp: 'service_probe',
  icmp: 'service_probe',
  ftp: 'service_probe',
  smtp: 'service_probe',
  pop3: 'service_probe',
  imap: 'service_probe',
  mqtt: 'service_probe',
  ntp: 'service_probe',
  modbus: 'service_probe',
  s7: 'service_probe',
  registry: 'service_probe',
  dns: 'service_probe',
  ipmi: 'service_probe',
  ldap: 'service_probe',
  jmx: 'service_probe',
  kafka: 'service_probe',
  k8s: 'kubernetes_api',
  vmware: 'virtualization_api',
  openstack: 'virtualization_api',
  proxmox: 'virtualization_api',
  zstack: 'virtualization_api',
  s3: 'object_storage_api',
  minio: 'object_storage_api',
  backup: 'storage_api',
  redfish: 'redfish_api',
  snmp: 'snmp',
  virtual: 'unknown',
}

const PROTOCOL_BADGE_TONES: Record<string, string> = {
  ssh: 'bg-blue-500/20 text-blue-400',
  mysql: 'bg-purple-500/20 text-purple-400',
  oracle: 'bg-purple-500/20 text-purple-400',
  postgresql: 'bg-purple-500/20 text-purple-400',
  mssql: 'bg-purple-500/20 text-purple-400',
  db2: 'bg-purple-500/20 text-purple-400',
  dameng: 'bg-purple-500/20 text-purple-400',
  xugu: 'bg-purple-500/20 text-purple-400',
  hive: 'bg-purple-500/20 text-purple-400',
  iotdb: 'bg-purple-500/20 text-purple-400',
  clickhouse: 'bg-purple-500/20 text-purple-400',
  elasticsearch: 'bg-purple-500/20 text-purple-400',
  nebula_graph: 'bg-purple-500/20 text-purple-400',
  redis: 'bg-red-500/20 text-red-400',
  mongodb: 'bg-emerald-500/20 text-emerald-400',
  http_api: 'bg-green-500/20 text-green-400',
  vmware: 'bg-cyan-500/20 text-cyan-400',
  openstack: 'bg-cyan-500/20 text-cyan-400',
  proxmox: 'bg-cyan-500/20 text-cyan-400',
  zstack: 'bg-cyan-500/20 text-cyan-400',
  s3: 'bg-emerald-500/20 text-emerald-300',
  minio: 'bg-emerald-500/20 text-emerald-300',
  backup: 'bg-emerald-500/20 text-emerald-300',
  winrm: 'bg-orange-500/20 text-orange-400',
  k8s: 'bg-cyan-500/20 text-cyan-400',
  redfish: 'bg-amber-500/20 text-amber-400',
  snmp: 'bg-slate-500/20 text-slate-300',
  virtual: 'bg-ops-accent/15 text-ops-accent',
}

export function normalizeFilterValue(value: unknown, fallback = 'unknown') {
  const text = String(value || '').trim().toLowerCase()
  return text || fallback
}

export function orderIndex(order: string[], id: string) {
  const idx = order.indexOf(id)
  return idx >= 0 ? idx : order.length
}

export function connectorForProtocol(protocol?: string) {
  return PROTOCOL_CONNECTOR_FALLBACK[normalizeFilterValue(protocol)] || 'unknown'
}

export function connectorForType(
  catalogTypeById: Map<string, AssetTypeDefinition>,
  assetType?: string,
  protocol?: string,
) {
  return catalogTypeById.get(normalizeFilterValue(assetType))?.capability?.connector || connectorForProtocol(protocol)
}

export function assetTypeKey(asset: Asset) {
  return normalizeFilterValue(asset.asset_type || asset.extra_args?.sub_type)
}

export function protocolBadgeTone(protocol: string) {
  return PROTOCOL_BADGE_TONES[protocol] || 'bg-ops-surface1 text-ops-subtext'
}
