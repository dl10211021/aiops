import datetime as dt
import unittest

from connections.object_storage_manager import ObjectStorageExecutor


class FakeS3Client:
    def __init__(self):
        self.calls = []

    def list_buckets(self):
        self.calls.append(("list_buckets", {}))
        return {
            "Buckets": [
                {"Name": "ops-logs", "CreationDate": dt.datetime(2026, 1, 1, 8, 0, 0)},
                {"Name": "backup", "CreationDate": dt.datetime(2026, 1, 2, 8, 0, 0)},
            ]
        }

    def head_bucket(self, **kwargs):
        self.calls.append(("head_bucket", kwargs))
        return {}

    def get_bucket_location(self, **kwargs):
        self.calls.append(("get_bucket_location", kwargs))
        return {"LocationConstraint": "ap-east-1"}

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        return {
            "IsTruncated": False,
            "Contents": [
                {
                    "Key": "app/a.log",
                    "Size": 128,
                    "LastModified": dt.datetime(2026, 1, 3, 8, 0, 0),
                    "ETag": '"etag"',
                    "StorageClass": "STANDARD",
                }
            ],
        }

    def head_object(self, **kwargs):
        self.calls.append(("head_object", kwargs))
        return {
            "ContentLength": 128,
            "ContentType": "text/plain",
            "LastModified": dt.datetime(2026, 1, 3, 8, 0, 0),
            "ETag": '"etag"',
            "Metadata": {"owner": "ops"},
        }


class TestObjectStorageManager(unittest.TestCase):
    def test_list_buckets_uses_managed_credentials_without_leaking_secret(self):
        client = FakeS3Client()
        factory_calls = []

        def factory(**kwargs):
            factory_calls.append(kwargs)
            return client

        result = ObjectStorageExecutor().execute(
            asset_type="minio",
            host="minio.local",
            port=9000,
            username="ignored",
            password="ignored-secret",
            extra_args={"access_key": "ak", "secret_key": "sk", "region": "us-east-1"},
            operation="list_buckets",
            client_factory=factory,
        )

        self.assertTrue(result["success"])
        self.assertEqual([bucket["name"] for bucket in result["buckets"]], ["ops-logs", "backup"])
        self.assertEqual(factory_calls[0]["aws_access_key_id"], "ak")
        self.assertEqual(factory_calls[0]["aws_secret_access_key"], "sk")
        self.assertNotIn("sk", str(result))

    def test_list_objects_uses_default_bucket_and_prefix(self):
        client = FakeS3Client()

        result = ObjectStorageExecutor().execute(
            asset_type="s3",
            host="s3.local",
            port=443,
            extra_args={"bucket": "ops-logs"},
            operation="list_objects",
            prefix="app/",
            max_keys=50,
            client_factory=lambda **kwargs: client,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["object_count"], 1)
        self.assertEqual(client.calls[0][0], "list_objects_v2")
        self.assertEqual(client.calls[0][1]["Bucket"], "ops-logs")
        self.assertEqual(client.calls[0][1]["Prefix"], "app/")
        self.assertEqual(client.calls[0][1]["MaxKeys"], 50)

    def test_write_like_operation_is_rejected_by_adapter(self):
        result = ObjectStorageExecutor().execute(
            asset_type="s3",
            host="s3.local",
            port=443,
            operation="delete_object",
            bucket="ops-logs",
            key="app/a.log",
            client_factory=lambda **kwargs: FakeS3Client(),
        )

        self.assertFalse(result["success"])
        self.assertIn("只读操作", result["error"])


if __name__ == "__main__":
    unittest.main()
