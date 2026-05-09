from __future__ import annotations

from core.observability.profile_packs import builtin_profile_packs


def test_builtin_profile_packs_load_with_required_fields():
    packs = builtin_profile_packs()
    ids = {pack.id for pack in packs}

    assert "database_oracle" in ids
    assert "infra_zstack" in ids
    assert "infra_vmware" in ids
    assert "observability_prometheus" in ids
    for pack in packs:
        assert pack.name
        assert pack.workload_family
        assert pack.component_types
        assert pack.relationship_types
        assert pack.investigation_playbooks
