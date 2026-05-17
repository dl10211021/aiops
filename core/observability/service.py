from __future__ import annotations

from datetime import datetime

from core.observability.models import (
    BusinessSystem,
    BusinessSystemProfile,
    Component,
    DiscoveryCandidate,
    EvidenceItem,
    InvestigationItem,
    InvestigationTask,
    ObservableSource,
    Relationship,
    RootCauseCandidate,
)
from core.observability.profile_packs import builtin_profile_packs


_PROFILE_REQUIRED_LAYERS = {"entry", "application", "container", "os", "virtualization", "network", "database", "middleware", "observability"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _slug(value: object) -> str:
    text = str(value or "unknown").strip().lower()
    return "".join(ch if ch.isalnum() else "-" for ch in text).strip("-") or "unknown"


def _component_shape(asset_type: str, protocol: str) -> tuple[str, str, str, str | None]:
    text = f"{asset_type} {protocol}".lower()
    if "prometheus" in text or "zabbix" in text or "grafana" in text:
        return "observability_source", "observability", "observability", "prometheus-source"
    if any(token in text for token in ["mysql", "postgres", "oracle", "mongodb", "tidb", "database"]):
        return "database_instance", "database", "database", "generic-database"
    if any(token in text for token in ["k8s", "kubernetes"]):
        return "k8s_cluster", "container", "container", "generic-k8s"
    if any(token in text for token in ["vmware", "zstack", "virtual"]):
        return "vm", "virtualization", "platform", "generic-virtualization"
    if any(token in text for token in ["switch", "router", "firewall", "snmp", "network"]):
        return "network_switch", "network", "network", "generic-network"
    return "os_host", "os", "os", "generic-os"


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
        self._discovery_candidates = self._sample_discovery_candidates()
        self._investigations = self._sample_investigations()

    def _sample_discovery_candidates(self) -> list[DiscoveryCandidate]:
        system_id = "global-portal-test"
        return [
            DiscoveryCandidate(
                id="disc-k8s-node-exporter",
                system_id=system_id,
                candidate_type="component",
                title="从 Prometheus target 发现 K8s 节点 exporter",
                summary="Prometheus 会话中出现 node-exporter 标签，可作为 OS 层候选节点补全。",
                status="pending_review",
                confidence="inferred",
                proposed_component=Component(
                    id="cmp-node-exporter-hosts",
                    system_id=system_id,
                    name="node-exporter hosts",
                    component_type="os_host",
                    layer="os",
                    workload_family="os",
                    profile_pack_id="generic-os",
                    environment="测试环境",
                    status="unknown",
                    confidence="inferred",
                    source="prometheus_target",
                    metadata={"label_keys": ["job", "instance", "cluster"]},
                ),
                evidence_ids=["ev-prom-target-node-exporter"],
                evidence_summary=["job=node-exporter", "cluster=global-test", "instance 标签可映射主机"],
                suggested_actions=["确认主机命名", "绑定已有资产", "生成 OS 层只读巡检计划"],
                created_at="2026-05-08 00:00:00",
            ),
            DiscoveryCandidate(
                id="disc-k8s-middleware-relation",
                system_id=system_id,
                candidate_type="relationship",
                title="K8s workload 可能依赖中间件服务器",
                summary="用户输入同时包含 K8s worker 与中间件服务器，关系需要人工确认后进入拓扑。",
                status="pending_review",
                confidence="pending_review",
                proposed_relationship=Relationship(
                    id="rel-k8s-middleware-candidate",
                    system_id=system_id,
                    from_component_id="cmp-k8s-workers",
                    to_component_id="cmp-middleware",
                    relationship_type="depends_on",
                    confidence="pending_review",
                    source="user_input",
                    evidence_ids=["ev-user-known-components"],
                ),
                evidence_ids=["ev-user-known-components"],
                evidence_summary=["已知组件同时属于测试环境", "缺少端口、服务名或调用链证据"],
                suggested_actions=["确认调用方向", "补充端口/协议", "等待日志或链路证据"],
                created_at="2026-05-08 00:00:00",
            ),
        ]

    def _sample_investigations(self) -> list[InvestigationItem]:
        investigation_id = "inv-global-portal-slow"
        tasks = [
            InvestigationTask(
                id="task-prometheus-baseline",
                investigation_id=investigation_id,
                agent_role="Prometheus Agent",
                source_id="src-prometheus-session",
                task_type="query_metrics_alerts",
                status="pending",
                input_json={"window": "最近 2 小时", "read_only": True},
                output_summary="等待执行：查询 target up、告警状态、CPU/内存/重启等基础曲线。",
            ),
            InvestigationTask(
                id="task-k8s-health",
                investigation_id=investigation_id,
                agent_role="K8s Agent",
                target_component_id="cmp-k8s-workers",
                task_type="inspect_k8s_workload",
                status="pending",
                input_json={"checks": ["pods", "events", "services", "ingress"], "read_only": True},
                output_summary="等待执行：检查 Pod 重启、事件、Service/Ingress 与资源限制。",
            ),
            InvestigationTask(
                id="task-summary",
                investigation_id=investigation_id,
                agent_role="Summary Agent",
                task_type="correlate_evidence",
                status="pending",
                input_json={"requires_evidence": True},
                output_summary="等待执行：汇总时间线、证据和根因候选。",
            ),
        ]
        return [
            InvestigationItem(
                id=investigation_id,
                system_id="global-portal-test",
                title="global 门户访问变慢",
                symptom="用户描述业务门户响应慢，当前仅有 Prometheus 会话和部分 K8s/中间件信息。",
                time_window="最近 2 小时",
                status="draft",
                severity="warning",
                agent_plan=[
                    "Prometheus Agent 查询 target 状态、关键告警和资源曲线",
                    "K8s Agent 检查 Pod 重启、事件、Service/Ingress 与资源限制",
                    "OS Agent 通过已绑定会话补充 CPU、内存、磁盘 IO 和网络状态",
                    "Summary Agent 汇总时间线、证据和根因候选",
                ],
                evidence_count=0,
                root_cause_candidates=["等待 Prometheus/K8s/OS 证据后排序"],
                tasks=tasks,
                created_at="2026-05-08 00:00:00",
                updated_at="2026-05-08 00:00:00",
            )
        ]

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

    def bind_asset(self, system_id: str, asset: dict) -> BusinessSystemProfile | None:
        profile = self.get_profile(system_id)
        if not profile:
            return None

        asset_id = asset.get("id") or asset.get("asset_id") or asset.get("host") or len(profile.components) + 1
        host = str(asset.get("host") or "")
        protocol = str(asset.get("protocol") or asset.get("login_protocol") or "")
        asset_type = str(asset.get("asset_type") or asset.get("type") or "")
        component_type, layer, workload_family, profile_pack_id = _component_shape(asset_type, protocol)
        component_id = f"cmp-asset-{_slug(asset_id)}"
        component = Component(
            id=component_id,
            system_id=system_id,
            name=str(asset.get("remark") or asset.get("name") or host or component_id),
            component_type=component_type,
            layer=layer,
            workload_family=workload_family,
            profile_pack_id=profile_pack_id,
            environment=profile.system.environment,
            status="unknown",
            confidence="confirmed",
            source="asset_binding",
            metadata={
                "asset_id": asset_id,
                "host": host,
                "port": asset.get("port"),
                "username": asset.get("username"),
                "asset_type": asset_type,
                "protocol": protocol,
                "binding_source": "asset_vault",
            },
        )
        profile.components = [item for item in profile.components if item.id != component_id]
        profile.components.append(component)
        self._remove_unknown_for_layer(profile, layer)
        self._refresh_profile(profile)

        if component_type == "observability_source":
            self._upsert_observable_source_from_component(profile, component)
        return profile

    def bind_session(self, system_id: str, session: dict, role: str = "investigation_channel") -> BusinessSystemProfile | None:
        profile = self.get_profile(system_id)
        if not profile:
            return None

        session_id = str(session.get("id") or session.get("session_id") or "")
        if not session_id:
            return None
        protocol = str(session.get("protocol") or "")
        asset_type = str(session.get("asset_type") or "")
        component_type, layer, workload_family, profile_pack_id = _component_shape(asset_type, protocol)
        component_id = f"cmp-session-{_slug(session_id)}"
        component = Component(
            id=component_id,
            system_id=system_id,
            name=str(session.get("remark") or session.get("host") or session_id),
            component_type=component_type,
            layer=layer,
            workload_family=workload_family,
            profile_pack_id=profile_pack_id,
            environment=profile.system.environment,
            status="active",
            confidence="confirmed",
            source="session_binding",
            metadata={
                "session_id": session_id,
                "host": session.get("host"),
                "user": session.get("user") or session.get("username"),
                "asset_type": asset_type,
                "protocol": protocol,
                "role": role,
                "binding_source": "active_session",
            },
        )
        profile.components = [item for item in profile.components if item.id != component_id]
        profile.components.append(component)
        self._remove_unknown_for_layer(profile, layer)
        self._refresh_profile(profile)

        if component_type == "observability_source":
            self._upsert_observable_source_from_component(profile, component)
        return profile

    def unbind_component(self, system_id: str, component_id: str) -> BusinessSystemProfile | None:
        profile = self.get_profile(system_id)
        if not profile:
            return None

        component = next((item for item in profile.components if item.id == component_id), None)
        if not component:
            return None

        profile.components = [item for item in profile.components if item.id != component_id]
        profile.relationships = [
            item for item in profile.relationships
            if item.from_component_id != component_id and item.to_component_id != component_id
        ]
        profile.observable_sources = [
            item for item in profile.observable_sources
            if component_id not in item.bound_component_ids and item.metadata.get("component_id") != component_id
        ]
        if component.layer in _PROFILE_REQUIRED_LAYERS and not any(item.layer == component.layer for item in profile.components):
            self._ensure_unknown_for_layer(profile, component.layer)
        self._refresh_profile(profile)
        return profile

    def update_component(self, system_id: str, component_id: str, updates: dict) -> BusinessSystemProfile | None:
        profile = self.get_profile(system_id)
        if not profile:
            return None

        current = next(
            (item for item in [*profile.components, *profile.unknowns] if item.id == component_id),
            None,
        )
        if not current:
            return None

        data = current.model_dump()
        for field in ["name", "component_type", "layer", "workload_family", "profile_pack_id", "environment", "status", "confidence"]:
            value = updates.get(field)
            if value is not None and value != "":
                data[field] = value
        metadata = updates.get("metadata")
        if isinstance(metadata, dict):
            data["metadata"] = {**data.get("metadata", {}), **metadata}
        if data["component_type"] != "unknown" or data["confidence"] != "unknown":
            data["confidence"] = data.get("confidence") if data.get("confidence") != "unknown" else "confirmed"
            data["source"] = "manual_edit"

        updated = Component(**data)
        profile.components = [item for item in profile.components if item.id != component_id]
        profile.unknowns = [item for item in profile.unknowns if item.id != component_id]
        if updated.component_type == "unknown" and updated.confidence == "unknown":
            profile.unknowns.append(updated)
        else:
            profile.components.append(updated)
            self._remove_unknown_for_layer(profile, updated.layer)
        self._refresh_profile(profile)

        if updated.component_type == "observability_source":
            self._upsert_observable_source_from_component(profile, updated)
        return profile

    def _remove_unknown_for_layer(self, profile: BusinessSystemProfile, layer: str) -> None:
        profile.unknowns = [
            item for item in profile.unknowns
            if not (item.layer == layer and item.source == "unknown_placeholder")
        ]

    def _ensure_unknown_for_layer(self, profile: BusinessSystemProfile, layer: str) -> None:
        if any(item.layer == layer and item.source == "unknown_placeholder" for item in profile.unknowns):
            return
        profile.unknowns.append(
            Component(
                id=f"unk-{layer}",
                system_id=profile.system.id,
                name=f"{layer} unknown",
                component_type="unknown",
                layer=layer,
                status="unknown",
                confidence="unknown",
                source="unknown_placeholder",
            )
        )

    def _refresh_profile(self, profile: BusinessSystemProfile) -> None:
        known_layers = {component.layer for component in profile.components}
        complete = len(known_layers & _PROFILE_REQUIRED_LAYERS)
        profile.system.profile_completeness = min(95, int(complete / len(_PROFILE_REQUIRED_LAYERS) * 100))
        profile.system.updated_at = _now()

    def _upsert_observable_source_from_component(self, profile: BusinessSystemProfile, component: Component) -> None:
        source_id = f"src-{component.id}"
        protocol = str(component.metadata.get("protocol") or "")
        source_type = "prometheus" if "prometheus" in protocol.lower() or "prometheus" in component.name.lower() else protocol or "monitor"
        source = ObservableSource(
            id=source_id,
            name=component.name,
            source_type=source_type,
            source_origin="session" if component.metadata.get("session_id") else "asset",
            status="candidate",
            capabilities=["query_metrics", "query_alerts", "discover_targets", "run_readonly_check"],
            bound_system_ids=[profile.system.id],
            bound_component_ids=[component.id],
            session_id=str(component.metadata.get("session_id")) if component.metadata.get("session_id") else None,
            metadata={"component_id": component.id, "binding_source": component.metadata.get("binding_source")},
        )
        profile.observable_sources = [item for item in profile.observable_sources if item.id != source_id]
        profile.observable_sources.append(source)

    def list_discovery_candidates(self, system_id: str | None = None) -> list[dict]:
        candidates = self._discovery_candidates
        if system_id:
            candidates = [candidate for candidate in candidates if candidate.system_id == system_id]
        return [candidate.model_dump() for candidate in candidates]

    def list_investigations(self, system_id: str | None = None) -> list[dict]:
        investigations = self._investigations
        if system_id:
            investigations = [item for item in investigations if item.system_id == system_id]
        return [item.model_dump() for item in investigations]

    def get_investigation(self, investigation_id: str) -> InvestigationItem | None:
        for item in self._investigations:
            if item.id == investigation_id:
                return item
        return None

    def create_investigation(
        self,
        *,
        system_id: str,
        title: str,
        symptom: str,
        time_window: str = "",
        severity: str = "unknown",
    ) -> InvestigationItem | None:
        profile = self.get_profile(system_id)
        if not profile:
            return None

        now = _now()
        investigation_id = f"inv-{system_id}-{len(self._investigations) + 1}"
        tasks = self._build_investigation_tasks(investigation_id, profile, time_window)
        item = InvestigationItem(
            id=investigation_id,
            system_id=system_id,
            title=title,
            symptom=symptom,
            time_window=time_window,
            status="draft",
            severity=severity,  # type: ignore[arg-type]
            agent_plan=[task.output_summary for task in tasks],
            evidence_count=0,
            root_cause_candidates=["等待证据回收后生成根因候选"],
            tasks=tasks,
            created_at=now,
            updated_at=now,
        )
        self._investigations.insert(0, item)
        return item

    def _build_investigation_tasks(
        self,
        investigation_id: str,
        profile: BusinessSystemProfile,
        time_window: str,
    ) -> list[InvestigationTask]:
        tasks: list[InvestigationTask] = []
        window = time_window or "最近 2 小时"
        if profile.observable_sources:
            source = profile.observable_sources[0]
            tasks.append(
                InvestigationTask(
                    id=f"{investigation_id}-prometheus",
                    investigation_id=investigation_id,
                    agent_role="Prometheus Agent",
                    source_id=source.id,
                    task_type="query_metrics_alerts",
                    input_json={"window": window, "capabilities": source.capabilities, "read_only": True},
                    output_summary="Prometheus Agent 查询 target 状态、关键告警和资源曲线",
                )
            )
        if any(component.workload_family == "container" for component in profile.components):
            target = next((component for component in profile.components if component.workload_family == "container"), None)
            tasks.append(
                InvestigationTask(
                    id=f"{investigation_id}-k8s",
                    investigation_id=investigation_id,
                    agent_role="K8s Agent",
                    target_component_id=target.id if target else None,
                    task_type="inspect_k8s_workload",
                    input_json={"checks": ["pods", "events", "services", "ingress"], "read_only": True},
                    output_summary="K8s Agent 检查 Pod 重启、事件、Service/Ingress 与资源限制",
                )
            )
        if any(component.layer == "os" for component in [*profile.components, *profile.unknowns]):
            tasks.append(
                InvestigationTask(
                    id=f"{investigation_id}-os",
                    investigation_id=investigation_id,
                    agent_role="OS Agent",
                    task_type="inspect_os_baseline",
                    input_json={"checks": ["cpu", "memory", "disk_io", "network"], "read_only": True},
                    output_summary="OS Agent 补充 CPU、内存、磁盘 IO 和网络状态",
                )
            )
        tasks.append(
            InvestigationTask(
                id=f"{investigation_id}-summary",
                investigation_id=investigation_id,
                agent_role="Summary Agent",
                task_type="correlate_evidence",
                input_json={"requires_evidence": True, "read_only": True},
                output_summary="Summary Agent 汇总时间线、证据和根因候选",
            )
        )
        return tasks

    def append_evidence(
        self,
        investigation_id: str,
        *,
        title: str,
        summary: str,
        evidence_type: str,
        task_id: str | None = None,
        component_id: str | None = None,
        source_id: str | None = None,
        raw_ref: str = "",
        raw_excerpt: str = "",
        tool_evidence: dict | None = None,
        confidence: str = "pending_review",
    ) -> EvidenceItem | None:
        investigation = self.get_investigation(investigation_id)
        if not investigation:
            return None
        now = _now()
        tool_evidence = tool_evidence or {}
        if tool_evidence:
            raw_ref = raw_ref or str(tool_evidence.get("evidence_id") or "")
            raw_excerpt = raw_excerpt or str(tool_evidence.get("output_preview") or "")
        evidence = EvidenceItem(
            id=f"ev-{investigation_id}-{len(investigation.evidence) + 1}",
            investigation_id=investigation_id,
            task_id=task_id,
            component_id=component_id,
            source_id=source_id,
            evidence_type=evidence_type,
            title=title,
            summary=summary,
            raw_ref=raw_ref,
            raw_excerpt=raw_excerpt,
            tool_evidence=tool_evidence,
            confidence=confidence,  # type: ignore[arg-type]
            timestamp=now,
            created_at=now,
        )
        investigation.evidence.append(evidence)
        investigation.evidence_count = len(investigation.evidence)
        investigation.updated_at = now
        return evidence

    def append_run_trace_evidence(
        self,
        investigation_id: str,
        *,
        session_id: str,
        trace_result: dict,
        task_id: str | None = None,
        title: str = "",
        summary: str = "",
        confidence: str = "confirmed",
    ) -> EvidenceItem | None:
        trace = trace_result.get("trace") if isinstance(trace_result.get("trace"), dict) else {}
        evidence = trace.get("evidence") if isinstance(trace.get("evidence"), dict) else {}
        result_meta = trace.get("resultMeta") if isinstance(trace.get("resultMeta"), dict) else {}
        tool_policy = result_meta.get("tool_policy") if isinstance(result_meta.get("tool_policy"), dict) else {}
        run = trace_result.get("run") if isinstance(trace_result.get("run"), dict) else {}
        evidence_id = str(trace.get("evidenceId") or evidence.get("evidence_id") or "").strip()
        tool_name = str(trace.get("tool") or evidence.get("tool_name") or "").strip()
        output_preview = str(evidence.get("output_preview") or evidence.get("result_preview") or "")
        tool_evidence = {
            "evidence_id": evidence_id,
            "session_id": str(session_id or evidence.get("session_id") or ""),
            "run_id": str(run.get("run_id") or evidence.get("run_id") or ""),
            "tool_call_id": str(trace.get("toolCallId") or evidence.get("tool_call_id") or ""),
            "tool_name": tool_name,
            "tool_family": str(evidence.get("tool_family") or tool_policy.get("evidence_family") or ""),
            "input_summary": str(evidence.get("input_summary") or evidence.get("redacted_input") or ""),
            "output_preview": output_preview,
            "result_status": str(trace.get("status") or evidence.get("result_status") or ""),
        }
        default_summary = "；".join(
            item for item in [
                f"工具={tool_name}" if tool_name else "",
                f"输入={tool_evidence['input_summary']}" if tool_evidence["input_summary"] else "",
                f"结果={output_preview}" if output_preview else "",
            ] if item
        )
        return self.append_evidence(
            investigation_id,
            title=title or f"Run Trace 工具证据：{tool_name or evidence_id or 'unknown'}",
            summary=summary or default_summary or "Run Trace 工具执行证据已挂接到排查事件。",
            evidence_type="run_trace_tool",
            task_id=task_id,
            raw_ref=evidence_id,
            raw_excerpt=output_preview,
            tool_evidence=tool_evidence,
            confidence=confidence,
        )

    def append_root_cause(
        self,
        investigation_id: str,
        *,
        title: str,
        description: str,
        likelihood: str = "unknown",
        impact: str = "unknown",
        confidence: str = "pending_review",
        supporting_evidence_ids: list[str] | None = None,
        recommended_next_steps: list[str] | None = None,
    ) -> RootCauseCandidate | None:
        investigation = self.get_investigation(investigation_id)
        if not investigation:
            return None
        now = _now()
        candidate = RootCauseCandidate(
            id=f"rc-{investigation_id}-{len(investigation.root_causes) + 1}",
            investigation_id=investigation_id,
            title=title,
            description=description,
            likelihood=likelihood,
            impact=impact,
            confidence=confidence,  # type: ignore[arg-type]
            supporting_evidence_ids=supporting_evidence_ids or [],
            recommended_next_steps=recommended_next_steps or [],
            created_at=now,
            updated_at=now,
        )
        investigation.root_causes.append(candidate)
        investigation.root_cause_candidates = [item.title for item in investigation.root_causes] or investigation.root_cause_candidates
        investigation.updated_at = now
        return candidate

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
            "discovery_candidate_count": len(self._discovery_candidates),
            "investigation_count": len(self._investigations),
        }


catalog_service = ObservabilityCatalogService()
