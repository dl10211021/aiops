import connections.db_manager as db_manager
from connections.db_manager import DatabaseExecutor


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


def test_oracle_error_explains_legacy_password_verifier():
    message = DatabaseExecutor._oracle_error_message(
        Exception("DPY-3015: password verifier type 0x939 is not supported")
    )

    assert "旧版 10G password verifier" in message
    assert "OPSCORE_ORACLE_THICK_MODE=true" in message


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
