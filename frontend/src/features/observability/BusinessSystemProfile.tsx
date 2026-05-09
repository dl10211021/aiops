import { useState } from 'react'
import ComponentBindings from './ComponentBindings'
import LayeredTopology from './LayeredTopology'
import type {
  ObservabilityArchitectureTemplate,
  ObservabilityComponent,
  ObservabilitySystem,
  ObservabilityTopology,
} from './types'

const COMPONENT_OPTIONS = [
  { type: 'unknown', label: '未知节点', family: 'unknown' },
  { type: 'application_service', label: '应用服务', family: 'application' },
  { type: 'os_host', label: '主机 / VM', family: 'infrastructure' },
  { type: 'k8s_cluster', label: 'Kubernetes 集群', family: 'container' },
  { type: 'database_instance', label: '数据库实例', family: 'database' },
  { type: 'database_node', label: '数据库节点', family: 'database' },
  { type: 'database_endpoint', label: 'SQL 入口', family: 'database' },
  { type: 'mpp_cluster', label: 'MPP 集群', family: 'mpp_database' },
  { type: 'bigdata_cluster', label: '大数据集群', family: 'bigdata' },
  { type: 'bigdata_job', label: '大数据作业', family: 'bigdata' },
  { type: 'message_queue', label: '消息队列', family: 'middleware' },
  { type: 'storage_pool', label: '对象 / HDFS 存储', family: 'storage' },
  { type: 'network_switch', label: '交换机', family: 'network' },
  { type: 'router', label: '路由器', family: 'network' },
  { type: 'firewall', label: '防火墙', family: 'network' },
  { type: 'vlan', label: 'VLAN / 网段', family: 'network' },
]

const ARCHITECTURE_TEMPLATES: ObservabilityArchitectureTemplate[] = [
  {
    id: 'bigdata_platform',
    title: '大数据集群',
    description: 'Hadoop/Spark、作业调度、消息队列和存储依赖的基础画像。',
    nodes: [
      { key: 'cluster', name: '大数据计算集群', component_type: 'bigdata_cluster', workload_family: 'bigdata', layer: 'compute', confidence: 'inferred' },
      { key: 'job', name: '批处理 / Spark 作业', component_type: 'bigdata_job', workload_family: 'bigdata', layer: 'application', confidence: 'inferred' },
      { key: 'queue', name: 'Kafka / MQ 队列', component_type: 'message_queue', workload_family: 'middleware', layer: 'middleware', confidence: 'inferred' },
      { key: 'storage', name: 'HDFS / 对象存储', component_type: 'storage_pool', workload_family: 'storage', layer: 'data', confidence: 'inferred' },
    ],
    relationships: [
      { from: 'job', to: 'cluster', relationship_type: 'runs_on', confidence: 'inferred' },
      { from: 'job', to: 'queue', relationship_type: 'uses_middleware', confidence: 'inferred' },
      { from: 'cluster', to: 'storage', relationship_type: 'uses_storage', confidence: 'inferred' },
    ],
  },
  {
    id: 'mpp_analytics',
    title: 'MPP 分析集群',
    description: 'SQL 入口、FE/CN、BE/DN 和底层存储的分析型数据库拓扑。',
    nodes: [
      { key: 'endpoint', name: 'MPP SQL 入口', component_type: 'database_endpoint', workload_family: 'mpp_database', layer: 'access', confidence: 'inferred' },
      { key: 'cluster', name: 'MPP 分析集群', component_type: 'mpp_cluster', workload_family: 'mpp_database', layer: 'database', confidence: 'inferred' },
      { key: 'frontend', name: 'FE / CN 节点组', component_type: 'database_node', workload_family: 'mpp_database', layer: 'database', confidence: 'inferred' },
      { key: 'backend', name: 'BE / DN 节点组', component_type: 'database_node', workload_family: 'mpp_database', layer: 'database', confidence: 'inferred' },
      { key: 'storage', name: '共享存储 / 数据文件', component_type: 'storage_pool', workload_family: 'storage', layer: 'data', confidence: 'inferred' },
    ],
    relationships: [
      { from: 'endpoint', to: 'frontend', relationship_type: 'exposes_service_via', confidence: 'inferred' },
      { from: 'frontend', to: 'cluster', relationship_type: 'managed_by', confidence: 'inferred' },
      { from: 'cluster', to: 'backend', relationship_type: 'depends_on', confidence: 'inferred' },
      { from: 'backend', to: 'storage', relationship_type: 'uses_storage', confidence: 'inferred' },
    ],
  },
  {
    id: 'network_architecture',
    title: '网络架构',
    description: '核心交换、汇聚交换、防火墙、VLAN 和未知上联的基础链路。',
    nodes: [
      { key: 'core', name: '核心交换机', component_type: 'network_switch', workload_family: 'network', layer: 'network', confidence: 'inferred' },
      { key: 'aggregation', name: '汇聚交换机', component_type: 'network_switch', workload_family: 'network', layer: 'network', confidence: 'inferred' },
      { key: 'firewall', name: '边界防火墙', component_type: 'firewall', workload_family: 'network', layer: 'security', confidence: 'inferred' },
      { key: 'vlan', name: '业务 VLAN / 网段', component_type: 'vlan', workload_family: 'network', layer: 'network', confidence: 'inferred' },
      { key: 'uplink', name: '未知上联 / 外部依赖', component_type: 'unknown', workload_family: 'network', layer: 'external', confidence: 'unknown' },
    ],
    relationships: [
      { from: 'vlan', to: 'aggregation', relationship_type: 'attached_to_network', confidence: 'inferred' },
      { from: 'aggregation', to: 'core', relationship_type: 'connected_to', confidence: 'inferred' },
      { from: 'core', to: 'firewall', relationship_type: 'routes_through', confidence: 'inferred' },
      { from: 'firewall', to: 'uplink', relationship_type: 'depends_on', confidence: 'unknown' },
    ],
  },
]

