import { useState, useEffect } from 'react'
import { useStore } from '@/store'
import { connectSession, testConnection, inspectConnection, getSkillRegistry, batchImportAssets, getAssetTypes } from '@/api/client'
import type { SkillInfo } from '@/types'

type AssetSubType = { id: string, label: string, asset_type: string, defaultPort: number, authMode?: 'basic' | 'password_only' | 'custom_snmp' | 'none' }

const ASSET_CATEGORIES = [
  { id: 'os', label: '操作系统与主机 (OS & Compute)' },
  { id: 'db', label: '数据库与缓存 (Database & Cache)' },
  { id: 'container', label: '容器与云原生 (Container & Kubernetes)' },
  { id: 'middleware', label: '中间件 (Middleware)' },
  { id: 'virtualization', label: '虚拟化与私有云 (Virtualization)' },
  { id: 'network', label: '网络与安全 (Network & Security)' },
  { id: 'storage', label: '存储与备份 (Storage & Backup)' },
  { id: 'monitor', label: '监控与告警 (Monitoring & APM)' },
  { id: 'oob', label: '硬件带外 (Hardware & OOB)' },
  { id: 'security', label: '安全与身份 (Security & Identity)' },
]

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  ASSET_CATEGORIES.map((item) => [item.id, item.label])
)

