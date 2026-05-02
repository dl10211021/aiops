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
from pydantic import ValidationError

from api import asset_routes, routes
from api.schemas import (
    AssetPayload,
    BatchAssetImportItem,
    ConnectionRequest,
    InspectionTemplateStepPayload,
    SafetyPolicyTestRequest,
)
from core.asset_protocols import get_asset_catalog
from core.memory import DEFAULT_SENSITIVE_EXTRA_ARG_KEYS


class FakeMemoryDB:
    sensitive_keys = list(DEFAULT_SENSITIVE_EXTRA_ARG_KEYS)

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
                "extra_args": {
                    "api_key": "real-api-key",
                    "api_token": "real-token",
                    "category": "monitor",
                    "secret_key": "real-secret",
                    "bearer_token": "real-bearer",
                    "kubeconfig": "real-kubeconfig",
                    "vmware_session_id": "real-session",
                    "zstack_session_uuid": "real-zstack-session",
                },
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
        updated["extra_args"] = {
            "api_key": "real-api-key",
            "api_token": "real-token",
            "category": "monitor",
            "secret_key": "real-secret",
            "bearer_token": "real-bearer",
            "kubeconfig": "real-kubeconfig",
            "vmware_session_id": "real-session",
            "zstack_session_uuid": "real-zstack-session",
        }
        return updated

    def get_all_assets(self):
        return [dict(asset) for asset in self.assets.values()]

    def delete_asset(self, asset_id):
        self.assets.pop(asset_id, None)


