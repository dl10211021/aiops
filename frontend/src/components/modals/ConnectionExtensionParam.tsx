import type { AssetParamDefinition } from '@/types'

const PARAM_HELP_TEXT: Record<string, string> = {
  endpoint_url: '对象存储访问入口，例如 https://s3.example.com 或 http://minio.local:9000。填写后主机地址可留空。',
  access_key: '对象存储访问密钥 ID，对应 S3/MinIO 的 Access Key。',
  ['secret_key']: '对象存储访问密钥 Secret，会按敏感字段保存和展示。',
  bucket: '默认操作的桶名，可留空，后续会话里再指定。',
  region: '云厂商区域，例如 cn-east-1、us-east-1；私有 MinIO 可留空。',
  use_ssl: '启用后默认按 HTTPS 访问，私有测试环境可关闭。',
  base_url: '平台 API 的基础地址，例如 https://api.example.com/v1。填写后主机地址可从这里自动识别。',
  api_token: '平台 API Token 或 Bearer Token，会按敏感字段保存。',
  model: '默认模型名，可留空，AI 会话中也可以临时指定。',
  namespace: 'Kubernetes 默认命名空间，常用 default、prod、kube-system。',
  context: 'Kubeconfig 中的 context 名称，多集群配置时使用。',
  ['bearer_token']: 'ServiceAccount Token，建议使用只读或最小权限账号。',
  kubeconfig: '完整 kubeconfig 内容，适合多集群或证书认证场景。',
  verify_ssl: '校验证书链。自签证书环境如连接失败，可临时关闭。',
  snmp_version: 'v2c 简单易用，v3 支持用户名、认证和加密，生产环境优先 v3。',
  community_string: 'SNMP v2c 的 Community 字符串，常见默认值 public 不建议用于生产。',
  v3_auth_user: 'SNMP v3 认证用户名。',
  v3_auth_pass: 'SNMP v3 认证密码。',
  v3_priv_pass: 'SNMP v3 加密密码。',
  oid_profile: 'OID 模板名称，可按厂商或设备类型填写，例如 huawei-switch、synology-nas。',
  jdbc_jar: 'JDBC 驱动 jar 路径。可填绝对路径，也可以使用后端环境变量统一配置。',
  jdbc_url: '高级选项，留空时系统按主机、端口和数据库名自动生成。',
  jdbc_driver_class: '高级选项，留空时使用内置驱动类。',
  db_name: '数据库名、Schema 或连接库名，不确定时可先留空再做只读验证。',
}

const isSensitiveParam = (field: string, label: string) =>
  /(pass|password|secret|token|key|credential|access.?key|secret.?key)/i.test(`${field} ${label}`)

interface ConnectionExtensionParamProps {
  param: AssetParamDefinition
  value: unknown
  onChange: (field: string, value: unknown) => void
}

export default function ConnectionExtensionParam({
  param,
  value,
  onChange,
}: ConnectionExtensionParamProps) {
  const label = `${param.label}${param.required ? ' *' : ''}`
  const help = PARAM_HELP_TEXT[param.field]
  const commonClass = 'w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent'
  const setValue = (next: unknown) => onChange(param.field, next)

  if (param.options?.length || ['radio', 'select'].includes(param.type)) {
    return (
      <div>
        <label className="text-xs text-ops-subtext">{label}</label>
        <select
          value={value === undefined ? '' : String(value)}
          onChange={(event) => setValue(event.target.value)}
          className={`${commonClass} appearance-none`}
        >
          {!param.required && <option value="">未设置</option>}
          {(param.options || []).map((option) => (
            <option key={String(option.value)} value={String(option.value)}>{option.label}</option>
          ))}
        </select>
        {help && <p className="mt-1 text-[11px] leading-4 text-ops-overlay">{help}</p>}
      </div>
    )
  }

  if (param.type === 'boolean') {
    return (
      <label className="mt-6 flex cursor-pointer items-center gap-2 text-sm text-ops-subtext hover:text-ops-text">
        <input
          type="checkbox"
          checked={!!value}
          onChange={(event) => setValue(event.target.checked)}
          className="accent-ops-accent"
        />
        {label}
        {help && <span className="text-[11px] text-ops-overlay">{help}</span>}
      </label>
    )
  }

  if (['textarea', 'json', 'array', 'map', 'key-value'].includes(param.type)) {
    return (
      <div className="col-span-2">
        <label className="text-xs text-ops-subtext">{label}</label>
        <textarea
          value={value === undefined ? '' : String(value)}
          onChange={(event) => setValue(event.target.value)}
          placeholder={param.placeholder || ''}
          className={`${commonClass} min-h-20 font-mono text-xs`}
        />
        {help && <p className="mt-1 text-[11px] leading-4 text-ops-overlay">{help}</p>}
      </div>
    )
  }

  return (
    <div>
      <label className="text-xs text-ops-subtext">{label}</label>
      <input
        type={isSensitiveParam(param.field, param.label) ? 'password' : param.type === 'number' ? 'number' : 'text'}
        value={value === undefined ? '' : String(value)}
        onChange={(event) => setValue(param.type === 'number' ? Number(event.target.value) : event.target.value)}
        placeholder={param.placeholder || ''}
        className={commonClass}
      />
      {help && <p className="mt-1 text-[11px] leading-4 text-ops-overlay">{help}</p>}
    </div>
  )
}
