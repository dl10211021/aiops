import unittest

from core import safety_policy
from core.safety_action_classifiers import (
    _command_segments,
    _sql_action_summary,
    _sql_actions,
    classify_linux_actions,
    classify_memcached_actions,
    classify_mongodb_actions,
    classify_network_actions,
    classify_redis_actions,
    classify_windows_actions,
)


class SafetyActionClassifierTests(unittest.TestCase):
    def test_linux_classifier_preserves_read_write_and_noop_redirect_semantics(self):
        self.assertEqual(_command_segments("systemctl status sshd 2>/dev/null"), ["systemctl status sshd"])
        self.assertIn("linux.read.service", classify_linux_actions("systemctl status sshd 2>/dev/null"))
        self.assertNotIn("linux.file.write", classify_linux_actions("systemctl status sshd 2>/dev/null"))
        self.assertIn("linux.file.write", classify_linux_actions("journalctl -xe > /tmp/journal.txt"))
        self.assertIn("linux.system.power", classify_linux_actions("sudo reboot"))

    def test_sql_classifier_and_summary_preserve_database_actions(self):
        self.assertEqual(_sql_actions("SELECT * FROM users"), ["sql.read"])
        self.assertIn("sql.instance_admin", _sql_actions("ALTER SYSTEM SWITCH LOGFILE"))
        self.assertEqual(_sql_action_summary("DROP USER app_user CASCADE")[0], "数据库高危删除")

    def test_platform_classifiers_cover_existing_datastores_and_network_devices(self):
        self.assertEqual(classify_redis_actions("SET app:key value"), ["redis.key_write"])
        self.assertEqual(classify_memcached_actions("flush_all"), ["memcached.flush"])
        self.assertEqual(classify_mongodb_actions(operation="dropDatabase"), ["mongodb.drop"])
        self.assertEqual(classify_network_actions("display current-configuration"), ["network.read.config"])
        self.assertIn("network.reset", classify_network_actions("reset saved-configuration"))

    def test_windows_classifier_preserves_read_and_change_distinctions(self):
        self.assertIn("windows.read.service", classify_windows_actions("Get-Service"))
        self.assertIn("windows.service.change", classify_windows_actions("Restart-Service Spooler"))
        self.assertIn("hyperv.vm.delete", classify_windows_actions("Remove-VM -Name old-vm -Force"))

    def test_safety_policy_keeps_backward_compatible_exports(self):
        self.assertIs(safety_policy.classify_linux_actions, classify_linux_actions)
        self.assertIs(safety_policy.classify_windows_actions, classify_windows_actions)
        self.assertIs(safety_policy.classify_redis_actions, classify_redis_actions)
        self.assertIs(safety_policy.classify_memcached_actions, classify_memcached_actions)


if __name__ == "__main__":
    unittest.main()
