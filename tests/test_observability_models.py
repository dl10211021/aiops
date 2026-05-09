from __future__ import annotations

import pytest

from core.observability.models import BusinessSystem, Component, Relationship, relationship_endpoints_are_valid


def test_partial_business_system_allows_unknown_architecture():
    system = BusinessSystem(name="集团global协作门户", environment="测试环境")
    db = Component(
        system_id=system.id,
        name="数据库",
        component_type="unknown",
        workload_family="database",
        status="unknown",
        confidence="unknown",
    )

    assert system.name == "集团global协作门户"
    assert db.component_type == "unknown"
    assert db.layer == "unknown"


def test_model_does_not_assume_specific_vendor():
    system = BusinessSystem(name="业务系统", environment="测试")
    zstack = Component(system_id=system.id, name="ZStack", component_type="cloud_cluster", workload_family="virtualization", confidence="confirmed")
    oracle = Component(system_id=system.id, name="Oracle", component_type="database_instance", workload_family="database", confidence="confirmed")
    prometheus = Component(system_id=system.id, name="Prometheus", component_type="observable_source", workload_family="observability", confidence="confirmed")

    assert {zstack.layer, oracle.layer, prometheus.layer} == {"virtualization", "database", "observability"}


def test_rejects_invalid_relationship_endpoints():
    system = BusinessSystem(name="业务系统", environment="测试")
    source = Component(system_id=system.id, name="app", component_type="application_service", confidence="confirmed")
    relationship = Relationship(
        system_id=system.id,
        from_component_id=source.id,
        to_component_id="missing",
        relationship_type="depends_on",
        status="pending_review",
        confidence="inferred",
    )

    assert not relationship_endpoints_are_valid(relationship, [source])


def test_relationship_endpoint_cannot_be_same_component():
    system = BusinessSystem(name="业务系统", environment="测试")
    component = Component(system_id=system.id, name="app", component_type="application_service")
    with pytest.raises(ValueError):
        Relationship(
            system_id=system.id,
            from_component_id=component.id,
            to_component_id=component.id,
            relationship_type="depends_on",
        )
