import unittest

from scripts.check_runtime_policy_coverage import (
    approval_policy_coverage_issues_for_text,
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

    def test_accepts_allowed_file_with_distant_runtime_policy_wrapper(self):
        issues = runtime_policy_coverage_issues_for_text(
            "core/agent_tool_loop.py",
            "async def run(dispatcher):\n"
            "    return await execute_with_runtime_policy(\n"
            "        'tool',\n"
            "        {\n"
            "            'asset': 37,\n"
            "            'mode': 'read_only',\n"
            "            'source': 'headless',\n"
            "            'trace': True,\n"
            "        },\n"
            "        lambda: dispatcher.route_and_execute('tool', {}, {}),\n"
            "    )\n",
        )

        self.assertEqual(issues, [])

    def test_ignores_route_and_execute_mentions_in_comments_and_strings(self):
        issues = runtime_policy_coverage_issues_for_text(
            "api/comment_only.py",
            "def run():\n"
            "    text = 'dispatcher.route_and_execute(' \n"
            "    # dispatcher.route_and_execute('tool', {}, {})\n"
            "    return text\n",
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

    def test_rejects_direct_safety_policy_approval_import(self):
        issues = approval_policy_coverage_issues_for_text(
            "core/unsafe_approval.py",
            "from core.safety_policy import check_approval_needed\n",
        )

        self.assertEqual(
            issues,
            [
                "core/unsafe_approval.py: import dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
            ],
        )

    def test_rejects_multiline_safety_policy_approval_import(self):
        issues = approval_policy_coverage_issues_for_text(
            "core/unsafe_approval.py",
            "from core.safety_policy import (\n"
            "    check_approval_needed,\n"
            "    SafetyLevel,\n"
            ")\n",
        )

        self.assertEqual(
            issues,
            [
                "core/unsafe_approval.py: import dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
            ],
        )

    def test_rejects_qualified_safety_policy_approval_call(self):
        issues = approval_policy_coverage_issues_for_text(
            "api/unsafe_approval.py",
            "needs_approval, reason = core.safety_policy.check_approval_needed('tool', {}, {})\n",
        )

        self.assertEqual(
            issues,
            [
                "api/unsafe_approval.py: call dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
            ],
        )

    def test_rejects_safety_policy_alias_approval_call(self):
        issues = approval_policy_coverage_issues_for_text(
            "api/unsafe_approval.py",
            "import core.safety_policy as safety\n"
            "needs_approval, reason = safety.check_approval_needed('tool', {}, {})\n",
        )

        self.assertEqual(
            issues,
            [
                "api/unsafe_approval.py: call dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
            ],
        )

    def test_dispatcher_may_import_safety_policy_approval(self):
        issues = approval_policy_coverage_issues_for_text(
            "core/dispatcher.py",
            "from core.safety_policy import check_approval_needed\n",
        )

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
