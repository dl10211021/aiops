import asyncio
import unittest
import warnings
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from fastapi import HTTPException

from api import routes


class FakeMemoryDB:
    sensitive_keys = ["api_token", "kubeconfig"]

    def __init__(self):
        self.saved = None
        self.updated = None
        self.assets = {
            1: {
                "id": 1,
                "remark": "Prometheus",
                "host": "prom.local",
                "port": 9090,
                "username": "api",
                "password": "real-password",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "agent_profile": "default",
                "extra_args": {"api_token": "real-token", "category": "monitor"},
                "skills": ["prometheus"],
                "tags": ["monitor"],
            }
        }

    def save_asset(self, *args):
        self.saved = args

    def get_asset(self, asset_id):
        asset = self.assets.get(asset_id)
        return dict(asset) if asset else None

    def update_asset(self, asset_id, item):
        self.updated = (asset_id, item)
        if asset_id not in self.assets:
            return None
        updated = dict(self.assets[asset_id])
        updated.update(item)
        updated["password"] = "real-password"
        updated["extra_args"] = {"api_token": "real-token", "category": "monitor"}
        return updated

    def delete_asset(self, asset_id):
        self.assets.pop(asset_id, None)


class TestAssetCrudRoutes(unittest.TestCase):
    def test_create_asset_calls_persistence_layer(self):
        fake = FakeMemoryDB()
        payload = routes.AssetPayload(
            remark="K8s",
            host="k8s.local",
            port=6443,
            username="admin",
            password="secret",
            asset_type="k8s",
            protocol="k8s",
            extra_args={"bearer_token": "token"},
            skills=["k8s-ops"],
            tags=["prod"],
        )

        with patch("core.memory.memory_db", fake):
            response = asyncio.run(routes.create_asset(payload))

        self.assertEqual(response.status, "success")
        self.assertIsNotNone(fake.saved)
        self.assertEqual(fake.saved[1], "k8s.local")
        self.assertEqual(fake.saved[5], "k8s")
        self.assertEqual(fake.saved[10], "k8s")

    def test_get_asset_masks_sensitive_fields(self):
        fake = FakeMemoryDB()

        with patch("core.memory.memory_db", fake):
            response = asyncio.run(routes.get_asset(1))

        asset = response.data["asset"]
        self.assertEqual(asset["password"], "********")
        self.assertEqual(asset["extra_args"]["api_token"], "********")
        self.assertEqual(asset["extra_args"]["category"], "monitor")

    def test_update_asset_preserves_mask_contract_and_masks_response(self):
        fake = FakeMemoryDB()
        payload = routes.AssetPayload(
            remark="Prometheus prod",
            host="prom.local",
            port=9090,
            username="api",
            password="********",
            asset_type="prometheus",
            protocol="http_api",
            extra_args={"api_token": "********", "category": "monitor"},
            skills=["prometheus"],
            tags=["monitor"],
        )

        with patch("core.memory.memory_db", fake):
            response = asyncio.run(routes.update_asset(1, payload))

        self.assertEqual(fake.updated[0], 1)
        self.assertEqual(fake.updated[1]["password"], "********")
        asset = response.data["asset"]
        self.assertEqual(asset["password"], "********")
        self.assertEqual(asset["extra_args"]["api_token"], "********")

    def test_get_missing_asset_raises_404(self):
        fake = FakeMemoryDB()

        with patch("core.memory.memory_db", fake):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(routes.get_asset(404))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_asset_types_response_exposes_datacenter_catalog_filters(self):
        response = routes._asset_types_response()

        category_labels = {item["id"]: item["label"] for item in response.data["categories"]}
        self.assertEqual(category_labels["virtualization"], "虚拟化与私有云")
        self.assertEqual(category_labels["storage"], "存储与备份")
        self.assertEqual(category_labels["oob"], "硬件带外")

        by_id = {item["id"]: item for item in response.data["types"]}
        self.assertEqual(by_id["s3"]["category"], "storage")
        self.assertEqual(by_id["s3"]["protocol"], "http_api")
        self.assertEqual(by_id["hdfs"]["protocol"], "ssh")
        self.assertEqual(by_id["glusterfs"]["category"], "storage")


if __name__ == "__main__":
    unittest.main()
