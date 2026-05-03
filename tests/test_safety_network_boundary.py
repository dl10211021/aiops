import unittest

from core.safety_network_boundary import check_network_boundary


TOOL_CATEGORY = {
    "linux_execute_command": "linux",
    "winrm_execute_command": "windows",
    "network_cli_execute_command": "network",
    "http_api_request": "http",
}


def boundary_policy(**overrides):
    boundary = {
        "enabled": True,
        "active_cidrs": ["172.17.0.0/16"],
        "readonly_cidrs": ["10.0.0.0/8"],
        "blocked_cidrs": [],
        "allowed_hosts": [],
        "blocked_hosts": [],
        "block_unknown_targets": True,
    }
    boundary.update(overrides)
    return {"network_boundary": boundary}


class SafetyNetworkBoundaryTests(unittest.TestCase):
    def test_allows_active_probe_inside_active_cidr(self):
        blocked, reason = check_network_boundary(
            "linux_execute_command",
            {"command": "ping -c 1 172.17.8.150"},
            {"host": "172.17.8.150"},
            policy=boundary_policy(),
            tool_category=TOOL_CATEGORY,
        )

        self.assertFalse(blocked)
        self.assertEqual(reason, "")

    def test_blocks_readonly_cidr_and_unknown_targets(self):
        readonly_blocked, readonly_reason = check_network_boundary(
            "linux_execute_command",
            {"command": "curl http://10.39.80.238:9100/metrics"},
            {"host": "172.17.8.150"},
            policy=boundary_policy(),
            tool_category=TOOL_CATEGORY,
        )
        unknown_blocked, unknown_reason = check_network_boundary(
            "linux_execute_command",
            {"command": "nc -vz 192.168.1.10 22"},
            {"host": "172.17.8.150"},
            policy=boundary_policy(),
            tool_category=TOOL_CATEGORY,
        )

        self.assertTrue(readonly_blocked)
        self.assertIn("10.39.80.238", readonly_reason)
        self.assertTrue(unknown_blocked)
        self.assertIn("192.168.1.10", unknown_reason)

    def test_ignores_network_option_values_when_extracting_targets(self):
        blocked, reason = check_network_boundary(
            "linux_execute_command",
            {"command": "curl -X GET -H 'Accept: application/json' http://172.17.8.150/api/health"},
            {"host": "172.17.8.150"},
            policy=boundary_policy(),
            tool_category=TOOL_CATEGORY,
        )

        self.assertFalse(blocked)
        self.assertEqual(reason, "")

    def test_blocks_http_request_outside_allowed_targets(self):
        blocked, reason = check_network_boundary(
            "http_api_request",
            {"method": "GET", "url": "http://203.0.113.10/api/health"},
            {},
            policy=boundary_policy(),
            tool_category=TOOL_CATEGORY,
        )

        self.assertTrue(blocked)
        self.assertIn("203.0.113.10", reason)

    def test_noops_when_boundary_disabled(self):
        blocked, reason = check_network_boundary(
            "linux_execute_command",
            {"command": "ping 203.0.113.10"},
            {},
            policy={"network_boundary": {"enabled": False}},
            tool_category=TOOL_CATEGORY,
        )

        self.assertFalse(blocked)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
