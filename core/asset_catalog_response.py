from __future__ import annotations

from core.asset_capabilities import category_metadata, connector_metadata
from core.asset_protocols import get_asset_catalog


FORM_CAPABILITY_FIELDS = {
    "family",
    "connector",
    "operation_model",
    "tools",
    "credential_fields",
    "driver_key",
    "maturity",
    "connector_group",
}


def build_asset_types_response(types: list[dict] | None = None) -> dict:
    asset_types = types if types is not None else get_asset_catalog()
    categories = []
    connector_groups = []
    seen_categories = set()
    seen_connectors = set()
    for item in asset_types:
        category = item.get("category") or "other"
        if category not in seen_categories:
            seen_categories.add(category)
            categories.append(category_metadata(category))
        connector = ((item.get("capability") or {}).get("connector")) or "unknown"
        if connector not in seen_connectors:
            seen_connectors.add(connector)
            connector_groups.append(connector_metadata(connector))
    categories.sort(key=lambda item: (item.get("order", 999), item.get("label", "")))
    connector_groups.sort(key=lambda item: (item.get("order", 999), item.get("label", "")))
    return {
        "types": asset_types,
        "categories": categories,
        "connector_groups": connector_groups,
    }


def build_asset_type_summary_response(types: list[dict] | None = None) -> dict:
    data = build_asset_types_response(types)
    summary_types = []
    for item in data["types"]:
        capability = item.get("capability") or {}
        summary_types.append({
            "id": item.get("id"),
            "label": item.get("label"),
            "category": item.get("category") or "other",
            "protocol": item.get("protocol"),
            "default_port": item.get("default_port"),
            "capability": {
                "connector": capability.get("connector") or "unknown",
            },
        })
    return {
        "types": summary_types,
        "categories": data["categories"],
        "connector_groups": data["connector_groups"],
    }


def build_asset_type_form_catalog_response(types: list[dict] | None = None) -> dict:
    data = build_asset_types_response(types)
    form_types = []
    for item in data["types"]:
        capability = item.get("capability") or {}
        compact_capability = {
            key: capability.get(key)
            for key in FORM_CAPABILITY_FIELDS
            if capability.get(key) is not None
        }
        compact_capability.setdefault("connector", capability.get("connector") or "unknown")
        form_types.append({
            "id": item.get("id"),
            "label": item.get("label"),
            "category": item.get("category") or "other",
            "protocol": item.get("protocol"),
            "default_port": item.get("default_port"),
            "source": item.get("source"),
            "hertzbeat_protocols": item.get("hertzbeat_protocols") or [],
            "hertzbeat_supported": bool(item.get("hertzbeat_supported")),
            "access_protocols": item.get("access_protocols") or [],
            "params": item.get("params") or [],
            "capability": compact_capability,
        })
    return {
        "types": form_types,
        "categories": data["categories"],
        "connector_groups": data["connector_groups"],
    }
