"""Virtualization platform API executor.

Native slices cover common read-only operations for Proxmox, VMware,
OpenStack, and ZStack while keeping a generic HTTP fallback for other platform
paths already used by templates.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from connections.http_api_manager import build_base_url, http_api_executor


PROXMOX_OPERATIONS = {
    "version": ("GET", "/api2/json/version"),
    "nodes": ("GET", "/api2/json/nodes"),
    "resources": ("GET", "/api2/json/cluster/resources"),
    "vms": ("GET", "/api2/json/cluster/resources?type=vm"),
    "storage": ("GET", "/api2/json/storage"),
}

VMWARE_OPERATIONS = {
    "version": ("GET", "/api/appliance/system/version"),
    "hosts": ("GET", "/api/vcenter/host"),
    "vms": ("GET", "/api/vcenter/vm"),
    "datastores": ("GET", "/api/vcenter/datastore"),
    "storage": ("GET", "/api/vcenter/datastore"),
}

OPENSTACK_OPERATIONS = {
    "version": ("GET", "/v3"),
    "catalog": ("GET", "/v3/auth/catalog"),
    "projects": ("GET", "/v3/projects"),
    "servers": ("GET", "compute:/servers/detail"),
    "vms": ("GET", "compute:/servers/detail"),
    "hypervisors": ("GET", "compute:/os-hypervisors/detail"),
    "volumes": ("GET", "volume:/volumes/detail"),
    "networks": ("GET", "network:/networks"),
    "routers": ("GET", "network:/routers"),
    "images": ("GET", "image:/images"),
}

ZSTACK_OPERATIONS = {
    "version": ("GET", "/zstack/v1/management-nodes"),
    "management_nodes": ("GET", "/zstack/v1/management-nodes"),
    "zones": ("GET", "/zstack/v1/zones"),
    "clusters": ("GET", "/zstack/v1/clusters"),
    "hosts": ("GET", "/zstack/v1/hosts"),
    "vms": ("GET", "/zstack/v1/vm-instances"),
    "servers": ("GET", "/zstack/v1/vm-instances"),
    "volumes": ("GET", "/zstack/v1/volumes"),
    "images": ("GET", "/zstack/v1/images"),
    "networks": ("GET", "/zstack/v1/l3-networks"),
    "l3_networks": ("GET", "/zstack/v1/l3-networks"),
    "primary_storage": ("GET", "/zstack/v1/primary-storage"),
    "backup_storage": ("GET", "/zstack/v1/backup-storage"),
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _proxmox_token_header(extra_args: dict[str, Any]) -> str:
    token = _clean(
        extra_args.get("api_token")
        or extra_args.get("proxmox_api_token")
        or extra_args.get("pve_api_token")
    )
    if not token:
        return ""
    return token if token.startswith("PVEAPIToken=") else f"PVEAPIToken={token}"


def _vmware_session_id(extra_args: dict[str, Any]) -> str:
    return _clean(
        extra_args.get("vmware_session_id")
        or extra_args.get("vcenter_session_id")
        or extra_args.get("api_token")
        or extra_args.get("bearer_token")
    )


def _openstack_token(extra_args: dict[str, Any]) -> str:
    return _clean(
        extra_args.get("openstack_token")
        or extra_args.get("os_token")
        or extra_args.get("api_token")
        or extra_args.get("bearer_token")
    )


def _zstack_authorization(extra_args: dict[str, Any]) -> str:
    token = _clean(
        extra_args.get("zstack_session_uuid")
        or extra_args.get("session_uuid")
        or extra_args.get("zstack_token")
        or extra_args.get("api_token")
        or extra_args.get("bearer_token")
    )
    if not token:
        return ""
    return token if token.lower().startswith("oauth ") else f"OAuth {token}"


def _zstack_password_hash(password: str, extra_args: dict[str, Any]) -> str:
    configured = _clean(extra_args.get("zstack_password_hash") or extra_args.get("password_hash"))
    if configured:
        return configured
    password = _clean(password)
    is_sha512 = len(password) == 128 and all(ch in "0123456789abcdefABCDEF" for ch in password)
    if is_sha512 or extra_args.get("password_is_sha512"):
        return password
    return hashlib.sha512(password.encode("utf-8")).hexdigest()


def _join_path(prefix: str, suffix: str) -> str:
    clean_prefix = _clean(prefix).rstrip("/")
    clean_suffix = _clean(suffix)
    if not clean_suffix.startswith("/"):
        clean_suffix = f"/{clean_suffix}"
    return f"{clean_prefix}{clean_suffix}" if clean_prefix else clean_suffix


@dataclass
class VirtualizationApiExecutor:
    default_timeout: int = 15

    def execute(
        self,
        *,
        asset_type: str,
        protocol: str,
        host: str,
        port: int | None,
        username: str = "",
        password: str | None = None,
        extra_args: dict | None = None,
        operation: str | None = None,
        method: str = "GET",
        path: str | None = None,
        headers: dict | None = None,
        body: object | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        extra_args = extra_args or {}
        asset_type = _clean(asset_type).lower()
        protocol = _clean(protocol or asset_type).lower()
        operation = _clean(operation or "").lower()

        if protocol == "proxmox" or asset_type == "proxmox":
            return self._execute_proxmox(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                operation=operation,
                method=method,
                path=path,
                headers=headers,
                body=body,
                timeout=timeout or self.default_timeout,
            )
        if protocol == "vmware" or asset_type == "vmware":
            return self._execute_vmware(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                operation=operation,
                method=method,
                path=path,
                headers=headers,
                body=body,
                timeout=timeout or self.default_timeout,
            )
        if protocol == "openstack" or asset_type == "openstack":
            return self._execute_openstack(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                operation=operation,
                method=method,
                path=path,
                headers=headers,
                body=body,
                timeout=timeout or self.default_timeout,
            )
        if protocol == "zstack" or asset_type == "zstack":
            return self._execute_zstack(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                operation=operation,
                method=method,
                path=path,
                headers=headers,
                body=body,
                timeout=timeout or self.default_timeout,
            )

        return http_api_executor.request(
            asset_type=asset_type,
            host=host,
            port=int(port or 443),
            username=username,
            password=password,
            extra_args=extra_args,
            method=method,
            path=path or "/",
            headers=headers or {},
            body=body,
            timeout=timeout or self.default_timeout,
        )

    def _execute_proxmox(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str | None,
        extra_args: dict[str, Any],
        operation: str,
        method: str,
        path: str | None,
        headers: dict | None,
        body: object | None,
        timeout: int,
    ) -> dict[str, Any]:
        headers = dict(headers or {})
        if operation and operation != "request":
            method, path = PROXMOX_OPERATIONS.get(operation, ("GET", path or "/api2/json/version"))
        else:
            method = _clean(method or "GET").upper()
            path = path or "/api2/json/version"

        token_header = _proxmox_token_header(extra_args)
        if token_header:
            headers.setdefault("Authorization", token_header)
        elif username and password and not headers.get("Cookie"):
            ticket = self._get_proxmox_ticket(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                timeout=timeout,
            )
            if not ticket.get("success"):
                return ticket
            headers.setdefault("Cookie", f"PVEAuthCookie={ticket['ticket']}")
            if ticket.get("csrf_token") and method.upper() not in {"GET", "HEAD"}:
                headers.setdefault("CSRFPreventionToken", ticket["csrf_token"])

        return http_api_executor.request(
            asset_type="proxmox",
            host=host,
            port=int(port or 8006),
            username="" if headers.get("Authorization") or headers.get("Cookie") else username,
            password=None if headers.get("Authorization") or headers.get("Cookie") else password,
            extra_args=extra_args,
            method=method,
            path=path,
            headers=headers,
            body=body,
            timeout=timeout,
        ) | {"operation": operation or "request"}

    def _execute_vmware(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str | None,
        extra_args: dict[str, Any],
        operation: str,
        method: str,
        path: str | None,
        headers: dict | None,
        body: object | None,
        timeout: int,
    ) -> dict[str, Any]:
        headers = dict(headers or {})
        if operation and operation != "request":
            method, path = VMWARE_OPERATIONS.get(operation, ("GET", path or "/api/appliance/system/version"))
        else:
            method = _clean(method or "GET").upper()
            path = path or "/api/appliance/system/version"

        session_id = _vmware_session_id(extra_args)
        if session_id:
            headers.setdefault("vmware-api-session-id", session_id)
        elif username and password and not headers.get("vmware-api-session-id"):
            session = self._get_vmware_session(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                timeout=timeout,
            )
            if not session.get("success"):
                return session
            headers.setdefault("vmware-api-session-id", session["session_id"])

        return http_api_executor.request(
            asset_type="vmware",
            host=host,
            port=int(port or 443),
            username="" if headers.get("vmware-api-session-id") else username,
            password=None if headers.get("vmware-api-session-id") else password,
            extra_args=extra_args,
            method=method,
            path=path,
            headers=headers,
            body=body,
            timeout=timeout,
        ) | {"operation": operation or "request"}

    def _get_vmware_session(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str,
        extra_args: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        configured_path = _clean(extra_args.get("session_path") or extra_args.get("vmware_session_path"))
        candidate_paths = [configured_path] if configured_path else ["/api/session", "/rest/com/vmware/cis/session"]
        last_result: dict[str, Any] | None = None
        for session_path in candidate_paths:
            result = http_api_executor.request(
                asset_type="vmware",
                host=host,
                port=int(port or 443),
                username=username,
                password=password,
                extra_args=extra_args,
                method="POST",
                path=session_path,
                headers={},
                body=None,
                timeout=timeout,
            )
            last_result = result
            if not result.get("success"):
                continue
            session_id = self._extract_vmware_session_id(result.get("output"))
            if session_id:
                return {"success": True, "session_id": session_id, "session_path": session_path}
        return {
            "success": False,
            "asset_type": "vmware",
            "error": "VMware session response missing session id",
            "details": last_result or {},
        }

    @staticmethod
    def _extract_vmware_session_id(output: Any) -> str:
        text = _clean(output)
        if not text:
            return ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text.strip('"')
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            value = payload.get("value") or payload.get("session_id")
            return _clean(value)
        return ""

    def _execute_openstack(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str | None,
        extra_args: dict[str, Any],
        operation: str,
        method: str,
        path: str | None,
        headers: dict | None,
        body: object | None,
        timeout: int,
    ) -> dict[str, Any]:
        headers = dict(headers or {})
        if operation and operation != "request":
            method, path = OPENSTACK_OPERATIONS.get(operation, ("GET", path or "/v3"))
            path = self._openstack_operation_path(path, extra_args)
        else:
            method = _clean(method or "GET").upper()
            path = path or "/v3"

        token = _openstack_token(extra_args)
        if token:
            headers.setdefault("X-Auth-Token", token)
        elif username and password and not headers.get("X-Auth-Token"):
            auth = self._get_openstack_token(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                timeout=timeout,
            )
            if not auth.get("success"):
                return auth
            headers.setdefault("X-Auth-Token", auth["token"])

        return http_api_executor.request(
            asset_type="openstack",
            host=host,
            port=int(port or 5000),
            username="" if headers.get("X-Auth-Token") else username,
            password=None if headers.get("X-Auth-Token") else password,
            extra_args=extra_args,
            method=method,
            path=path,
            headers=headers,
            body=body,
            timeout=timeout,
        ) | {"operation": operation or "request"}

    def _openstack_operation_path(self, path: str, extra_args: dict[str, Any]) -> str:
        if ":" not in path:
            return path
        service, suffix = path.split(":", 1)
        project_id = _clean(extra_args.get("project_id") or extra_args.get("tenant_id"))
        defaults = {
            "compute": _clean(extra_args.get("compute_base_path") or extra_args.get("nova_base_path") or "/compute/v2.1"),
            "volume": _clean(
                extra_args.get("volume_base_path")
                or extra_args.get("cinder_base_path")
                or (f"/volume/v3/{project_id}" if project_id else "/volume/v3")
            ),
            "network": _clean(extra_args.get("network_base_path") or extra_args.get("neutron_base_path") or "/networking/v2.0"),
            "image": _clean(extra_args.get("image_base_path") or extra_args.get("glance_base_path") or "/image/v2"),
        }
        return _join_path(defaults.get(service, ""), suffix)

    def _get_openstack_token(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str,
        extra_args: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        user_domain = _clean(extra_args.get("user_domain_name") or extra_args.get("domain_name") or "Default")
        project_domain = _clean(extra_args.get("project_domain_name") or extra_args.get("domain_name") or "Default")
        project_name = _clean(extra_args.get("project_name") or extra_args.get("tenant_name"))
        project_id = _clean(extra_args.get("project_id") or extra_args.get("tenant_id"))
        auth: dict[str, Any] = {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "password": password,
                        "domain": {"name": user_domain},
                    }
                },
            }
        }
        if project_id:
            auth["scope"] = {"project": {"id": project_id}}
        elif project_name:
            auth["scope"] = {
                "project": {
                    "name": project_name,
                    "domain": {"name": project_domain},
                }
            }
        body = json.dumps({"auth": auth}).encode("utf-8")
        auth_path = _clean(extra_args.get("auth_path") or extra_args.get("keystone_auth_path") or "/v3/auth/tokens")
        url = urllib.parse.urljoin(f"{build_base_url(host, int(port or 5000), extra_args)}/", auth_path.lstrip("/"))
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                token = resp.headers.get("X-Subject-Token") or resp.headers.get("x-subject-token")
                payload_text = resp.read(2 * 1024 * 1024).decode("utf-8", "replace")
        except Exception as exc:
            return {"success": False, "asset_type": "openstack", "url": url, "error": str(exc)}
        if not token:
            return {
                "success": False,
                "asset_type": "openstack",
                "url": url,
                "error": "OpenStack token response missing X-Subject-Token",
                "output": payload_text,
            }
        return {"success": True, "token": token, "auth_path": auth_path}

    def _execute_zstack(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str | None,
        extra_args: dict[str, Any],
        operation: str,
        method: str,
        path: str | None,
        headers: dict | None,
        body: object | None,
        timeout: int,
    ) -> dict[str, Any]:
        headers = dict(headers or {})
        if operation and operation != "request":
            method, path = ZSTACK_OPERATIONS.get(operation, ("GET", path or "/zstack/v1/management-nodes"))
        else:
            method = _clean(method or "GET").upper()
            path = path or "/zstack/v1/management-nodes"

        authorization = _zstack_authorization(extra_args)
        if authorization:
            headers.setdefault("Authorization", authorization)
        elif username and password and "Authorization" not in headers:
            session = self._get_zstack_session(
                host=host,
                port=port,
                username=username,
                password=password,
                extra_args=extra_args,
                timeout=timeout,
            )
            if not session.get("success"):
                return session
            headers.setdefault("Authorization", f"OAuth {session['session_uuid']}")

        return http_api_executor.request(
            asset_type="zstack",
            host=host,
            port=int(port or 8080),
            username="" if headers.get("Authorization") else username,
            password=None if headers.get("Authorization") else password,
            extra_args=extra_args,
            method=method,
            path=path,
            headers=headers,
            body=body,
            timeout=timeout,
        ) | {"operation": operation or "request"}

    def _get_zstack_session(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str,
        extra_args: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        path = _clean(extra_args.get("auth_path") or extra_args.get("zstack_auth_path") or "/zstack/v1/accounts/login")
        result = http_api_executor.request(
            asset_type="zstack",
            host=host,
            port=int(port or 8080),
            username="",
            password=None,
            extra_args=extra_args,
            method="PUT",
            path=path,
            headers={"Content-Type": "application/json;charset=UTF-8"},
            body={
                "logInByAccount": {
                    "accountName": username,
                    "password": _zstack_password_hash(password, extra_args),
                }
            },
            timeout=timeout,
        )
        if not result.get("success"):
            return result | {"asset_type": "zstack", "auth_path": path}
        session_uuid = self._extract_zstack_session_uuid(result.get("output"))
        if not session_uuid:
            return {
                "success": False,
                "asset_type": "zstack",
                "auth_path": path,
                "error": "ZStack login response missing session uuid",
                "details": result,
            }
        return {"success": True, "session_uuid": session_uuid, "auth_path": path}

    @staticmethod
    def _extract_zstack_session_uuid(output: Any) -> str:
        text = _clean(output)
        if not text:
            return ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text.strip('"')
        if isinstance(payload, str):
            return payload
        candidates: list[Any] = []
        if isinstance(payload, dict):
            candidates.extend([payload.get("sessionUuid"), payload.get("uuid")])
            for key in ("inventory", "value", "data"):
                value = payload.get(key)
                if isinstance(value, dict):
                    candidates.extend([value.get("sessionUuid"), value.get("uuid")])
        for candidate in candidates:
            value = _clean(candidate)
            if value:
                return value
        return ""

    def _get_proxmox_ticket(
        self,
        *,
        host: str,
        port: int | None,
        username: str,
        password: str,
        extra_args: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        realm = _clean(extra_args.get("realm") or extra_args.get("proxmox_realm"))
        effective_username = username if "@" in username or not realm else f"{username}@{realm}"
        data = urllib.parse.urlencode({"username": effective_username, "password": password}).encode("utf-8")
        url = urllib.parse.urljoin(f"{build_base_url(host, int(port or 8006), extra_args)}/", "api2/json/access/ticket")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as exc:
            return {"success": False, "asset_type": "proxmox", "url": url, "error": str(exc)}
        data_obj = payload.get("data") if isinstance(payload, dict) else {}
        ticket = data_obj.get("ticket") if isinstance(data_obj, dict) else ""
        if not ticket:
            return {"success": False, "asset_type": "proxmox", "url": url, "error": "Proxmox ticket response missing ticket"}
        return {
            "success": True,
            "ticket": ticket,
            "csrf_token": data_obj.get("CSRFPreventionToken"),
        }


virtualization_api_executor = VirtualizationApiExecutor()
