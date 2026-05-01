import type { AssetParamDefinition } from '@/types'

export const CORE_ASSET_PARAM_FIELDS = new Set([
  'host',
  'port',
  'username',
  'password',
  'database',
])

export const SNMP_DEDICATED_PARAM_FIELDS = new Set([
  'snmpVersion',
  'community',
  'username',
  'contextName',
  'authPassphrase',
  'authPasswordEncryption',
  'privPassphrase',
  'privPasswordEncryption',
  'snmp_version',
  'community_string',
  'v3_auth_user',
  'v3_auth_protocol',
  'v3_auth_pass',
  'v3_priv_protocol',
  'v3_priv_pass',
])

export const HTTP_DEDICATED_PARAM_FIELDS = new Set([
  'scheme',
  'base_path',
  'api_token',
])

export const DATABASE_DEDICATED_PARAM_FIELDS = new Set([
  'database',
  'db_name',
  'use_ssl',
  'oracle_connect_type',
  'connect_type',
  'service_name',
  'sid',
  'tns_alias',
  'use_thick_mode',
  'oracle_client_lib_dir',
])

export const K8S_DEDICATED_PARAM_FIELDS = new Set([
  'bearer_token',
  'kubeconfig',
  'k8s_auth_type',
])

export const MATURITY_LABELS: Record<string, string> = {
  native: '原生可操作',
  generic: '通用接入',
  needs_adapter: '待补专用工具',
  driver_required: '需配置驱动',
}

export const FIELD_GROUP_LABELS: Record<string, string> = {
  mysql: 'MySQL 连接选项',
  postgresql: 'PostgreSQL 连接选项',
  mssql: 'SQL Server 连接选项',
  oracle: 'Oracle 连接选项',
  jdbc: 'JDBC 驱动配置',
  redis: 'Redis 连接选项',
  redis_cluster: 'Redis Cluster',
  redis_sentinel: 'Redis Sentinel',
  mongodb: 'MongoDB 连接选项',
  database_http: '数据库接口参数',
  http: 'HTTP 接口参数',
  snmp: 'SNMP 参数',
  k8s: 'Kubernetes 凭据',
  kubernetes: 'Kubernetes 凭据',
  object_storage: '对象存储凭据',
  openai: 'OpenAI 兼容接口',
  deepseek: 'DeepSeek 接口',
  ollama: 'Ollama 接口',
  lmstudio: 'LM Studio 接口',
  ai_compute: 'AI 算力主机',
  storage_api: '存储平台接口',
  virtualization: '虚拟化接口',
  openstack: 'OpenStack 参数',
  vmware: 'VMware 参数',
  proxmox: 'Proxmox 参数',
  zstack: 'ZStack 参数',
  service: '服务探测参数',
  service_probe: '服务探测参数',
  middleware_shell: '中间件主机参数',
  container: '容器运行时参数',
  ssh: 'SSH 参数',
}

export const HTTP_BACKED_PROTOCOLS = new Set([
  'http',
  'tls',
  'websocket',
  'clickhouse',
  'elasticsearch',
  'nebula_graph',
  'vmware',
  'openstack',
  'proxmox',
  'zstack',
  's3',
  'minio',
  'backup',
])

export const NO_AUTH_PROTOCOLS = new Set(['http', 'tls', 'websocket', 'tcp', 'udp', 'icmp', 'dns', 'ntp', 'modbus', 's7', 'registry'])
export const ENDPOINT_BACKED_CONNECTORS = new Set(['object_storage_api', 'ai_platform_api'])
export const DEDICATED_HTTP_CONNECTORS = new Set(['object_storage_api', 'ai_platform_api', 'kubernetes_api'])

export function groupOptions<T>(items: T[], groupFor: (item: T) => string) {
  const groups: Array<{ group: string; items: T[] }> = []
  items.forEach((item) => {
    const group = groupFor(item) || '其它'
    const existing = groups.find((entry) => entry.group === group)
    if (existing) {
      existing.items.push(item)
    } else {
      groups.push({ group, items: [item] })
    }
  })
  return groups
}

export function groupParamDefinitions(params: AssetParamDefinition[]) {
  return groupOptions(params, (param) => FIELD_GROUP_LABELS[param.group || ''] || param.group || '其它参数')
}

export function parseHostFromUrl(value?: unknown) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  try {
    const normalized = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`
    return new URL(normalized).hostname
  } catch {
    return ''
  }
}
