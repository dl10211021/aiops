import unittest

from connections.storage_platform_manager import StoragePlatformExecutor


class TestStoragePlatformManager(unittest.TestCase):
    def test_health_uses_configured_readonly_path_and_managed_credentials(self):
        calls = []

        def request_executor(**kwargs):
            calls.append(kwargs)
            return {"success": True, "status_code": 200, "output": "ok"}

        result = StoragePlatformExecutor().execute(
            asset_type="backup",
            host="backup.local",
            port=443,
            username="ops",
            password="secret",
            extra_args={"api_token": "token", "health_path": "/api/health"},
            operation="health",
            request_executor=request_executor,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "health")
        self.assertEqual(result["path"], "/api/health")
        self.assertEqual(calls[0]["username"], "ops")
        self.assertEqual(calls[0]["password"], "secret")
        self.assertEqual(calls[0]["extra_args"]["api_token"], "token")

    def test_standard_backup_operations_map_to_configurable_paths(self):
        calls = []

        def request_executor(**kwargs):
            calls.append(kwargs)
            return {"success": True, "output": kwargs["path"]}

        result = StoragePlatformExecutor().execute(
            asset_type="backup",
            host="backup.local",
            port=443,
            extra_args={"jobs_path": "v1/backup-jobs"},
            operation="jobs",
            request_executor=request_executor,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], "/v1/backup-jobs")
        self.assertEqual(calls[0]["method"], "GET")

    def test_request_operation_requires_explicit_path(self):
        result = StoragePlatformExecutor().execute(
            asset_type="backup",
            host="backup.local",
            port=443,
            operation="request",
            request_executor=lambda **kwargs: {"success": True},
        )

        self.assertFalse(result["success"])
        self.assertIn("path", result["error"])

    def test_write_method_is_rejected_before_http_request(self):
        called = False

        def request_executor(**kwargs):
            nonlocal called
            called = True
            return {"success": True}

        result = StoragePlatformExecutor().execute(
            asset_type="backup",
            host="backup.local",
            port=443,
            operation="request",
            method="POST",
            path="/api/v1/jobs/1/run",
            request_executor=request_executor,
        )

        self.assertFalse(result["success"])
        self.assertIn("仅支持 GET/HEAD", result["error"])
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