const ASSET_SUB_TYPES: Record<string, AssetSubType[]> = {
  os: [
    { id: 'linux', label: 'Linux / Unix (SSH)', asset_type: 'ssh', defaultPort: 22 },
    { id: 'windows', label: 'Windows Server (WinRM)', asset_type: 'winrm', defaultPort: 5985 },
  ],
  db: [
    { id: 'mysql', label: 'MySQL', asset_type: 'mysql', defaultPort: 3306 },
    { id: 'oracle', label: 'Oracle', asset_type: 'oracle', defaultPort: 1521 },
    { id: 'postgresql', label: 'PostgreSQL', asset_type: 'postgresql', defaultPort: 5432 },
    { id: 'mssql', label: 'SQL Server', asset_type: 'mssql', defaultPort: 1433 },
    { id: 'redis', label: 'Redis', asset_type: 'redis', defaultPort: 6379, authMode: 'password_only' },
    { id: 'mongodb', label: 'MongoDB', asset_type: 'mongodb', defaultPort: 27017 },
    { id: 'elasticsearch', label: 'ElasticSearch', asset_type: 'http_api', defaultPort: 9200 },
  ],
  container: [
    { id: 'docker', label: 'Docker Host (SSH)', asset_type: 'ssh', defaultPort: 22 },
    { id: 'containerd', label: 'containerd Host (SSH)', asset_type: 'ssh', defaultPort: 22 },
    { id: 'podman', label: 'Podman Host (SSH)', asset_type: 'ssh', defaultPort: 22 },
    { id: 'harbor', label: 'Harbor Registry', asset_type: 'http_api', defaultPort: 443 },
    { id: 'k8s', label: 'Kubernetes (K8s)', asset_type: 'k8s', defaultPort: 6443 },
  ],
  middleware: [
    { id: 'nginx', label: 'Nginx', asset_type: 'ssh', defaultPort: 22 },
    { id: 'tomcat', label: 'Tomcat', asset_type: 'ssh', defaultPort: 22 },
    { id: 'kafka', label: 'Kafka', asset_type: 'ssh', defaultPort: 22 },
    { id: 'rabbitmq', label: 'RabbitMQ', asset_type: 'http_api', defaultPort: 15672 },
    { id: 'rocketmq', label: 'RocketMQ', asset_type: 'ssh', defaultPort: 22 },
    { id: 'zookeeper', label: 'ZooKeeper', asset_type: 'ssh', defaultPort: 22 },
    { id: 'nacos', label: 'Nacos', asset_type: 'http_api', defaultPort: 8848 },
    { id: 'consul', label: 'Consul', asset_type: 'http_api', defaultPort: 8500 },
  ],
  virtualization: [
    { id: 'vmware', label: 'VMware vCenter/ESXi', asset_type: 'http_api', defaultPort: 443 },
    { id: 'kvm', label: 'KVM / Libvirt Host (SSH)', asset_type: 'ssh', defaultPort: 22 },
    { id: 'openstack', label: 'OpenStack', asset_type: 'http_api', defaultPort: 5000 },
    { id: 'proxmox', label: 'Proxmox VE', asset_type: 'http_api', defaultPort: 8006 },
    { id: 'hyperv', label: 'Hyper-V (WinRM)', asset_type: 'winrm', defaultPort: 5985 },
    { id: 'zstack', label: 'ZStack', asset_type: 'http_api', defaultPort: 5000 },
  ],
  network: [
    { id: 'f5', label: 'F5 BIG-IP', asset_type: 'http_api', defaultPort: 443 },
    { id: 'switch', label: 'Switch / Router', asset_type: 'ssh', defaultPort: 22 },
    { id: 'firewall', label: 'Firewall', asset_type: 'ssh', defaultPort: 22 },
    { id: 'a10', label: 'A10 Load Balancer', asset_type: 'http_api', defaultPort: 443 },
    { id: 'waf', label: 'WAF', asset_type: 'http_api', defaultPort: 443 },
    { id: 'dns', label: 'DNS Server', asset_type: 'ssh', defaultPort: 22 },
    { id: 'vpn', label: 'VPN Gateway', asset_type: 'ssh', defaultPort: 22 },
  ],
  storage: [
    { id: 'ceph', label: 'Ceph Cluster', asset_type: 'ssh', defaultPort: 22 },
    { id: 'nfs', label: 'NFS Server', asset_type: 'ssh', defaultPort: 22 },
    { id: 'nas', label: 'NAS / SAN (SNMP)', asset_type: 'snmp', defaultPort: 161, authMode: 'custom_snmp' },
    { id: 'minio', label: 'MinIO', asset_type: 'http_api', defaultPort: 9000 },
    { id: 's3', label: 'S3 / Object Storage', asset_type: 'http_api', defaultPort: 443 },
    { id: 'hdfs', label: 'HDFS', asset_type: 'ssh', defaultPort: 22 },
    { id: 'glusterfs', label: 'GlusterFS', asset_type: 'ssh', defaultPort: 22 },
    { id: 'backup', label: 'Backup System', asset_type: 'http_api', defaultPort: 443 },
  ],
  monitor: [
    { id: 'zabbix', label: 'Zabbix', asset_type: 'http_api', defaultPort: 80 },
    { id: 'prometheus', label: 'Prometheus', asset_type: 'http_api', defaultPort: 9090 },
    { id: 'alertmanager', label: 'Alertmanager', asset_type: 'http_api', defaultPort: 9093 },
    { id: 'grafana', label: 'Grafana', asset_type: 'http_api', defaultPort: 3000 },
    { id: 'loki', label: 'Loki', asset_type: 'http_api', defaultPort: 3100 },
    { id: 'victoriametrics', label: 'VictoriaMetrics', asset_type: 'http_api', defaultPort: 8428 },
    { id: 'manageengine', label: 'ManageEngine / 卓豪监控', asset_type: 'http_api', defaultPort: 8443 },
  ],
  oob: [
    { id: 'snmp', label: 'SNMP', asset_type: 'snmp', defaultPort: 161, authMode: 'custom_snmp' },
    { id: 'redfish', label: 'Redfish/iLO/iDRAC', asset_type: 'redfish', defaultPort: 443 },
    { id: 'ipmi', label: 'IPMI', asset_type: 'snmp', defaultPort: 161, authMode: 'custom_snmp' },
  ],
  security: [
    { id: 'bastion', label: '堡垒机 / Bastion', asset_type: 'http_api', defaultPort: 443 },
    { id: 'ldap', label: 'LDAP / Active Directory', asset_type: 'http_api', defaultPort: 389 },
    { id: 'audit', label: 'Audit Platform', asset_type: 'http_api', defaultPort: 443 },
  ],
}

const authModeFor = (id: string): AssetSubType['authMode'] => {
  if (id === 'redis') return 'password_only'
  if (['snmp', 'ipmi', 'nas'].includes(id)) return 'custom_snmp'
  return 'basic'
}

const getAuthVisibility = (subTypes: Record<string, AssetSubType[]>, subType: string, category: string, extraArgs: any) => {
  const currentSubInfo = subTypes[category]?.find(s => s.id === subType);
  const authMode = currentSubInfo?.authMode || 'basic';

  if (authMode === 'password_only') return { showUser: false, showPass: true };
  if (authMode === 'custom_snmp' && extraArgs?.snmp_version === 'v3') return { showUser: false, showPass: false };
  if (authMode === 'none') return { showUser: false, showPass: false };
  return { showUser: true, showPass: true };
}

