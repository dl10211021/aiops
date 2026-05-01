import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

import connections.db_manager as db_manager
from connections.db_manager import (
    DatabaseExecutor,
    discover_oracle_client_lib_dir,
    get_database_driver_capabilities,
    get_database_operation_profile,
    normalize_database_driver_key,
)


class FakeOracleDb:
    @staticmethod
    def makedsn(host, port, sid=None, service_name=None):
        return {
            "host": host,
            "port": port,
            "sid": sid,
            "service_name": service_name,
        }


def test_oracle_dsn_defaults_database_field_to_sid():
    dsn = DatabaseExecutor._oracle_dsn(FakeOracleDb, "oracle.local", 1561, "TEST", {"db_name": "TEST"})

    assert dsn == {
        "host": "oracle.local",
        "port": 1561,
        "sid": "TEST",
        "service_name": None,
    }


def test_oracle_dsn_uses_service_name_when_explicit():
    dsn = DatabaseExecutor._oracle_dsn(
        FakeOracleDb,
        "db.local",
        1521,
        "ignored",
        {"service_name": "ORCLPDB1"},
    )

    assert dsn == {
        "host": "db.local",
        "port": 1521,
        "sid": None,
        "service_name": "ORCLPDB1",
    }


def test_oracle_dsn_supports_explicit_service_connect_type():
    dsn = DatabaseExecutor._oracle_dsn(
        FakeOracleDb,
        "db.local",
        1521,
        "ORCLPDB1",
        {"connect_type": "service"},
    )

    assert dsn == {
        "host": "db.local",
        "port": 1521,
        "sid": None,
        "service_name": "ORCLPDB1",
    }


def test_oracle_dsn_supports_tns_alias_field():
    dsn = DatabaseExecutor._oracle_dsn(
        FakeOracleDb,
        "db.local",
        1521,
        "ignored",
        {"oracle_connect_type": "tns_alias", "tns_alias": "PROD_ALIAS"},
    )

    assert dsn == "PROD_ALIAS"


def test_oracle_dsn_supports_tns_alias_from_database_field():
    dsn = DatabaseExecutor._oracle_dsn(
        FakeOracleDb,
        "db.local",
        1521,
        "PROD_ALIAS",
        {"oracle_connect_type": "tns_alias"},
    )

    assert dsn == "PROD_ALIAS"


def test_oracle_error_explains_legacy_password_verifier():
    message = DatabaseExecutor._oracle_error_message(
        Exception("DPY-3015: password verifier type 0x939 is not supported")
    )

    assert "旧版 10G password verifier" in message
    assert "OPSCORE_ORACLE_THICK_MODE=true" in message


def test_oracle_non_query_statement_returns_affected_rows_without_fetch(monkeypatch):
    class FakeCursor:
        description = None
        rowcount = -1
        fetched = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql):
            self.sql = sql

        def fetchmany(self, limit):
            self.fetched = True
            raise AssertionError("non-query Oracle statements must not fetch rows")

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = FakeCursor()
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return self.cursor_obj

        def commit(self):
            self.committed = True

    fake_conn = FakeConnection()
    fake_oracledb = types.SimpleNamespace(
        connect=lambda **kwargs: fake_conn,
        makedsn=FakeOracleDb.makedsn,
    )
    monkeypatch.setitem(sys.modules, "oracledb", fake_oracledb)

    result_text = DatabaseExecutor().execute_query(
        "oracle",
        "db.local",
        1521,
        "system",
        "manager",
        "TEST",
        "ALTER SYSTEM SWITCH LOGFILE",
        {},
    )

    result = json.loads(result_text)
    assert result["success"] is True
    assert result["affected_rows"] == -1
    assert result["has_result_set"] is False
    assert result["statement_type"] == "alter"
    assert result["committed"] is True
    assert "ALTER" in result["message"]
    assert fake_conn.cursor_obj.fetched is False
    assert fake_conn.committed is True


def test_database_executor_commit_classifier_skips_readonly_and_transaction_control():
    assert DatabaseExecutor._should_commit_after_statement("ALTER SYSTEM SWITCH LOGFILE") is True
    assert DatabaseExecutor._should_commit_after_statement("UPDATE users SET name='x'") is True
    assert DatabaseExecutor._should_commit_after_statement("SELECT 1 FROM DUAL") is False
    assert DatabaseExecutor._should_commit_after_statement("SHOW DATABASES") is False
    assert DatabaseExecutor._should_commit_after_statement("ROLLBACK") is False


