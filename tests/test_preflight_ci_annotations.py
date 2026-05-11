import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import preflight


class TestPreflightCiAnnotations(unittest.TestCase):
    def test_github_escape_uses_actions_annotation_escaping(self):
        self.assertEqual(
            preflight.github_escape("a%b\r\nc"),
            "a%25b%0D%0Ac",
        )

    def test_run_emits_github_error_annotation_on_failure_in_actions(self):
        command = [sys.executable, "-c", "print('line 1'); raise SystemExit(7)"]
        output = io.StringIO()

        with (
            patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}),
            redirect_stdout(output),
        ):
            code = preflight.run("sample check", command, Path.cwd())

        self.assertEqual(code, 7)
        self.assertIn("::error title=sample check failed::line 1", output.getvalue())
        self.assertIn("FAILED: sample check exited with 7", output.getvalue())


if __name__ == "__main__":
    unittest.main()