const autoSelectSkills = (subType: string, allSkills: SkillInfo[]) => {
  const skillMapping: Record<string, string[]> = {
    linux: ['linux', 'linux-hardening-plan', 'nfs-ops'],
    kvm: ['linux', 'linux-hardening-plan'],
    windows: ['windows-admin'],
    winrm: ['windows-admin'],
    mysql: ['mysql-client', 'mysql-upgrade-expert', 'database'],
    oracle: ['database'],
    postgresql: ['database'],
    mssql: ['database'],
    redis: ['database'],
    mongodb: ['database'],
    elasticsearch: ['database'],
    clickhouse: ['database'],
    tidb: ['database'],
    oceanbase: ['database'],
    dameng: ['database'],
    kingbase: ['database'],
    k8s: ['k8s-ops'],
    docker: ['linux'],
    containerd: ['linux'],
    podman: ['linux'],
    nginx: ['linux'],
    tomcat: ['linux'],
    kafka: ['linux'],
    ceph: ['linux'],
    nfs: ['linux'],
    switch: ['network-switch-inspector'],
    firewall: ['network-switch-inspector'],
    vpn: ['network-switch-inspector'],
    prometheus: ['prometheus', 'prometheus_tools'],
    alertmanager: ['prometheus', 'prometheus_tools'],
    grafana: ['prometheus', 'prometheus_tools'],
    loki: ['prometheus', 'prometheus_tools'],
    victoriametrics: ['prometheus', 'prometheus_tools'],
    manageengine: ['manage-engine'],
    zstack: ['zstack-cloud-dev'],
  };

  const matchedIds = skillMapping[subType] || [];
  const validIds = matchedIds.filter(id => allSkills.some(s => s.id === id));
  return new Set(validIds);
}

