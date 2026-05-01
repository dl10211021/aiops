import unittest
from unittest.mock import patch

from connections.datastore_manager import MemcachedExecutor


class FakeSocket:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.sent = b""
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, data):
        self.sent += data

    def recv(self, size):
        if self.payloads:
            return self.payloads.pop(0)
        return b""


class TestMemcachedManager(unittest.TestCase):
    def test_version_command_uses_text_protocol(self):
        fake = FakeSocket([b"VERSION 1.6.22\r\n"])
        with patch("connections.datastore_manager.socket.create_connection", return_value=fake) as create_connection:
            result = MemcachedExecutor().execute_command(
                host="cache.local",
                port=11211,
                command="version",
            )

        self.assertTrue(result["success"])
        self.assertEqual(fake.sent, b"version\r\n")
        self.assertEqual(result["data"]["version"], "1.6.22")
        create_connection.assert_called_once_with(("cache.local", 11211), timeout=8)

    def test_stats_command_parses_key_value_lines(self):
        fake = FakeSocket([b"STAT curr_items 3\r\nSTAT bytes 128\r\nEND\r\n"])
        with patch("connections.datastore_manager.socket.create_connection", return_value=fake):
            result = MemcachedExecutor().execute_command(
                host="cache.local",
                port=11211,
                command="stats",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["curr_items"], "3")
        self.assertEqual(result["data"]["bytes"], "128")

    def test_write_command_is_rejected_before_socket_connection(self):
        with patch("connections.datastore_manager.socket.create_connection") as create_connection:
            result = MemcachedExecutor().execute_command(
                host="cache.local",
                port=11211,
                command="flush_all",
            )

        self.assertFalse(result["success"])
        self.assertIn("只读命令", result["error"])
        create_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
