import type { SkillInfo } from '@/types'

export const autoSelectSkills = (subType: string, allSkills: SkillInfo[]) => {
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
    elastic_stack: ['prometheus', 'prometheus_tools'],
    kibana: ['prometheus', 'prometheus_tools'],
    logstash: ['prometheus', 'prometheus_tools'],
    graylog: ['prometheus', 'prometheus_tools'],
    opensearch: ['prometheus', 'prometheus_tools'],
    victoriametrics: ['prometheus', 'prometheus_tools'],
    manageengine: ['manage-engine'],
    zstack: ['zstack-cloud-dev'],
  }

  const matchedIds = skillMapping[subType] || []
  const validIds = matchedIds.filter((id) => allSkills.some((skill) => skill.id === id))
  return new Set(validIds)
}
