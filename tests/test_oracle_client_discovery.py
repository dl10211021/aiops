import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from connections.oracle_client_discovery import (
    discover_oracle_client_lib_dir,
    truthy,
    valid_oracle_client_dir,
)


class OracleClientDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = (
            Path.cwd() / "tests" / f"tmp_oracle_client_discovery_{uuid.uuid4().hex}"
        )
        self.tmp_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def test_truthy_accepts_supported_flags(self):
        self.assertTrue(truthy("true"))
        self.assertTrue(truthy("YES"))
        self.assertTrue(truthy("1"))
        self.assertFalse(truthy("false"))
        self.assertFalse(truthy(None))

    def test_valid_oracle_client_dir_requires_native_client_library(self):
        client_dir = self.tmp_path / "instantclient_23_0"
        client_dir.mkdir()

        self.assertIsNone(valid_oracle_client_dir(client_dir))

        (client_dir / "oci.dll").write_text("fake", encoding="utf-8")

        self.assertEqual(valid_oracle_client_dir(client_dir), client_dir.resolve())

    def test_discover_oracle_client_lib_dir_uses_explicit_path(self):
        client_dir = self.tmp_path / "instantclient_23_0"
        client_dir.mkdir()
        (client_dir / "oci.dll").write_text("fake", encoding="utf-8")

        with patch.dict(
            os.environ,
            {"OPSCORE_ORACLE_THICK_MODE": "true"},
            clear=False,
        ):
            config = discover_oracle_client_lib_dir(
                {"oracle_client_lib_dir": str(client_dir)}
            )

        self.assertEqual(
            config,
            {
                "detected": True,
                "lib_dir": str(client_dir.resolve()),
                "source": "explicit",
                "thick_mode_env_enabled": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
