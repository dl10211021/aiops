import json
import unittest
from unittest.mock import patch
import hashlib

from connections.virtualization_manager import virtualization_api_executor


class TestVirtualizationManager(unittest.TestCase):
    def test_proxmox_operation_maps_to_readonly_api_path(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "output": "{}"}
            result = virtualization_api_executor.execute(
                asset_type="proxmox",
                protocol="proxmox",
                host="pve.local",
                port=8006,
                extra_args={"api_token": "root@pam!ops=token"},
                operation="nodes",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "nodes")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["path"], "/api2/json/nodes")
        self.assertEqual(kwargs["headers"]["Authorization"], "PVEAPIToken=root@pam!ops=token")
        self.assertEqual(kwargs["username"], "")
        self.assertIsNone(kwargs["password"])

    def test_proxmox_request_keeps_custom_path(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "output": "{}"}
            virtualization_api_executor.execute(
                asset_type="proxmox",
                protocol="proxmox",
                host="pve.local",
                port=8006,
                extra_args={"api_token": "PVEAPIToken=root@pam!ops=token"},
                operation="request",
                path="/api2/json/cluster/status",
            )

        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["path"], "/api2/json/cluster/status")
        self.assertEqual(kwargs["headers"]["Authorization"], "PVEAPIToken=root@pam!ops=token")

    def test_vmware_operation_maps_to_readonly_api_path_with_session_token(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "output": "{}"}
            result = virtualization_api_executor.execute(
                asset_type="vmware",
                protocol="vmware",
                host="vcenter.local",
                port=443,
                extra_args={"vmware_session_id": "session-123"},
                operation="hosts",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "hosts")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["asset_type"], "vmware")
        self.assertEqual(kwargs["path"], "/api/vcenter/host")
        self.assertEqual(kwargs["headers"]["vmware-api-session-id"], "session-123")
        self.assertEqual(kwargs["username"], "")
        self.assertIsNone(kwargs["password"])

    def test_vmware_username_password_gets_session_before_readonly_call(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.side_effect = [
                {"success": True, "output": '"session-from-login"'},
                {"success": True, "output": "{}"},
            ]
            result = virtualization_api_executor.execute(
                asset_type="vmware",
                protocol="vmware",
                host="vcenter.local",
                port=443,
                username="administrator@vsphere.local",
                password="secret",
                extra_args={},
                operation="version",
            )

        self.assertTrue(result["success"])
        self.assertEqual(request.call_args_list[0].kwargs["path"], "/api/session")
        self.assertEqual(request.call_args_list[0].kwargs["method"], "POST")
        self.assertEqual(request.call_args_list[1].kwargs["path"], "/api/appliance/system/version")
        self.assertEqual(request.call_args_list[1].kwargs["headers"]["vmware-api-session-id"], "session-from-login")

    def test_openstack_operation_maps_compute_path_with_token(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "output": "{}"}
            result = virtualization_api_executor.execute(
                asset_type="openstack",
                protocol="openstack",
                host="openstack.local",
                port=5000,
                extra_args={"openstack_token": "secret", "compute_base_path": "/nova/v2.1"},
                operation="servers",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "servers")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["asset_type"], "openstack")
        self.assertEqual(kwargs["path"], "/nova/v2.1/servers/detail")
        self.assertEqual(kwargs["headers"]["X-Auth-Token"], "secret")
        self.assertEqual(kwargs["username"], "")
        self.assertIsNone(kwargs["password"])

    def test_openstack_username_password_gets_keystone_token_before_readonly_call(self):
        class FakeResponse:
            headers = {"X-Subject-Token": "keystone-token"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, *_args):
                return json.dumps({"token": {"methods": ["password"]}}).encode()

        with (
            patch("connections.virtualization_manager.urllib.request.urlopen", return_value=FakeResponse()) as urlopen,
            patch("connections.virtualization_manager.http_api_executor.request") as request,
        ):
            request.return_value = {"success": True, "output": "{}"}
            result = virtualization_api_executor.execute(
                asset_type="openstack",
                protocol="openstack",
                host="openstack.local",
                port=5000,
                username="admin",
                password="secret",
                extra_args={"project_name": "admin", "project_id": "proj-1"},
                operation="volumes",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "volumes")
        self.assertEqual(urlopen.call_count, 1)
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["path"], "/volume/v3/proj-1/volumes/detail")
        self.assertEqual(kwargs["headers"]["X-Auth-Token"], "keystone-token")
        self.assertEqual(kwargs["username"], "")
        self.assertIsNone(kwargs["password"])

    def test_zstack_keeps_generic_http_fallback(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "output": "{}"}
            virtualization_api_executor.execute(
                asset_type="zstack",
                protocol="zstack",
                host="zstack.local",
                port=8080,
                extra_args={"api_token": "secret"},
                path="/zstack/v1/hosts",
            )

        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["asset_type"], "zstack")
        self.assertEqual(kwargs["path"], "/zstack/v1/hosts")

    def test_zstack_operation_maps_to_readonly_api_path_with_session_uuid(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "output": "{}"}
            result = virtualization_api_executor.execute(
                asset_type="zstack",
                protocol="zstack",
                host="zstack.local",
                port=8080,
                extra_args={"zstack_session_uuid": "session-123"},
                operation="vms",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "vms")
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["asset_type"], "zstack")
        self.assertEqual(kwargs["path"], "/zstack/v1/vm-instances")
        self.assertEqual(kwargs["headers"]["Authorization"], "OAuth session-123")
        self.assertEqual(kwargs["username"], "")
        self.assertIsNone(kwargs["password"])

    def test_zstack_username_password_gets_session_before_readonly_call(self):
        with patch("connections.virtualization_manager.http_api_executor.request") as request:
            request.side_effect = [
                {"success": True, "output": json.dumps({"inventory": {"uuid": "session-from-login"}})},
                {"success": True, "output": "{}"},
            ]
            result = virtualization_api_executor.execute(
                asset_type="zstack",
                protocol="zstack",
                host="zstack.local",
                port=8080,
                username="admin",
                password="secret",
                extra_args={},
                operation="hosts",
            )

        self.assertTrue(result["success"])
        login_kwargs = request.call_args_list[0].kwargs
        self.assertEqual(login_kwargs["method"], "PUT")
        self.assertEqual(login_kwargs["path"], "/zstack/v1/accounts/login")
        self.assertEqual(
            login_kwargs["body"]["logInByAccount"]["password"],
            hashlib.sha512(b"secret").hexdigest(),
        )
        readonly_kwargs = request.call_args_list[1].kwargs
        self.assertEqual(readonly_kwargs["path"], "/zstack/v1/hosts")
        self.assertEqual(readonly_kwargs["headers"]["Authorization"], "OAuth session-from-login")
        self.assertEqual(readonly_kwargs["username"], "")
        self.assertIsNone(readonly_kwargs["password"])


if __name__ == "__main__":
    unittest.main()
