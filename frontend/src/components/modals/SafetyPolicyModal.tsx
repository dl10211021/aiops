import { useEffect, useMemo, useState } from 'react'
import { useStore } from '@/store'
import { getSafetyPolicy, testSafetyPolicy, updateSafetyPolicy } from '@/api/client'
import type { SafetyPolicy, SafetyPolicyCategory, SafetyPolicyRule, SafetyPolicyTestResult } from '@/types'

type CategoryKey = 'linux' | 'windows' | 'sql' | 'redis' | 'http' | 'network' | 'local' | 'skill_change'
type Decision = 'approval' | 'deny'
type MatcherType = 'contains' | 'prefix' | 'equals' | 'regex' | 'http_method' | 'platform_action'
type ListField =
  | 'approval_patterns'
  | 'readonly_block_patterns'
  | 'readonly_safe_roots'
  | 'approval_commands'
  | 'readonly_block_commands'
  | 'approval_methods'
  | 'readonly_block_methods'
  | 'hard_block_substrings'

type DomainDefinition = {
  id: string
  label: string
  icon: string
  category: CategoryKey
  platforms: string[]
  objects: string
  hint: string
  examples: Array<{ action: string; decision: 'allow' | 'approval' | 'deny'; example: string }>
}

const DOMAINS: DomainDefinition[] = [
  {
    id: 'os',
    label: '主机系统',
    icon: '主',
    category: 'linux',
    platforms: ['Linux', 'Windows', 'KVM Host'],
    objects: '服务、文件、进程、账号、系统配置',
    hint: '巡检和查询默认允许，重启、改配置、删文件进入审批，格式化和破坏性命令禁止执行。',
    examples: [
      { action: '查看系统状态', decision: 'allow', example: 'uptime / df -h / systemctl status' },
      { action: '重启服务', decision: 'approval', example: 'systemctl restart nginx' },
      { action: '格式化磁盘', decision: 'deny', example: 'mkfs.ext4 /dev/sda' },
    ],
  },
  {
    id: 'database',
    label: '数据库',
    icon: '数',
    category: 'sql',
    platforms: ['MySQL', 'PostgreSQL', 'Oracle', 'SQL Server', 'MongoDB', 'Redis', 'ElasticSearch'],
    objects: '库、表、索引、缓存 Key、集合',
    hint: '结构查询和状态查询允许，写入和结构变更需要审批，删库清库类动作禁止执行。',
    examples: [
      { action: '查询表结构', decision: 'allow', example: 'show create table orders' },
      { action: '修改数据', decision: 'approval', example: 'update orders set status = ...' },
      { action: '清空数据库', decision: 'deny', example: 'drop database prod' },
    ],
  },
  {
    id: 'cloudnative',
    label: '容器与云原生',
    icon: '容',
    category: 'http',
    platforms: ['Kubernetes', 'Docker', 'containerd', 'Harbor'],
    objects: 'Pod、Deployment、Namespace、镜像、Secret',
    hint: '查看资源和事件允许，扩缩容与重启需要审批，删除命名空间和敏感对象禁止执行。',
    examples: [
      { action: '查看 Pod', decision: 'allow', example: 'GET /api/v1/pods' },
      { action: '扩缩容 Deployment', decision: 'approval', example: 'PATCH /apis/apps/v1/deployments' },
      { action: '删除 Namespace', decision: 'deny', example: 'DELETE /api/v1/namespaces/prod' },
    ],
  },
  {
    id: 'virtualization',
    label: '虚拟化与私有云',
    icon: '虚',
    category: 'http',
    platforms: ['VMware', 'Proxmox', 'OpenStack', 'ZStack', 'Hyper-V'],
    objects: '虚拟机、宿主机、资源池、快照、卷',
    hint: '查询容量和虚拟机状态允许，重启、迁移、快照回滚需要审批，删除虚拟机和卷禁止执行。',
    examples: [
      { action: '查看虚拟机状态', decision: 'allow', example: 'GET /vms' },
      { action: '重启虚拟机', decision: 'approval', example: 'POST /vms/{id}/reboot' },
      { action: '删除虚拟机', decision: 'deny', example: 'DELETE /vms/{id}' },
    ],
  },
  {
    id: 'network',
    label: '网络与安全设备',
    icon: '网',
    category: 'network',
    platforms: ['Switch', 'Router', 'Firewall', 'F5', 'A10', 'WAF', 'VPN'],
    objects: '接口、路由、ACL、NAT、负载均衡策略',
    hint: 'show/display/ping 允许，进入配置模式和保存配置需要审批，清空配置禁止执行。',
    examples: [
      { action: '查看接口状态', decision: 'allow', example: 'display interface brief' },
      { action: '下发配置', decision: 'approval', example: 'system-view / configure terminal' },
      { action: '清空配置', decision: 'deny', example: 'reset saved-configuration' },
    ],
  },
  {
    id: 'storage',
    label: '存储与备份 / S3',
    icon: '存',
    category: 'http',
    platforms: ['S3', 'MinIO', 'Ceph RGW', 'OSS', 'COS', 'OBS', 'Ceph', 'NAS/SAN', '备份平台'],
    objects: 'Bucket、Object、Policy、生命周期、存储池、备份任务',
    hint: '列目录和查元数据允许，下载对象默认审批，删除 Bucket、公开 Bucket、清空 Bucket 禁止执行。',
    examples: [
      { action: '查看 Bucket 列表', decision: 'allow', example: 'GET /?list-type=2' },
      { action: '下载对象', decision: 'approval', example: 'GET /bucket/object.zip' },
      { action: '删除 Bucket', decision: 'deny', example: 'DELETE /bucket' },
    ],
  },
  {
    id: 'monitoring',
    label: '监控与告警',
    icon: '告',
    category: 'http',
    platforms: ['Prometheus', 'Alertmanager', 'Grafana', 'Loki', 'Zabbix', 'ManageEngine'],
    objects: '指标、日志、告警、静默、规则、Dashboard',
    hint: '查询指标和日志允许，静默告警和改规则需要审批，删除规则可配置为禁止执行。',
    examples: [
      { action: '查询指标', decision: 'allow', example: 'GET /api/v1/query?query=up' },
      { action: '创建告警静默', decision: 'approval', example: 'POST /api/v2/silences' },
      { action: '删除告警规则', decision: 'deny', example: 'DELETE /api/ruler/rules' },
    ],
  },
  {
    id: 'hardware',
    label: '硬件带外管理',
    icon: '硬',
    category: 'http',
    platforms: ['SNMP', 'Redfish', 'iLO', 'iDRAC', 'IPMI'],
    objects: '传感器、电源、启动项、BIOS、硬件事件',
    hint: '读取硬件状态允许，修改启动项和远程电源操作需要审批或禁止执行。',
    examples: [
      { action: '读取传感器', decision: 'allow', example: 'GET /redfish/v1/Chassis' },
      { action: '远程重启', decision: 'approval', example: 'POST /Actions/ComputerSystem.Reset' },
      { action: '修改启动项', decision: 'deny', example: 'PATCH /Boot' },
    ],
  },
  {
    id: 'platform',
    label: '平台自身能力',
    icon: '平',
    category: 'local',
    platforms: ['本地脚本', '技能变更', '知识库', '自动化任务'],
    objects: '脚本、技能文件、策略、任务、平台文件',
    hint: '平台自修改能力风险最高，本地脚本和技能变更应默认审批，删除平台文件禁止执行。',
    examples: [
      { action: '读取平台状态', decision: 'allow', example: 'list_active_sessions' },
      { action: '执行本地脚本', decision: 'approval', example: 'local_execute_script' },
      { action: '删除平台文件', decision: 'deny', example: 'rm -rf ./data' },
    ],
  },
]

