"""Read-only service probe executor for non-management service assets."""

from __future__ import annotations

import base64
import os
import platform
import socket
import ssl
import struct
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_PORTS = {
    "http": 80,
    "tls": 443,
    "websocket": 80,
    "tcp": 80,
    "udp": 53,
    "icmp": 0,
    "dns": 53,
    "ftp": 21,
    "smtp": 25,
    "pop3": 110,
    "imap": 143,
    "mqtt": 1883,
    "ntp": 123,
    "modbus": 502,
    "s7": 102,
    "registry": 80,
    "ipmi": 623,
    "ldap": 389,
    "jmx": 9999,
    "kafka": 9092,
}

ASSET_PROTOCOL_FALLBACKS = {
    "api": "http",
    "api_code": "http",
    "dns": "dns",
    "website": "http",
    "fullsite": "http",
    "registry": "registry",
    "ssl_cert": "tls",
    "port": "tcp",
    "udp_port": "udp",
    "ping": "icmp",
    "netease_mailbox": "imap",
    "qq_mailbox": "imap",
}


def _clean_host(host: str) -> str:
    raw = str(host or "").strip()
    if raw.startswith(("http://", "https://", "ws://", "wss://")):
        parsed = urllib.parse.urlparse(raw)
        return parsed.hostname or raw
    if ":" in raw and not raw.count(":") > 1:
        return raw.split(":", 1)[0]
    return raw


def _success(protocol: str, message: str, **details: Any) -> dict[str, Any]:
    return {"success": True, "protocol": protocol, "message": message, **details}


def _error(protocol: str, error: Exception | str, **details: Any) -> dict[str, Any]:
    return {"success": False, "protocol": protocol, "error": str(error), **details}