class TestAssetCrudRoutes(unittest.TestCase):
    def test_asset_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/assets/saved", paths)
        self.assertIn("/assets", paths)
        self.assertIn("/assets/types", paths)
        self.assertIn("/assets/{asset_id}", paths)
        self.assertIn("/assets/normalize/preview", paths)
        self.assertIn("/assets/normalize/apply", paths)
        self.assertIn("/assets/batch_import", paths)

    def test_asset_request_defaults_are_not_shared_between_instances(self):
        first = BatchAssetImportItem(host="a.local")
        second = BatchAssetImportItem(host="b.local")

        first.extra_args["api_token"] = "token-a"
        first.skills.append("skill-a")
        first.tags.append("prod")

        self.assertEqual(second.extra_args, {})
        self.assertEqual(second.skills, [])
        self.assertEqual(second.tags, ["未分组"])

        first_step = InspectionTemplateStepPayload(
            name="basic_status",
            tool="linux_execute_command",
        )
        second_step = InspectionTemplateStepPayload(
            name="network_status",
            tool="linux_execute_command",
        )
        first_step.args["timeout"] = 30

        self.assertEqual(second_step.args, {})

        first_policy_test = SafetyPolicyTestRequest(
            tool_name="linux_execute_command",
            command="whoami",
        )
        second_policy_test = SafetyPolicyTestRequest(
            tool_name="linux_execute_command",
            command="hostname",
        )
        first_policy_test.tags.append("prod")

        self.assertEqual(second_policy_test.tags, [])

    def test_create_asset_calls_persistence_layer(self):
        fake = FakeMemoryDB()
        payload = AssetPayload(
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
            response = asyncio.run(asset_routes.create_asset(payload))

        self.assertEqual(response.status, "success")
        self.assertIsNotNone(fake.saved)
        self.assertEqual(fake.saved[1], "k8s.local")
        self.assertEqual(fake.saved[5], "k8s")
        self.assertEqual(fake.saved[10], "k8s")

    def test_get_asset_masks_sensitive_fields(self):
        fake = FakeMemoryDB()

        with patch("core.memory.memory_db", fake):
            response = asyncio.run(asset_routes.get_asset(1))

        asset = response.data["asset"]
        self.assertEqual(asset["password"], "********")
        self.assertEqual(asset["extra_args"]["api_key"], "********")
        self.assertEqual(asset["extra_args"]["api_token"], "********")
        self.assertEqual(asset["extra_args"]["secret_key"], "********")
        self.assertEqual(asset["extra_args"]["bearer_token"], "********")
        self.assertEqual(asset["extra_args"]["kubeconfig"], "********")
        self.assertEqual(asset["extra_args"]["vmware_session_id"], "********")
        self.assertEqual(asset["extra_args"]["zstack_session_uuid"], "********")
        self.assertEqual(asset["extra_args"]["category"], "monitor")

    def test_saved_assets_list_masks_sensitive_extra_args(self):
        fake = FakeMemoryDB()

        with patch("core.memory.memory_db", fake):
            response = asyncio.run(asset_routes.get_saved_assets())

        asset = response.data["assets"][0]
        self.assertEqual(asset["password"], "********")
        self.assertEqual(asset["extra_args"]["api_key"], "********")
        self.assertEqual(asset["extra_args"]["api_token"], "********")
        self.assertEqual(asset["extra_args"]["secret_key"], "********")
        self.assertEqual(asset["extra_args"]["bearer_token"], "********")
        self.assertEqual(asset["extra_args"]["kubeconfig"], "********")
        self.assertEqual(asset["extra_args"]["vmware_session_id"], "********")
        self.assertEqual(asset["extra_args"]["zstack_session_uuid"], "********")
        self.assertEqual(asset["extra_args"]["category"], "monitor")

    def test_update_asset_preserves_mask_contract_and_masks_response(self):
        fake = FakeMemoryDB()
        payload = AssetPayload(
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
            response = asyncio.run(asset_routes.update_asset(1, payload))

        self.assertEqual(fake.updated[0], 1)
        self.assertEqual(fake.updated[1]["password"], "********")
        asset = response.data["asset"]
        self.assertEqual(asset["password"], "********")
        self.assertEqual(asset["extra_args"]["api_key"], "********")
        self.assertEqual(asset["extra_args"]["api_token"], "********")

    def test_catalog_password_params_are_masked_by_memory_policy(self):
        password_fields = {
            param["field"]
            for item in get_asset_catalog()
            for param in item.get("params", [])
            if param.get("type") == "password"
        }

        self.assertEqual(password_fields - set(DEFAULT_SENSITIVE_EXTRA_ARG_KEYS), set())

    def test_get_missing_asset_raises_404(self):
        fake = FakeMemoryDB()

        with patch("core.memory.memory_db", fake):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(asset_routes.get_asset(404))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_asset_types_response_exposes_datacenter_catalog_filters(self):
        response = asset_routes._asset_types_response()

        category_labels = {item["id"]: item["label"] for item in response.data["categories"]}
        self.assertEqual(category_labels["virtualization"], "虚拟化与私有云")
        self.assertEqual(category_labels["storage"], "存储与备份")
        self.assertEqual(category_labels["oob"], "硬件带外")

        by_id = {item["id"]: item for item in response.data["types"]}
        self.assertEqual(by_id["s3"]["category"], "storage")
        self.assertEqual(by_id["s3"]["protocol"], "s3")
        self.assertEqual(by_id["hdfs"]["protocol"], "ssh")
        self.assertEqual(by_id["glusterfs"]["category"], "storage")

    def test_asset_normalization_routes_preserve_response_shapes(self):
        plan = {"changes": [], "duplicates": [], "summary": {"assets_scanned": 2}}
        report = {
            "backup_path": "asset_cleanup_backup.json",
            "removed_ids": [1],
            "summary": {"duplicates_removed": 1},
        }

        with (
            patch("api.asset_routes.build_asset_cleanup_plan_record", return_value=plan),
            patch("api.asset_routes.apply_asset_cleanup_record", return_value=report),
        ):
            preview = asyncio.run(asset_routes.preview_asset_normalization())
            applied = asyncio.run(asset_routes.apply_asset_normalization())

        self.assertEqual(preview.status, "success")
        self.assertEqual(preview.data, plan)
        self.assertEqual(applied.status, "success")
        self.assertEqual(applied.message, "资产规范化清理完成")
        self.assertEqual(applied.data, report)

    def test_snmp_protocol_validation_applies_to_nas_and_ipmi(self):
        with self.assertRaises(ValidationError):
            ConnectionRequest(
                host="nas.local",
                port=161,
                username="",
                password="",
                asset_type="nas",
                protocol="snmp",
                extra_args={
                    "category": "storage",
                    "sub_type": "nas",
                    "snmp_version": "v3",
                    "v3_auth_protocol": "SHA",
                },
            )

    def test_oracle_connection_validation_accepts_tns_alias(self):
        request = ConnectionRequest(
            host="oracle.local",
            port=1521,
            username="system",
            password="manager",
            asset_type="oracle",
            protocol="oracle",
            extra_args={
                "category": "db",
                "sub_type": "oracle",
                "oracle_connect_type": "tns_alias",
                "tns_alias": "TESTDB",
            },
        )

        self.assertEqual(request.extra_args["tns_alias"], "TESTDB")


if __name__ == "__main__":
    unittest.main()
