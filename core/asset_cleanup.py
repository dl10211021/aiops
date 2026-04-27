import datetime as _dt
import json
import os
import sqlite3
from contextlib import closing
from urllib.parse import urlparse

from core.asset_protocols import get_asset_definition, resolve_asset_identity


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def _load_rows(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT a.*, GROUP_CONCAT(t.name) as tags_concat
        FROM assets a
        LEFT JOIN asset_tags at ON a.id = at.asset_id
        LEFT JOIN tags t ON at.tag_id = t.id
        GROUP BY a.id
        ORDER BY a.id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _json_obj(value: str | None) -> dict:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


def _parse_endpoint(host: str | None, port: int | None, protocol: str, extra_args: dict) -> tuple[str, int | None, dict]:
    raw = str(host or "").strip()
    args = dict(extra_args or {})
    effective_port = int(port) if port else None
    if not raw:
        return raw, effective_port, args

    try:
        parsed = urlparse(raw if "://" in raw else f"//{raw}")
    except ValueError:
        parsed = None

    if parsed and parsed.hostname:
        if parsed.scheme in {"http", "https"}:
            args.setdefault("scheme", parsed.scheme)
        if parsed.path and parsed.path not in {"", "/"}:
            args.setdefault("base_path", parsed.path.rstrip("/"))
        raw = parsed.hostname
        if parsed.port:
            effective_port = parsed.port

    if not effective_port:
        definition = get_asset_definition(args.get("sub_type") or protocol) or {}
        effective_port = definition.get("default_port")

    return raw, effective_port, args


def _normalize_row(row: dict) -> dict:
    raw_args = _json_obj(row.get("extra_args_json"))
    normalized_host, normalized_port, endpoint_args = _parse_endpoint(
        row.get("host"),
        row.get("port"),
        row.get("protocol") or row.get("asset_type") or "",
        raw_args,
    )
    identity = resolve_asset_identity(
        row.get("asset_type"),
        row.get("protocol"),
        endpoint_args,
        normalized_host,
        normalized_port,
        row.get("remark"),
    )
    return {
        "id": row["id"],
        "remark": row.get("remark") or "",
        "host": normalized_host,
        "port": normalized_port or row.get("port") or 0,
        "username": row.get("username") or "",
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "extra_args": identity["extra_args"],
        "skills": _json_list(row.get("skills_json")),
        "tags": [t for t in str(row.get("tags_concat") or "").split(",") if t],
    }


def _dedupe_key(item: dict) -> tuple:
    return (
        str(item.get("host") or "").lower(),
        int(item.get("port") or 0),
        str(item.get("username") or "").lower(),
        str(item.get("asset_type") or "").lower(),
        str(item.get("protocol") or "").lower(),
    )


def build_asset_cleanup_plan(db_path: str | None = None) -> dict:
    db_path = db_path or os.path.join(ROOT_DIR, "opscore.db")
    with closing(sqlite3.connect(db_path)) as conn:
        rows = _load_rows(conn)

    normalized = [_normalize_row(row) for row in rows]
    changes = []
    for raw, item in zip(rows, normalized):
        before_args = _json_obj(raw.get("extra_args_json"))
        before = {
            "host": raw.get("host") or "",
            "port": raw.get("port") or 0,
            "asset_type": raw.get("asset_type") or "",
            "protocol": raw.get("protocol") or "",
        }
        after = {
            "host": item["host"],
            "port": item["port"],
            "asset_type": item["asset_type"],
            "protocol": item["protocol"],
        }
        if before != after or before_args != item["extra_args"]:
            changes.append({"id": item["id"], "remark": item["remark"], "before": before, "after": after})

    groups: dict[tuple, list[dict]] = {}
    for item in normalized:
        groups.setdefault(_dedupe_key(item), []).append(item)

    duplicates = []
    for items in groups.values():
        if len(items) <= 1:
            continue
        keep = max(items, key=lambda x: int(x["id"]))
        remove = [item["id"] for item in items if item["id"] != keep["id"]]
        merged_tags = sorted({tag for item in items for tag in item.get("tags", [])})
        duplicates.append(
            {
                "keep_id": keep["id"],
                "remove_ids": remove,
                "host": keep["host"],
                "port": keep["port"],
                "asset_type": keep["asset_type"],
                "protocol": keep["protocol"],
                "merged_tags": merged_tags,
            }
        )

    return {
        "changes": changes,
        "duplicates": duplicates,
        "summary": {
            "assets_scanned": len(rows),
            "rows_to_update": len(changes),
            "duplicate_groups": len(duplicates),
            "duplicates_to_remove": sum(len(item["remove_ids"]) for item in duplicates),
        },
    }


def _backup_assets(conn: sqlite3.Connection) -> str:
    rows = _load_rows(conn)
    backup = {
        "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "assets": rows,
    }
    path = os.path.join(
        ROOT_DIR,
        f"asset_cleanup_backup_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")
    return path


def apply_asset_cleanup(db_path: str | None = None) -> dict:
    db_path = db_path or os.path.join(ROOT_DIR, "opscore.db")
    with closing(sqlite3.connect(db_path)) as conn:
        rows = _load_rows(conn)
        backup_path = _backup_assets(conn)
        normalized = [_normalize_row(row) for row in rows]
        by_id = {item["id"]: item for item in normalized}

        for item in normalized:
            conn.execute(
                """
                UPDATE assets
                SET host=?, port=?, asset_type=?, protocol=?, extra_args_json=?
                WHERE id=?
                """,
                (
                    item["host"],
                    item["port"],
                    item["asset_type"],
                    item["protocol"],
                    json.dumps(item["extra_args"], ensure_ascii=False),
                    item["id"],
                ),
            )

        groups: dict[tuple, list[dict]] = {}
        for item in normalized:
            groups.setdefault(_dedupe_key(item), []).append(item)

        removed_ids: list[int] = []
        merged_groups = []
        for items in groups.values():
            if len(items) <= 1:
                continue
            keep = max(items, key=lambda x: int(x["id"]))
            merged_tags = sorted({tag for item in items for tag in item.get("tags", [])})
            remove_ids = [item["id"] for item in items if item["id"] != keep["id"]]
            if merged_tags:
                conn.execute("DELETE FROM asset_tags WHERE asset_id = ?", (keep["id"],))
                for tag in merged_tags:
                    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()[0]
                    conn.execute(
                        "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                        (keep["id"], tag_id),
                    )
            for asset_id in remove_ids:
                conn.execute("DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,))
                conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            removed_ids.extend(remove_ids)
            merged_groups.append(
                {
                    "keep_id": keep["id"],
                    "remove_ids": remove_ids,
                    "host": keep["host"],
                    "port": keep["port"],
                }
            )

        conn.commit()

    plan = build_asset_cleanup_plan(db_path)
    return {
        "backup_path": backup_path,
        "removed_ids": removed_ids,
        "merged_groups": merged_groups,
        "summary": {
            "assets_updated": len(by_id),
            "duplicates_removed": len(removed_ids),
            "remaining_issues": plan["summary"],
        },
    }
