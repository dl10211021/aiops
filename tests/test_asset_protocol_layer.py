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
from core.tool_registry import tool_registry


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
            "memcached": "memcached",
            "prometheus": "http_api",
            "alertmanager": "http_api",
            "grafana": "http_api",
            "zabbix": "http_api",
            "vmware": "vmware",
            "esxi": "ssh",
            "kvm": "ssh",
            "openstack": "openstack",
            "proxmox": "proxmox",
            "zstack": "zstack",
            "hyperv": "winrm",
            "switch": "ssh",
            "firewall": "ssh",
            "ceph": "ssh",
            "nas": "snmp",
            "minio": "minio",
            "s3": "s3",
            "hdfs": "ssh",
            "glusterfs": "ssh",
            "clickhouse": "clickhouse",
            "elasticsearch": "elasticsearch",
            "manageengine": "http_api",
            "redfish": "redfish",
            "snmp": "snmp",
            "bastion": "http_api",
            "api": "http",
            "dns": "dns",
        }
        for asset_type, protocol in expected.items():
            self.assertIn(asset_type, by_id)
            self.assertEqual(by_id[asset_type]["protocol"], protocol)
            self.assertEqual(normalize_protocol(asset_type), protocol)

    def test_asset_catalog_includes_hertzbeat_extension_assets(self):
        catalog = get_asset_catalog()
        by_id = {item["id"]: item for item in catalog}

        self.assertGreaterEqual(len([item for item in catalog if item.get("source") == "hertzbeat"]), 100)
        self.assertEqual(by_id["huawei_switch"]["category"], "network")
        self.assertEqual(by_id["huawei_switch"]["protocol"], "snmp")
        huawei_params = {param["field"]: param for param in by_id["huawei_switch"].get("params", [])}
        self.assertNotIn("snmpVersion", huawei_params)
        self.assertNotIn("community", huawei_params)
        self.assertEqual(by_id["airflow"]["category"], "bigdata")
        self.assertEqual(by_id["airflow"]["protocol"], "http_api")
        airflow_params = {param["field"]: param for param in by_id["airflow"].get("params", [])}
        self.assertNotIn("ssl", airflow_params)
        self.assertNotIn("timeout", airflow_params)
        for database_asset in (
            "doris_be",
            "hbase_master",
            "hbase_regionserver",
            "hugegraph",
            "influxdb",
            "starrocks_be",
        ):
            self.assertEqual(by_id[database_asset]["category"], "db")
            self.assertEqual(by_id[database_asset]["capability"]["connector"], "database_http")
        for database_asset in ("doris_fe", "starrocks_fe", "greptime"):
            self.assertEqual(by_id[database_asset]["category"], "db")
            self.assertEqual(by_id[database_asset]["protocol"], "mysql")
            self.assertEqual(by_id[database_asset]["capability"]["connector"], "native_sql")
            self.assertEqual(by_id[database_asset]["capability"]["driver_key"], "mysql")
        for database_asset, protocol, port in (
            ("hive", "hive", 10000),
            ("iotdb", "iotdb", 6667),
        ):
            self.assertEqual(by_id[database_asset]["category"], "db")
            self.assertEqual(by_id[database_asset]["protocol"], protocol)
            self.assertEqual(by_id[database_asset]["default_port"], port)
            self.assertEqual(by_id[database_asset]["capability"]["connector"], "database_jdbc")
            self.assertEqual(by_id[database_asset]["capability"]["driver_key"], protocol)
        self.assertEqual(by_id["deepseek"]["category"], "ai")
        self.assertEqual(by_id["hertzbeat"]["category"], "monitor")
        self.assertEqual(by_id["hertzbeat_token"]["category"], "monitor")
        self.assertEqual(by_id["influxdb_promql"]["category"], "monitor")
        self.assertEqual(by_id["synology_nas"]["category"], "storage")
        self.assertEqual(by_id["synology_nas"]["protocol"], "snmp")
        self.assertEqual(by_id["synology_nas"]["capability"]["family"], "storage")
        self.assertEqual(by_id["synology_nas"]["capability"]["connector"], "snmp")
        self.assertEqual(by_id["huawei_switch"]["capability"]["connector"], "snmp")
        self.assertEqual(by_id["huawei_switch"]["capability"]["connector_group"]["label"], "SNMP")
        self.assertEqual(by_id["huawei_switch"]["category_meta"]["label"], "网络设备")
        self.assertEqual(by_id["huawei_switch"]["capability"]["tools"], ["snmp_get"])
        self.assertEqual(by_id["huawei_switch"]["params"][0]["field"], "snmp_version")
        self.assertEqual(by_id["huawei_switch"]["params"][0]["defaultValue"], "v2c")
        huawei_param_map = {param["field"]: param for param in by_id["huawei_switch"].get("params", [])}
        self.assertEqual(huawei_param_map["community_string"]["type"], "password")
        self.assertEqual(huawei_param_map["v3_auth_pass"]["type"], "password")
        self.assertEqual(huawei_param_map["v3_priv_pass"]["type"], "password")
        self.assertIn("oid_profile", {param["field"] for param in by_id["huawei_switch"].get("params", [])})

        # Existing OpsCore definitions keep their native protocol mappings.
        self.assertEqual(by_id["oracle"]["protocol"], "oracle")
        self.assertNotEqual(by_id["oracle"].get("source"), "hertzbeat")
        self.assertTrue(by_id["oracle"].get("hertzbeat_supported"))
        self.assertNotIn("timeout", {param["field"] for param in by_id["oracle"].get("params", [])})
        self.assertEqual(by_id["oracle"]["capability"]["family"], "database")
        self.assertEqual(by_id["oracle"]["capability"]["driver_key"], "oracle")
        self.assertEqual(by_id["oracle"]["capability"]["maturity"], "native")
        self.assertIn("OPSCORE_ORACLE_CLIENT_LIB_DIR", by_id["oracle"]["capability"]["setup"]["env_vars"])
        oracle_params = {param["field"]: param for param in by_id["oracle"].get("params", [])}
        self.assertEqual(oracle_params["oracle_connect_type"]["defaultValue"], "sid")
        self.assertIn("tns_alias", oracle_params)

    def test_every_catalog_asset_has_standard_operational_capability(self):
        missing = []
        for item in get_asset_catalog():
            capability = item.get("capability") or {}
            if not all(
                [
                    capability.get("family"),
                    capability.get("connector"),
                    capability.get("operation_model"),
                    isinstance(capability.get("tools"), list),
                    capability.get("risk_model", {}).get("safety_category"),
                    capability.get("standard_version"),
                ]
            ):
                missing.append(item["id"])

        self.assertEqual(missing, [])

    def test_special_asset_capability_overrides_are_applied(self):
        by_id = {item["id"]: item for item in get_asset_catalog()}

        def params(asset_id):
            return {param["field"]: param for param in by_id[asset_id].get("params", [])}

        self.assertEqual(by_id["mysql"]["capability"]["connector"], "native_sql")
        self.assertEqual(by_id["mysql"]["capability"]["driver_key"], "mysql")
        self.assertEqual(params("mysql")["ssl_mode"]["defaultValue"], "preferred")
        self.assertEqual(params("mysql")["charset"]["defaultValue"], "utf8mb4")
        self.assertEqual(by_id["mariadb"]["protocol"], "mysql")
        self.assertEqual(by_id["mariadb"]["capability"]["connector"], "native_sql")
        self.assertEqual(by_id["sqlserver"]["protocol"], "mssql")
        self.assertEqual(params("sqlserver")["encrypt"]["defaultValue"], True)
        self.assertEqual(by_id["opengauss"]["protocol"], "postgresql")
        self.assertEqual(by_id["greenplum"]["protocol"], "postgresql")
        self.assertEqual(params("postgresql")["ssl_mode"]["defaultValue"], "prefer")
        self.assertIn("search_path", params("opengauss"))
        self.assertEqual(by_id["clickhouse"]["protocol"], "clickhouse")
        self.assertEqual(by_id["clickhouse"]["capability"]["connector"], "database_http")
        self.assertEqual(by_id["clickhouse"]["capability"]["tools"], ["database_api_request"])
        self.assertEqual(by_id["elasticsearch"]["protocol"], "elasticsearch")
        self.assertEqual(by_id["elasticsearch"]["capability"]["connector"], "database_http")
        self.assertEqual(by_id["elasticsearch"]["capability"]["tools"], ["database_api_request"])
        self.assertEqual(by_id["nebula_graph"]["protocol"], "nebula_graph")
        self.assertEqual(by_id["nebula_graph_cluster"]["protocol"], "nebula_graph")
        self.assertEqual(by_id["db2"]["protocol"], "db2")
        self.assertEqual(by_id["dameng"]["protocol"], "dameng")
        self.assertEqual(by_id["dm"]["protocol"], "dameng")
        self.assertEqual(by_id["xugu"]["protocol"], "xugu")
        self.assertEqual(by_id["db2"]["capability"]["connector"], "database_jdbc")
        self.assertEqual(by_id["db2"]["capability"]["maturity"], "driver_required")
        self.assertEqual(by_id["memcached"]["protocol"], "memcached")
        self.assertEqual(by_id["memcached"]["capability"]["connector"], "native_kv")
        self.assertEqual(by_id["memcached"]["capability"]["maturity"], "native")
        self.assertEqual(params("memcached")["binary_protocol"]["defaultValue"], False)
        self.assertEqual(params("redis")["db_index"]["defaultValue"], 0)
        self.assertEqual(params("redis_cluster")["startup_nodes"]["field"], "startup_nodes")
        self.assertEqual(params("redis_sentinel")["sentinel_master"]["defaultValue"], "mymaster")
        self.assertEqual(params("mongodb")["auth_source"]["defaultValue"], "admin")
        self.assertEqual(params("mongodb_atlas")["tls"]["defaultValue"], True)
        self.assertEqual(by_id["windows"]["capability"]["connector"], "winrm_powershell")
        self.assertEqual(params("linux")["shell"]["defaultValue"], "bash")
        self.assertEqual(params("linux")["sudo_method"]["defaultValue"], "none")
        self.assertEqual(params("docker")["runtime_socket"]["field"], "runtime_socket")
        self.assertEqual(params("process")["service_name"]["field"], "service_name")
        self.assertEqual(params("nvidia")["driver_check_command"]["defaultValue"], "nvidia-smi")
        self.assertEqual(by_id["prometheus"]["capability"]["connector"], "monitoring_api")
        self.assertEqual(params("prometheus")["query_path"]["defaultValue"], "/api/v1/query")
        self.assertEqual(params("prometheus")["query_range_path"]["defaultValue"], "/api/v1/query_range")
        self.assertEqual(params("alertmanager")["alerts_path"]["defaultValue"], "/api/v2/alerts")
        self.assertEqual(params("grafana")["org_id"]["defaultValue"], 1)
        self.assertEqual(params("grafana")["dashboard_search_path"]["defaultValue"], "/api/search")
        self.assertEqual(params("loki")["query_range_path"]["defaultValue"], "/loki/api/v1/query_range")
        self.assertEqual(params("victoriametrics")["query_path"]["defaultValue"], "/api/v1/query")
        self.assertEqual(params("zabbix")["api_path"]["defaultValue"], "/api_jsonrpc.php")
        self.assertEqual(by_id["kubernetes"]["protocol"], "k8s")
        self.assertEqual(by_id["kubernetes"]["capability"]["connector"], "kubernetes_api")
        self.assertEqual(params("kubernetes")["namespace"]["defaultValue"], "default")
        self.assertEqual(by_id["vmware"]["protocol"], "vmware")
        self.assertEqual(by_id["vmware"]["capability"]["connector"], "virtualization_api")
        self.assertEqual(by_id["openstack"]["protocol"], "openstack")
        self.assertEqual(by_id["proxmox"]["protocol"], "proxmox")
        self.assertEqual(by_id["zstack"]["protocol"], "zstack")
        self.assertEqual(by_id["zstack"]["default_port"], 8080)
        self.assertEqual(by_id["hyperv"]["protocol"], "winrm")
        self.assertEqual(by_id["hyperv"]["capability"]["connector"], "winrm_powershell")
        self.assertEqual(by_id["hyperv"]["capability"]["family"], "virtualization")
        self.assertEqual(by_id["hyperv"]["capability"]["tools"], ["winrm_execute_command"])
        self.assertIn("project_name", {param["field"] for param in by_id["openstack"].get("params", [])})
        self.assertNotIn("project_name", {param["field"] for param in by_id["vmware"].get("params", [])})
        self.assertNotIn("compute_base_path", {param["field"] for param in by_id["proxmox"].get("params", [])})
        self.assertEqual(params("proxmox")["api_base_path"]["defaultValue"], "/api2/json")
        self.assertEqual(params("proxmox")["realm"]["defaultValue"], "pam")
        self.assertIn("zstack_session_uuid", {param["field"] for param in by_id["zstack"].get("params", [])})
        self.assertNotIn("compute_base_path", {param["field"] for param in by_id["zstack"].get("params", [])})
        self.assertEqual(by_id["f5"]["capability"]["connector"], "network_api")
        self.assertEqual(by_id["f5"]["capability"]["tools"], ["network_api_request"])
        self.assertEqual(params("f5")["scheme"]["defaultValue"], "https")
        self.assertEqual(params("f5")["api_base_path"]["defaultValue"], "/mgmt/tm")
        self.assertEqual(params("a10")["api_base_path"]["defaultValue"], "/axapi/v3")
        self.assertEqual(params("waf")["policies_path"]["defaultValue"], "/api/policies")
        self.assertEqual(by_id["airflow"]["capability"]["connector"], "bigdata_api")
        self.assertEqual(by_id["airflow"]["capability"]["tools"], ["bigdata_api_request"])
        self.assertEqual(params("airflow")["api_base_path"]["defaultValue"], "/api/v1")
        self.assertEqual(params("dolphinscheduler")["api_base_path"]["defaultValue"], "/dolphinscheduler")
        self.assertEqual(params("flink")["jobs_path"]["defaultValue"], "/jobs")
        self.assertEqual(params("flink_on_yarn")["yarn_application_id"]["field"], "yarn_application_id")
        self.assertEqual(params("yarn")["applications_path"]["defaultValue"], "/ws/v1/cluster/apps")
        self.assertEqual(params("storm")["cluster_summary_path"]["defaultValue"], "/api/v1/cluster/summary")
        self.assertEqual(params("prestodb")["statement_path"]["defaultValue"], "/v1/statement")
        self.assertEqual(by_id["rabbitmq"]["capability"]["connector"], "middleware_api")
        self.assertEqual(by_id["rabbitmq"]["capability"]["tools"], ["middleware_api_request"])
        self.assertIn("api_token", {param["field"] for param in by_id["rabbitmq"].get("params", [])})
        self.assertIn("amqp_port", {param["field"] for param in by_id["rabbitmq"].get("params", [])})
        self.assertEqual(params("nacos")["instance_path"]["defaultValue"], "/nacos/v1/ns/instance")
        self.assertEqual(params("consul")["catalog_services_path"]["defaultValue"], "/v1/catalog/services")
        self.assertEqual(params("springboot3")["health_path"]["defaultValue"], "/actuator/health")
        self.assertEqual(params("spring_gateway")["gateway_routes_path"]["defaultValue"], "/actuator/gateway/routes")
        self.assertEqual(params("dynamic_tp")["thread_pool_path"]["defaultValue"], "/actuator/dynamic-tp")
        self.assertEqual(by_id["harbor"]["capability"]["connector"], "container_api")
        self.assertEqual(by_id["harbor"]["capability"]["tools"], ["container_api_request"])
        self.assertEqual(params("harbor")["scheme"]["defaultValue"], "https")
        self.assertEqual(params("harbor")["api_path"]["defaultValue"], "/api/v2.0")
        self.assertEqual(by_id["bastion"]["capability"]["connector"], "security_api")
        self.assertEqual(by_id["bastion"]["capability"]["tools"], ["security_api_request"])
        self.assertEqual(params("bastion")["scheme"]["defaultValue"], "https")
        self.assertIn("tenant", params("bastion"))
        self.assertIn("events_path", params("audit"))
        self.assertEqual(by_id["dahua"]["capability"]["connector"], "oob_api")
        self.assertEqual(by_id["dahua"]["capability"]["tools"], ["oob_api_request"])
        self.assertEqual(params("redfish")["scheme"]["defaultValue"], "https")
        self.assertEqual(params("redfish")["root_path"]["defaultValue"], "/redfish/v1")
        self.assertEqual(params("hikvision_isapi")["isapi_base_path"]["defaultValue"], "/ISAPI")
        self.assertEqual(params("dahua")["cgi_base_path"]["defaultValue"], "/cgi-bin")
        self.assertEqual(params("uniview")["lapi_base_path"]["defaultValue"], "/LAPI")
        self.assertEqual(by_id["consul_sd"]["capability"]["connector"], "discovery_api")
        self.assertEqual(by_id["consul_sd"]["capability"]["tools"], ["discovery_api_request"])
        self.assertEqual(by_id["ollama"]["capability"]["connector"], "ai_platform_api")
        self.assertEqual(by_id["ollama"]["capability"]["tools"], ["ai_platform_api_request"])
        self.assertEqual(params("openai")["base_url"]["defaultValue"], "https://api.openai.com/v1")
        self.assertEqual(params("deepseek")["base_url"]["defaultValue"], "https://api.deepseek.com")
        self.assertEqual(params("ollama")["base_url"]["defaultValue"], "http://localhost:11434")
        self.assertIn("model", params("ollama"))
        self.assertEqual(params("lmstudio")["base_url"]["defaultValue"], "http://localhost:1234/v1")
        self.assertEqual(by_id["jenkins"]["capability"]["connector"], "cicd_api")
        self.assertEqual(by_id["jenkins"]["capability"]["tools"], ["cicd_api_request"])
        self.assertEqual(params("jenkins")["crumb_path"]["defaultValue"], "/crumbIssuer/api/json")
        self.assertEqual(by_id["s3"]["protocol"], "s3")
        self.assertEqual(by_id["minio"]["protocol"], "minio")
        self.assertEqual(by_id["nas"]["protocol"], "snmp")
        self.assertEqual(by_id["nas"]["capability"]["family"], "storage")
        self.assertEqual(by_id["nas"]["capability"]["connector"], "snmp")
        self.assertEqual(by_id["nas"]["capability"]["tools"], ["snmp_get"])
        self.assertEqual(by_id["backup"]["capability"]["connector"], "storage_api")
        self.assertEqual(by_id["backup"]["capability"]["tools"], ["storage_api_request"])
        self.assertIn("api_token", by_id["backup"]["capability"]["credential_fields"])
        backup_fields = {param["field"] for param in by_id["backup"].get("params", [])}
        self.assertIn("api_token", backup_fields)
        self.assertIn("health_path", backup_fields)
        self.assertIn("jobs_path", backup_fields)
        for storage_asset in ("ceph", "nfs", "hdfs", "glusterfs"):
            self.assertEqual(by_id[storage_asset]["protocol"], "ssh")
            self.assertEqual(by_id[storage_asset]["capability"]["connector"], "storage_shell")
            self.assertEqual(by_id[storage_asset]["capability"]["tools"], ["storage_execute_command"])
        self.assertIn("mon_v2_port", {param["field"] for param in by_id["ceph"].get("params", [])})
        self.assertIn("nfs_port", {param["field"] for param in by_id["nfs"].get("params", [])})
        self.assertIn("namenode_http_port", {param["field"] for param in by_id["hdfs"].get("params", [])})
        self.assertIn("management_port", {param["field"] for param in by_id["glusterfs"].get("params", [])})
        self.assertIn("libvirt_port", {param["field"] for param in by_id["kvm"].get("params", [])})
        self.assertEqual(by_id["api"]["protocol"], "http")
        self.assertEqual(by_id["api"]["capability"]["connector"], "service_probe")
        self.assertEqual(params("api")["method"]["defaultValue"], "GET")
        self.assertEqual(params("api_code")["expected_status"]["defaultValue"], "200-399")
        self.assertEqual(params("website")["path"]["defaultValue"], "/")
        self.assertEqual(params("fullsite")["sitemap_path"]["defaultValue"], "/sitemap.xml")
        self.assertEqual(by_id["dns"]["category"], "service")
        self.assertEqual(by_id["dns"]["protocol"], "dns")
        self.assertEqual(by_id["dns"]["default_port"], 53)
        self.assertEqual(by_id["dns"]["capability"]["connector"], "service_probe")
        self.assertEqual(params("dns")["record_type"]["defaultValue"], "A")
        self.assertEqual(by_id["ping"]["protocol"], "icmp")
        self.assertEqual(by_id["ping"]["default_port"], 0)
        self.assertEqual(params("ping")["packet_count"]["defaultValue"], 4)
        self.assertEqual(by_id["udp_port"]["default_port"], 53)
        self.assertEqual(by_id["ntp"]["default_port"], 123)
        self.assertEqual(params("ntp")["max_offset_ms"]["defaultValue"], 1000)
        self.assertEqual(by_id["netease_mailbox"]["default_port"], 993)
        self.assertEqual(params("netease_mailbox")["tls_mode"]["defaultValue"], "auto")
        self.assertEqual(by_id["qq_mailbox"]["default_port"], 993)
        self.assertEqual(params("ssl_cert")["expiry_warning_days"]["defaultValue"], 30)
        self.assertEqual(params("websocket")["path"]["defaultValue"], "/")
        self.assertEqual(params("mqtt")["topic"]["defaultValue"], "$SYS/#")
        self.assertEqual(params("modbus")["function_code"]["defaultValue"], "3")
        self.assertEqual(params("s7")["slot"]["defaultValue"], 1)
        self.assertIn("service_name", params("registry"))
        self.assertEqual(by_id["openai"]["default_port"], 443)
        self.assertEqual(by_id["deepseek"]["default_port"], 443)
        self.assertEqual(by_id["hadoop"]["default_port"], 9870)
        self.assertEqual(by_id["hdfs_namenode"]["default_port"], 9870)
        self.assertEqual(by_id["hdfs_datanode"]["default_port"], 9864)
        self.assertEqual(params("hadoop")["webhdfs_path"]["defaultValue"], "/webhdfs/v1")
        self.assertEqual(params("hdfs_datanode")["datanode_transfer_port"]["defaultValue"], 9866)
        self.assertEqual(by_id["spark"]["default_port"], 8080)
        self.assertEqual(params("spark")["submission_rest_port"]["defaultValue"], 6066)
        self.assertEqual(by_id["prestodb"]["default_port"], 8080)
        self.assertEqual(by_id["pulsar"]["default_port"], 8080)
        self.assertEqual(by_id["activemq"]["default_port"], 8161)
        self.assertEqual(by_id["jetty"]["default_port"], 8080)
        self.assertEqual(by_id["doris_fe"]["default_port"], 9030)
        self.assertEqual(by_id["starrocks_fe"]["default_port"], 9030)
        self.assertEqual(by_id["greptime"]["default_port"], 4002)
        self.assertEqual(by_id["hive"]["default_port"], 10000)
        self.assertEqual(by_id["iotdb"]["default_port"], 6667)
        self.assertEqual(by_id["iceberg"]["default_port"], 8181)
        self.assertIn("warehouse", {param["field"] for param in by_id["iceberg"].get("params", [])})
        self.assertEqual(by_id["consul_sd"]["default_port"], 8500)
        self.assertEqual(params("consul_sd")["agent_services_path"]["defaultValue"], "/v1/agent/services")
        self.assertEqual(by_id["dns_sd"]["default_port"], 53)
        self.assertEqual(params("dns_sd")["record_type"]["defaultValue"], "A")
        self.assertEqual(by_id["eureka_sd"]["default_port"], 8761)
        self.assertEqual(params("eureka_sd")["apps_path"]["defaultValue"], "/eureka/apps")
        self.assertEqual(by_id["nacos_sd"]["default_port"], 8848)
        self.assertEqual(params("nacos_sd")["namespace_id"]["defaultValue"], "public")
        self.assertEqual(by_id["zookeeper_sd"]["default_port"], 2181)
        self.assertEqual(by_id["dns_sd"]["protocol"], "dns")
        self.assertEqual(by_id["dns_sd"]["capability"]["connector"], "service_probe")
        self.assertEqual(by_id["zookeeper_sd"]["protocol"], "tcp")
        self.assertEqual(by_id["zookeeper_sd"]["capability"]["connector"], "service_probe")
        self.assertIn("namespace", params("zookeeper_sd"))
        self.assertEqual(by_id["kafka_client"]["protocol"], "kafka")
        self.assertEqual(by_id["kafka_client"]["capability"]["connector"], "service_probe")
        self.assertIn("security_protocol", {param["field"] for param in by_id["kafka_client"].get("params", [])})
        self.assertEqual(by_id["jvm"]["protocol"], "jmx")
        self.assertEqual(by_id["jvm"]["capability"]["connector"], "service_probe")
        self.assertIn("jmx_service_url", {param["field"] for param in by_id["jvm"].get("params", [])})
        self.assertEqual(by_id["shenyu"]["default_port"], 9095)
        self.assertIn("gateway_port", {param["field"] for param in by_id["shenyu"].get("params", [])})
        self.assertEqual(by_id["spring_gateway"]["default_port"], 8080)
        self.assertIn("broker_port", {param["field"] for param in by_id["activemq"].get("params", [])})
        self.assertIn("broker_port", {param["field"] for param in by_id["pulsar"].get("params", [])})
        self.assertIn("mqtt_port", {param["field"] for param in by_id["emqx"].get("params", [])})
        self.assertIn("portal_port", {param["field"] for param in by_id["apollo"].get("params", [])})
        self.assertEqual(params("seatunnel")["running_jobs_path"]["defaultValue"], "/running-jobs")
        self.assertIn("http_port", {param["field"] for param in by_id["tomcat"].get("params", [])})
        self.assertIn("http_port", {param["field"] for param in by_id["nginx"].get("params", [])})
        self.assertIn("namesrv_port", {param["field"] for param in by_id["rocketmq"].get("params", [])})
        self.assertIn("client_port", {param["field"] for param in by_id["zookeeper"].get("params", [])})
        self.assertIn("broker_port", {param["field"] for param in by_id["kafka"].get("params", [])})
        self.assertEqual(by_id["ipmi"]["protocol"], "ipmi")
        self.assertEqual(by_id["ipmi"]["default_port"], 623)
        self.assertEqual(by_id["ipmi"]["capability"]["connector"], "service_probe")
        self.assertIn("username", by_id["ipmi"]["capability"]["credential_fields"])
        self.assertEqual(by_id["ldap"]["protocol"], "ldap")
        self.assertEqual(by_id["ldap"]["default_port"], 389)
        self.assertEqual(by_id["ldap"]["capability"]["connector"], "service_probe")
        self.assertIn("base_dn", by_id["ldap"]["capability"]["credential_fields"])
        self.assertIn("base_dn", {param["field"] for param in by_id["ldap"].get("params", [])})
        self.assertEqual(by_id["docker"]["capability"]["connector"], "container_shell")
        self.assertEqual(by_id["nginx"]["capability"]["connector"], "middleware_shell")
        self.assertEqual(by_id["windows_script"]["protocol"], "winrm")
        self.assertEqual(by_id["windows_script"]["capability"]["connector"], "winrm_powershell")
        self.assertEqual(by_id["hertzbeat"]["capability"]["connector"], "monitoring_api")
        self.assertEqual(by_id["influxdb_promql"]["capability"]["connector"], "monitoring_api")
        self.assertEqual(params("influxdb_promql")["query_path"]["defaultValue"], "/api/v1/query")
        self.assertEqual(params("kafka_promql")["query_range_path"]["defaultValue"], "/api/v1/query_range")
        self.assertEqual(params("tdengine_promql")["rest_sql_path"]["defaultValue"], "/rest/sql")
        self.assertEqual(params("jetty")["jmx_port"]["defaultValue"], 1099)
        self.assertEqual(params("http_sd")["targets_path"]["defaultValue"], "/targets")
        self.assertNotIn("a_example", by_id)
        self.assertEqual(by_id["switch"]["capability"]["connector"], "ssh_network_cli")
        self.assertEqual(by_id["s3"]["capability"]["connector"], "object_storage_api")
        self.assertEqual(by_id["s3"]["capability"]["maturity"], "native")
        self.assertEqual(by_id["nebula_graph"]["default_port"], 9669)
        self.assertIn("username", by_id["clickhouse"]["capability"]["credential_fields"])
        self.assertIn("database", by_id["clickhouse"]["capability"]["credential_fields"])
        self.assertIn("jdbc_jar", {param["field"] for param in by_id["db2"].get("params", [])})
        self.assertIn("username", by_id["vmware"]["capability"]["credential_fields"])
        self.assertIn("enable_pass", {param["field"] for param in by_id["switch"].get("params", [])})
        self.assertIn("transport", {param["field"] for param in by_id["windows"].get("params", [])})
        self.assertIn("access_key", {param["field"] for param in by_id["s3"].get("params", [])})
        self.assertIn("endpoint_url", {param["field"] for param in by_id["s3"].get("params", [])})
        self.assertIn("use_ssl", {param["field"] for param in by_id["minio"].get("params", [])})

    def test_hertzbeat_raw_params_do_not_pollute_asset_forms(self):
        noisy_fields = {"snmpVersion", "ssl", "timeout", "__sd_host__", "__sd_port__"}
        polluted = []
        for item in get_asset_catalog():
            fields = {param.get("field") for param in item.get("params", [])}
            if fields & noisy_fields:
                polluted.append((item["id"], sorted(fields & noisy_fields)))

        self.assertEqual(polluted, [])

    def test_asset_parameter_templates_are_frontend_safe(self):
        supported_types = {
            "text",
            "number",
            "boolean",
            "select",
            "password",
            "textarea",
            "json",
            "array",
            "map",
            "key-value",
            "radio",
        }
        issues = []
        for item in get_asset_catalog():
            params = item.get("params") or []
            fields = [param.get("field") for param in params]
            duplicate_fields = sorted({field for field in fields if fields.count(field) > 1})
            if duplicate_fields:
                issues.append((item["id"], "duplicate_fields", duplicate_fields))
            if not params:
                issues.append((item["id"], "empty_params"))
            for param in params:
                if not param.get("field") or not param.get("label"):
                    issues.append((item["id"], "missing_field_or_label", param))
                if param.get("type") not in supported_types:
                    issues.append((item["id"], "unsupported_type", param.get("field"), param.get("type")))
                field_label = f"{param.get('field', '')} {param.get('label', '')}".lower()
                if (
                    any(token in field_label for token in ("pass", "password", "secret"))
                    and param.get("type") != "password"
                ):
                    issues.append((item["id"], "sensitive_not_password", param.get("field"), param.get("type")))

        self.assertEqual(issues, [])

    def test_each_catalog_asset_has_protocol_scoped_tool(self):
        missing = []
        for item in get_asset_catalog():
            context = {
                "target_scope": "asset",
                "asset_type": item["id"],
                "protocol": item["protocol"],
                "extra_args": {"category": item["category"], "sub_type": item["id"]},
                "host": "asset.local",
                "port": item["default_port"],
            }
            active = [
                tool.name
                for tool in tool_registry.available(context)
                if tool.scope == "asset"
            ]
            if not active:
                missing.append((item["id"], item["protocol"]))

        self.assertEqual(missing, [])

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
