from __future__ import annotations

from typing import Any

from core.asset_protocols import resolve_asset_identity


MASKED_SECRET = "********"


def get_login_protocol_from_request(req: Any) -> str:
    return resolve_asset_identity(
        req.asset_type,
        req.protocol,
        req.extra_args,
        req.host,
        req.port,
        req.remark,
    )["protocol"]


def asset_matches_connection_request(asset: dict[str, Any], req: Any) -> bool:
    if (
        asset.get("host") != req.host
        or asset.get("port") != req.port
        or asset.get("username") != req.username
    ):
        return False
    asset_identity = resolve_asset_identity(
        asset.get("asset_type"),
        asset.get("protocol"),
        asset.get("extra_args", {}),
        asset.get("host"),
        asset.get("port"),
        asset.get("remark"),
    )
    req_identity = resolve_asset_identity(
        req.asset_type,
        req.protocol,
        req.extra_args,
        req.host,
        req.port,
        req.remark,
    )
    return (
        asset_identity["asset_type"] == req_identity["asset_type"]
        and asset_identity["protocol"] == req_identity["protocol"]
    )


def restore_masked_extra_args(req: Any, memory_db: Any) -> dict[str, Any]:
    """Restore masked extra_args values from the matching saved asset."""
    if not getattr(req, "extra_args", None):
        return {}
    if not any(value == MASKED_SECRET for value in req.extra_args.values()):
        return req.extra_args

    restored = dict(req.extra_args)
    for asset in memory_db.get_all_assets():
        if not asset_matches_connection_request(asset, req):
            continue
        db_args = asset.get("extra_args", {})
        for key, value in restored.items():
            if value == MASKED_SECRET and key in db_args:
                restored[key] = db_args[key]
        break
    return restored


def restore_masked_password(req: Any, memory_db: Any) -> str | None:
    """Restore masked password from the matching saved asset."""
    if req.password != MASKED_SECRET:
        return req.password

    for asset in memory_db.get_all_assets():
        if asset_matches_connection_request(asset, req):
            return asset.get("password")
    return None


def restore_connection_request_secrets(req: Any, memory_db: Any) -> tuple[Any, str | None]:
    """Return a request rebuilt with restored extra_args plus the effective password."""
    restored_args = restore_masked_extra_args(req, memory_db)
    if hasattr(req, "model_dump"):
        request_data = req.model_dump()
    else:
        request_data = vars(req).copy()
    restored_req = req.__class__(**{**request_data, "extra_args": restored_args})
    return restored_req, restore_masked_password(restored_req, memory_db)


def normalize_private_key_path(private_key_path: str | None) -> str | None:
    if private_key_path and private_key_path.strip().lower() not in ("string", ""):
        return private_key_path
    return None
