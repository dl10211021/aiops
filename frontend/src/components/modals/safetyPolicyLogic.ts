import type { SafetyPolicy, SafetyPolicyCategory } from '@/types'
import {
  HTTP_ACTION_RULE_OPTIONS,
  LINUX_ACTION_OPTIONS,
  MEMCACHED_ACTION_RULE_OPTIONS,
  MONGODB_ACTION_RULE_OPTIONS,
  NETWORK_ACTION_RULE_OPTIONS,
  REDIS_ACTION_RULE_OPTIONS,
  SQL_ACTION_RULE_OPTIONS,
  WINDOWS_ACTION_OPTIONS,
} from './safetyPolicyShared'
import type { CategoryKey, DomainDefinition } from './safetyPolicyShared'

export function categoryCount(category: SafetyPolicyCategory | undefined) {
  if (!category) return 0
  return [
    category.approval_patterns,
    category.approval_commands,
    category.approval_methods,
    category.readonly_block_patterns,
    category.readonly_block_commands,
    category.readonly_block_methods,
    category.hard_block_substrings,
  ].reduce((total, value) => total + (value?.length || 0), 0)
}

export function resolveCategory(domain: DomainDefinition, platform: string): CategoryKey {
  const normalized = platform.toLowerCase()
  if (normalized.includes('windows') || normalized.includes('hyper-v')) return 'windows'
  if (normalized.includes('redis')) return 'redis'
  if (normalized.includes('memcached')) return 'memcached'
  if (normalized.includes('mongo')) return 'mongodb'
  if (normalized.includes('switch') || normalized.includes('router') || normalized.includes('firewall')) return 'network'
  if (['mysql', 'postgresql', 'oracle', 'sql server', 'elasticsearch'].some((item) => normalized.includes(item))) return 'sql'
  return domain.category
}

export function resolveToolName(domain: DomainDefinition, platform: string) {
  const normalized = platform.toLowerCase()
  if (normalized.includes('windows') || normalized.includes('hyper-v')) return 'winrm_execute_command'
  if (normalized.includes('redis')) return 'redis_execute_command'
  if (normalized.includes('memcached')) return 'memcached_execute_command'
  if (normalized.includes('mongo')) return 'mongodb_find'
  if (domain.id === 'database') return 'db_execute_query'
  if (domain.id === 'network') return 'network_cli_execute_command'
  if (domain.id === 'cloudnative' && normalized.includes('kubernetes')) return 'k8s_api_request'
  if (domain.id === 'virtualization') return 'virtualization_api_request'
  if (domain.id === 'middleware') return 'middleware_api_request'
  if (domain.id === 'bigdata') return 'bigdata_api_request'
  if (domain.id === 'storage') return 'storage_api_request'
  if (domain.id === 'cicd') return 'cicd_api_request'
  if (domain.id === 'ai') return 'ai_platform_api_request'
  if (domain.id === 'monitoring') return 'monitoring_api_query'
  if (domain.id === 'hardware') return 'http_api_request'
  if (domain.id === 'platform') return 'local_execute_script'
  return 'linux_execute_command'
}

export function actionRuleDomain(actionId: string, fallback: CategoryKey) {
  if (actionId.startsWith('linux.')) return 'linux'
  if (actionId.startsWith('windows.') || actionId.startsWith('hyperv.')) return 'windows'
  if (actionId.startsWith('sql.')) return 'sql'
  if (actionId.startsWith('redis.')) return 'redis'
  if (actionId.startsWith('memcached.')) return 'memcached'
  if (actionId.startsWith('mongodb.')) return 'mongodb'
  if (actionId.startsWith('network.')) return 'network'
  return fallback
}

export function builtinActionIds(domain: string) {
  if (domain === 'linux') return new Set(LINUX_ACTION_OPTIONS.map((item) => item.id))
  if (domain === 'windows') return new Set(WINDOWS_ACTION_OPTIONS.map((item) => item.id))
  if (domain === 'sql') return new Set(SQL_ACTION_RULE_OPTIONS.map((item) => item.id))
  if (domain === 'redis') return new Set(REDIS_ACTION_RULE_OPTIONS.map((item) => item.id))
  if (domain === 'memcached') return new Set(MEMCACHED_ACTION_RULE_OPTIONS.map((item) => item.id))
  if (domain === 'mongodb') return new Set(MONGODB_ACTION_RULE_OPTIONS.map((item) => item.id))
  if (domain === 'network') return new Set(NETWORK_ACTION_RULE_OPTIONS.map((item) => item.id))
  if (domain === 'http') return new Set(HTTP_ACTION_RULE_OPTIONS.map((item) => item.id))
  return new Set<string>()
}