const CATEGORY_LABELS: Record<CategoryKey, string> = {
  linux: 'Linux / KVM',
  windows: 'Windows WinRM',
  sql: '数据库 SQL',
  redis: 'Redis',
  http: 'HTTP / API 平台',
  network: '交换机 / 网络设备',
  local: '本地 Skill 脚本',
  skill_change: '技能变更',
}

const DECISION_LABELS = {
  allow: { label: '允许执行', className: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' },
  approval: { label: '需要审批', className: 'border-yellow-300/30 bg-yellow-300/10 text-yellow-200' },
  deny: { label: '禁止执行', className: 'border-red-400/30 bg-red-400/10 text-red-200' },
}

const DEFAULT_FORM = {
  name: '',
  platform: '',
  matcherType: 'contains' as MatcherType,
  matcherValue: '',
  decision: 'approval' as Decision,
  reason: '',
  scopeType: 'all',
  scopeValue: '',
  sources: ['chat', 'cron', 'alert'],
}

const DEFAULT_TEST_FORM = {
  input: '',
  method: 'GET',
  mode: 'readonly' as 'readonly' | 'readwrite',
}

const RULE_TEMPLATES: Array<{
  id: string
  name: string
  description: string
  rules: SafetyPolicyRule[]
}> = [
  {
    id: 'production-standard',
    name: '标准生产保护',
    description: '生产标签下，重启/变更动作需要审批，删除类平台动作禁止执行。',
    rules: [
      {
        id: 'tpl-prod-linux-restart',
        name: '生产主机重启服务需要审批',
        domain: 'os',
        platform: 'Linux',
        category: 'linux',
        resource: '服务',
        action: '重启',
        decision: 'approval',
        description: '生产主机重启服务会影响业务可用性，必须人工确认。',
        enabled: true,
        scope: { type: 'tag', value: '生产' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'command_prefix', value: 'systemctl restart' }],
      },
      {
        id: 'tpl-prod-vm-delete',
        name: '生产环境禁止删除虚拟机',
        domain: 'virtualization',
        platform: 'VMware',
        category: 'http',
        resource: '虚拟机',
        action: '删除',
        decision: 'deny',
        description: '生产虚拟机删除必须由人工平台操作，不允许 AI 执行。',
        enabled: true,
        scope: { type: 'tag', value: '生产' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'platform_action', value: 'virtualization.delete_vm' }],
      },
    ],
  },
  {
    id: 's3-data-protection',
    name: 'S3 数据防泄露',
    description: '下载对象需要审批，公开/删除 Bucket 直接禁止。',
    rules: [
      {
        id: 'tpl-s3-download',
        name: 'S3 下载对象需要审批',
        domain: 'storage',
        platform: 'S3',
        category: 'http',
        resource: 'Object',
        action: '下载',
        decision: 'approval',
        description: '对象内容可能包含敏感数据，下载前需要人工确认。',
        enabled: true,
        scope: { type: 'all', value: '' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'platform_action', value: 's3.download_object' }],
      },
      {
        id: 'tpl-s3-public',
        name: '禁止公开 Bucket',
        domain: 'storage',
        platform: 'S3',
        category: 'http',
        resource: 'Bucket Policy',
        action: '公开',
        decision: 'deny',
        description: '公开 Bucket 会造成数据泄露风险。',
        enabled: true,
        scope: { type: 'all', value: '' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'platform_action', value: 's3.public_bucket' }],
      },
      {
        id: 'tpl-s3-delete-bucket',
        name: '禁止删除 Bucket',
        domain: 'storage',
        platform: 'S3',
        category: 'http',
        resource: 'Bucket',
        action: '删除',
        decision: 'deny',
        description: '删除 Bucket 是不可逆高危动作。',
        enabled: true,
        scope: { type: 'all', value: '' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'platform_action', value: 's3.delete_bucket' }],
      },
    ],
  },
  {
    id: 'k8s-strict',
    name: 'K8s 严格保护',
    description: '禁止删除 Namespace，扩缩容 Deployment 需要审批。',
    rules: [
      {
        id: 'tpl-k8s-delete-namespace',
        name: '禁止删除 Kubernetes Namespace',
        domain: 'cloudnative',
        platform: 'Kubernetes',
        category: 'http',
        resource: 'Namespace',
        action: '删除',
        decision: 'deny',
        description: '删除 Namespace 会批量删除业务资源。',
        enabled: true,
        scope: { type: 'all', value: '' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'platform_action', value: 'k8s.delete_namespace' }],
      },
      {
        id: 'tpl-k8s-scale-deployment',
        name: 'Deployment 扩缩容需要审批',
        domain: 'cloudnative',
        platform: 'Kubernetes',
        category: 'http',
        resource: 'Deployment',
        action: '扩缩容',
        decision: 'approval',
        description: '扩缩容会改变业务容量，必须人工确认。',
        enabled: true,
        scope: { type: 'all', value: '' },
        sources: ['chat', 'cron', 'alert'],
        matchers: [{ type: 'platform_action', value: 'k8s.scale_deployment' }],
      },
    ],
  },
]

