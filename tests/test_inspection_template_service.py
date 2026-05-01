import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import inspection_templates
from core.inspection_template_service import (
    InspectionTemplateServiceError,
    list_inspection_template_records,
    remove_inspection_template_record,
    save_inspection_template_record,
)


class TestInspectionTemplateService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_inspection_template_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_inspection_template_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "templates.json"

    def test_save_list_and_remove_template_records(self):
        store_path = self._store_path("crud")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            template = save_inspection_template_record(
                {
                    "id": "linux-basic-custom",
                    "name": "Linux Basic Custom",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "enabled": True,
                    "steps": [
                        {
                            "name": "uptime",
                            "title": "Uptime",
                            "tool": "linux_execute_command",
                            "command": "uptime",
                        }
                    ],
                }
            )
            records = list_inspection_template_records()
            remove_inspection_template_record("linux-basic-custom")

        self.assertEqual(template["id"], "linux-basic-custom")
        self.assertIn("linux-basic-custom", {item["id"] for item in records})

    def test_update_template_record_uses_path_id(self):
        store_path = self._store_path("update")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            template = save_inspection_template_record(
                {
                    "id": "body-id",
                    "name": "Linux Basic Custom",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "enabled": True,
                    "steps": [
                        {
                            "name": "uptime",
                            "title": "Uptime",
                            "tool": "linux_execute_command",
                            "command": "uptime",
                        }
                    ],
                },
                "path-id",
            )

        self.assertEqual(template["id"], "path-id")

    def test_remove_missing_template_raises_404(self):
        store_path = self._store_path("missing")
        with patch.object(inspection_templates, "TEMPLATE_STORE_PATH", store_path):
            with self.assertRaises(InspectionTemplateServiceError) as ctx:
                remove_inspection_template_record("missing")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "巡检模板不存在")
