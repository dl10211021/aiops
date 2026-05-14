import unittest

from scripts.check_runtime_policy_coverage import find_runtime_policy_coverage_issues


class RuntimePolicyCoverageTests(unittest.TestCase):
    def test_production_route_and_execute_calls_are_runtime_policy_wrapped(self):
        self.assertEqual(find_runtime_policy_coverage_issues(), [])


if __name__ == "__main__":
    unittest.main()
