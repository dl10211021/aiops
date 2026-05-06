"""Asset subtype, legacy asset rows, and login protocol normalization."""

from __future__ import annotations

from urllib.parse import urlparse

from core.asset_catalog_builder import (
    ASSET_CATALOG,
    ASSET_CATEGORY_OVERRIDES,
    ASSET_PORT_OVERRIDES,
    ASSET_PROTOCOL_OVERRIDES,
    BASE_ASSET_CATALOG,
    EXCLUDED_HERTZBEAT_ASSET_IDS,
    HERTZBEAT_ASSET_CATALOG,
    _apply_protocol_overrides,
    _merge_asset_catalog,
)
from core.asset_capabilities import enrich_asset_capability
from core.asset_access_protocols import build_access_protocols

from core.asset_protocol_constants import (
    AI_PLATFORM_API_ASSET_TYPES,
    API_PROTOCOLS,
    ASSET_PROTOCOL_MAP,
    ASSET_TYPE_ALIASES,
    BIGDATA_API_ASSET_TYPES,
    CICD_API_ASSET_TYPES,
    CONTAINER_API_ASSET_TYPES,
    CONTAINER_ASSET_TYPES,
    DATABASE_HTTP_ASSET_TYPES,
    DATABASE_HTTP_PROTOCOLS,
    DATASTORE_PROTOCOLS,
    DB_PROTOCOLS,
    DISCOVERY_API_ASSET_TYPES,
    DOMAIN_HTTP_API_ASSET_TYPES,
    GENERIC_ASSET_TYPES,
    KEYWORD_ASSET_HINTS,
    LEGACY_GENERIC_TYPES,
    MIDDLEWARE_API_ASSET_TYPES,
    MIDDLEWARE_ASSET_TYPES,
    MONITORING_ASSET_TYPES,
    NETWORK_API_ASSET_TYPES,
    NETWORK_CLI_ASSET_TYPES,
    OOB_API_ASSET_TYPES,
    PORT_ASSET_HINTS,
    SECURITY_API_ASSET_TYPES,
    SERVICE_ASSET_TYPES,
    SERVICE_PROBE_PROTOCOLS,
    SNMP_PROTOCOLS,
    SQL_PROTOCOLS,
    SSH_PROTOCOLS,
    STORAGE_API_PROTOCOLS,
    STORAGE_ASSET_TYPES,
    VIRTUALIZATION_API_PROTOCOLS,
    VIRTUALIZATION_ASSET_TYPES,
    _category_asset_types,
)


def get_asset_catalog() -> list[dict]:
    result = []
    for item in ASSET_CATALOG:
        enriched = enrich_asset_capability(item)
        enriched["access_protocols"] = build_access_protocols(enriched)
        result.append(enriched)
    return result


def get_asset_definition(asset_type: str | None) -> dict | None:
    subtype = canonical_asset_type(asset_type)
    for item in ASSET_CATALOG:
        if item["id"] == subtype:
            enriched = enrich_asset_capability(item)
            enriched["access_protocols"] = build_access_protocols(enriched)
            return enriched
    return None


def _clean(value: object) -> str:
    return str(value or "").strip().lower()


def _catalog_ids() -> set[str]:
    return {item["id"] for item in ASSET_CATALOG}


def _alias_asset_type(value: str | None) -> str:
    subtype = _clean(value)
    return ASSET_TYPE_ALIASES.get(subtype, subtype)


def _port_from_host(host: str | None) -> int | None:
    raw = str(host or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw if "://" in raw else f"//{raw}")
        return parsed.port
    except ValueError:
        return None


def _keyword_hint(*values: object) -> str | None:
    text = " ".join(str(v or "") for v in values).lower()
    for keyword, asset_type in KEYWORD_ASSET_HINTS:
        if keyword in text:
            return asset_type
    return None


