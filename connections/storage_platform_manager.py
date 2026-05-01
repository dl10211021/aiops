"""Generic storage and backup platform API adapter.

The adapter provides a conservative read-only surface for backup systems and
storage management planes whose vendor APIs differ but still expose similar
concepts such as health, jobs, repositories and policies.
"""

from __future__ import annotations

from typing import Any, Callable

from connections.http_api_manager import http_api_executor


READONLY_OPERATIONS: dict[str, dict[str, str]] = {
    "health": {"path_key": "health_path", "default_path": "/health"},
    "status": {"path_key": "status_path", "default_path": "/status"},
    "version": {"path_key": "version_path", "default_path": "/version"},
    "jobs": {"path_key": "jobs_path", "default_path": "/api/v1/jobs"},
    "repositories": {"path_key": "repositories_path", "default_path": "/api/v1/repositories"},
    "policies": {"path_key": "policies_path", "default_path": "/api/v1/policies"},
    "capacity": {"path_key": "capacity_path", "default_path": "/api/v1/capacity"},
    "alerts": {"path_key": "alerts_path", "default_path": "/api/v1/alerts"},
}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _path(value: Any, default: str = "/") -> str:
    path = _string(value) or default
    if not path.startswith("/"):
        path = f"/{path}"
    return path


class StoragePlatformExecutor:
    def execute(
        self,
        *,
        asset_type: str,
        host: str,
        port: int | None,
        username: str = "",
        password: str | None = None,
        extra_args: dict[str, Any] | None = None,
        operation: str = "health",
        method: str = "GET",
        path: str | None = None,
        headers: dict[str, str] | None = None,
        body: object | None = None,
        timeout: int | None = None,
        request_executor: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        extra_args = extra_args or {}
        operation = _string(operation).lower() or "health"
        method = _string(method).upper() or "GET"
        if method not in {"GET", "HEAD"}:
            return {
                "success": False,
                "asset_type": asset_type,
                "operation": operation,
                "error": "存储/备份平台当前仅支持 GET/HEAD 只读请求；配置修改、删除、恢复、清理等动作必须走专门审批工具。",
            }

        if operation == "request":
            if not path:
                return {
                    "success": False,
                    "asset_type": asset_type,
                    "operation": operation,
                    "error": "request 操作需要显式 path 参数。",
                }
            request_path = _path(path)
        elif operation in READONLY_OPERATIONS:
            spec = READONLY_OPERATIONS[operation]
            request_path = _path(extra_args.get(spec["path_key"]) or path, spec["default_path"])
        else:
            return {
                "success": False,
                "asset_type": asset_type,
                "operation": operation,
                "error": f"存储/备份平台当前仅支持只读操作: {', '.join(sorted(set(READONLY_OPERATIONS) | {'request'}))}",
            }

        executor = request_executor or http_api_executor.request
        result = executor(
            asset_type=asset_type,
            host=host,
            port=port or 443,
            username=username,
            password=password,
            extra_args=extra_args,
            method=method,
            path=request_path,
            headers=headers or {},
            body=body,
            timeout=timeout or 20,
        )
        result.setdefault("asset_type", asset_type)
        result["operation"] = operation
        result["method"] = method
        result["path"] = request_path
        return result


storage_platform_executor = StoragePlatformExecutor()