export default function ConnectionModal() {
  const closeModal = useStore((s) => s.closeModal)
  const addSession = useStore((s) => s.addSession)
  const addToast = useStore((s) => s.addToast)
  const setView = useStore((s) => s.setView)

  const [form, setForm] = useState({
    host: '', port: 22, username: 'root', password: '',
    remark: '', asset_type: 'linux', protocol: 'ssh', agent_profile: 'default',
    group_name: '未分组', allow_modifications: false,
    target_scope: 'asset', category: 'os', sub_type: 'linux',
    extra_args: {} as Record<string, unknown>,
  })
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [assetCategories, setAssetCategories] = useState(ASSET_CATEGORIES)
  const [assetSubTypes, setAssetSubTypes] = useState<Record<string, AssetSubType[]>>(ASSET_SUB_TYPES)
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set())
  const [skillSearch, setSkillSearch] = useState('')
  const [testing, setTesting] = useState(false)
  const [inspecting, setInspecting] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [inspectionResult, setInspectionResult] = useState<{
    ok: boolean
    summary: string
    checks: Array<{ title: string; status: string; output: string }>
  } | null>(null)

  const getProtocolForSubType = (category: string, subType: string) =>
    assetSubTypes[category]?.find(s => s.id === subType)?.asset_type || subType;
  const currentProtocol = getProtocolForSubType(form.category, form.sub_type)

  // Load backend asset catalog, then skills and optional asset prefill.
  useEffect(() => {
    Promise.all([
      getAssetTypes().catch(() => null),
      getSkillRegistry().catch(() => null),
    ]).then(([assetResponse, skillResponse]) => {
      let effectiveSubTypes = ASSET_SUB_TYPES
      const grouped: Record<string, AssetSubType[]> = {}
      ;(assetResponse?.data.types || []).forEach((item) => {
        if (!grouped[item.category]) grouped[item.category] = []
        grouped[item.category].push({
          id: item.id,
          label: item.label,
          asset_type: item.protocol,
          defaultPort: item.default_port,
          authMode: authModeFor(item.id),
        })
      })
      if (Object.keys(grouped).length > 0) {
        effectiveSubTypes = grouped
        setAssetSubTypes(grouped)
        const backendCategories = assetResponse?.data.categories || []
        setAssetCategories(
          backendCategories.length > 0
            ? backendCategories.filter((c) => grouped[c.id]).map((c) => ({ id: c.id, label: c.label }))
            : Object.keys(grouped).map((id) => ({
                id,
                label: CATEGORY_LABELS[id] || id.toUpperCase(),
              }))
        )
      }

      const protocolFor = (category: string, subType: string) =>
        effectiveSubTypes[category]?.find(s => s.id === subType)?.asset_type || subType;

      const loadedSkills = skillResponse?.data.registry?.filter((s) => !s.is_market) || [];
      setSkills(loadedSkills);

      const prefill = sessionStorage.getItem('prefill_asset');
      if (prefill) {
        try {
          const a = JSON.parse(prefill);
          const extraArgs = a.extra_args || {};
          let category = extraArgs.category || a.category;
          let sub_type = extraArgs.sub_type || a.sub_type;

          if (!category || !sub_type) {
            const p = a.asset_type || 'ssh';
            const protocol = a.protocol || extraArgs.login_protocol || extraArgs.protocol;
            for (const [cat, subs] of Object.entries(effectiveSubTypes)) {
              const match = subs.find(s => s.id === p || s.asset_type === p || (s.asset_type === protocol && s.id === p));
              if (match) {
                category = cat;
                sub_type = match.id;
                break;
              }
            }
            if (!category || !sub_type) { category = 'os'; sub_type = 'linux'; }
          }

          setForm(prev => ({
            ...prev,
            host: a.host || '', port: a.port || 22, username: a.username || 'root',
            password: a.password || '', remark: a.remark || '',
            asset_type: a.asset_type || sub_type || 'linux',
            protocol: a.protocol || protocolFor(category, sub_type),
            agent_profile: a.agent_profile || 'default', group_name: (a.tags && a.tags[0]) || '未分组',
            allow_modifications: false, target_scope: 'asset', extra_args: extraArgs,
            category, sub_type,
          }));

          if (a.skills && a.skills.length > 0) {
            setSelectedSkills(new Set(a.skills));
          } else {
            setSelectedSkills(autoSelectSkills(sub_type, loadedSkills));
          }
        } catch { /* ignore */ }
        sessionStorage.removeItem('prefill_asset');
      } else {
        setSelectedSkills(autoSelectSkills(form.sub_type, loadedSkills));
      }
    })
  }, [])

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    setInspectionResult(null)
    try {

  const filteredSkills = skills.filter(sk =>
    !skillSearch.trim() ||
    sk.name?.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.id.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.description?.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const isGlobal = form.target_scope === 'global'
      const host = isGlobal ? 'global' : form.host
      const username = isGlobal ? 'admin' : form.username

      const res = await testConnection({
        host, port: form.port, username,
        password: form.password, asset_type: isGlobal ? 'virtual' : form.sub_type,
        protocol: isGlobal ? 'virtual' : getProtocolForSubType(form.category, form.sub_type),
        extra_args: form.extra_args, active_skills: [],
        target_scope: form.target_scope,
        scope_value: form.target_scope === 'group' ? form.group_name : host,
      })
      setTestResult({ ok: res.status === 'success', msg: res.message })
    } catch (e: unknown) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : 'Test failed' })
    }
    setTesting(false)
  }

  const handleInspect = async () => {
    const isGlobal = form.target_scope === 'global'
    const host = isGlobal ? 'global' : form.host
    const username = isGlobal ? 'admin' : form.username

    if (!isGlobal && !form.host) { addToast('请输入主机地址', 'error'); return }
    setInspecting(true)
    setTestResult(null)
    setInspectionResult(null)
    try {
      const res = await inspectConnection({
        host, port: form.port, username,
        password: form.password, asset_type: isGlobal ? 'virtual' : form.sub_type,
        protocol: isGlobal ? 'virtual' : getProtocolForSubType(form.category, form.sub_type),
        extra_args: form.extra_args,
        active_skills: Array.from(selectedSkills),
        agent_profile: form.agent_profile,
        remark: form.remark,
        tags: [form.group_name],
        target_scope: form.target_scope,
        scope_value: form.target_scope === 'group' ? form.group_name : host,
        keep_session: false,
      })
      const inspection = res.data.inspection
      setInspectionResult({
        ok: res.status === 'success' && inspection.status !== 'error',
        summary: inspection.summary || inspection.message || res.message,
        checks: inspection.checks || [],
      })
    } catch (e: unknown) {
      setInspectionResult({
        ok: false,
        summary: e instanceof Error ? e.message : '巡检失败',
        checks: [],
      })
    }
    setInspecting(false)
  }

  const handleConnect = async () => {

  const filteredSkills = skills.filter(sk =>
    !skillSearch.trim() ||
    sk.name?.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.id.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.description?.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const isGlobal = form.target_scope === 'global'
    const host = isGlobal ? 'global' : form.host
    const username = isGlobal ? 'admin' : form.username

    if (!isGlobal && !form.host) { addToast('请输入主机地址', 'error'); return }
    setConnecting(true)
    try {
      const res = await connectSession({
        ...form,
        host, username, asset_type: isGlobal ? 'virtual' : form.sub_type,
        protocol: isGlobal ? 'virtual' : getProtocolForSubType(form.category, form.sub_type),
        active_skills: Array.from(selectedSkills),
        tags: [form.group_name],
        target_scope: form.target_scope,
        scope_value: form.target_scope === 'group' ? form.group_name : host,
      })
      const sid = res.data.session_id
      addSession({
        id: sid, host, remark: form.remark,
        isReadWriteMode: form.allow_modifications,
        skills: Array.from(selectedSkills), agentProfile: form.agent_profile,
        user: isGlobal ? 'opscore_agent' : username,
        asset_type: isGlobal ? 'virtual' : form.sub_type,
        protocol: isGlobal ? 'virtual' : getProtocolForSubType(form.category, form.sub_type),
        extra_args: form.extra_args, heartbeatEnabled: false,
        tags: [form.group_name], messages: [], isStreaming: false,
      })
      addToast(`已连接到 ${form.remark || host}`, 'success')
      closeModal()
      setView('chat')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '连接失败', 'error')
    }
    setConnecting(false)
  }

  const handleSaveOnly = async () => {

  const filteredSkills = skills.filter(sk =>
    !skillSearch.trim() ||
    sk.name?.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.id.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.description?.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const isGlobal = form.target_scope === 'global'
    const host = isGlobal ? 'global' : form.host
    const username = isGlobal ? 'admin' : form.username

    if (!isGlobal && !form.host) { addToast('请输入主机地址', 'error'); return }
    setConnecting(true)
    try {
      await batchImportAssets([{
        host, username, password: form.password, port: form.port,
        asset_type: isGlobal ? 'virtual' : form.sub_type,
        protocol: isGlobal ? 'virtual' : getProtocolForSubType(form.category, form.sub_type),
        remark: form.remark, agent_profile: form.agent_profile,
        extra_args: form.extra_args, skills: Array.from(selectedSkills),
        tags: [form.group_name]
      }])
      addToast(`已保存资产 ${form.remark || host}`, 'success')
      closeModal()
      if (useStore.getState().currentView !== 'assets') {
        setView('assets')
      }
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : '保存失败', 'error')
    }
    setConnecting(false)
  }

  const toggleSkill = (id: string) => {
    const next = new Set(selectedSkills)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelectedSkills(next)
  }


  const filteredSkills = skills.filter(sk =>
    !skillSearch.trim() ||
    sk.name?.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.id.toLowerCase().includes(skillSearch.toLowerCase()) ||
    sk.description?.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const isGlobal = form.target_scope === 'global'

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={closeModal}>
      <div className="bg-ops-panel rounded-xl p-6 w-[560px] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-ops-text">⚡ 新建连接</h2>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-lg">✕</button>
        </div>

        <div className="space-y-3">
          {/* Target Scope selector */}
          <div className="flex gap-4 mb-2 pb-2 border-b border-ops-surface0">
            {[
              { value: 'asset', label: '单台资产' },
              { value: 'group', label: '资产组别' },
              { value: 'global', label: '全局会话' },
            ].map((p) => (
              <label key={p.value} className="flex items-center gap-1.5 text-sm font-medium text-ops-subtext cursor-pointer hover:text-ops-text">
                <input type="radio" name="target_scope" value={p.value} checked={form.target_scope === p.value}
                  onChange={(e) => setForm({ ...form, target_scope: e.target.value })}
                  className="accent-ops-accent" />
                {p.label}
              </label>
            ))}
          </div>

          {/* Asset Taxonomy selector */}
          {form.target_scope !== 'global' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-ops-subtext mb-1 block">资产类别</label>
                <select
                  value={form.category}
                  onChange={(e) => {
                    const newCat = e.target.value;
                    const firstSub = assetSubTypes[newCat][0];
                    setForm({
                      ...form,
                      category: newCat,
                      sub_type: firstSub.id,
                      asset_type: firstSub.id,
                      protocol: firstSub.asset_type,
                      port: firstSub.defaultPort,
                      extra_args: {
                        category: newCat,
                        sub_type: firstSub.id,
                        ...(newCat === 'db' ? { db_type: firstSub.id } : {}),
                        ...(firstSub.id === 'oracle' ? { oracle_connect_type: 'sid' } : {}),
                      }
                    });
                    setSelectedSkills(autoSelectSkills(firstSub.id, skills));
                  }}
                  className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent appearance-none"
                >
                  {assetCategories.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-ops-subtext mb-1 block">连接类型</label>
                <select
                  value={form.sub_type}
                  onChange={(e) => {
                    const newSubId = e.target.value;
                    const subInfo = assetSubTypes[form.category].find(s => s.id === newSubId);
                    if (subInfo) {
                      setForm({
                        ...form,
                        sub_type: newSubId,
                        asset_type: newSubId,
                        protocol: subInfo.asset_type,
                        port: subInfo.defaultPort,
                        extra_args: {
                          category: form.category,
                          sub_type: newSubId,
                          ...(form.category === 'db' ? { db_type: newSubId } : {}),
                          ...(newSubId === 'oracle' ? { oracle_connect_type: 'sid' } : {}),
                        }
                      });
                      setSelectedSkills(autoSelectSkills(newSubId, skills));
                    }
                  }}
                  className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent appearance-none"
                >
                  {assetSubTypes[form.category]?.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
              </div>
            </div>
          )}

          {form.target_scope !== 'global' && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-ops-subtext">主机地址 {form.target_scope === 'group' && '(代表主机)'}</label>
                  <input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    placeholder="192.168.1.100" />
                </div>
                <div>
                  <label className="text-xs text-ops-subtext">端口</label>
                  <input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 22 })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                </div>
              </div>

              {(() => {
                const authVis = getAuthVisibility(assetSubTypes, form.sub_type, form.category, form.extra_args);
                if (!authVis.showUser && !authVis.showPass) return null;
                return (
                  <div className="grid grid-cols-2 gap-3">
                    {authVis.showUser && (
                      <div>
                        <label className="text-xs text-ops-subtext">用户名</label>
                        <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                      </div>
                    )}
                    {authVis.showPass && (
                      <div className={!authVis.showUser ? 'col-span-2' : ''}>
                        <label className="text-xs text-ops-subtext">密码</label>
                        <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                      </div>
                    )}
                  </div>
                );
              })()}
            </>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-ops-subtext">备注/别名</label>
              <input value={form.remark} onChange={(e) => setForm({ ...form, remark: e.target.value })}
                className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                placeholder="生产-WebServer-01" />
            </div>
            <div>
              <label className="text-xs text-ops-subtext">分组</label>
              <input value={form.group_name} onChange={(e) => setForm({ ...form, group_name: e.target.value })}
                className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                placeholder="未分组" />
            </div>
          </div>

          {/* Custom Extra Fields */}
          {form.target_scope !== 'global' && (
            <div className="space-y-3">
              {form.category === 'db' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-ops-subtext">
                      {form.sub_type === 'oracle' ? 'SID / Service Name' : 'Database Name / SID'}
                    </label>
                    <input value={(form.extra_args.db_name as string) || (form.extra_args.database as string) || ''}
                      onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, db_name: e.target.value } })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                  </div>
                  <div className="flex items-center mt-6">
                    <label className="flex items-center gap-2 text-sm text-ops-subtext cursor-pointer hover:text-ops-text">
                      <input type="checkbox" checked={!!form.extra_args.use_ssl}
                        onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, use_ssl: e.target.checked } })}
                        className="accent-ops-accent" />
                      Use SSL
                    </label>
                  </div>
                  {form.sub_type === 'oracle' && (
                    <>
                      <div>
                        <label className="text-xs text-ops-subtext">Oracle 连接类型</label>
                        <select
                          value={(form.extra_args.oracle_connect_type as string) || (form.extra_args.connect_type as string) || 'sid'}
                          onChange={(e) => setForm({
                            ...form,
                            extra_args: { ...form.extra_args, oracle_connect_type: e.target.value },
                          })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent appearance-none"
                        >
                          <option value="sid">SID</option>
                          <option value="service_name">Service Name</option>
                        </select>
                      </div>
                      <div className="flex items-center mt-6">
                        <label className="flex items-center gap-2 text-sm text-ops-subtext cursor-pointer hover:text-ops-text">
                          <input
                            type="checkbox"
                            checked={!!form.extra_args.use_thick_mode}
                            onChange={(e) => setForm({
                              ...form,
                              extra_args: { ...form.extra_args, use_thick_mode: e.target.checked },
                            })}
                            className="accent-ops-accent"
                          />
                          Thick Mode
                        </label>
                      </div>
                      {!!form.extra_args.use_thick_mode && (
                        <div className="col-span-2">
                          <label className="text-xs text-ops-subtext">Oracle Instant Client 目录</label>
                          <input
                            value={(form.extra_args.oracle_client_lib_dir as string) || ''}
                            onChange={(e) => setForm({
                              ...form,
                              extra_args: { ...form.extra_args, oracle_client_lib_dir: e.target.value },
                            })}
                            className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                            placeholder="例如 C:\\oracle\\instantclient_21_13，已配置环境变量时可留空"
                          />
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {form.sub_type === 'k8s' && (
                <div className="space-y-3">
                  <div className="flex gap-4">
                    <label className="flex items-center gap-1.5 text-sm text-ops-subtext cursor-pointer">
                      <input type="radio" name="k8s_auth" value="token" checked={form.extra_args.k8s_auth_type !== 'kubeconfig'}
                        onChange={() => setForm({ ...form, extra_args: { ...form.extra_args, k8s_auth_type: 'token' } })}
                        className="accent-ops-accent" /> Token
                    </label>
                    <label className="flex items-center gap-1.5 text-sm text-ops-subtext cursor-pointer">
                      <input type="radio" name="k8s_auth" value="kubeconfig" checked={form.extra_args.k8s_auth_type === 'kubeconfig'}
                        onChange={() => setForm({ ...form, extra_args: { ...form.extra_args, k8s_auth_type: 'kubeconfig' } })}
                        className="accent-ops-accent" /> Kubeconfig
                    </label>
                  </div>
                  {form.extra_args.k8s_auth_type === 'kubeconfig' ? (
                    <div>
                      <label className="text-xs text-ops-subtext">Kubeconfig</label>
                      <textarea value={(form.extra_args.kubeconfig as string) || ''}
                        onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, kubeconfig: e.target.value } })}
                        className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent h-24 font-mono text-xs" />
                    </div>
                  ) : (
                    <div>
                      <label className="text-xs text-ops-subtext">Bearer Token</label>
                      <input type="password" value={(form.extra_args.bearer_token as string) || ''}
                        onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, bearer_token: e.target.value } })}
                        className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                    </div>
                  )}
                </div>
              )}

              {currentProtocol === 'snmp' && (
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-ops-subtext">SNMP Version</label>
                    <select value={(form.extra_args.snmp_version as string) || 'v2c'}
                      onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, snmp_version: e.target.value } })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent appearance-none">
                      <option value="v2c">v2c</option>
                      <option value="v3">v3</option>
                    </select>
                  </div>
                  {((form.extra_args.snmp_version as string) || 'v2c') === 'v2c' ? (
                    <div>
                      <label className="text-xs text-ops-subtext">Community String</label>
                      <input type="password" value={(form.extra_args.community_string as string) || ''}
                        onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, community_string: e.target.value } })}
                        className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-ops-subtext">Auth User</label>
                        <input value={(form.extra_args.v3_auth_user as string) || ''}
                          onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, v3_auth_user: e.target.value } })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                      </div>
                      <div>
                        <label className="text-xs text-ops-subtext">认证协议</label>
                        <select value={(form.extra_args.v3_auth_protocol as string) || 'MD5'}
                          onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, v3_auth_protocol: e.target.value } })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent appearance-none">
                          <option value="MD5">MD5</option>
                          <option value="SHA">SHA</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-ops-subtext">Auth Pass</label>
                        <input type="password" value={(form.extra_args.v3_auth_pass as string) || ''}
                          onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, v3_auth_pass: e.target.value } })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                      </div>
                      <div className="col-span-1" />
                      <div>
                        <label className="text-xs text-ops-subtext">加密协议</label>
                        <select value={(form.extra_args.v3_priv_protocol as string) || 'DES'}
                          onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, v3_priv_protocol: e.target.value } })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent appearance-none">
                          <option value="DES">DES</option>
                          <option value="AES">AES</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-ops-subtext">Priv Pass</label>
                        <input type="password" value={(form.extra_args.v3_priv_pass as string) || ''}
                          onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, v3_priv_pass: e.target.value } })}
                          className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {['http_api', 'redfish'].includes(currentProtocol) && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-ops-subtext">访问协议</label>
                    <select
                      value={(form.extra_args.scheme as string) || (form.port === 443 ? 'https' : 'http')}
                      onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, scheme: e.target.value } })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent appearance-none"
                    >
                      <option value="https">HTTPS</option>
                      <option value="http">HTTP</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-ops-subtext">Base Path</label>
                    <input
                      value={(form.extra_args.base_path as string) || ''}
                      onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, base_path: e.target.value } })}
                      placeholder="/api 或留空"
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ops-subtext">API Token</label>
                    <input type="password" value={(form.extra_args.api_token as string) || ''}
                      onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, api_token: e.target.value } })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                  </div>
                  <div>
                    <label className="text-xs text-ops-subtext">Token Header</label>
                    <input
                      value={(form.extra_args.auth_header as string) || 'Authorization'}
                      onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, auth_header: e.target.value } })}
                      className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent"
                    />
                  </div>
                </div>
              )}

              {form.sub_type === 'switch' && (
                <div>
                  <label className="text-xs text-ops-subtext">Enable Password</label>
                  <input type="password" value={(form.extra_args.enable_pass as string) || ''}
                    onChange={(e) => setForm({ ...form, extra_args: { ...form.extra_args, enable_pass: e.target.value } })}
                    className="w-full bg-ops-dark border border-ops-surface1 rounded-lg px-3 py-2 text-sm text-ops-text mt-1 outline-none focus:border-ops-accent" />
                </div>
              )}
            </div>
          )}

          {/* Skills */}
          {skills.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs text-ops-subtext block">挂载技能</label>
                <input
                  type="text"
                  placeholder="搜索技能..."
                  value={skillSearch}
                  onChange={(e) => setSkillSearch(e.target.value)}
                  className="bg-ops-dark border border-ops-surface1 rounded px-2 py-0.5 text-[11px] text-ops-text outline-none focus:border-ops-accent w-40"
                />
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                {filteredSkills.map((sk) => (
                  <button key={sk.id} onClick={() => toggleSkill(sk.id)}
                    className={`text-[11px] px-2 py-1 rounded transition-colors ${selectedSkills.has(sk.id) ? 'bg-ops-accent/20 text-ops-accent' : 'bg-ops-surface0 text-ops-subtext hover:text-ops-text'}`}>
                    {sk.name || sk.id}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Permission toggle */}
          <label className="flex items-center gap-2 text-sm text-ops-subtext cursor-pointer">
            <input type="checkbox" checked={form.allow_modifications}
              onChange={(e) => setForm({ ...form, allow_modifications: e.target.checked })}
              className="accent-ops-accent" />
            允许 AI 执行修改操作（读写模式）
          </label>

          {/* Test result */}
          {testResult && (
            <div className={`text-xs p-2 rounded-lg ${testResult.ok ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
              {testResult.msg}
            </div>
          )}
          {inspectionResult && (
            <div className={`text-xs p-2 rounded-lg space-y-2 ${inspectionResult.ok ? 'bg-ops-success/15 text-ops-success' : 'bg-ops-alert/15 text-ops-alert'}`}>
              <div>{inspectionResult.summary}</div>
              {inspectionResult.checks.length > 0 && (
                <div className="space-y-1 max-h-40 overflow-y-auto text-ops-subtext">
                  {inspectionResult.checks.map((check) => (
                    <div key={check.title} className="bg-ops-dark/60 rounded p-1.5">
                      <div className="font-medium text-ops-text">{check.status === 'success' ? 'OK' : check.status.toUpperCase()} · {check.title}</div>
                      <pre className="whitespace-pre-wrap break-words text-[10px] mt-1">{check.output.slice(0, 800)}</pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex justify-between mt-5">
          <button onClick={handleSaveOnly} disabled={connecting || (!isGlobal && !form.host)}
            className="px-4 py-2 text-sm bg-ops-surface0 text-ops-subtext rounded-lg hover:text-ops-text disabled:opacity-40 transition-colors">
            💾 仅保存资产
          </button>
          <div className="flex gap-2">
            <button onClick={handleTest} disabled={testing || (!isGlobal && !form.host)}
              className="px-4 py-2 text-sm bg-ops-surface0 text-ops-subtext rounded-lg hover:text-ops-text disabled:opacity-40 transition-colors">
              {testing ? '测试中...' : '🔌 测试'}
            </button>
            <button onClick={handleInspect} disabled={inspecting || (!isGlobal && !form.host)}
              className="px-4 py-2 text-sm bg-ops-surface0 text-ops-subtext rounded-lg hover:text-ops-text disabled:opacity-40 transition-colors">
              {inspecting ? '巡检中...' : '🩺 巡检测试'}
            </button>
            <button onClick={handleConnect} disabled={connecting || (!isGlobal && !form.host)}
              className="px-4 py-2 text-sm bg-ops-accent text-ops-dark rounded-lg font-medium hover:bg-ops-accent/80 disabled:opacity-40 transition-colors">
              {connecting ? '连接中...' : '⚡ 连接'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
