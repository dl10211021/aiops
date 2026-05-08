from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


COMPONENT_TYPES = {
    "business_entry",
    "application_service",
    "batch_job",
    "api_gateway",
    "load_balancer",
    "dns_record",
    "k8s_cluster",
    "k8s_namespace",
    "k8s_workload",
    "k8s_pod",
    "k8s_service",
    "container_registry",
    "os_host",
    "vm",
    "physical_server",
    "hypervisor_host",
    "cloud_cluster",
    "network_switch",
    "router",
    "firewall",
    "vlan",
    "switch_port",
    "storage_pool",
    "datastore",
    "san",
    "database_system",
    "database_cluster",
    "database_instance",
    "database_node",
    "database_endpoint",
    "database_shard",
    "database_replica",
    "database_partition",
    "middleware",
    "message_queue",
    "cache",
    "bigdata_cluster",
    "bigdata_job",
    "mpp_cluster",
    "security_tool",
    "observable_source",
    "unknown",
}

RELATIONSHIP_TYPES = {
    "runs_on",
    "has_os",
    "deployed_to",
    "hosted_on",
    "managed_by",
    "connected_to",
    "attached_to_network",
    "routes_through",
    "exposes_service_via",
    "pulls_image_from",
    "uses_database",
    "uses_middleware",
    "uses_storage",
    "uses_datastore",
    "uses_shared_storage",
    "uses_interconnect",
    "replicates_to",
    "depends_on",
    "observed_by",
    "logs_to",
    "traces_to",
    "protected_by",
    "queried_through_session",
    "discovered_from",
    "inferred_from",
}

SOURCE_TYPES = {
    "prometheus",
    "zabbix",
    "grafana",
    "loki",
    "elk",
    "skywalking",
    "pinpoint",
    "jaeger",
    "zstack",
    "vmware_vcenter",
    "k8s_api",
    "ssh_command",
    "database_connection",
    "snmp",
    "netflow",
    "sflow",
    "ndr",
    "edr",
    "antivirus",
    "siem",
    "cmdb",
    "itsm",
    "custom_http_api",
}

SOURCE_CAPABILITIES = {
    "query_metrics",
    "query_logs",
    "query_alerts",
    "query_traces",
    "discover_targets",
    "discover_topology",
    "query_changes",
    "query_security_events",
    "query_network_flows",
    "run_readonly_check",
    "query_promql",
    "map_exporter_to_component",
}

CONFIDENCE_VALUES = {"confirmed", "discovered", "inferred", "unknown"}
RELATIONSHIP_STATUSES = {"confirmed", "discovered", "inferred", "unknown", "pending_review", "rejected"}
SYSTEM_STATUSES = {"active", "inactive", "draft", "archived"}
INVESTIGATION_STATUSES = {"open", "planned", "running", "completed", "failed", "closed"}
TASK_STATUSES = {"pending", "running", "completed", "failed", "skipped"}
ROOT_CAUSE_STATUSES = {"candidate", "confirmed", "rejected", "needs_more_evidence"}


LAYER_ORDER = [
    "business",
    "entry",
    "app",
    "container",
    "os",
    "virtualization",
    "physical",
    "network",
    "database",
    "bigdata",
    "mpp",
    "middleware",
    "security",
    "observability",
    "unknown",
]

