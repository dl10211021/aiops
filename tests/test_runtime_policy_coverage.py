import unittest

from scripts.check_runtime_policy_coverage import (
    find_runtime_policy_coverage_issues,
    runtime_policy_coverage_issues_for_text,
)


class RuntimePolicyCoverageTests(unittest.TestCase):
    def test_production_route_and_execute_calls_are_runtime_policy_wrapped(self):
        self.assertEqual(find_runtime_policy_coverage_issues(), [])

    def test_rejects_allowed_file_with_unwrapped_direct_call(self):
        issues = runtime_policy_coverage_issues_for_text(
            "core/agent_tool_loop.py",
            "async def run(dispatcher):\n"
            "    return await dispatcher.route_and_execute('tool', {}, {})\n",
        )

        self.assertEqual(
            issues,
            [
                "core/agent_tool_loop.py:2: route_and_execute call is not wrapped by execute_with_runtime_policy"
            ],
        )

    def test_accepts_allowed_file_with_nearby_runtime_policy_wrapper(self):
        issues = runtime_policy_coverage_issues_for_text(
            "core/agent_tool_loop.py",
            "async def run(dispatcher):\n"
            "    return await execute_with_runtime_policy(\n"
            "        'tool',\n"
            "        lambda: dispatcher.route_and_execute('tool', {}, {}),\n"
            "    )\n",
        )

        self.assertEqual(issues, [])

    def test_rejects_unreviewed_production_file(self):
        issues = runtime_policy_coverage_issues_for_text(
            "api/unsafe_route.py",
            "async def run(dispatcher):\n"
            "    return await dispatcher.route_and_execute('tool', {}, {})\n",
        )

        self.assertEqual(
            issues,
            ["api/unsafe_route.py: route_and_execute call is not on the reviewed execution allowlist"],
        )


if __name__ == "__main__":
    unittest.main()
