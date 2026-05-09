import unittest
from pydantic import ValidationError

from core.observability.models import (
    BusinessSystem,
    BusinessSystemProfile,
    Component,
    Relationship,
)
from core.observability.profile_packs import builtin_profile_packs


class TestObservabilityModels(unittest.TestCase):
    def test_partial_business_system_profile_allows_unknown_nodes(self):
        system = BusinessSystem(
            id="global-portal-test",
            name="集团global协作门户",
            environment="测试环境",
        )
        known = Component(
            id="cmp-registry",
            system_id=system.id,
            name="registry 测试环境",
            component_type="container_registry",
            layer="container",
            confidence="confirmed",
        )
        unknown_db = Component(
            id="unk-db",
            system_id=system.id,
            name="数据库 unknown",
            component_type="unknown",
            layer="database",
            confidence="unknown",
        )

        profile = BusinessSystemProfile(
            system=system,
            components=[known],
            unknowns=[unknown_db],
        )

        self.assertEqual(profile.summary()["unknown_count"], 1)
        self.assertEqual(profile.layer_counts()["database"], 1)

    def test_rejects_relationship_with_missing_endpoint(self):
        system = BusinessSystem(id="sys-1", name="业务系统")
        component = Component(
            id="cmp-1",
            system_id=system.id,
            name="应用服务",
            component_type="application_service",
            layer="application",
        )
        relationship = Relationship(
            id="rel-1",
            system_id=system.id,
            from_component_id="cmp-1",
            to_component_id="missing",
            relationship_type="depends_on",
        )

        with self.assertRaises(ValidationError):
            BusinessSystemProfile(
                system=system,
                components=[component],
                relationships=[relationship],
            )

    def test_builtin_profile_packs_cover_platform_neutral_families(self):
        packs = {pack.id: pack for pack in builtin_profile_packs()}

        self.assertIn("generic-k8s", packs)
        self.assertIn("generic-database", packs)
        self.assertIn("generic-network", packs)
        self.assertIn("generic-virtualization", packs)
        self.assertIn("prometheus-source", packs)
        self.assertTrue(all(pack.read_only for pack in packs.values()))