export default function BusinessSystemProfile({
  system,
  topology,
  onAddComponent,
  onCreateTemplate,
  onBindAsset,
  onBindSession,
}: {
  system: ObservabilitySystem | null
  topology: ObservabilityTopology | null
  onAddComponent: (payload: Record<string, unknown>) => Promise<void>
  onCreateTemplate: (template: ObservabilityArchitectureTemplate) => Promise<void>
  onBindAsset: (componentId: string, assetId: string) => Promise<void>
  onBindSession: (componentId: string, sessionId: string) => Promise<void>
}) {
  const [selected, setSelected] = useState<ObservabilityComponent | null>(null)
  const [name, setName] = useState('未知节点')
  const [componentType, setComponentType] = useState('unknown')
  const selectedOption = COMPONENT_OPTIONS.find((item) => item.type === componentType) || COMPONENT_OPTIONS[0]
  if (!system) return <div className="ops-data-panel p-6 text-sm text-ops-subtext">请选择业务系统。</div>
  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <div className="ops-data-panel mb-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-black text-ops-text">{system.name}</h2>
              <p className="mt-1 text-sm text-ops-subtext">{system.environment} · 完整度 {system.profile_completeness || 0}% · 未知节点 {system.unknown_count || 0}</p>
            </div>
            <div className="flex gap-2">
              <input className="ops-control w-36 rounded-lg px-3 py-2 text-sm" value={name} onChange={(event) => setName(event.target.value)} />
              <select className="ops-control rounded-lg px-3 py-2 text-sm" value={componentType} onChange={(event) => setComponentType(event.target.value)}>
                {COMPONENT_OPTIONS.map((item) => (
                  <option key={item.type} value={item.type}>{item.label}</option>
                ))}
              </select>
              <button
                className="ops-control rounded-lg px-3 py-2 text-sm font-semibold"
                onClick={() => void onAddComponent({
                  name,
                  component_type: componentType,
                  workload_family: selectedOption.family,
                  confidence: componentType === 'unknown' ? 'unknown' : 'confirmed',
                })}
              >
                添加节点
              </button>
            </div>
          </div>
        </div>
        <div className="ops-data-panel mb-4 p-5">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-black text-ops-text">架构模板</h3>
              <p className="mt-1 text-xs text-ops-subtext">用于快速建立一套集群或网络环境的初始拓扑，后续再绑定真实资产和会话。</p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {ARCHITECTURE_TEMPLATES.map((template) => (
              <button
                key={template.id}
                className="rounded-lg border border-ops-surface0 bg-ops-surface1/45 p-3 text-left transition hover:border-ops-accent/55 hover:bg-ops-accent/10"
                onClick={() => void onCreateTemplate(template)}
              >
                <div className="text-sm font-black text-ops-text">{template.title}</div>
                <p className="mt-1 min-h-10 text-xs leading-5 text-ops-subtext">{template.description}</p>
                <div className="mt-3 flex gap-2 text-[11px] text-ops-overlay">
                  <span>{template.nodes.length} 节点</span>
                  <span>{template.relationships.length} 关系</span>
                </div>
              </button>
            ))}
          </div>
        </div>
        <LayeredTopology topology={topology} selectedComponentId={selected?.id || null} onSelect={setSelected} />
      </div>
      <ComponentBindings system={system} component={selected} onBindAsset={onBindAsset} onBindSession={onBindSession} />
    </section>
  )
}
