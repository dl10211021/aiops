from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProfilePack:
    id: str
    name: str
    workload_family: str
    version: str = "1.0"
    component_types: list[str] = field(default_factory=list)
    relationship_types: list[str] = field(default_factory=list)
    discovery_rules: list[dict[str, Any]] = field(default_factory=list)
    metric_mappings: dict[str, Any] = field(default_factory=dict)
    log_patterns: list[str] = field(default_factory=list)
    health_checks: list[dict[str, Any]] = field(default_factory=list)
    investigation_playbooks: list[dict[str, Any]] = field(default_factory=list)
    default_unknown_nodes: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return dict(self.__dict__)
