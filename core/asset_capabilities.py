"""Unified operational capability model for OpsCore assets.

HertzBeat tells us what can be monitored. This module translates asset catalog
entries into OpsCore's standard: how the AI can connect, what tools are exposed,
what setup is required, and how risky operations should be handled.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.asset_category_adjustments import _category_adjustment
from core.asset_capability_profiles import (
    DATABASE_ALIASES,
    PROTOCOL_CAPABILITY_PROFILES,
    SPECIAL_CAPABILITY_OVERRIDES,
    SQL_DRIVER_KEYS,
)
from core.asset_metadata import (
    ASSET_CATEGORY_DEFINITIONS,
    CONNECTOR_GROUP_DEFINITIONS,
    category_metadata,
    connector_metadata,
)
from core.asset_parameter_templates import (
    GENERIC_HTTP_API_PARAMETERS,
    SHARED_PARAMETER_TEMPLATES,
    _boolean_parameter,
    _number_parameter,
    _password_parameter,
    _select_parameter,
    _text_parameter,
)
from core.asset_specific_parameters import apply_asset_parameter_template
from core.tool_display import asset_tool_detail


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _standard_risk_model(safety_category: str) -> dict[str, Any]:
    return {
        "read_only_default": True,
        "approval_required_for_write": True,
        "hard_block_supported": True,
        "safety_category": safety_category,
    }


def capability_for_asset(asset: dict[str, Any]) -> dict[str, Any]:
    asset_id = str(asset.get("id") or "").strip().lower()
    category = str(asset.get("category") or "other").strip().lower()
    protocol = str(asset.get("protocol") or "").strip().lower()
    driver_key = DATABASE_ALIASES.get(asset_id, SQL_DRIVER_KEYS.get(protocol, protocol))

    base = deepcopy(PROTOCOL_CAPABILITY_PROFILES.get(protocol, {}))
    if not base:
        base = {
            "family": category,
            "connector": "unknown",
            "operation_model": "unknown",
            "tools": [],
            "credential_fields": ["host", "port"],
            "safety_category": "unknown",
            "maturity": "needs_adapter",
        }

    category_adjustment = _category_adjustment(asset_id, category, protocol)
    capability = _deep_merge(base, category_adjustment)
    if asset_id in SPECIAL_CAPABILITY_OVERRIDES:
        capability = _deep_merge(capability, SPECIAL_CAPABILITY_OVERRIDES[asset_id])

    if category == "db" and protocol in SQL_DRIVER_KEYS:
        capability["driver_key"] = driver_key
        capability["family"] = "database"
    if category == "db" and asset_id in DATABASE_ALIASES:
        capability["driver_key"] = DATABASE_ALIASES[asset_id]
        capability["family"] = "database"

    safety_category = str(capability.get("safety_category") or capability.get("connector") or "unknown")
    capability.setdefault("operation_model", base.get("operation_model") or "native_client")
    capability.setdefault("tools", [])
    capability.setdefault("credential_fields", ["host", "port"])
    capability.setdefault("maturity", "generic" if capability.get("tools") else "needs_adapter")
    capability["connector_group"] = connector_metadata(capability.get("connector"))
    apply_asset_parameter_template(capability, asset_id)
    capability["tool_details"] = [asset_tool_detail(str(tool)) for tool in capability.get("tools", [])]
    capability["risk_model"] = _standard_risk_model(safety_category)
    capability["standard_version"] = "2026-04-28"
    return capability


def enrich_asset_capability(asset: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(asset)
    enriched.pop("params", None)
    enriched["category_meta"] = category_metadata(enriched.get("category"))
    enriched["capability"] = capability_for_asset(enriched)
    enriched["params"] = deepcopy(enriched["capability"].get("parameter_template") or [])
    return enriched
