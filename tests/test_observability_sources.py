from __future__ import annotations

from pathlib import Path
import uuid

from core.observability.source_registry import SourceRegistry
from core.observability.store import ObservabilityStore


def make_store() -> ObservabilityStore:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"observability_sources_{uuid.uuid4().hex}.sqlite"
    return ObservabilityStore(path)


def test_existing_prometheus_session_can_become_source():
    registry = SourceRegistry(make_store())
    source = registry.create_source_from_session(session_id="prom-session", source_type="prometheus", name="Prometheus 会话")

    assert source["source_origin"] == "session"
    assert "query_promql" in source["capabilities"]


def test_future_source_types_are_data_driven():
    registry = SourceRegistry(make_store())
    for source_type in ["snmp", "vmware_vcenter", "zstack", "elk", "edr", "ndr", "database_connection"]:
        source = registry.create_source({"name": source_type, "source_type": source_type})
        assert source["capabilities"]