@dataclass
class ServiceProbeExecutor:
    default_timeout: float = 5.0

    def execute(
        self,
        *,
        asset_type: str,
        protocol: str,
        host: str,
        port: int | None = None,
        username: str = "",
        password: str | None = None,
        extra_args: dict | None = None,
        operation: str = "probe",
        path: str | None = None,
        timeout: int | float | None = None,
    ) -> dict[str, Any]:
        extra_args = extra_args or {}
        asset_type = str(asset_type or "").strip().lower()
        protocol = str(protocol or asset_type or "").strip().lower()
        if protocol in {"", "http_api"}:
            protocol = ASSET_PROTOCOL_FALLBACKS.get(asset_type, "http")
        operation = str(operation or "probe").strip().lower()
        host = _clean_host(host)
        effective_timeout = float(timeout or extra_args.get("timeout") or self.default_timeout)
        effective_port = int(port or extra_args.get("port") or DEFAULT_PORTS.get(protocol, 80))

        if not host:
            return _error(protocol, "host is required")
        if operation not in {"probe", "connect", "health"}:
            return _error(protocol, f"unsupported service probe operation: {operation}")

        started = time.perf_counter()
        try:
            if protocol in {"http", "registry"}:
                result = self._http_probe(host, effective_port, extra_args, path, effective_timeout)
            elif protocol == "tls":
                result = self._tls_probe(host, effective_port, effective_timeout)
            elif protocol == "websocket":
                result = self._websocket_probe(host, effective_port, extra_args, path, effective_timeout)
            elif protocol == "tcp":
                result = self._tcp_probe(protocol, host, effective_port, effective_timeout)
            elif protocol == "udp":
                result = self._udp_probe(host, effective_port, effective_timeout)
            elif protocol == "icmp":
                result = self._icmp_probe(host, effective_timeout)
            elif protocol == "dns":
                result = self._dns_probe(host, effective_port, extra_args, effective_timeout)
            elif protocol in {"ftp", "smtp", "pop3", "imap"}:
                result = self._banner_probe(protocol, host, effective_port, username, password, effective_timeout)
            elif protocol == "mqtt":
                result = self._mqtt_probe(host, effective_port, effective_timeout)
            elif protocol == "ntp":
                result = self._ntp_probe(host, effective_port, effective_timeout)
            elif protocol in {"modbus", "s7"}:
                result = self._tcp_probe(protocol, host, effective_port, effective_timeout)
            elif protocol == "ipmi":
                result = self._udp_probe(host, effective_port, effective_timeout)
            elif protocol in {"ldap", "jmx", "kafka"}:
                result = self._tcp_probe(protocol, host, effective_port, effective_timeout)
            else:
                result = self._tcp_probe(protocol or "tcp", host, effective_port, effective_timeout)
        except Exception as exc:
            return _error(protocol, exc, host=host, port=effective_port)

        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result.setdefault("host", host)
        result.setdefault("port", effective_port)
        return result

    def _tcp_probe(self, protocol: str, host: str, port: int, timeout: float) -> dict[str, Any]:
        with socket.create_connection((host, port), timeout=timeout):
            return _success(protocol, f"{host}:{port} TCP 连接成功")

    def _udp_probe(self, host: str, port: int, timeout: float) -> dict[str, Any]:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(b"", (host, port))
        return _success("udp", f"{host}:{port} UDP 数据包已发送")

    def _icmp_probe(self, host: str, timeout: float) -> dict[str, Any]:
        system = platform.system().lower()
        if system.startswith("win"):
            cmd = ["ping", "-n", "1", "-w", str(max(1000, int(timeout * 1000))), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), host]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            shell=False,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode == 0:
            return _success("icmp", f"{host} PING 成功", output=output[-1000:])
        return _error("icmp", output or f"ping exited with {completed.returncode}", exit_status=completed.returncode)

    def _dns_probe(
        self,
        host: str,
        port: int,
        extra_args: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        query_name = str(extra_args.get("query") or extra_args.get("dns_query") or "example.com").strip(".")
        labels = query_name.split(".") if query_name else ["example", "com"]
        qname = b"".join(bytes([len(label)]) + label.encode("ascii", "ignore") for label in labels) + b"\x00"
        transaction_id = os.urandom(2)
        packet = transaction_id + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + qname + b"\x00\x01\x00\x01"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (host, port))
            data, _ = sock.recvfrom(512)
        if len(data) >= 12 and data[:2] == transaction_id:
            rcode = data[3] & 0x0F
            answers = struct.unpack("!H", data[6:8])[0]
            if rcode in {0, 3}:
                return _success("dns", "DNS 查询响应成功", query=query_name, answers=answers, rcode=rcode)
            return _error("dns", f"DNS 返回错误码 {rcode}", query=query_name, rcode=rcode)
        return _error("dns", "DNS 响应事务 ID 不匹配或报文过短", query=query_name)

    def _http_probe(
        self,
        host: str,
        port: int,
        extra_args: dict[str, Any],
        path: str | None,
        timeout: float,
    ) -> dict[str, Any]:
        scheme = str(extra_args.get("scheme") or ("https" if port == 443 else "http"))
        request_path = path or str(extra_args.get("health_path") or extra_args.get("base_path") or "/")
        if not request_path.startswith("/"):
            request_path = f"/{request_path}"
        url = f"{scheme}://{host}:{port}{request_path}"
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "OpsCore-ServiceProbe/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read(512)
                return _success("http", f"HTTP {resp.status} 探测成功", status_code=resp.status, url=url, sample=body.decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if 200 <= exc.code < 500:
                return _success("http", f"HTTP {exc.code} 服务可达", status_code=exc.code, url=url)
            return _error("http", exc, status_code=exc.code, url=url)

    def _tls_probe(self, host: str, port: int, timeout: float) -> dict[str, Any]:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as sock:
                cert = sock.getpeercert() or {}
                return _success(
                    "tls",
                    "TLS 握手成功",
                    tls_version=sock.version(),
                    subject=cert.get("subject"),
                    not_after=cert.get("notAfter"),
                )

    def _websocket_probe(
        self,
        host: str,
        port: int,
        extra_args: dict[str, Any],
        path: str | None,
        timeout: float,
    ) -> dict[str, Any]:
        use_tls = str(extra_args.get("scheme") or "").lower() in {"https", "wss"} or port == 443
        request_path = path or str(extra_args.get("health_path") or "/")
        if not request_path.startswith("/"):
            request_path = f"/{request_path}"
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {request_path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii")
        with socket.create_connection((host, port), timeout=timeout) as raw:
            sock: socket.socket | ssl.SSLSocket
            if use_tls:
                sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
            else:
                sock = raw
            with sock:
                sock.sendall(request)
                response = sock.recv(512).decode("iso-8859-1", "replace")
        if " 101 " in response.split("\r\n", 1)[0]:
            return _success("websocket", "WebSocket 握手成功", status_line=response.split("\r\n", 1)[0])
        return _error("websocket", "WebSocket 握手未升级", status_line=response.split("\r\n", 1)[0])

    def _banner_probe(
        self,
        protocol: str,
        host: str,
        port: int,
        username: str,
        password: str | None,
        timeout: float,
    ) -> dict[str, Any]:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            banner = sock.recv(512).decode("utf-8", "replace").strip()
            if protocol == "smtp":
                sock.sendall(b"QUIT\r\n")
            elif protocol == "ftp":
                sock.sendall(b"QUIT\r\n")
            elif protocol == "pop3":
                sock.sendall(b"QUIT\r\n")
            elif protocol == "imap":
                sock.sendall(b"a001 LOGOUT\r\n")
        return _success(protocol, f"{protocol.upper()} 服务响应成功", banner=banner, auth_configured=bool(username or password))

    def _mqtt_probe(self, host: str, port: int, timeout: float) -> dict[str, Any]:
        client_id = b"opscore-probe"
        variable_header = b"\x00\x04MQTT\x04\x02\x00\x0f"
        payload = struct.pack("!H", len(client_id)) + client_id
        remaining = len(variable_header) + len(payload)
        packet = b"\x10" + bytes([remaining]) + variable_header + payload
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(packet)
            response = sock.recv(4)
        if len(response) >= 4 and response[0] == 0x20:
            return _success("mqtt", "MQTT CONNACK 响应成功", return_code=response[3])
        return _error("mqtt", "未收到有效 MQTT CONNACK", raw=response.hex())

    def _ntp_probe(self, host: str, port: int, timeout: float) -> dict[str, Any]:
        packet = b"\x1b" + 47 * b"\0"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (host, port))
            data, _ = sock.recvfrom(48)
        if len(data) >= 48:
            return _success("ntp", "NTP 响应成功", stratum=data[1])
        return _error("ntp", "NTP 响应长度异常", bytes=len(data))


service_probe_executor = ServiceProbeExecutor()