def _has_legacy_identity_hint(
    extra_args: dict,
    host: str | None,
    port: int | None,
    remark: str | None,
) -> bool:
    if extra_args.get("sub_type") or extra_args.get("device_type") or extra_args.get("db_type"):
        return True
    if _keyword_hint(remark, host):
        return True
    effective_port = _port_from_host(host) or (int(port) if port else None)
    return bool(effective_port and effective_port in PORT_ASSET_HINTS and effective_port != 22)


def _infer_from_legacy_device_type(
    device_type: str,
    protocol: str,
    host: str | None,
    port: int | None,
    remark: str | None,
    extra_args: dict,
) -> str | None:
    device_type = _clean(device_type)
    if not device_type:
        return None

    keyword = _keyword_hint(
        remark,
        host,
        extra_args.get("db_type"),
        extra_args.get("database"),
        extra_args.get("db_name"),
    )
    if keyword and keyword != "linux":
        return keyword

    effective_port = _port_from_host(host) or (int(port) if port else None)
    if device_type in {"database", "db"}:
        return _alias_asset_type(extra_args.get("db_type")) or PORT_ASSET_HINTS.get(effective_port)
    if device_type in {"api", "monitor", "monitoring"}:
        hint = PORT_ASSET_HINTS.get(effective_port)
        if hint and hint not in {"linux", "http_api"}:
            return hint
        return "http_api"
    if device_type in {"network", "switch", "router"}:
        return "switch"
    if device_type in {"windows", "window", "winrm"}:
        return "windows"
    if device_type in {"linux", "ssh"}:
        return "linux"
    if device_type in _catalog_ids():
        return device_type
    mapped_protocol = ASSET_PROTOCOL_MAP.get(device_type)
    if mapped_protocol == "winrm":
        return "windows"
    if mapped_protocol == "ssh":
        return "linux"
    if mapped_protocol == "http_api":
        return keyword or "http_api"
    if mapped_protocol in DB_PROTOCOLS or mapped_protocol in {"k8s", "snmp", "redfish"}:
        return mapped_protocol
    return None


def canonical_asset_type(
    asset_type: str | None = None,
    protocol: str | None = None,
    extra_args: dict | None = None,
    host: str | None = None,
    port: int | None = None,
    remark: str | None = None,
) -> str:
    """Resolve business asset subtype, including legacy linux/virtual rows."""
    extra_args = extra_args or {}
    explicit_subtype = _alias_asset_type(
        extra_args.get("sub_type")
        or extra_args.get("asset_sub_type")
        or extra_args.get("asset_type")
    )
    if explicit_subtype in _catalog_ids():
        return explicit_subtype

    subtype = _alias_asset_type(asset_type)
    proto = _clean(protocol or extra_args.get("login_protocol") or extra_args.get("protocol"))
    is_legacy = proto in {"", "virtual"} and subtype in LEGACY_GENERIC_TYPES

    if is_legacy:
        if proto == "virtual" and not str(host or "").strip():
            return subtype if subtype in _catalog_ids() else "virtual"

        inferred = _infer_from_legacy_device_type(
            extra_args.get("device_type", ""),
            proto,
            host,
            port,
            remark,
            extra_args,
        )
        if inferred:
            return _alias_asset_type(inferred)

        keyword = _keyword_hint(remark, host)
        if keyword:
            return _alias_asset_type(keyword)

        effective_port = _port_from_host(host) or (int(port) if port else None)
        port_hint = PORT_ASSET_HINTS.get(effective_port)
        if port_hint and port_hint != "http_api":
            return _alias_asset_type(port_hint)

    if subtype in _catalog_ids():
        return subtype

    if subtype in {"http_api", "api", "http", "https"}:
        keyword = _keyword_hint(remark, host)
        return _alias_asset_type(keyword) if keyword else "http_api"

    protocol_asset = _alias_asset_type(proto)
    if protocol_asset in _catalog_ids():
        return protocol_asset
    if proto == "winrm":
        return "windows"
    if proto in DB_PROTOCOLS or proto in {"k8s", "snmp", "redfish"}:
        return proto
    if proto == "ssh":
        return "linux"
    if proto == "http_api":
        return "http_api"
    return subtype or protocol_asset or "virtual"


