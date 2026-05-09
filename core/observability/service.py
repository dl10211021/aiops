from __future__ import annotations

from core.observability.models import (
    BusinessSystem,
    BusinessSystemProfile,
    Component,
    ObservableSource,
    Relationship,
)
from core.observability.profile_packs import builtin_profile_packs


def _sample_profile() -> BusinessSystemProfile:
    system = BusinessSystem(
        id="global-portal-test",
        name="集团global协作门户",
        environment="测试环境",
        description="从用户已知的 registry、K8s 节点、中间件服务器和 Prometheus 会话开始建模。",
        criticality="important",
        owner="运维团队",
        aliases=["global门户", "协作门户"],
        tags=["k8s", "middleware", "partial-profile"],
        status="unknown",
        profile_completeness=36,
        created_at="2026-05-08 00:00:00",
        updated_at="2026-05-08 00:00:00",
    )
    components = [
        Component(
            id="cmp-registry",
            system_id=system.id,
            name="registry 测试环境",
            component_type="container_registry",
            layer="container",
            workload_family="container",
            profile_pack_id="generic-k8s",
            environment=system.environment,
            status="unknown",
            confidence="confirmed",
            source="user_input",
        ),
        Component(
            id="cmp-k8s-master",
            system_id=system.id,
            name="k8s-master 测试环境",
            component_type="k8s_cluster",
            layer="container",
            workload_family="container",
            profile_pack_id="generic-k8s",
            environment=system.environment,
            status="unknown",
            confidence="confirmed",
            source="user_input",
        ),
        Component(
            id="cmp-k8s-workers",
            system_id=system.id,
            name="k8s-worker 测试环境",
            component_type="k8s_workload",
            layer="container",
            workload_family="container",
            profile_pack_id="generic-k8s",
            environment=system.environment,
            status="unknown",
            confidence="confirmed",
            source="user_input",
            metadata={"count": 2},
        ),
        Component(
            id="cmp-middleware",
            system_id=system.id,
            name="中间件服务器 测试环境",
            component_type="middleware",
            layer="middleware",
            workload_family="middleware",
            environment=system.environment,
            status="unknown",
            confidence="confirmed",
            source="user_input",
        ),
    ]
    unknowns = [
        Component(
            id="unk-entry",
            system_id=system.id,
            name="入口 unknown",
            component_type="unknown",
            layer="entry",
            status="unknown",
            confidence="unknown",
            source="unknown_placeholder",
        ),
        Component(
            id="unk-os",
            system_id=system.id,
            name="OS unknown",
            component_type="unknown",
            layer="os",
            status="unknown",
            confidence="unknown",
            source="unknown_placeholder",
        ),
        Component(
            id="unk-platform",
            system_id=system.id,
            name="虚拟化/物理平台 unknown",
            component_type="unknown",
            layer="virtualization",
            status="unknown",
            confidence="unknown",
            source="unknown_placeholder",
        ),
        Component(
            id="unk-network",
            system_id=system.id,
            name="交换机/VLAN/端口 unknown",
            component_type="unknown",
            layer="network",
            status="unknown",
            confidence="unknown",
            source="unknown_placeholder",
        ),
        Component(
            id="unk-database",
            system_id=system.id,
            name="数据库 unknown",
            component_type="unknown",
            layer="database",
            status="unknown",
            confidence="unknown",
            source="unknown_placeholder",
        ),
    ]
    relationships = [
        Relationship(
            id="rel-entry-k8s",
            system_id=system.id,
            from_component_id="unk-entry",
            to_component_id="cmp-k8s-master",
            relationship_type="routes_to",
            confidence="unknown",
            source="unknown_placeholder",
        ),
        Relationship(
            id="rel-k8s-middleware",
            system_id=system.id,
            from_component_id="cmp-k8s-workers",
            to_component_id="cmp-middleware",
            relationship_type="depends_on",
            confidence="pending_review",
            source="user_input",
        ),
    ]
    sources = [
        ObservableSource(
            id="src-prometheus-session",
            name="Prometheus 会话",
            source_type="prometheus",
            source_origin="session",
            status="candidate",
            capabilities=["query_metrics", "query_alerts", "discover_targets", "query_promql", "map_exporter_to_component"],
            bound_system_ids=[system.id],
            metadata={"registration_state": "candidate_from_session"},
        )
    ]
    return BusinessSystemProfile(
        system=system,
        components=components,
        relationships=relationships,
        observable_sources=sources,
        unknowns=unknowns,
    )


class ObservabilityCatalogService:
    def __init__(self):
        self._profiles = [_sample_profile()]

    def list_systems(self) -> list[dict]:
        return [profile.summary() for profile in self._profiles]

    def get_profile(self, system_id: str) -> BusinessSystemProfile | None:
        for profile in self._profiles:
            if profile.system.id == system_id:
                return profile
        return None

    def list_sources(self) -> list[dict]:
        sources: list[dict] = []
        for profile in self._profiles:
            sources.extend(source.model_dump() for source in profile.observable_sources)
        return sources

    def list_profile_packs(self) -> list[dict]:
        return [pack.model_dump() for pack in builtin_profile_packs()]

    def overview(self) -> dict:
        systems = self.list_systems()
        sources = self.list_sources()
        packs = self.list_profile_packs()
        return {
            "system_count": len(systems),
            "source_count": len(sources),
            "profile_pack_count": len(packs),
            "unknown_count": sum(item["unknown_count"] for item in systems),
            "pending_review_count": sum(
                1
                for profile in self._profiles
                for relation in profile.relationships
                if relation.confidence == "pending_review"
            ),
        }


catalog_service = ObservabilityCatalogService()
