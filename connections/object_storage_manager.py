"""S3-compatible object storage adapter.

The adapter intentionally exposes a small read-only surface first. Destructive
operations should be added only with explicit policy and approval coverage.
"""

from __future__ import annotations

import datetime as _dt
import logging
from typing import Any, Callable

from connections.http_api_manager import build_base_url

logger = logging.getLogger(__name__)


READONLY_OPERATIONS = {
    "list_buckets",
    "head_bucket",
    "get_bucket_location",
    "list_objects",
    "head_object",
}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    return value


def _bounded_int(value: Any, default: int, minimum: int = 1, maximum: int = 1000) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(minimum, min(maximum, parsed))


class ObjectStorageExecutor:
    def _client(
        self,
        *,
        host: str,
        port: int | None,
        username: str = "",
        password: str | None = None,
        extra_args: dict[str, Any] | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> Any:
        extra_args = extra_args or {}
        access_key = (
            _string(extra_args.get("access_key"))
            or _string(extra_args.get("aws_access_key_id"))
            or _string(username)
        )
        secret_key = (
            _string(extra_args.get("secret_key"))
            or _string(extra_args.get("aws_secret_access_key"))
            or _string(password)
        )
        region = _string(extra_args.get("region")) or "us-east-1"
        endpoint_url = _string(extra_args.get("endpoint_url"))
        if not endpoint_url:
            endpoint_url = build_base_url(host, port, extra_args)

        if client_factory is None:
            try:
                import boto3
                from botocore.config import Config
            except Exception as exc:  # pragma: no cover - exercised in runtime environments only
                raise RuntimeError(
                    "对象存储适配需要安装 boto3：pip install boto3。"
                ) from exc

            path_style = bool(extra_args.get("path_style", True))
            config = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if path_style else "virtual"},
                connect_timeout=_bounded_int(extra_args.get("connect_timeout"), 10, 1, 60),
                read_timeout=_bounded_int(extra_args.get("read_timeout"), 30, 1, 300),
            )
            client_factory = boto3.client
            return client_factory(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key or None,
                aws_secret_access_key=secret_key or None,
                config=config,
                verify=bool(extra_args.get("verify_ssl", True)),
            )

        return client_factory(
            service_name="s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
        )

    def execute(
        self,
        *,
        asset_type: str,
        host: str,
        port: int | None,
        username: str = "",
        password: str | None = None,
        extra_args: dict[str, Any] | None = None,
        operation: str = "list_buckets",
        bucket: str | None = None,
        prefix: str | None = None,
        key: str | None = None,
        max_keys: int | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        extra_args = extra_args or {}
        operation = _string(operation).lower() or "list_buckets"
        if operation not in READONLY_OPERATIONS:
            return {
                "success": False,
                "asset_type": asset_type,
                "operation": operation,
                "error": f"对象存储当前仅支持只读操作: {', '.join(sorted(READONLY_OPERATIONS))}",
            }

        bucket_name = _string(bucket) or _string(extra_args.get("bucket"))
        object_key = _string(key)
        object_prefix = _string(prefix)

        try:
            client = self._client(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                client_factory=client_factory,
            )

            if operation == "list_buckets":
                response = client.list_buckets()
                buckets = [
                    {
                        "name": item.get("Name"),
                        "creation_date": _jsonable(item.get("CreationDate")),
                    }
                    for item in response.get("Buckets", [])
                ]
                return {
                    "success": True,
                    "asset_type": asset_type,
                    "operation": operation,
                    "buckets": buckets,
                    "output": f"Buckets: {', '.join(item['name'] for item in buckets if item.get('name')) or '[empty]'}",
                }

            if not bucket_name:
                return {
                    "success": False,
                    "asset_type": asset_type,
                    "operation": operation,
                    "error": "该对象存储操作需要 bucket 参数，或在资产扩展参数中配置默认 Bucket。",
                }

            if operation == "head_bucket":
                client.head_bucket(Bucket=bucket_name)
                return {
                    "success": True,
                    "asset_type": asset_type,
                    "operation": operation,
                    "bucket": bucket_name,
                    "output": f"Bucket {bucket_name} 可访问。",
                }

            if operation == "get_bucket_location":
                response = client.get_bucket_location(Bucket=bucket_name)
                location = response.get("LocationConstraint") or "us-east-1"
                return {
                    "success": True,
                    "asset_type": asset_type,
                    "operation": operation,
                    "bucket": bucket_name,
                    "location": location,
                    "output": f"Bucket {bucket_name} 区域: {location}",
                }

            if operation == "list_objects":
                limit = _bounded_int(max_keys or extra_args.get("max_keys"), 100)
                params: dict[str, Any] = {"Bucket": bucket_name, "MaxKeys": limit}
                if object_prefix:
                    params["Prefix"] = object_prefix
                response = client.list_objects_v2(**params)
                objects = [
                    {
                        "key": item.get("Key"),
                        "size": item.get("Size"),
                        "last_modified": _jsonable(item.get("LastModified")),
                        "etag": item.get("ETag"),
                        "storage_class": item.get("StorageClass"),
                    }
                    for item in response.get("Contents", [])
                ]
                return {
                    "success": True,
                    "asset_type": asset_type,
                    "operation": operation,
                    "bucket": bucket_name,
                    "prefix": object_prefix,
                    "object_count": len(objects),
                    "is_truncated": bool(response.get("IsTruncated")),
                    "objects": objects,
                    "output": f"Objects({len(objects)}): {', '.join(item['key'] for item in objects[:20] if item.get('key')) or '[empty]'}",
                }

            if operation == "head_object":
                if not object_key:
                    return {
                        "success": False,
                        "asset_type": asset_type,
                        "operation": operation,
                        "bucket": bucket_name,
                        "error": "head_object 需要 key 参数。",
                    }
                response = client.head_object(Bucket=bucket_name, Key=object_key)
                metadata = {
                    "content_length": response.get("ContentLength"),
                    "content_type": response.get("ContentType"),
                    "last_modified": _jsonable(response.get("LastModified")),
                    "etag": response.get("ETag"),
                    "storage_class": response.get("StorageClass"),
                    "metadata": response.get("Metadata") or {},
                }
                return {
                    "success": True,
                    "asset_type": asset_type,
                    "operation": operation,
                    "bucket": bucket_name,
                    "key": object_key,
                    "metadata": metadata,
                    "output": f"{bucket_name}/{object_key} 大小: {metadata.get('content_length')}",
                }
        except Exception as exc:
            logger.error("Object storage operation failed: %s", exc)
            return {
                "success": False,
                "asset_type": asset_type,
                "operation": operation,
                "bucket": bucket_name,
                "error": str(exc),
            }

        return {
            "success": False,
            "asset_type": asset_type,
            "operation": operation,
            "error": "未知对象存储操作。",
        }


object_storage_executor = ObjectStorageExecutor()
