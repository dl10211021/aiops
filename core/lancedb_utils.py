"""Small LanceDB helpers shared by memory and knowledge-base storage."""

from __future__ import annotations

from typing import Any


def lancedb_table_names(db: Any) -> list[str]:
    if not db:
        return []
    if hasattr(db, "list_tables"):
        return [item.name if hasattr(item, "name") else str(item) for item in db.list_tables()]
    return list(db.table_names())


def ensure_lancedb_table(db: Any, table_name: str, schema: Any):
    if not db:
        raise RuntimeError("LanceDB connection is not initialized")
    if table_name in lancedb_table_names(db):
        return db.open_table(table_name)
    try:
        return db.create_table(table_name, schema=schema)
    except Exception as e:
        message = str(e).lower()
        if "already exists" in message or "table exists" in message:
            return db.open_table(table_name)
        raise
