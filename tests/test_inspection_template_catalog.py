import unittest

from core import inspection_templates
from core.inspection_template_catalog import (
    ALLOWED_TOOLS,
    BUILTIN_TEMPLATES,
    WINDOWS_SECURITY_AUDIT_COMMAND,
)


class InspectionTemplateCatalogTests(unittest.TestCase):
    def test_catalog_exports_builtin_templates_and_allowed_tools(self):
        template_ids = {template["id"] for template in BUILTIN_TEMPLATES}

        self.assertIn("builtin-k8s-core-readonly", template_ids)
        self.assertIn("builtin-windows-core-readonly", template_ids)
        self.assertIn("builtin-mysql-core-readonly", template_ids)
        self.assertLessEqual(
            {"linux_execute_command", "winrm_execute_command", "db_execute_query", "k8s_api_request"},
            ALLOWED_TOOLS,
        )

    def test_windows_security_audit_command_keeps_permission_fallback(self):
        self.assertIn("LogName='Security'", WINDOWS_SECURITY_AUDIT_COMMAND)
        self.assertIn("permission_denied", WINDOWS_SECURITY_AUDIT_COMMAND)
        self.assertIn("Event Log Readers", WINDOWS_SECURITY_AUDIT_COMMAND)

    def test_inspection_templates_keeps_backward_compatible_catalog_exports(self):
        self.assertIs(inspection_templates.ALLOWED_TOOLS, ALLOWED_TOOLS)
        self.assertIs(inspection_templates.BUILTIN_TEMPLATES, BUILTIN_TEMPLATES)
        self.assertIs(
            inspection_templates.WINDOWS_SECURITY_AUDIT_COMMAND,
            WINDOWS_SECURITY_AUDIT_COMMAND,
        )


if __name__ == "__main__":
    unittest.main()