COMPONENT_LAYER = {
    "business_entry": "entry",
    "application_service": "app",
    "batch_job": "app",
    "api_gateway": "entry",
    "load_balancer": "entry",
    "dns_record": "entry",
    "k8s_cluster": "container",
    "k8s_namespace": "container",
    "k8s_workload": "container",
    "k8s_pod": "container",
    "k8s_service": "container",
    "container_registry": "container",
    "os_host": "os",
    "vm": "virtualization",
    "hypervisor_host": "virtualization",
    "cloud_cluster": "virtualization",
    "physical_server": "physical",
    "network_switch": "network",
    "router": "network",
    "firewall": "network",
    "vlan": "network",
    "switch_port": "network",
    "storage_pool": "physical",
    "datastore": "physical",
    "san": "physical",
    "database_system": "database",
    "database_cluster": "database",
    "database_instance": "database",
    "database_node": "database",
    "database_endpoint": "database",
    "database_shard": "database",
    "database_replica": "database",
    "database_partition": "database",
    "middleware": "middleware",
    "message_queue": "middleware",
    "cache": "middleware",
    "bigdata_cluster": "bigdata",
    "bigdata_job": "bigdata",
    "mpp_cluster": "mpp",
    "security_tool": "security",
    "observable_source": "observability",
    "unknown": "unknown",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def require_allowed(value: str, allowed: set[str], field_name: str) -> str:
    raw = str(value or "").strip()
    if raw not in allowed:
        raise ValueError(f"invalid {field_name}: {raw}")
    return raw


@dataclass
class BusinessSystem:
    name: str
    environment: str
    id: str = field(default_factory=lambda: new_id("obs_sys"))
    description: str = ""
    criticality: str = "medium"
    owner: str = ""
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: str = "active"
    profile_completeness: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("business system name is required")
        require_allowed(self.status, SYSTEM_STATUSES, "system status")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Component:
    system_id: str
    name: str
    component_type: str
    workload_family: str = "application"
    id: str = field(default_factory=lambda: new_id("obs_cmp"))
    profile_pack_id: str = ""
    environment: str = ""
    status: str = "unknown"
    confidence: str = "unknown"
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.system_id:
            raise ValueError("system_id is required")
        if not self.name.strip():
            raise ValueError("component name is required")
        require_allowed(self.component_type, COMPONENT_TYPES, "component type")
        require_allowed(self.confidence, CONFIDENCE_VALUES, "confidence")

    @property
    def layer(self) -> str:
        return COMPONENT_LAYER.get(self.component_type, "unknown")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Relationship:
    system_id: str
    from_component_id: str
    to_component_id: str
    relationship_type: str
    id: str = field(default_factory=lambda: new_id("obs_rel"))
    confidence: str = "unknown"
    source: str = "manual"
    evidence_id: str = ""
    status: str = "pending_review"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.system_id or not self.from_component_id or not self.to_component_id:
            raise ValueError("relationship endpoints are required")
        if self.from_component_id == self.to_component_id:
            raise ValueError("relationship endpoints must be different")
        require_allowed(self.relationship_type, RELATIONSHIP_TYPES, "relationship type")
        require_allowed(self.confidence, CONFIDENCE_VALUES, "confidence")
        require_allowed(self.status, RELATIONSHIP_STATUSES, "relationship status")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ObservableSource:
    name: str
    source_type: str
    id: str = field(default_factory=lambda: new_id("obs_src"))
    source_origin: str = "manual"
    session_id: str = ""
    endpoint: str = ""
    capabilities: list[str] = field(default_factory=list)
    auth_ref: str = ""
    status: str = "unknown"
    last_checked_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("source name is required")
        require_allowed(self.source_type, SOURCE_TYPES, "source type")
        invalid = set(self.capabilities) - SOURCE_CAPABILITIES
        if invalid:
            raise ValueError(f"invalid source capabilities: {sorted(invalid)}")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Investigation:
    system_id: str
    title: str
    symptom: str
    id: str = field(default_factory=lambda: new_id("obs_inv"))
    time_window_start: str = ""
    time_window_end: str = ""
    severity: str = "warning"
    status: str = "open"
    created_by: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.system_id:
            raise ValueError("system_id is required")
        if not self.title.strip():
            raise ValueError("investigation title is required")
        require_allowed(self.status, INVESTIGATION_STATUSES, "investigation status")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class InvestigationTask:
    investigation_id: str
    agent_role: str
    task_type: str
    id: str = field(default_factory=lambda: new_id("obs_task"))
    target_component_id: str = ""
    source_id: str = ""
    status: str = "pending"
    input: dict[str, Any] = field(default_factory=dict)
    output_summary: str = ""
    started_at: str = ""
    finished_at: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.investigation_id:
            raise ValueError("investigation_id is required")
        require_allowed(self.status, TASK_STATUSES, "task status")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Evidence:
    investigation_id: str
    evidence_type: str
    title: str
    summary: str
    id: str = field(default_factory=lambda: new_id("obs_evd"))
    task_id: str = ""
    component_id: str = ""
    source_id: str = ""
    raw_ref: str = ""
    raw_excerpt: str = ""
    confidence: str = "unknown"
    timestamp: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.investigation_id:
            raise ValueError("investigation_id is required")
        if not self.title.strip():
            raise ValueError("evidence title is required")
        require_allowed(self.confidence, CONFIDENCE_VALUES, "confidence")

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RootCauseCandidate:
    investigation_id: str
    title: str
    description: str
    id: str = field(default_factory=lambda: new_id("obs_rc"))
    likelihood: int = 50
    impact: str = "medium"
    confidence: str = "unknown"
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)
    status: str = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.investigation_id:
            raise ValueError("investigation_id is required")
        require_allowed(self.confidence, CONFIDENCE_VALUES, "confidence")
        require_allowed(self.status, ROOT_CAUSE_STATUSES, "root cause status")
        self.likelihood = max(0, min(100, int(self.likelihood)))

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


def relationship_endpoints_are_valid(
    relationship: Relationship,
    components: list[Component | dict[str, Any]],
) -> bool:
    component_ids = {
        item.id if isinstance(item, Component) else str(item.get("id") or "")
        for item in components
    }
    return relationship.from_component_id in component_ids and relationship.to_component_id in component_ids
