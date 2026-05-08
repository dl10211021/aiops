from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from core.observability.models import now_iso


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT_DIR / "data" / "observability.db"


JSON_FIELDS = {
    "systems": {"aliases", "tags", "metadata"},
    "components": {"metadata"},
    "relationships": {"metadata"},
    "bindings": {"metadata"},
    "sources": {"capabilities", "metadata"},
    "profile_packs": {
        "component_types",
        "relationship_types",
        "discovery_rules",
        "metric_mappings",
        "log_patterns",
        "health_checks",
        "investigation_playbooks",
        "default_unknown_nodes",
        "metadata",
    },
    "discovery_runs": {"input", "summary", "metadata"},
    "review_items": {"evidence", "metadata"},
    "investigations": {"metadata"},
    "tasks": {"input", "metadata"},
    "evidence": {"metadata"},
    "root_causes": {
        "supporting_evidence_ids",
        "contradicting_evidence_ids",
        "recommended_next_steps",
        "metadata",
    },
}


class ObservabilityStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._lock = threading.RLock()
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS systems (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, environment TEXT NOT NULL,
                    description TEXT, criticality TEXT, owner TEXT, aliases TEXT,
                    tags TEXT, status TEXT, profile_completeness INTEGER,
                    metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS components (
                    id TEXT PRIMARY KEY, system_id TEXT NOT NULL, name TEXT NOT NULL,
                    component_type TEXT NOT NULL, workload_family TEXT, profile_pack_id TEXT,
                    environment TEXT, status TEXT, confidence TEXT, source TEXT,
                    metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY, system_id TEXT NOT NULL, from_component_id TEXT NOT NULL,
                    to_component_id TEXT NOT NULL, relationship_type TEXT NOT NULL,
                    confidence TEXT, source TEXT, evidence_id TEXT, status TEXT,
                    metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS bindings (
                    id TEXT PRIMARY KEY, system_id TEXT NOT NULL, component_id TEXT,
                    target_type TEXT NOT NULL, target_id TEXT NOT NULL, relation_type TEXT,
                    source_id TEXT, metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, source_type TEXT NOT NULL,
                    source_origin TEXT, session_id TEXT, endpoint TEXT, capabilities TEXT,
                    auth_ref TEXT, status TEXT, last_checked_at TEXT, metadata TEXT,
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS source_bindings (
                    id TEXT PRIMARY KEY, source_id TEXT NOT NULL, system_id TEXT,
                    component_id TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS profile_packs (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, workload_family TEXT,
                    version TEXT, component_types TEXT, relationship_types TEXT,
                    discovery_rules TEXT, metric_mappings TEXT, log_patterns TEXT,
                    health_checks TEXT, investigation_playbooks TEXT,
                    default_unknown_nodes TEXT, metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS discovery_runs (
                    id TEXT PRIMARY KEY, system_id TEXT NOT NULL, status TEXT,
                    input TEXT, summary TEXT, metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS review_items (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, system_id TEXT NOT NULL,
                    candidate_type TEXT, from_component_id TEXT, to_component_id TEXT,
                    relationship_type TEXT, confidence TEXT, status TEXT, evidence TEXT,
                    metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY, system_id TEXT NOT NULL, title TEXT NOT NULL,
                    symptom TEXT, time_window_start TEXT, time_window_end TEXT, severity TEXT,
                    status TEXT, created_by TEXT, summary TEXT, metadata TEXT,
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL, agent_role TEXT,
                    target_component_id TEXT, source_id TEXT, task_type TEXT, status TEXT,
                    input TEXT, output_summary TEXT, started_at TEXT, finished_at TEXT,
                    error_message TEXT, metadata TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL, task_id TEXT,
                    component_id TEXT, source_id TEXT, evidence_type TEXT, title TEXT,
                    summary TEXT, raw_ref TEXT, raw_excerpt TEXT, confidence TEXT,
                    timestamp TEXT, metadata TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS root_causes (
                    id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL, title TEXT,
                    description TEXT, likelihood INTEGER, impact TEXT, confidence TEXT,
                    supporting_evidence_ids TEXT, contradicting_evidence_ids TEXT,
                    recommended_next_steps TEXT, status TEXT, metadata TEXT,
                    created_at TEXT, updated_at TEXT
                );
                """
            )

    def upsert(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        record = self._encode_record(table, record)
        keys = list(record.keys())
        placeholders = ", ".join("?" for _ in keys)
        updates = ", ".join(f"{key}=excluded.{key}" for key in keys if key != "id")
        sql = f"""
            INSERT INTO {table} ({", ".join(keys)})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
        """
        with self._lock, self._connect() as conn:
            conn.execute(sql, [record[key] for key in keys])
        return self.get(table, str(record["id"])) or record

    def insert(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        return self.upsert(table, record)

    def get(self, table: str, item_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
        return self._decode_record(table, dict(row)) if row else None

    def list(
        self,
        table: str,
        *,
        where: str = "",
        params: tuple[Any, ...] = (),
        order_by: str = "created_at DESC",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += " LIMIT ?"
            params = (*params, int(limit))
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._decode_record(table, dict(row)) for row in rows]

    def delete(self, table: str, item_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        return cursor.rowcount > 0

    def delete_where(self, table: str, where: str, params: tuple[Any, ...]) -> int:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(f"DELETE FROM {table} WHERE {where}", params)
        return int(cursor.rowcount)

    def update_fields(self, table: str, item_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get(table, item_id)
        if not current:
            return None
        current.update(fields)
        if "updated_at" in current:
            current["updated_at"] = now_iso()
        return self.upsert(table, current)

    def _encode_record(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        encoded = dict(record)
        for key in JSON_FIELDS.get(table, set()):
            encoded[key] = json.dumps(encoded.get(key) or ([] if key.endswith("s") else {}), ensure_ascii=False)
        return encoded

    def _decode_record(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(record)
        for key in JSON_FIELDS.get(table, set()):
            value = decoded.get(key)
            if value in (None, ""):
                decoded[key] = [] if key.endswith("s") else {}
                continue
            try:
                decoded[key] = json.loads(value)
            except Exception:
                decoded[key] = [] if key.endswith("s") else {}
        return decoded


_default_store: ObservabilityStore | None = None


def get_observability_store() -> ObservabilityStore:
    global _default_store
    if _default_store is None:
        _default_store = ObservabilityStore()
    return _default_store


def set_observability_store(store: ObservabilityStore | None) -> None:
    global _default_store
    _default_store = store

