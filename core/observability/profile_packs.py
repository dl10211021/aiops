from __future__ import annotations

from core.observability.models import ProfilePack


def builtin_profile_packs() -> list[ProfilePack]:
    return [
        ProfilePack(
            id="generic-os",
            name="通用 OS 主机",
            workload_family="os",
            layer="os",
            component_types=["os_host", "vm", "physical_server"],
            source_types=["ssh", "winrm", "node_exporter", "snmp"],
            capabilities=["inspect_cpu", "inspect_memory", "inspect_disk", "inspect_network", "inspect_process"],
            signals=["cpu", "memory", "disk", "load", "network", "process"],
        ),
        ProfilePack(
            id="generic-k8s",
            name="Kubernetes 工作负载",
            workload_family="container",
            layer="container",
            component_types=["k8s_cluster", "k8s_namespace", "k8s_workload"],
            source_types=["kubernetes_api", "prometheus"],
            capabilities=["inspect_pods", "inspect_events", "inspect_services", "inspect_ingress"],
            signals=["pod_restart", "pending_pod", "throttling", "service_error", "ingress_error"],
        ),
        ProfilePack(
            id="generic-database",
            name="通用数据库",
            workload_family="database",
            layer="database",
            component_types=["database_system", "database_cluster", "database_instance", "database_endpoint"],
            source_types=["database_connection", "prometheus", "jdbc"],
            capabilities=["inspect_connections", "inspect_slow_queries", "inspect_locks", "inspect_replication"],
            signals=["connections", "latency", "slow_query", "lock_wait", "replication_lag"],
        ),
        ProfilePack(
            id="generic-network",
            name="网络与交换设备",
            workload_family="network",
            layer="network",
            component_types=["network_switch", "router", "firewall", "vlan"],
            source_types=["snmp", "netflow", "api"],
            capabilities=["inspect_ports", "inspect_errors", "inspect_routes", "inspect_acl"],
            signals=["port_error", "packet_drop", "bandwidth", "route_change", "acl_hit"],
        ),
        ProfilePack(
            id="generic-virtualization",
            name="虚拟化与物理平台",
            workload_family="platform",
            layer="virtualization",
            component_types=["vm", "hypervisor_host", "physical_server"],
            source_types=["vmware", "zstack", "ipmi", "api"],
            capabilities=["inspect_vm_state", "inspect_host_capacity", "inspect_storage_binding"],
            signals=["vm_status", "host_capacity", "datastore_latency", "snapshot_growth"],
        ),
        ProfilePack(
            id="prometheus-source",
            name="Prometheus 观测源",
            workload_family="observability",
            layer="observability",
            component_types=["observability_source"],
            source_types=["prometheus"],
            capabilities=["query_metrics", "query_alerts", "discover_targets", "query_promql", "map_exporter_to_component"],
            signals=["target_up", "alert_state", "metric_timeseries", "exporter_label"],
        ),
        ProfilePack(
            id="generic-security",
            name="安全与流量源",
            workload_family="security",
            layer="security",
            component_types=["security_source", "firewall"],
            source_types=["edr", "ndr", "siem", "firewall"],
            capabilities=["inspect_security_events", "inspect_network_flows", "inspect_endpoint_status"],
            signals=["security_event", "flow_anomaly", "endpoint_alert", "policy_block"],
        ),
    ]
