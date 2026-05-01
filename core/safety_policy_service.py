from __future__ import annotations

import logging
from typing import Any

from core.safety_policy import explain_policy_decision, get_safety_policy, save_safety_policy


logger = logging.getLogger(__name__)


class SafetyPolicyServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


SAFETY_POLICY_TEST_TOOLS = {
    "linux_execute_command",
    "container_execute_command",
    "middleware_execute_command",
    "storage_execute_command",
    "network_cli_execute_command",
    "execute_on_scope",
    "winrm_execute_command",
    "db_execute_query",
    "redis_execute_command",
    "memcached_execute_command",
    "mongodb_find",
    "http_api_request",
    "database_api_request",
    "bigdata_api_request",
    "middleware_api_request",
    "discovery_api_request",
    "container_api_request",
    "network_api_request",
    "security_api_request",
    "cicd_api_request",
    "ai_platform_api_request",
    "oob_api_request",
    "k8s_api_request",
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "service_probe_request",
    "snmp_get",
    "local_execute_script",
    "evolve_skill",
}

HTTP_SAFETY_POLICY_TEST_TOOLS = {
    "http_api_request",
    "database_api_request",
    "bigdata_api_request",
    "middleware_api_request",
    "discovery_api_request",
    "container_api_request",
    "network_api_request",
    "security_api_request",
    "cicd_api_request",
    "ai_platform_api_request",
    "oob_api_request",
    "k8s_api_request",
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "service_probe_request",
}


def get_safety_policy_record() -> dict[str, Any]:
    return get_safety_policy()


def save_safety_policy_record(policy: dict[str, Any]) -> dict[str, Any]:
    try:
        return save_safety_policy(policy)
    except ValueError as exc:
        raise SafetyPolicyServiceError(422, str(exc)) from exc
    except Exception as exc:
        logger.error("保存安全策略失败: %s", exc)
        raise SafetyPolicyServiceError(500, f"保存安全策略失败: {exc}") from exc


def explain_safety_policy_decision(
    tool_name: str,
    tool_args: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    return explain_policy_decision(tool_name, tool_args, context)


def build_safety_policy_test_tool_args(payload: Any) -> dict[str, Any]:
    if payload.tool_name == "db_execute_query":
        return {"sql": payload.sql or payload.command or ""}
    if payload.tool_name in HTTP_SAFETY_POLICY_TEST_TOOLS:
        return {
            "method": (payload.method or "GET").upper(),
            "path": payload.path or payload.command or "/",
            "oid": payload.oid or "",
            "body": payload.body or {},
        }
    if payload.tool_name == "evolve_skill":
        return {"skill_id": payload.command or "", "file_name": payload.path or ""}
    if payload.tool_name == "snmp_get":
        return {"oid": payload.oid or payload.command or payload.path or ""}
    return {"command": payload.command or payload.sql or payload.path or ""}


def build_safety_policy_test_context(payload: Any) -> dict[str, Any]:
    return {
        "allow_modifications": payload.allow_modifications,
        "asset_type": payload.asset_type or "",
        "protocol": payload.protocol or "",
        "host": payload.host or "",
        "trigger_source": payload.trigger_source or "chat",
        "tags": payload.tags,
    }


def explain_safety_policy_test(payload: Any) -> dict[str, Any]:
    return explain_safety_policy_decision(
        payload.tool_name,
        build_safety_policy_test_tool_args(payload),
        build_safety_policy_test_context(payload),
    )
