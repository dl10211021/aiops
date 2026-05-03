import unittest

from core import safety_policy
from core.safety_platform_actions import classify_platform_actions


class SafetyPlatformActionTests(unittest.TestCase):
    def test_k8s_namespace_delete_is_classified(self):
        self.assertEqual(
            classify_platform_actions(
                "k8s_api_request",
                {"method": "DELETE", "path": "/api/v1/namespaces/prod"},
            ),
            ["k8s.delete_namespace"],
        )

    def test_virtualization_migration_and_snapshot_are_classified(self):
        self.assertEqual(
            classify_platform_actions(
                "virtualization_api_request",
                {"method": "POST", "path": "/vms/prod-01/migrate"},
            ),
            ["virtualization.migrate_vm"],
        )
        self.assertEqual(
            classify_platform_actions(
                "virtualization_api_request",
                {"method": "POST", "path": "/vms/prod-01/snapshot"},
            ),
            ["virtualization.snapshot_or_rollback", "virtualization.rollback_snapshot"],
        )

    def test_middleware_cicd_and_ai_actions_are_classified(self):
        self.assertEqual(
            classify_platform_actions(
                "middleware_api_request",
                {"method": "PUT", "path": "/nacos/v1/cs/configs"},
            ),
            ["nacos.publish_config"],
        )
        self.assertEqual(
            classify_platform_actions(
                "cicd_api_request",
                {"method": "POST", "path": "/pipelines/prod/deploy"},
            ),
            ["cicd.deploy_prod"],
        )
        self.assertEqual(
            classify_platform_actions(
                "ai_platform_api_request",
                {"method": "DELETE", "path": "/models/recommendation/versions/2026-05"},
            ),
            ["mlflow.delete_model_version"],
        )

    def test_storage_actions_preserve_operation_and_path_semantics(self):
        self.assertEqual(
            classify_platform_actions(
                "storage_api_request",
                {"operation": "download_object"},
            ),
            ["s3.download_object"],
        )
        self.assertEqual(
            classify_platform_actions(
                "storage_api_request",
                {"method": "DELETE", "path": "/prod-bucket"},
            ),
            ["s3.delete_bucket"],
        )
        self.assertEqual(
            classify_platform_actions(
                "storage_api_request",
                {"method": "DELETE", "path": "/prod-bucket/a.log"},
            ),
            ["s3.delete_object"],
        )
        self.assertEqual(
            classify_platform_actions(
                "storage_api_request",
                {
                    "method": "PUT",
                    "path": "/prod-bucket?publicAccessBlock",
                    "body": {"public": True},
                },
            ),
            ["s3.change_bucket_policy", "s3.public_bucket"],
        )

    def test_monitoring_silence_and_policy_alias_are_preserved(self):
        self.assertEqual(
            classify_platform_actions(
                "monitoring_api_query",
                {"method": "POST", "path": "/api/v2/silences"},
            ),
            ["monitoring.create_silence", "alertmanager.create_silence"],
        )
        self.assertIs(safety_policy._platform_actions, classify_platform_actions)


if __name__ == "__main__":
    unittest.main()
