from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Confidence = Literal["confirmed", "inferred", "unknown", "pending_review"]
ComponentStatus = Literal["active", "degraded", "unknown", "pending_review"]
SourceOrigin = Literal["session", "asset", "manual", "api", "unknown"]


COMPONENT_TYPES = {
    "business_entry",
    "application_service",
    "api_gateway",
    "load_balancer",
    "k8s_cluster",
    "k8s_namespace",
    "k8s_workload",
    "container_registry",
    "os_host",
    "vm",
    "physical_server",
    "hypervisor_host",
    "network_switch",
    "router",
    "firewall",
    "vlan",
    "storage_pool",
    "database_system",
    "database_cluster",
    "database_instance",
    "database_endpoint",
    "big_data_cluster",
    "mpp_database",
    "middleware",
    "observability_source",
    "security_source",
    "unknown",
}

RELATIONSHIP_TYPES = {
    "depends_on",
    "runs_on",
    "hosted_by",
    "connects_to",
    "queries",
    "publishes_to",
    "monitored_by",
    "protected_by",
    "routes_to",
    "stores_in",
    "queried_through_session",
    "unknown",
}

OBSERVABILITY_LAYERS = [
    "business",
    "entry",
    "application",
    "container",
    "os",
    "virtualization",
    "physical",
    "network",
    "storage",
    "database",
    "big_data",
    "middleware",
    "security",
    "observability",
    "unknown",
]


class BusinessSystem(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    environment: str = Field(default="unknown", max_length=80)
    description: str = Field(default="", max_length=600)
    criticality: str = Field(default="unknown", max_length=40)
    owner: str = Field(default="", max_length=80)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="unknown", max_length=40)
    profile_completeness: int = Field(default=0, ge=0, le=100)
    created_at: str = ""
    updated_at: str = ""


class Component(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    system_id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=160)
    component_type: str = Field(default="unknown", max_length=80)
    layer: str = Field(default="unknown", max_length=80)
    workload_family: str = Field(default="unknown", max_length=80)
    profile_pack_id: str | None = Field(default=None, max_length=120)
    environment: str = Field(default="unknown", max_length=80)
    status: ComponentStatus = "unknown"
    confidence: Confidence = "unknown"
    source: str = Field(default="manual", max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_component_contract(self):
        if self.component_type not in COMPONENT_TYPES:
            raise ValueError(f"unsupported component_type: {self.component_type}")
        if self.layer not in OBSERVABILITY_LAYERS:
            raise ValueError(f"unsupported layer: {self.layer}")
        return self


class Relationship(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    system_id: str = Field(..., min_length=1, max_length=120)
    from_component_id: str = Field(..., min_length=1, max_length=120)
    to_component_id: str = Field(..., min_length=1, max_length=120)
    relationship_type: str = Field(..., min_length=1, max_length=80)
    confidence: Confidence = "unknown"
    source: str = Field(default="manual", max_length=80)
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_relationship_contract(self):
        if self.relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"unsupported relationship_type: {self.relationship_type}")
        if self.from_component_id == self.to_component_id:
            raise ValueError("relationship endpoints must be different")
        return self


class ObservableSource(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=160)
    source_type: str = Field(..., min_length=1, max_length=80)
    source_origin: SourceOrigin = "unknown"
    status: str = Field(default="unknown", max_length=40)
    capabilities: list[str] = Field(default_factory=list)
    bound_system_ids: list[str] = Field(default_factory=list)
    bound_component_ids: list[str] = Field(default_factory=list)
    session_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProfilePack(BaseModel):
    id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    workload_family: str = Field(..., min_length=1, max_length=80)
    layer: str = Field(default="unknown", max_length=80)
    component_types: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    read_only: bool = True

    @model_validator(mode="after")
    def validate_pack_contract(self):
        if self.layer not in OBSERVABILITY_LAYERS:
            raise ValueError(f"unsupported layer: {self.layer}")
        invalid_types = [item for item in self.component_types if item not in COMPONENT_TYPES]
        if invalid_types:
            raise ValueError(f"unsupported component_types: {', '.join(invalid_types)}")
        return self


class BusinessSystemProfile(BaseModel):
    system: BusinessSystem
    components: list[Component] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    observable_sources: list[ObservableSource] = Field(default_factory=list)
    unknowns: list[Component] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_relationship_endpoints(self):
        component_ids = {component.id for component in [*self.components, *self.unknowns]}
        missing: list[str] = []
        for relation in self.relationships:
            if relation.from_component_id not in component_ids:
                missing.append(relation.from_component_id)
            if relation.to_component_id not in component_ids:
                missing.append(relation.to_component_id)
        if missing:
            raise ValueError(f"relationship references unknown components: {', '.join(sorted(set(missing)))}")
        return self

    def layer_counts(self) -> dict[str, int]:
        counts = {layer: 0 for layer in OBSERVABILITY_LAYERS}
        for component in [*self.components, *self.unknowns]:
            counts[component.layer] = counts.get(component.layer, 0) + 1
        return {layer: count for layer, count in counts.items() if count}

    def summary(self) -> dict[str, Any]:
        return {
            "system": self.system.model_dump(),
            "component_count": len(self.components),
            "unknown_count": len(self.unknowns),
            "relationship_count": len(self.relationships),
            "source_count": len(self.observable_sources),
            "layer_counts": self.layer_counts(),
        }