def normalize_protocol(
    asset_type: str | None = None,
    protocol: str | None = None,
    extra_args: dict | None = None,
    host: str | None = None,
    port: int | None = None,
    remark: str | None = None,
) -> str:
    """Resolve login protocol while keeping asset_type as the business subtype."""
    extra_args = extra_args or {}
    explicit = (
        protocol
        or extra_args.get("login_protocol")
        or extra_args.get("protocol")
        or ""
    )
    value = str(explicit).strip().lower()
    subtype = canonical_asset_type(asset_type, protocol, extra_args, host, port, remark)

    # Legacy rows often used "virtual" because non-ssh asset_type was treated as
    # virtual. Re-resolve it from asset_type when we can classify the subtype.
    if value == "virtual" and not str(host or "").strip():
        return "virtual"

    if value in {"api", "http_api"}:
        subtype_protocol = ASSET_PROTOCOL_MAP.get(subtype)
        if subtype_protocol in API_PROTOCOLS or subtype_protocol in SNMP_PROTOCOLS:
            return subtype_protocol
        return "http_api"

    if value == "virtual" and not _has_legacy_identity_hint(extra_args, host, port, remark):
        return "virtual"

    if value and value != "virtual":
        return ASSET_PROTOCOL_MAP.get(value, value)

    definition = get_asset_definition(subtype)
    if definition:
        return definition["protocol"]
    if subtype:
        return ASSET_PROTOCOL_MAP.get(subtype, subtype)
    return value or "virtual"


def normalize_extra_args(asset_type: str, protocol: str, extra_args: dict | None = None) -> dict:
    args = dict(extra_args or {})
    definition = get_asset_definition(asset_type) or {}

    if "enable_password" in args and "enable_pass" not in args:
        args["enable_pass"] = args["enable_password"]

    if protocol == "virtual":
        args["login_protocol"] = "virtual"
        return args

    if definition.get("category"):
        args.setdefault("category", definition["category"])
    if asset_type not in GENERIC_ASSET_TYPES:
        args.setdefault("sub_type", asset_type)
    args["login_protocol"] = protocol

    if protocol in SQL_PROTOCOLS:
        args["db_type"] = protocol
    elif protocol in DATASTORE_PROTOCOLS:
        args.setdefault("db_type", protocol)
    elif protocol in DATABASE_HTTP_PROTOCOLS:
        args.setdefault("db_type", protocol)
    return args


def resolve_asset_identity(
    asset_type: str | None = None,
    protocol: str | None = None,
    extra_args: dict | None = None,
    host: str | None = None,
    port: int | None = None,
    remark: str | None = None,
) -> dict:
    """Return canonical asset subtype, login protocol, and normalized metadata."""
    extra_args = extra_args or {}
    subtype = canonical_asset_type(asset_type, protocol, extra_args, host, port, remark)
    login_protocol = normalize_protocol(subtype, protocol, extra_args, host, port, remark)
    definition = get_asset_definition(subtype) or {}
    return {
        "asset_type": subtype,
        "protocol": login_protocol,
        "category": definition.get("category"),
        "inspection_profile": definition.get("inspection_profile"),
        "extra_args": normalize_extra_args(subtype, login_protocol, extra_args),
    }


def is_ssh_protocol(protocol: str | None) -> bool:
    return normalize_protocol(protocol=protocol) in SSH_PROTOCOLS


def is_db_protocol(protocol: str | None) -> bool:
    return normalize_protocol(protocol=protocol) in DB_PROTOCOLS


def is_api_protocol(protocol: str | None) -> bool:
    return normalize_protocol(protocol=protocol) in API_PROTOCOLS
