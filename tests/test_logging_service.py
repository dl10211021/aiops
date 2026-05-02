import logging
import unittest

from core.logging_service import LOG_FORMAT, build_request_id_log_record_factory


class TestLoggingService(unittest.TestCase):
    def test_log_record_factory_adds_current_request_id(self):
        previous_factory = logging.getLogRecordFactory()
        factory = build_request_id_log_record_factory(previous_factory, lambda: "req-unit")

        record = factory("opscore.test", logging.INFO, __file__, 10, "hello", (), None)

        self.assertEqual(record.request_id, "req-unit")

    def test_log_record_factory_uses_dash_when_request_id_missing(self):
        previous_factory = logging.getLogRecordFactory()
        factory = build_request_id_log_record_factory(previous_factory, lambda: None)

        record = factory("opscore.test", logging.INFO, __file__, 10, "hello", (), None)

        self.assertEqual(record.request_id, "-")

    def test_log_format_includes_request_id(self):
        self.assertIn("request_id", LOG_FORMAT)


if __name__ == "__main__":
    unittest.main()
