from __future__ import annotations

from typing import Any

from core.asset_capability_profiles import (
    DATABASE_DRIVER_REQUIRED_IDS,
    DATABASE_HTTP_IDS,
    DATABASE_HTTP_PROTOCOLS,
    MONITORING_QUERY_IDS,
    NETWORK_CLI_IDS,
    OBJECT_STORAGE_IDS,
    SERVICE_PROBE_PROTOCOLS,
    SERVICE_PROTOCOL_CREDENTIAL_FIELDS,
    SPECIAL_CAPABILITY_OVERRIDES,
    STORAGE_API_PROTOCOLS,
    VIRTUALIZATION_API_PROTOCOLS,
)

def _category_adjustment(asset_id: str, category: str, protocol: str) -> dict[str, Any]:
    if protocol == "ssh" and (category == "network" or asset_id in NETWORK_CLI_IDS):
        return {
            "family": "network",
            "connector": "ssh_network_cli",
            "tools": ["network_cli_execute_command"],
            "safety_category": "network_cli",
        }
    if protocol == "ssh" and category == "container":
        return {"family": "container", "connector": "container_shell", "tools": ["container_execute_command"]}
    if protocol == "ssh" and category == "middleware":
        return {"family": "middleware", "connector": "middleware_shell", "tools": ["middleware_execute_command"]}
    if protocol == "ssh" and category == "storage":
        return {"family": "storage", "connector": "storage_shell", "tools": ["storage_execute_command"]}
    if protocol == "ssh" and category == "virtualization":
        return {"family": "virtualization", "connector": "virtualization_shell", "tools": ["linux_execute_command"]}
    if protocol == "ssh" and category == "ai":
        return {"family": "ai", "connector": "ai_compute_shell", "tools": ["linux_execute_command"]}
    if protocol == "http_api" and category == "monitor":
        return {"family": "monitoring", "connector": "monitoring_api", "tools": ["monitoring_api_query"]}
    if category == "db" and (protocol == "http_api" or protocol in DATABASE_HTTP_PROTOCOLS):
        if asset_id in DATABASE_HTTP_IDS or protocol in DATABASE_HTTP_PROTOCOLS:
            return {
                "family": "database",
                "connector": "database_http",
                "operation_model": "database_api_client",
                "tools": ["database_api_request"],
                "credential_fields": ["host", "port", "username", "password", "database", "api_token"],
                "safety_category": "http_api",
                "maturity": "generic",
            }
        if asset_id in DATABASE_DRIVER_REQUIRED_IDS:
            return {
                "family": "database",
                "connector": "database_driver",
                "operation_model": "driver_adapter_required",
                "tools": [],
                "safety_category": "sql",
                "maturity": "needs_adapter",
            }
        return {
            "family": "database",
            "connector": "database_http",
            "operation_model": "database_api_client",
            "tools": ["database_api_request"],
            "credential_fields": ["host", "port", "username", "password", "database", "api_token"],
            "safety_category": "http_api",
            "maturity": "generic",
        }
    if (protocol == "http_api" and category == "virtualization") or protocol in VIRTUALIZATION_API_PROTOCOLS:
        return {
            "family": "virtualization",
            "connector": "virtualization_api",
            "operation_model": "api_client",
            "tools": ["virtualization_api_request"],
            "credential_fields": ["host", "port", "username", "password", "api_token"],
            "safety_category": "http_api",
            "maturity": "generic",
        }
    if category == "db" and protocol in {"db2", "dameng", "xugu", "hive", "iotdb"}:
        return {
            "family": "database",
            "connector": "database_jdbc",
            "driver_key": protocol,
            "operation_model": "jdbc_client",
            "tools": ["db_execute_query"],
            "credential_fields": ["host", "port", "username", "password", "database"],
            "safety_category": "sql",
            "maturity": "driver_required",
        }
    if protocol == "http_api" and category == "network":
        return {"family": "network", "connector": "network_api", "tools": ["network_api_request"]}
    if protocol == "http_api" and category == "container":
        return {"family": "container", "connector": "container_api", "tools": ["container_api_request"]}
    if protocol == "http_api" and category == "middleware":
        return {"family": "middleware", "connector": "middleware_api", "tools": ["middleware_api_request"]}
    if protocol == "http_api" and category == "bigdata":
        return {"family": "bigdata", "connector": "bigdata_api", "tools": ["bigdata_api_request"]}
    if protocol == "http_api" and category == "security":
        return {"family": "security", "connector": "security_api", "tools": ["security_api_request"]}
    if protocol == "http_api" and category == "oob":
        return {"family": "hardware_oob", "connector": "oob_api", "tools": ["oob_api_request"]}
    if protocol == "http_api" and category == "discovery":
        return {"family": "discovery", "connector": "discovery_api", "tools": ["discovery_api_request"]}
    if (protocol == "http_api" and category == "service") or protocol in SERVICE_PROBE_PROTOCOLS:
        return {
            "family": "service",
            "connector": "service_probe",
            "operation_model": "probe_client",
            "tools": ["service_probe_request"],
            "credential_fields": SERVICE_PROTOCOL_CREDENTIAL_FIELDS.get(protocol, ["host", "port"]),
            "safety_category": "http_api",
            "maturity": "generic",
        }
    if protocol == "http_api" and category == "ai":
        return {"family": "ai", "connector": "ai_platform_api", "tools": ["ai_platform_api_request"]}
    if protocol == "http_api" and category == "cicd":
        return {"family": "cicd", "connector": "cicd_api", "tools": ["cicd_api_request"]}
    if protocol == "snmp" and category == "storage":
        return {
            "family": "storage",
            "connector": "snmp",
            "operation_model": "native_client",
            "tools": ["snmp_get"],
            "safety_category": "snmp",
            "maturity": "generic",
        }
    if (protocol == "http_api" and category == "storage") or protocol in STORAGE_API_PROTOCOLS:
        return {
            "family": "storage",
            "connector": "storage_api",
            "operation_model": "api_client",
            "tools": ["storage_api_request"],
            "credential_fields": ["host", "port", "username", "password", "api_token"],
            "safety_category": "http_api",
            "maturity": "generic",
        }
    if protocol == "http_api" and category == "custom":
        if asset_id in MONITORING_QUERY_IDS:
            return {"family": "monitoring", "connector": "monitoring_api", "tools": ["monitoring_api_query"]}
        return {"family": "custom", "connector": "custom_api", "tools": ["http_api_request"]}
    if asset_id in OBJECT_STORAGE_IDS:
        return SPECIAL_CAPABILITY_OVERRIDES.get(asset_id, SPECIAL_CAPABILITY_OVERRIDES["s3"])
    return {}