def test_oracle_thick_mode_can_be_requested_from_extra_args(monkeypatch):
    class FakeOracleDbWithInit:
        calls = []

        @classmethod
        def init_oracle_client(cls, **kwargs):
            cls.calls.append(kwargs)

    monkeypatch.setattr(db_manager, "_ORACLE_CLIENT_INIT_ATTEMPTED", False)

    DatabaseExecutor._init_oracle_client_if_requested(
        FakeOracleDbWithInit,
        {"use_thick_mode": True, "oracle_client_lib_dir": r"C:\oracle\instantclient"},
    )

    assert FakeOracleDbWithInit.calls == [{"lib_dir": r"C:\oracle\instantclient"}]
    assert db_manager._ORACLE_CLIENT_INIT_ATTEMPTED is True


def test_oracle_thick_mode_expands_env_var_from_extra_args(monkeypatch):
    class FakeOracleDbWithInit:
        calls = []

        @classmethod
        def init_oracle_client(cls, **kwargs):
            cls.calls.append(kwargs)

    monkeypatch.setattr(db_manager, "_ORACLE_CLIENT_INIT_ATTEMPTED", False)
    monkeypatch.setenv("OPSCORE_ORACLE_CLIENT_LIB_DIR", r"C:\oracle\instantclient")

    DatabaseExecutor._init_oracle_client_if_requested(
        FakeOracleDbWithInit,
        {
            "use_thick_mode": True,
            "oracle_client_lib_dir": "${OPSCORE_ORACLE_CLIENT_LIB_DIR}",
        },
    )

    assert FakeOracleDbWithInit.calls == [{"lib_dir": r"C:\oracle\instantclient"}]
    assert db_manager._ORACLE_CLIENT_INIT_ATTEMPTED is True


def test_oracle_client_dir_implies_thick_mode(monkeypatch):
    class FakeOracleDbWithInit:
        calls = []

        @classmethod
        def init_oracle_client(cls, **kwargs):
            cls.calls.append(kwargs)

    monkeypatch.setattr(db_manager, "_ORACLE_CLIENT_INIT_ATTEMPTED", False)
    monkeypatch.delenv("OPSCORE_ORACLE_THICK_MODE", raising=False)

    DatabaseExecutor._init_oracle_client_if_requested(
        FakeOracleDbWithInit,
        {"oracle_client_lib_dir": r"C:\oracle\instantclient"},
    )

    assert FakeOracleDbWithInit.calls == [{"lib_dir": r"C:\oracle\instantclient"}]
    assert db_manager._ORACLE_CLIENT_INIT_ATTEMPTED is True


def test_oracle_client_discovery_uses_configured_root(monkeypatch):
    root = Path(tempfile.mkdtemp(prefix="oracle_client_", dir=Path.cwd()))
    try:
        client_dir = root / "instantclient_23_0"
        client_dir.mkdir()
        (client_dir / "oci.dll").write_text("")

        monkeypatch.setenv("OPSCORE_ORACLE_CLIENT_ROOT", str(root))
        monkeypatch.delenv("OPSCORE_ORACLE_CLIENT_LIB_DIR", raising=False)

        config = discover_oracle_client_lib_dir()

        assert config["detected"] is True
        assert config["lib_dir"] == str(client_dir.resolve())
        assert config["source"] == "auto"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_database_driver_capabilities_group_core_database_connectors():
    capabilities = get_database_driver_capabilities()
    drivers = capabilities["drivers"]

    assert {"oracle", "mysql", "postgresql", "mssql", "redis", "mongodb"}.issubset(drivers)
    assert drivers["oracle"]["connector"] == "native_sql"
    assert drivers["oracle"]["external_client_name"] == "Oracle Instant Client"
    assert "OPSCORE_ORACLE_CLIENT_LIB_DIR" in drivers["oracle"]["install_hint"]
    assert drivers["mysql"]["external_client_required"] is False
    assert drivers["mysql"]["test_sql"] == "SELECT 1"
    assert drivers["oracle"]["operation_profile"]["identity_label"] == "SID / Service Name / TNS Alias"
    assert drivers["mysql"]["operation_profile"]["identity_label"] == "Database Name"


def test_database_operation_profiles_normalize_compatible_engines():
    assert normalize_database_driver_key("tidb") == "mysql"
    assert normalize_database_driver_key("oceanbase") == "mysql"
    assert normalize_database_driver_key("kingbase") == "postgresql"

    mysql_profile = get_database_operation_profile("tidb")
    oracle_profile = get_database_operation_profile("oracle")

    assert mysql_profile["id"] == "mysql"
    assert mysql_profile["test_statement"] == "SELECT 1"
    assert oracle_profile["test_statement"] == "SELECT 1 FROM DUAL"
