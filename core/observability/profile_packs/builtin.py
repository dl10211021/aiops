from __future__ import annotations

from core.observability.profile_packs.base import ProfilePack


def _pack(
    pack_id: str,
    name: str,
    family: str,
    components: list[str],
    relationships: list[str] | None = None,
    metrics: dict | None = None,
) -> ProfilePack:
    return ProfilePack(
        id=pack_id,
        name=name,
        workload_family=family,
        component_types=components,
        relationship_types=relationships or ["depends_on", "observed_by"],
        metric_mappings=metrics or {"health": ["up"], "latency": [], "saturation": []},
        investigation_playbooks=[
            {"role": f"{family}_agent", "task": "collect_readonly_health_evidence"},
        ],
        default_unknown_nodes=[
            {"component_type": "unknown", "name": f"unknown {name} dependency"},
        ],
    )


def builtin_profile_packs() -> list[ProfilePack]:
    return [
        _pack("infra_os", "通用操作系统", "os", ["os_host"], ["has_os", "runs_on"]),
        _pack("infra_physical_server", "物理服务器", "physical", ["physical_server"]),
        _pack("infra_network_device", "网络设备", "network", ["network_switch", "router", "firewall", "vlan"]),
        _pack("infra_virtualization_generic", "通用虚拟化", "virtualization", ["vm", "hypervisor_host", "cloud_cluster"]),
        _pack("infra_zstack", "ZStack", "virtualization", ["cloud_cluster", "vm", "hypervisor_host"]),
        _pack("infra_vmware", "VMware", "virtualization", ["cloud_cluster", "vm", "hypervisor_host", "datastore"]),
        _pack("container_k8s", "Kubernetes", "container", ["k8s_cluster", "k8s_namespace", "k8s_workload", "k8s_pod", "k8s_service"]),
        _pack("database_generic", "通用数据库", "database", ["database_system", "database_instance", "database_endpoint"], ["uses_database", "replicates_to"]),
        _pack("database_mysql", "MySQL", "database", ["database_instance", "database_replica"]),
        _pack("database_postgresql", "PostgreSQL", "database", ["database_instance", "database_replica"]),
        _pack("database_mongodb", "MongoDB", "distributed_database", ["database_cluster", "database_shard", "database_node"]),
        _pack("database_tidb", "TiDB", "distributed_database", ["database_cluster", "database_node"]),
        _pack("database_oracle", "Oracle", "database", ["database_instance", "database_endpoint"]),
        _pack("database_redis", "Redis", "database", ["cache", "database_instance"]),
        _pack("database_elasticsearch", "Elasticsearch", "database", ["database_cluster", "database_node"]),
        _pack("mpp_generic", "通用 MPP", "mpp_database", ["mpp_cluster", "database_node"]),
        _pack("mpp_clickhouse", "ClickHouse", "mpp_database", ["mpp_cluster", "database_node"]),
        _pack("mpp_doris", "Doris", "mpp_database", ["mpp_cluster", "database_node"]),
        _pack("mpp_starrocks", "StarRocks", "mpp_database", ["mpp_cluster", "database_node"]),
        _pack("mpp_greenplum", "Greenplum", "mpp_database", ["mpp_cluster", "database_node"]),
        _pack("bigdata_generic", "通用大数据", "bigdata", ["bigdata_cluster", "bigdata_job"]),
        _pack("bigdata_hadoop", "Hadoop", "bigdata", ["bigdata_cluster", "bigdata_job"]),
        _pack("bigdata_spark", "Spark", "bigdata", ["bigdata_cluster", "bigdata_job"]),
        _pack("bigdata_flink", "Flink", "bigdata", ["bigdata_cluster", "bigdata_job"]),
        _pack("bigdata_kafka", "Kafka", "bigdata", ["message_queue", "bigdata_cluster"]),
        _pack("middleware_generic", "通用中间件", "middleware", ["middleware", "message_queue"]),
        _pack("security_generic", "通用安全工具", "security", ["security_tool"]),
        _pack(
            "observability_prometheus",
            "Prometheus",
            "observability",
            ["observable_source"],
            ["observed_by", "discovered_from"],
            {"availability": ["up"], "cpu": ["node_cpu_seconds_total"], "memory": ["node_memory_MemAvailable_bytes"]},
        ),
    ]