function httpActionPrefixes(domainId: string, platform: string) {
  const normalized = platform.toLowerCase()
  if (domainId === 'storage' || ['s3', 'minio', 'ceph rgw', 'oss', 'cos', 'obs'].some((item) => normalized.includes(item))) {
    return ['s3.']
  }
  if (normalized.includes('kubernetes') || normalized.includes('k8s')) return ['k8s.']
  if (domainId === 'virtualization') return ['virtualization.']
  if (domainId === 'middleware') {
    if (normalized.includes('nacos')) return ['nacos.']
    if (normalized.includes('kafka') || normalized.includes('rabbit') || normalized.includes('rocket')) return ['kafka.']
    return ['middleware.']
  }
  if (domainId === 'bigdata') return ['yarn.', 'bigdata.']
  if (domainId === 'cicd') {
    if (normalized.includes('argo')) return ['argocd.']
    if (normalized.includes('nexus') || normalized.includes('artifactory')) return ['artifact.']
    return ['cicd.', 'argocd.', 'artifact.']
  }
  if (domainId === 'ai') {
    if (normalized.includes('mlflow')) return ['mlflow.']
    return ['ai.', 'mlflow.']
  }
  if (domainId === 'monitoring') return ['monitoring.', 'alertmanager.']
  return []
}

function httpActionOptionsForPlatform(domainId: string, platform: string) {
  const prefixes = httpActionPrefixes(domainId, platform)
  if (!prefixes.length) return []
  return HTTP_ACTION_RULE_OPTIONS.filter((action) => prefixes.some((prefix) => action.id.startsWith(prefix)))
}

export function actionPolicyForCategory(activeCategory: CategoryKey, selectedPlatform: string, domainId: string) {
  const httpActionOptions = activeCategory === 'http'
    ? httpActionOptionsForPlatform(domainId, selectedPlatform)
    : []

  if (activeCategory === 'linux') {
    return {
      domain: 'linux',
      title: 'Linux 动作策略',
      description: '优先按动作处理，不需要写命令或正则。系统会把命令识别为“读取日志、查看服务、重启服务、主动网络访问”等动作。',
      options: LINUX_ACTION_OPTIONS,
    }
  }
  if (activeCategory === 'windows') {
    return {
      domain: 'windows',
      title: 'Windows / WinRM 动作策略',
      description: '优先按 PowerShell/CMD 动作处理。查询系统、服务、事件日志默认允许；服务变更、文件写入、注册表、防火墙、Hyper-V 变更进入审批或禁止。',
      options: WINDOWS_ACTION_OPTIONS,
    }
  }
  if (activeCategory === 'redis') {
    return {
      domain: 'redis',
      title: 'Redis 动作策略',
      description: '按 Redis 命令语义处理。读取状态和 Key 默认允许，写入、删除、过期时间、配置、ACL、复制变更默认审批，清空库默认禁止。',
      options: REDIS_ACTION_RULE_OPTIONS,
    }
  }
  if (activeCategory === 'memcached') {
    return {
      domain: 'memcached',
      title: 'Memcached 动作策略',
      description: '按 Memcached 文本协议命令处理。version、stats、get/gets 默认允许，写入、删除、计数变更默认审批，flush_all 默认禁止。',
      options: MEMCACHED_ACTION_RULE_OPTIONS,
    }
  }
  if (activeCategory === 'mongodb') {
    return {
      domain: 'mongodb',
      title: 'MongoDB 动作策略',
      description: '按 MongoDB 操作语义处理。find 查询默认允许，聚合查询、写入、索引和实例管理默认审批，dropDatabase/dropCollection 默认禁止。',
      options: MONGODB_ACTION_RULE_OPTIONS,
    }
  }
  if (activeCategory === 'network') {
    return {
      domain: 'network',
      title: '网络设备动作策略',
      description: '按网络设备命令语义处理。查看接口、路由、版本默认允许；读取完整配置、进入配置模式、接口/路由/ACL/NAT 变更需要审批；重启或清空配置默认禁止。',
      options: NETWORK_ACTION_RULE_OPTIONS,
    }
  }
  if (activeCategory === 'sql') {
    return {
      domain: 'sql',
      title: '数据库 SQL 动作策略',
      description: '按 SQL 语义处理 Oracle、MySQL、PostgreSQL、SQL Server 等数据库操作。查询默认允许，写入和实例管理默认审批，高危删除默认禁止。',
      options: SQL_ACTION_RULE_OPTIONS,
    }
  }
  if (activeCategory === 'http' && httpActionOptions.length) {
    return {
      domain: 'http',
      title: `${selectedPlatform} 动作策略`,
      description: '仅显示当前平台可识别的业务动作。高危删除默认禁止，生产变更默认审批；未覆盖动作可在下方加入自定义动作 ID。',
      options: httpActionOptions,
    }
  }
  return null
}

export function calculatePolicyTotals(policy: SafetyPolicy | null) {
  const categories = policy?.categories || {}
  let action = 0
  let advanced = policy?.rules?.length || 0
  Object.values(categories).forEach((item) => {
    advanced += categoryCount(item)
  })
  Object.values(policy?.action_rules || {}).forEach((rules) => {
    action += Object.keys(rules || {}).length
  })
  return { action, advanced, networkEnabled: Boolean(policy?.network_boundary?.enabled) }
}