function lines(value?: string[]) {
  return (value || []).join('\n')
}

function splitLines(value: string) {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
}

function categoryCount(category: SafetyPolicyCategory | undefined) {
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

function resolveCategory(domain: DomainDefinition, platform: string): CategoryKey {
  const normalized = platform.toLowerCase()
  if (normalized.includes('windows') || normalized.includes('hyper-v')) return 'windows'
  if (normalized.includes('redis')) return 'redis'
  if (normalized.includes('switch') || normalized.includes('router') || normalized.includes('firewall')) return 'network'
  if (['mysql', 'postgresql', 'oracle', 'sql server', 'mongodb', 'elasticsearch'].some((item) => normalized.includes(item))) return 'sql'
  return domain.category
}

function resolveToolName(domain: DomainDefinition, platform: string) {
  const normalized = platform.toLowerCase()
  if (normalized.includes('windows') || normalized.includes('hyper-v')) return 'winrm_execute_command'
  if (normalized.includes('redis')) return 'redis_execute_command'
  if (domain.id === 'database') return 'db_execute_query'
  if (domain.id === 'network') return 'network_cli_execute_command'
  if (domain.id === 'cloudnative' && normalized.includes('kubernetes')) return 'k8s_api_request'
  if (domain.id === 'virtualization') return 'virtualization_api_request'
  if (domain.id === 'storage') return 'storage_api_request'
  if (domain.id === 'monitoring') return 'monitoring_api_query'
  if (domain.id === 'hardware') return 'http_api_request'
  if (domain.id === 'platform') return 'local_execute_script'
  return 'linux_execute_command'
}

function semanticMatcherType(type: MatcherType) {
  if (type === 'prefix') return 'command_prefix'
  if (type === 'equals') return 'equals'
  if (type === 'http_method') return 'http_method'
  if (type === 'platform_action') return 'platform_action'
  return type
}

function createRuleId() {
  return `rule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function cloneTemplateRule(rule: SafetyPolicyRule) {
  return { ...rule, id: `${rule.id}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}` }
}

function isValidRegex(value: string) {
  try {
    new RegExp(value)
    return true
  } catch {
    return false
  }
}

function testResultStyle(decision: string) {
  if (decision === 'allow') return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
  if (decision === 'approval') return 'border-yellow-300/30 bg-yellow-300/10 text-yellow-200'
  return 'border-red-400/30 bg-red-400/10 text-red-200'
}

export default function SafetyPolicyModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addToast = useStore((s) => s.addToast)
  const [policy, setPolicy] = useState<SafetyPolicy | null>(null)
  const [activeDomainId, setActiveDomainId] = useState('os')
  const [saving, setSaving] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [testForm, setTestForm] = useState(DEFAULT_TEST_FORM)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<SafetyPolicyTestResult | null>(null)

  useEffect(() => {
    getSafetyPolicy()
      .then((res) => setPolicy(res.data.policy))
      .catch(() => addToast('加载安全策略失败', 'error'))
  }, [addToast])

  const activeDomain = DOMAINS.find((domain) => domain.id === activeDomainId) || DOMAINS[0]
  const selectedPlatform = activeDomain.platforms.includes(form.platform) ? form.platform : activeDomain.platforms[0]
  const activeCategory = resolveCategory(activeDomain, selectedPlatform)
  const category = policy?.categories?.[activeCategory] || {}
  const domainRules = (policy?.rules || []).filter((rule) => rule.domain === activeDomain.id)

  const totals = useMemo(() => {
    const categories = policy?.categories || {}
    let approval = 0
    let deny = 0
    Object.values(categories).forEach((item) => {
      approval += (item.approval_patterns?.length || 0) + (item.approval_commands?.length || 0) + (item.approval_methods?.length || 0)
      deny += item.hard_block_substrings?.length || 0
    })
    ;(policy?.rules || []).forEach((rule) => {
      if (rule.decision === 'approval') approval += 1
      if (rule.decision === 'deny') deny += 1
    })
    return { approval, deny }
  }, [policy])

  const updatePolicy = (patch: Partial<SafetyPolicy>) => {
    if (!policy) return
    setPolicy({ ...policy, ...patch })
  }

  const updateCategory = (categoryKey: CategoryKey, patch: Partial<SafetyPolicyCategory>) => {
    if (!policy) return
    setPolicy({
      ...policy,
      categories: {
        ...policy.categories,
        [categoryKey]: { ...(policy.categories[categoryKey] || {}), ...patch },
      },
    })
  }

  const updateList = (field: ListField, value: string) => {
    updateCategory(activeCategory, { [field]: splitLines(value) })
  }

  const addSimpleRule = () => {
    if (!policy) return
    const value = form.matcherValue.trim()
    if (!value) {
      addToast('请填写匹配内容', 'error')
      return
    }
    if (form.matcherType === 'regex' && !isValidRegex(value)) {
      addToast('正则表达式无效，请检查括号、转义和字符范围', 'error')
      return
    }

    const targetCategory = resolveCategory(activeDomain, selectedPlatform)
    const matcherType = targetCategory === 'http' && !['http_method', 'platform_action', 'regex'].includes(form.matcherType)
      ? 'api_path_contains'
      : semanticMatcherType(form.matcherType)
    const matcherValue = form.matcherType === 'http_method' ? value.toUpperCase() : value
    const rule: SafetyPolicyRule = {
      id: createRuleId(),
      name: form.name.trim() || `${activeDomain.label} ${form.decision === 'deny' ? '禁止执行' : '需要审批'}规则`,
      domain: activeDomain.id,
      platform: selectedPlatform,
      category: targetCategory,
      resource: activeDomain.objects,
      action: form.decision === 'deny' ? '禁止执行' : '需要审批',
      decision: form.decision,
      description: form.reason.trim() || `${selectedPlatform} 命中 ${value} 时${form.decision === 'deny' ? '禁止执行' : '需要人工审批'}。`,
      enabled: true,
      scope: { type: form.scopeType, value: form.scopeValue.trim() },
      sources: form.sources,
      matchers: [{ type: matcherType, value: matcherValue }],
    }

    setPolicy({
      ...policy,
      rules: [...(policy.rules || []), rule],
    })
    setForm(DEFAULT_FORM)
    addToast(form.decision === 'deny' ? '已加入禁止执行规则，保存后生效' : '已加入审批规则，保存后生效', 'success')
  }

  const updateSemanticRule = (ruleId: string, patch: Partial<SafetyPolicyRule>) => {
    if (!policy) return
    setPolicy({
      ...policy,
      rules: (policy.rules || []).map((rule) => (rule.id === ruleId ? { ...rule, ...patch } : rule)),
    })
  }

  const removeSemanticRule = (ruleId: string) => {
    if (!policy) return
    setPolicy({
      ...policy,
      rules: (policy.rules || []).filter((rule) => rule.id !== ruleId),
    })
  }

  const applyTemplate = (templateId: string) => {
    if (!policy) return
    const template = RULE_TEMPLATES.find((item) => item.id === templateId)
    if (!template) return
    setPolicy({
      ...policy,
      rules: [...(policy.rules || []), ...template.rules.map(cloneTemplateRule)],
    })
    addToast(`已套用模板：${template.name}，保存后生效`, 'success')
  }

  const toggleSource = (source: string) => {
    const next = form.sources.includes(source)
      ? form.sources.filter((item) => item !== source)
      : [...form.sources, source]
    setForm({ ...form, sources: next })
  }

  const runPolicyTest = async () => {
    const input = testForm.input.trim()
    if (!input) {
      addToast('请填写要测试的命令、SQL 或 API 路径', 'error')
      return
    }
    const toolName = resolveToolName(activeDomain, selectedPlatform)
    const payload = {
      tool_name: toolName,
      command: input,
      sql: activeCategory === 'sql' ? input : undefined,
      method: activeCategory === 'http' ? testForm.method : undefined,
      path: activeCategory === 'http' ? input : undefined,
      allow_modifications: testForm.mode === 'readwrite',
      asset_type: selectedPlatform,
      protocol: activeCategory === 'http' ? 'http_api' : undefined,
      trigger_source: 'chat',
    }

    setTesting(true)
    try {
      const res = await testSafetyPolicy(payload)
      setTestResult(res.data.result)
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '测试安全策略失败', 'error')
    } finally {
      setTesting(false)
    }
  }

  const save = async () => {
    if (!policy) return
    setSaving(true)
    try {
      const res = await updateSafetyPolicy(policy)
      setPolicy(res.data.policy)
      addToast('安全策略已保存', 'success')
      closeModal()
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存安全策略失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  const textArea = (label: string, field: ListField, rows = 5) => (
    <label className="block">
      <span className="text-xs text-ops-subtext">{label}</span>
      <textarea
        value={lines(category[field] as string[] | undefined)}
        onChange={(e) => updateList(field, e.target.value)}
        rows={rows}
        className="mt-1 w-full resize-y rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 font-mono text-xs text-ops-text outline-none focus:border-ops-accent"
        spellCheck={false}
      />
    </label>
  )

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/55" onClick={closeModal}>
      <div
        className="flex h-[760px] w-[1180px] max-w-[96vw] overflow-hidden rounded-xl border border-ops-surface0 bg-ops-panel shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <aside className="flex w-72 flex-col border-r border-ops-surface0 bg-ops-dark">
          <div className="border-b border-ops-surface0 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-bold text-ops-text">安全策略</h2>
                <p className="mt-1 text-[11px] text-ops-subtext">按资源、平台、动作配置审批和禁止执行</p>
              </div>
              <button onClick={closeModal} className="text-xl text-ops-subtext hover:text-ops-text">&times;</button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 border-b border-ops-surface0 p-3 text-center">
            <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 px-2 py-2">
              <div className="text-lg font-bold text-yellow-200">{totals.approval}</div>
              <div className="text-[10px] text-ops-subtext">审批规则</div>
            </div>
            <div className="rounded-lg border border-red-400/20 bg-red-400/10 px-2 py-2">
              <div className="text-lg font-bold text-red-200">{totals.deny}</div>
              <div className="text-[10px] text-ops-subtext">禁止规则</div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {DOMAINS.map((domain) => (
              <button
                key={domain.id}
                onClick={() => setActiveDomainId(domain.id)}
                className={`mb-1 flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left transition-colors ${
                  activeDomain.id === domain.id ? 'bg-ops-surface1 text-ops-text' : 'text-ops-subtext hover:bg-ops-surface0'
                }`}
              >
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-ops-surface1 bg-ops-panel text-xs font-bold">
                  {domain.icon}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium">{domain.label}</span>
                  <span className="block truncate text-[10px] text-ops-overlay">
                    {CATEGORY_LABELS[domain.category]} · {categoryCount(policy?.categories?.[domain.category])} 条
                  </span>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-ops-surface0 px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-ops-accent/15 text-sm font-bold text-ops-accent">
                    {activeDomain.icon}
                  </span>
                  <div>
                    <h3 className="text-base font-semibold text-ops-text">{activeDomain.label}</h3>
                    <p className="text-xs text-ops-subtext">{activeDomain.hint}</p>
                  </div>
                </div>
              </div>
              <label className="flex items-center gap-2 whitespace-nowrap text-xs text-ops-subtext">
                <input
                  type="checkbox"
                  checked={showAdvanced}
                  onChange={(e) => setShowAdvanced(e.target.checked)}
                  className="accent-ops-accent"
                />
                高级规则
              </label>
            </div>
          </header>

          {!policy ? (
            <div className="flex flex-1 items-center justify-center text-ops-subtext">加载中...</div>
          ) : (
            <div className="flex-1 overflow-y-auto p-5">
              <section className="mb-4 grid grid-cols-3 gap-3">
                <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-3">
                  <div className="text-sm font-semibold text-emerald-200">允许执行</div>
                  <p className="mt-1 text-xs leading-5 text-ops-subtext">只读巡检、状态查询、日志查看默认允许，不需要单独拦截。</p>
                </div>
                <div className="rounded-lg border border-yellow-300/20 bg-yellow-300/10 p-3">
                  <div className="text-sm font-semibold text-yellow-200">需要审批</div>
                  <p className="mt-1 text-xs leading-5 text-ops-subtext">读写会话进入审批；只读会话阻止执行并提示切换读写。</p>
                </div>
                <div className="rounded-lg border border-red-400/20 bg-red-400/10 p-3">
                  <div className="text-sm font-semibold text-red-200">禁止执行</div>
                  <p className="mt-1 text-xs leading-5 text-ops-subtext">无论只读或读写，命中后直接拒绝，不进入审批。</p>
                </div>
              </section>

              <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45">
                <div className="grid grid-cols-[1.2fr_1fr_1fr_1.8fr] border-b border-ops-surface0 px-4 py-2 text-[11px] font-semibold text-ops-overlay">
                  <span>动作</span>
                  <span>建议策略</span>
                  <span>平台对象</span>
                  <span>示例</span>
                </div>
                {activeDomain.examples.map((item) => (
                  <div key={`${item.action}-${item.example}`} className="grid grid-cols-[1.2fr_1fr_1fr_1.8fr] items-center border-b border-ops-surface0/70 px-4 py-3 last:border-b-0">
                    <span className="text-sm font-medium text-ops-text">{item.action}</span>
                    <span>
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${DECISION_LABELS[item.decision].className}`}>
                        {DECISION_LABELS[item.decision].label}
                      </span>
                    </span>
                    <span className="text-xs text-ops-subtext">{activeDomain.objects}</span>
                    <span className="truncate font-mono text-xs text-ops-overlay">{item.example}</span>
                  </div>
                ))}
              </section>

              <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-ops-text">策略模板</h4>
                    <p className="mt-1 text-xs text-ops-subtext">一键加入常用规则组合，保存后生效，可继续单条启停或删除。</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {RULE_TEMPLATES.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => applyTemplate(template.id)}
                      className="rounded-lg border border-ops-surface1 bg-ops-panel/50 p-3 text-left transition-colors hover:border-ops-accent/60 hover:bg-ops-surface0/60"
                    >
                      <span className="block text-sm font-semibold text-ops-text">{template.name}</span>
                      <span className="mt-1 block text-xs leading-5 text-ops-subtext">{template.description}</span>
                      <span className="mt-2 block text-[11px] text-ops-overlay">{template.rules.length} 条规则</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45">
                <div className="flex items-center justify-between border-b border-ops-surface0 px-4 py-3">
                  <div>
                    <h4 className="text-sm font-semibold text-ops-text">已配置动作规则</h4>
                    <p className="mt-1 text-xs text-ops-subtext">这里展示通过普通表单保存的结构化规则，可直接启停或删除。</p>
                  </div>
                  <span className="text-xs text-ops-overlay">{domainRules.length} 条</span>
                </div>
                {domainRules.length === 0 ? (
                  <div className="px-4 py-5 text-sm text-ops-subtext">当前资源域还没有结构化规则，可以在下方新增。</div>
                ) : (
                  <div className="divide-y divide-ops-surface0">
                    {domainRules.map((rule) => (
                      <div key={rule.id} className="grid grid-cols-[1.3fr_1fr_1fr_auto] items-center gap-3 px-4 py-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${DECISION_LABELS[rule.decision].className}`}>
                              {DECISION_LABELS[rule.decision].label}
                            </span>
                            <span className="truncate text-sm font-medium text-ops-text">{rule.name}</span>
                          </div>
                          <p className="mt-1 truncate text-xs text-ops-subtext">{rule.description || '无说明'}</p>
                          <p className="mt-1 truncate text-[11px] text-ops-overlay">
                            范围：{rule.scope?.type === 'all' || !rule.scope?.type ? '全部资产' : `${rule.scope?.type}=${rule.scope?.value || '-'}`} · 来源：{rule.sources?.length ? rule.sources.join('/') : '全部'}
                          </p>
                        </div>
                        <span className="text-xs text-ops-subtext">{rule.platform || '-'}</span>
                        <span className="truncate font-mono text-xs text-ops-overlay">
                          {rule.matchers?.map((matcher) => `${matcher.type}:${matcher.value}`).join(' / ')}
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => updateSemanticRule(rule.id, { enabled: !rule.enabled })}
                            className={`rounded-md border px-2 py-1 text-xs ${
                              rule.enabled === false
                                ? 'border-ops-surface1 text-ops-subtext hover:text-ops-text'
                                : 'border-emerald-400/30 text-emerald-200 hover:bg-emerald-400/10'
                            }`}
                          >
                            {rule.enabled === false ? '已停用' : '启用中'}
                          </button>
                          <button
                            onClick={() => removeSemanticRule(rule.id)}
                            className="rounded-md border border-red-400/30 px-2 py-1 text-xs text-red-200 hover:bg-red-400/10"
                          >
                            删除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-surface0/30 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-ops-text">新增规则</h4>
                    <p className="mt-1 text-xs text-ops-subtext">不用写正则也可以加入审批或禁止执行规则；名称、平台和匹配条件会作为结构化规则保存。</p>
                  </div>
                  <span className="rounded-full border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">
                    分类 {CATEGORY_LABELS[activeCategory]}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <label>
                    <span className="text-xs text-ops-subtext">规则名称</span>
                    <input
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      placeholder="例如：生产环境禁止删除虚拟机"
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">平台类型</span>
                    <select
                      value={selectedPlatform}
                      onChange={(e) => setForm({ ...form, platform: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      {activeDomain.platforms.map((platform) => (
                        <option key={platform} value={platform}>{platform}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">处理方式</span>
                    <select
                      value={form.decision}
                      onChange={(e) => setForm({ ...form, decision: e.target.value as Decision })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      <option value="approval">需要审批</option>
                      <option value="deny">禁止执行</option>
                    </select>
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">匹配方式</span>
                    <select
                      value={form.matcherType}
                      onChange={(e) => setForm({ ...form, matcherType: e.target.value as MatcherType })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      <option value="contains">包含关键词</option>
                      <option value="prefix">命令开头</option>
                      <option value="equals">完全等于</option>
                      <option value="http_method">HTTP 方法</option>
                      <option value="platform_action">平台动作</option>
                      <option value="regex">正则匹配（高级）</option>
                    </select>
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">匹配内容</span>
                    <input
                      value={form.matcherValue}
                      onChange={(e) => setForm({ ...form, matcherValue: e.target.value })}
                      placeholder={activeCategory === 'http' ? '例如 DELETE 或 /api/v1/namespaces' : '例如 systemctl restart'}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  <label className="col-span-2">
                    <span className="text-xs text-ops-subtext">规则说明</span>
                    <input
                      value={form.reason}
                      onChange={(e) => setForm({ ...form, reason: e.target.value })}
                      placeholder="例如：生产虚拟机删除必须由人工平台操作"
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">生效范围</span>
                    <select
                      value={form.scopeType}
                      onChange={(e) => setForm({ ...form, scopeType: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      <option value="all">全部资产</option>
                      <option value="tag">资产标签</option>
                      <option value="asset_group">资产组</option>
                      <option value="asset_type">资产类型</option>
                      <option value="environment">环境</option>
                      <option value="asset">单资产</option>
                    </select>
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">范围值</span>
                    <input
                      value={form.scopeValue}
                      onChange={(e) => setForm({ ...form, scopeValue: e.target.value })}
                      disabled={form.scopeType === 'all'}
                      placeholder={form.scopeType === 'tag' ? '例如：生产' : '全部资产无需填写'}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-45"
                    />
                  </label>
                  <div className="col-span-2">
                    <span className="text-xs text-ops-subtext">操作来源</span>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {[
                        ['chat', '会话'],
                        ['cron', '定时巡检'],
                        ['alert', '告警联动'],
                        ['api', 'API'],
                      ].map(([source, label]) => (
                        <label key={source} className="inline-flex items-center gap-2 rounded-full border border-ops-surface1 px-3 py-1 text-xs text-ops-text">
                          <input
                            type="checkbox"
                            checked={form.sources.includes(source)}
                            onChange={() => toggleSource(source)}
                            className="accent-ops-accent"
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
                  <p className="text-xs leading-5 text-ops-subtext">
                    {form.decision === 'approval'
                      ? '审批规则：读写会话进入审批；只读会话会被阻止，避免误执行变更动作。'
                      : '禁止执行规则：当前阶段按包含关键词生效，适合放删库、格式化、公开 Bucket、删除虚拟机等明确危险动作。'}
                  </p>
                  <button
                    onClick={addSimpleRule}
                    className="shrink-0 rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark transition-colors hover:bg-ops-accent/80"
                  >
                    加入规则
                  </button>
                </div>
              </section>

              <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-ops-text">规则测试器</h4>
                    <p className="mt-1 text-xs text-ops-subtext">只做策略预演，不会连接或执行目标资产。适合保存前检查一条命令会被如何处理。</p>
                  </div>
                  <span className="rounded-full border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">
                    {testForm.mode === 'readwrite' ? '读写会话' : '只读会话'}
                  </span>
                </div>

                <div className="grid grid-cols-[1fr_120px_120px_auto] gap-3">
                  <label>
                    <span className="text-xs text-ops-subtext">命令 / SQL / API 路径</span>
                    <input
                      value={testForm.input}
                      onChange={(e) => setTestForm({ ...testForm, input: e.target.value })}
                      placeholder={activeCategory === 'http' ? '例如 /api/v1/namespaces/prod' : '例如 systemctl restart nginx'}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    />
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">HTTP 方法</span>
                    <select
                      value={testForm.method}
                      onChange={(e) => setTestForm({ ...testForm, method: e.target.value })}
                      disabled={activeCategory !== 'http'}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-45"
                    >
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                      <option value="PATCH">PATCH</option>
                      <option value="DELETE">DELETE</option>
                    </select>
                  </label>
                  <label>
                    <span className="text-xs text-ops-subtext">会话模式</span>
                    <select
                      value={testForm.mode}
                      onChange={(e) => setTestForm({ ...testForm, mode: e.target.value as 'readonly' | 'readwrite' })}
                      className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                    >
                      <option value="readonly">只读</option>
                      <option value="readwrite">读写</option>
                    </select>
                  </label>
                  <button
                    onClick={runPolicyTest}
                    disabled={testing}
                    className="mt-5 rounded-lg border border-ops-accent/50 px-4 py-2 text-sm font-medium text-ops-accent transition-colors hover:bg-ops-accent/10 disabled:opacity-45"
                  >
                    {testing ? '测试中...' : '测试'}
                  </button>
                </div>

                {testResult && (
                  <div className="mt-3 rounded-lg border border-ops-surface0 bg-ops-panel/50 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${testResultStyle(testResult.decision)}`}>
                        {testResult.label}
                      </span>
                      <span className="font-mono text-[11px] text-ops-overlay">{resolveToolName(activeDomain, selectedPlatform)}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-ops-text">{testResult.reason}</p>
                    <div className="mt-3 grid grid-cols-3 gap-2">
                      {testResult.checks.map((check) => (
                        <div key={check.name} className="rounded-md border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-medium text-ops-text">{check.name}</span>
                            <span className={check.matched ? 'text-xs text-yellow-200' : 'text-xs text-ops-overlay'}>
                              {check.matched ? '命中' : '未命中'}
                            </span>
                          </div>
                          {check.reason && <p className="mt-1 text-[11px] leading-4 text-ops-subtext">{check.reason}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              <section className="mb-4 grid grid-cols-2 gap-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
                <label>
                  <span className="text-xs text-ops-subtext">审批等待超时（秒）</span>
                  <input
                    type="number"
                    min={30}
                    max={1800}
                    value={policy.approval_timeout_seconds}
                    onChange={(e) => updatePolicy({ approval_timeout_seconds: Number(e.target.value) || 300 })}
                    className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                  />
                </label>
                <label className="flex items-center gap-2 pt-6 text-sm text-ops-text">
                  <input
                    type="checkbox"
                    checked={policy.readwrite_chat_warning_enabled}
                    onChange={(e) => updatePolicy({ readwrite_chat_warning_enabled: e.target.checked })}
                    className="accent-ops-accent"
                  />
                  读写会话聊天前弹窗提醒
                </label>
              </section>

              {showAdvanced && (
                <section className="space-y-4 rounded-lg border border-ops-surface0 bg-ops-dark/55 p-4">
                  <div>
                    <h4 className="text-sm font-semibold text-ops-text">高级规则</h4>
                    <p className="mt-1 text-xs text-ops-subtext">
                      这里保留底层字段，给懂正则或需要精确兜底的管理员使用。普通规则会同步写入这些字段。
                    </p>
                  </div>

                  {textArea('禁止执行片段（无论只读或读写都拒绝，每行一个）', 'hard_block_substrings', 5)}

                  {(activeCategory === 'linux' || activeCategory === 'windows' || activeCategory === 'sql' || activeCategory === 'network' || activeCategory === 'local') && (
                    <>
                      {textArea('需要审批的命令 / SQL 正则', 'approval_patterns', 7)}
                      {textArea('只读会话阻止的命令 / SQL 正则', 'readonly_block_patterns', 7)}
                    </>
                  )}

                  {activeCategory === 'linux' && (
                    <details className="rounded-lg border border-ops-surface0 bg-ops-panel/40 p-3">
                      <summary className="cursor-pointer text-xs text-ops-subtext">只读未知命令策略</summary>
                      <div className="mt-3 space-y-3">
                        {textArea('只读安全根命令（每行一个）', 'readonly_safe_roots', 5)}
                        <label className="flex items-center gap-2 text-sm text-ops-text">
                          <input
                            type="checkbox"
                            checked={Boolean(category.readonly_unknown_requires_approval)}
                            onChange={(e) => updateCategory(activeCategory, { readonly_unknown_requires_approval: e.target.checked })}
                            className="accent-ops-accent"
                          />
                          只读模式下未知根命令需要人工审批
                        </label>
                      </div>
                    </details>
                  )}

                  {activeCategory === 'redis' && (
                    <>
                      {textArea('需要审批的 Redis 命令', 'approval_commands', 7)}
                      {textArea('只读会话阻止的 Redis 命令', 'readonly_block_commands', 7)}
                    </>
                  )}

                  {activeCategory === 'http' && (
                    <>
                      {textArea('需要审批的 HTTP 方法', 'approval_methods', 4)}
                      {textArea('只读会话阻止的 HTTP 方法', 'readonly_block_methods', 4)}
                    </>
                  )}

                  {activeCategory === 'local' && (
                    <>
                      <label className="flex items-center gap-2 text-sm text-ops-text">
                        <input
                          type="checkbox"
                          checked={Boolean(category.always_approval)}
                          onChange={(e) => updateCategory(activeCategory, { always_approval: e.target.checked })}
                          className="accent-ops-accent"
                        />
                        本地 Skill 脚本始终需要人工审批
                      </label>
                      <label className="block">
                        <span className="text-xs text-ops-subtext">审批提示文案</span>
                        <input
                          value={category.approval_reason || ''}
                          onChange={(e) => updateCategory(activeCategory, { approval_reason: e.target.value })}
                          className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
                        />
                      </label>
                    </>
                  )}
                </section>
              )}
            </div>
          )}

          <footer className="flex justify-end gap-2 border-t border-ops-surface0 px-5 py-3">
            <button onClick={closeModal} className="px-4 py-2 text-sm text-ops-subtext hover:text-ops-text">取消</button>
            <button
              onClick={save}
              disabled={!policy || saving}
              className="rounded-lg bg-ops-accent px-4 py-2 text-sm font-medium text-ops-dark transition-colors hover:bg-ops-accent/80 disabled:opacity-40"
            >
              {saving ? '保存中...' : '保存策略'}
            </button>
          </footer>
        </main>
      </div>
    </div>
  )
}
