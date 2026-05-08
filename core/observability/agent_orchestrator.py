from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Awaitable

from core.observability.evidence_service import EvidenceService
from core.observability.investigation_service import InvestigationService
from core.observability.profile_service import BusinessSystemProfileService
from core.observability.store import ObservabilityStore, get_observability_store
from core.observability.topology_service import TopologyService


DispatchFunc = Callable[[list[dict[str, str]], bool], Awaitable[Any]]


class ObservabilityAgentOrchestrator:
    def __init__(self, store: ObservabilityStore | None = None, dispatch_func: DispatchFunc | None = None):
        self.store = store or get_observability_store()
        self.profile = BusinessSystemProfileService(self.store)
        self.topology = TopologyService(self.store)
        self.investigations = InvestigationService(self.store)
        self.evidence = EvidenceService(self.store)
        self.dispatch_func = dispatch_func

    def read_business_system_profile(self, system_id: str) -> dict[str, Any]:
        system = self.profile.get_system(system_id)
        if not system:
            raise ValueError("business system not found")
        return {
            "system": system,
            "topology": self.topology.layered_topology(system_id),
            "bindings": self.store.list("bindings", where="system_id = ?", params=(system_id,), order_by="created_at ASC"),
            "sources": self.store.list("source_bindings", where="system_id = ?", params=(system_id,), order_by="created_at ASC"),
        }

    def append_investigation_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.evidence.append_evidence(payload)

    async def dispatch_investigation_tasks(self, investigation_id: str, allow_modifications: bool = False) -> dict[str, Any]:
        tasks = self.investigations.build_plan(investigation_id)
        session_by_component = self._session_bindings_by_component(tasks)
        dispatchable = [
            {
                "target_session_id": str(
                    task["input"].get("session_id")
                    or session_by_component.get(task.get("target_component_id") or "")
                    or task.get("source_id")
                    or task.get("target_component_id")
                    or ""
                ),
                "task_description": self._task_description(task),
            }
            for task in tasks
        ]
        dispatchable = [item for item in dispatchable if item["target_session_id"]]
        if allow_modifications:
            return {"status": "blocked", "error": "V1 observability orchestration only supports read-only tasks by default."}
        if self.dispatch_func and dispatchable:
            result = await self.dispatch_func(dispatchable, False)
        else:
            result = {"status": "planned_only", "tasks": dispatchable}
        for task in tasks:
            self.investigations.complete_task_with_evidence(
                task["id"],
                output_summary="已生成只读排查任务计划，等待会话执行。" if not self.dispatch_func else "会话调度已返回结果。",
                raw_excerpt=json.dumps(result, ensure_ascii=False, default=str)[:2000],
            )
        return {"status": "completed", "task_count": len(tasks), "dispatch": result}

    def _task_description(self, task: dict[str, Any]) -> str:
        payload = task.get("input") or {}
        return (
            f"{task.get('agent_role')}: 围绕症状 `{payload.get('symptom') or ''}` 对组件 "
            f"`{(payload.get('component') or {}).get('name') or task.get('target_component_id')}` 执行只读排查，"
            "返回证据、时间线和根因候选，不执行变更。"
        )

    def _session_bindings_by_component(self, tasks: list[dict[str, Any]]) -> dict[str, str]:
        component_ids = {str(task.get("target_component_id") or "") for task in tasks if task.get("target_component_id")}
        if not component_ids:
            return {}
        mapping: dict[str, str] = {}
        for component_id in component_ids:
            rows = self.store.list(
                "bindings",
                where="component_id = ? AND target_type = ?",
                params=(component_id, "session"),
                order_by="created_at ASC",
            )
            if rows:
                mapping[component_id] = str(rows[0].get("target_id") or "")
        return mapping


async def dispatch_observability_investigation(investigation_id: str) -> dict[str, Any]:
    from core.agent import dispatch_group_tasks

    orchestrator = ObservabilityAgentOrchestrator(dispatch_func=dispatch_group_tasks)
    return await orchestrator.dispatch_investigation_tasks(investigation_id, allow_modifications=False)


def run_dispatch_sync(investigation_id: str) -> dict[str, Any]:
    return asyncio.run(dispatch_observability_investigation(investigation_id))
