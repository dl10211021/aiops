import sqlite3
import shutil
import threading
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from connections.ssh_manager import SSHConnectionManager
from core.asset_protocols import get_asset_catalog, normalize_protocol, resolve_asset_identity
from core.memory import MemoryDB


class FakeSSHClient:
    connect_calls = []

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)

    def close(self):
        pass


def make_memory_db(tmpdir: Path) -> MemoryDB:
    tmpdir.mkdir(parents=True, exist_ok=True)
    db = MemoryDB.__new__(MemoryDB)
    db._db_lock = threading.Lock()
    db.root_dir = str(tmpdir)
    db.db_path = str(tmpdir / "opscore.db")
    db.lancedb_path = str(tmpdir / "opscore_lancedb")
    db.key_path = str(tmpdir / "fernet.key")
    db._fernet = None
    db._encrypted_prefix = "fernet:"
    db.sensitive_keys = []
    with closing(sqlite3.connect(db.db_path)) as conn:
        conn.execute("""
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remark TEXT,
                host TEXT,
                port INTEGER,
                username TEXT,
                password TEXT,
                asset_type TEXT,
                agent_profile TEXT,
                extra_args_json TEXT,
                skills_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE asset_tags (
                asset_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (asset_id, tag_id)
            )
        """)
        conn.commit()
    return db


class TestAssetProtocolLayer(unittest.TestCase):
    def setUp(self):
        FakeSSHClient.connect_calls = []

    def tearDown(self):
        for p in (Path.cwd() / "tests").glob("tmp_protocol_layer_*"):
            shutil.rmtree(p, ignore_errors=True)

    def test_linux_asset_uses_ssh_protocol_without_becoming_virtual(self):
        manager = SSHConnectionManager()

        with patch("connections.ssh_manager.paramiko.SSHClient", FakeSSHClient):
            result = manager.connect(
                host="172.17.10.2",
                port=22,
                username="chroot",
                password="secret",
                asset_type="linux",
                protocol="ssh",
            )

        self.assertTrue(result["success"])
        session = manager.active_sessions[result["session_id"]]["info"]
        self.assertEqual(session["asset_type"], "linux")
        self.assertEqual(session["protocol"], "ssh")
        self.assertFalse(session["is_virtual"])
        self.assertEqual(FakeSSHClient.connect_calls[0]["hostname"], "172.17.10.2")

    def test_linux_asset_without_protocol_defaults_to_ssh(self):
        manager = SSHConnectionManager()

        with patch("connections.ssh_manager.paramiko.SSHClient", FakeSSHClient):
            result = manager.connect(
                host="10.0.0.10",
                port=22,
                username="root",
                password="secret",
                asset_type="linux",
            )

        self.assertTrue(result["success"])
        session = manager.active_sessions[result["session_id"]]["info"]
        self.assertEqual(session["protocol"], "ssh")
        self.assertFalse(session["is_virtual"])

    def test_api_asset_keeps_asset_type_and_registers_virtual_protocol_session(self):
        manager = SSHConnectionManager()

        result = manager.connect(
            host="zabbix.local",
            port=80,
            username="api",
            password="secret",
            asset_type="zabbix",
            protocol="http_api",
        )

        self.assertTrue(result["success"])
        session = manager.active_sessions[result["session_id"]]["info"]
        self.assertEqual(session["asset_type"], "zabbix")
        self.assertEqual(session["protocol"], "http_api")
        self.assertTrue(session["is_virtual"])

    def test_memory_persists_protocol_separately_from_asset_type(self):
        db = make_memory_db(Path.cwd() / "tests" / f"tmp_protocol_layer_{uuid.uuid4().hex}")

        db.save_asset(
            remark="linux host",
            host="172.17.10.2",
            port=22,
            username="chroot",
            password="secret",
            asset_type="linux",
            protocol="ssh",
            agent_profile="default",
            extra_args={},
            skills=["linux"],
            tags=["测试"],
        )

        asset = db.get_all_assets()[0]
        self.assertEqual(asset["asset_type"], "linux")
        self.assertEqual(asset["protocol"], "ssh")

    def test_asset_catalog_covers_core_ops_assets(self):
        catalog = get_asset_catalog()
        by_id = {item["id"]: item for item in catalog}

        expected = {
            "windows": "winrm",
            "linux": "ssh",
            "docker": "ssh",
            "containerd": "ssh",
            "harbor": "http_api",
            "k8s": "k8s",
            "oracle": "oracle",
            "mysql": "mysql",
            "prometheus": "http_api",
            "alertmanager": "http_api",
            "grafana": "http_api",
            "zabbix": "http_api",
            "vmware": "http_api",
            "kvm": "ssh",
            "openstack": "http_api",
            "proxmox": "http_api",
            "switch": "ssh",
            "firewall": "ssh",
            "ceph": "ssh",
            "nas": "snmp",
            "minio": "http_api",
            "s3": "http_api",
            "hdfs": "ssh",
            "glusterfs": "ssh",
            "elasticsearch": "http_api",
            "manageengine": "http_api",
            "redfish": "redfish",
            "snmp": "snmp",
            "bastion": "http_api",
        }
        for asset_type, protocol in expected.items():
            self.assertIn(asset_type, by_id)
            self.assertEqual(by_id[asset_type]["protocol"], protocol)
            self.assertEqual(normalize_protocol(asset_type), protocol)

    def test_legacy_virtual_database_asset_is_resolved_from_port_and_metadata(self):
        identity = resolve_asset_identity(
            asset_type="linux",
            protocol="virtual",
            host="172.17.8.151",
            port=3306,
            remark="mysql",
            extra_args={"device_type": "database", "database": ""},
        )

        self.assertEqual(identity["asset_type"], "mysql")
        self.assertEqual(identity["protocol"], "mysql")
        self.assertEqual(identity["extra_args"]["db_type"], "mysql")

    def test_legacy_virtual_monitor_asset_is_resolved_from_host_or_remark(self):
        identity = resolve_asset_identity(
            asset_type="linux",
            protocol="virtual",
            host="192.168.130.45:9090",
            port=443,
            remark="prometheus",
            extra_args={"device_type": "api"},
        )

        self.assertEqual(identity["asset_type"], "prometheus")
        self.assertEqual(identity["protocol"], "http_api")

    def test_legacy_virtual_network_asset_is_resolved_to_switch(self):
        identity = resolve_asset_identity(
            asset_type="linux",
            protocol="virtual",
            host="192.168.46.30",
            port=22,
            remark="交换机test",
            extra_args={"device_type": "network", "enable_password": "secret"},
        )

        self.assertEqual(identity["asset_type"], "switch")
        self.assertEqual(identity["protocol"], "ssh")
        self.assertIn("enable_pass", identity["extra_args"])

    def test_explicit_virtual_asset_without_legacy_hint_stays_virtual(self):
        identity = resolve_asset_identity(
            asset_type="linux",
            protocol="virtual",
            host="localhost",
            port=22,
            remark="技能研发 CLI",
            extra_args={},
        )

        self.assertEqual(identity["asset_type"], "linux")
        self.assertEqual(identity["protocol"], "virtual")


if __name__ == "__main__":
    unittest.main()
