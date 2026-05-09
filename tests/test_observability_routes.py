import asyncio
import unittest

from fastapi import HTTPException

from api import observability_routes


class TestObservabilityRoutes(unittest.TestCase):
    def test_list_systems_returns_unknown_friendly_sample_profile(self):
        response = asyncio.run(observability_routes.list_observability_systems())

        self.assertEqual(response.status, "success")
        systems = response.data["systems"]
        self.assertEqual(len(systems), 1)
        self.assertEqual(systems[0]["system"]["name"], "集团global协作门户")
        self.assertGreaterEqual(systems[0]["unknown_count"], 1)

    def test_get_profile_returns_components_sources_and_unknowns(self):
        response = asyncio.run(
            observability_routes.get_observability_system_profile("global-portal-test")
        )

        profile = response.data["profile"]
        self.assertEqual(profile["system"]["environment"], "测试环境")
        self.assertTrue(profile["components"])
        self.assertTrue(profile["unknowns"])
        self.assertTrue(profile["observable_sources"])

    def test_missing_profile_maps_to_404(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(observability_routes.get_observability_system_profile("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_profile_packs_endpoint_exposes_prometheus_capabilities(self):
        response = asyncio.run(observability_routes.list_observability_profile_packs())

        packs = response.data["profile_packs"]
        prometheus = next(pack for pack in packs if pack["id"] == "prometheus-source")
        self.assertIn("query_promql", prometheus["capabilities"])
