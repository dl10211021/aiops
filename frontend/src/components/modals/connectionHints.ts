import type { AssetSubType } from './connectionModalTypes'

export const connectionHintFor = (subInfo?: AssetSubType, protocol = '') => {
  const connector = subInfo?.capability?.connector || ''
  if (connector === 'object_storage_api') {
    return '对象存储优先填写 Endpoint URL、Access Key、Secret Key；主机地址可以从 Endpoint 自动识别。'
  }
  if (connector === 'kubernetes_api') {
    return 'Kubernetes 可以使用 Bearer Token 或 Kubeconfig，建议使用只读 ServiceAccount。'
  }
  if (connector === 'ai_platform_api') {
    return 'AI 平台通常只需要 Base URL 和 API Key，主机地址可由 Base URL 自动识别。'
  }
  if (protocol === 'snmp') {
    return 'SNMP v2c 填 Community 即可；生产设备建议使用 v3 的认证和加密参数。'
  }
  if (connector === 'database_jdbc') {
    return 'JDBC 类数据库需要对应厂商驱动 jar；可在资产参数填写路径，也可在部署环境用变量统一配置。'
  }
  if (connector === 'database_http') {
    return '数据库接口类资产通过自身 HTTP/API 管理面接入，适合只读查询、健康检查和节点状态分析。'
  }
  return ''
}
