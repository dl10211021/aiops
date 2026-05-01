import socket
import threading
import unittest

from connections.service_probe_manager import service_probe_executor


class OneShotTcpServer:
    def __init__(self, response: bytes = b""):
        self.response = response
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.sock.close()
        except OSError:
            pass
        self.thread.join(timeout=2)

    def _serve(self):
        try:
            conn, _ = self.sock.accept()
            with conn:
                if self.response:
                    conn.sendall(self.response)
                try:
                    conn.recv(512)
                except OSError:
                    pass
        except OSError:
            return


class OneShotUdpDnsServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.sock.close()
        except OSError:
            pass
        self.thread.join(timeout=2)

    def _serve(self):
        try:
            data, addr = self.sock.recvfrom(512)
            if len(data) < 12:
                return
            header = data[:2] + b"\x81\x80" + data[4:6] + b"\x00\x00\x00\x00\x00\x00"
            self.sock.sendto(header + data[12:], addr)
        except OSError:
            return


class TestServiceProbeManager(unittest.TestCase):
    def test_tcp_probe_uses_plain_socket_connect(self):
        with OneShotTcpServer() as server:
            result = service_probe_executor.execute(
                asset_type="port",
                protocol="tcp",
                host="127.0.0.1",
                port=server.port,
                timeout=2,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["protocol"], "tcp")

    def test_smtp_probe_reads_banner_without_authenticating(self):
        with OneShotTcpServer(b"220 mail.example ESMTP ready\r\n") as server:
            result = service_probe_executor.execute(
                asset_type="smtp",
                protocol="smtp",
                host="127.0.0.1",
                port=server.port,
                timeout=2,
            )

        self.assertTrue(result["success"])
        self.assertIn("ESMTP", result["banner"])

    def test_unknown_operation_is_rejected(self):
        result = service_probe_executor.execute(
            asset_type="port",
            protocol="tcp",
            host="127.0.0.1",
            port=1,
            operation="delete",
            timeout=1,
        )

        self.assertFalse(result["success"])
        self.assertIn("unsupported", result["error"])

    def test_http_api_service_asset_falls_back_to_http_probe(self):
        with OneShotTcpServer(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok") as server:
            result = service_probe_executor.execute(
                asset_type="api",
                protocol="http_api",
                host="127.0.0.1",
                port=server.port,
                timeout=2,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["protocol"], "http")

    def test_dns_probe_sends_readonly_query(self):
        with OneShotUdpDnsServer() as server:
            result = service_probe_executor.execute(
                asset_type="dns",
                protocol="dns",
                host="127.0.0.1",
                port=server.port,
                extra_args={"dns_query": "example.com"},
                timeout=2,
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["protocol"], "dns")
        self.assertEqual(result["query"], "example.com")


if __name__ == "__main__":
    unittest.main()
