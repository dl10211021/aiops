from core.asset_protocols import get_asset_catalog
from core.slash_commands import COMMANDS, render_builtin_templates, render_slash_commands


def labels_for(context):
    return {item["label"] for item in render_slash_commands(context, ["example_tool"])}


def test_builtin_command_sort_orders_are_simple_user_values():
    assert all(1 <= command.sort_order <= 100 for command in COMMANDS)


def test_linux_ssh_does_not_match_other_ssh_asset_templates():
    labels = labels_for({"asset_type": "linux", "protocol": "ssh", "host": "10.0.0.1"})

    assert "/services 服务状态" in labels
    assert "/middleware 中间件健康" not in labels
    assert "/net-health 网络设备健康" not in labels
    assert "/storage 存储健康" not in labels


def test_protocol_scoped_http_api_template_still_matches_by_protocol():
    labels = labels_for({"asset_type": "custom_platform", "protocol": "http_api", "host": "api.local"})

    assert "/api-health API 健康" in labels


def test_asset_type_templates_require_matching_protocol_guard():
    labels = labels_for({"asset_type": "oracle", "protocol": "http_api", "host": "db.local"})

    assert "/oracle-health 实例健康" not in labels
    assert "/db-inspect 数据库巡检" not in labels


def test_database_sessions_get_database_inspection_shortcuts():
    context = {"asset_type": "dameng", "protocol": "dameng", "host": "db.local"}
    commands = render_slash_commands(context, ["db_execute_query"])
    labels = {item["label"] for item in commands}
    db_inspect = next(item for item in commands if item["id"] == "database-inspect")

    assert "/db-inspect 数据库巡检" in labels
    assert "/db-slow 慢SQL分析" in labels
    assert "/db-baseline 配置基线" in labels
    assert "/db-index 索引健康" in labels
    assert db_inspect["category"] == "数据库巡检"
    assert "不要本地脚本" in db_inspect["prompt"]


def test_oracle_commands_use_current_oracle_context_not_linux_templates():
    context = {"asset_type": "oracle", "protocol": "oracle", "host": "172.17.1.207"}
    commands = render_slash_commands(context, ["db_execute_query"])
    labels = {item["label"] for item in commands}
    inspect = next(item for item in commands if item["id"] == "inspect")

    assert "/oracle-health 实例健康" in labels
    assert "/services 服务状态" not in labels
    assert "/network 网络监听" not in labels
    assert "oracle/oracle 172.17.1.207" in inspect["prompt"]
    assert "linux/ssh" not in inspect["prompt"].lower()


def test_database_inspection_shortcuts_do_not_pollute_linux_sessions():
    labels = labels_for({"asset_type": "linux", "protocol": "ssh", "host": "10.0.0.1"})

    assert "/db-inspect 数据库巡检" not in labels
    assert "/db-slow 慢SQL分析" not in labels


def test_vendor_network_subtypes_get_network_shortcuts_not_linux_templates():
    labels = labels_for({"asset_type": "h3c_switch", "protocol": "ssh", "host": "192.168.100.100"})

    assert "/net-health 网络设备健康" in labels
    assert "/services 服务状态" not in labels


def test_storage_ssh_subtypes_get_storage_shortcuts():
    labels = labels_for({"asset_type": "synology_nas", "protocol": "ssh", "host": "nas.local"})

    assert "/storage 存储健康" in labels
    assert "/services 服务状态" not in labels


def test_middleware_shell_subtypes_get_middleware_shortcuts():
    labels = labels_for({"asset_type": "process", "protocol": "ssh", "host": "app.local"})

    assert "/middleware 中间件健康" in labels
    assert "/services 服务状态" not in labels


def test_middleware_probe_subtypes_get_middleware_shortcuts():
    labels = labels_for({"asset_type": "kafka_client", "protocol": "kafka", "host": "kafka.local"})

    assert "/middleware 中间件健康" in labels
    assert "/api-health API 健康" not in labels


def test_database_catalog_types_get_data_service_inspection_shortcut():
    expected_samples = {
        "clickhouse",
        "db2",
        "doris_fe",
        "hive",
        "iotdb",
        "mongodb_atlas",
        "redis_cluster",
        "starrocks_fe",
        "xugu",
    }
    by_id = {item["id"]: item for item in get_asset_catalog()}

    for asset_id in expected_samples:
        item = by_id[asset_id]
        labels = labels_for({"asset_type": asset_id, "protocol": item["protocol"], "host": "db.local"})

        assert "/db-inspect 数据库巡检" in labels, asset_id


def test_category_specific_shortcuts_cover_current_asset_catalog():
    required_by_category = {
        "db": "/db-inspect 数据库巡检",
        "middleware": "/middleware 中间件健康",
        "network": "/net-health 网络设备健康",
        "storage": "/storage 存储健康",
        "container": "/container 容器平台健康",
        "bigdata": "/bigdata 大数据健康",
        "virtualization": "/vmware-health 虚拟化健康",
        "monitor": "/alerts 告警摘要",
        "service": "/service 服务探测",
        "discovery": "/discovery 服务发现",
        "security": "/security 安全平台健康",
    }

    for item in get_asset_catalog():
        expected = required_by_category.get(item["category"])
        if not expected:
            continue
        labels = labels_for({"asset_type": item["id"], "protocol": item["protocol"], "host": "asset.local"})

        assert expected in labels, item["id"]


def test_builtin_template_override_replaces_default_command():
    context = {"asset_type": "linux", "protocol": "ssh", "host": "10.0.0.1"}
    override = {
        "id": "linux-services",
        "label": "/svc 企业服务巡检",
        "description": "企业标准服务巡检",
        "prompt_template": "按企业标准检查 {target} 服务状态",
        "category": "操作系统",
        "scope_type": "asset_type",
        "asset_type": "linux",
        "protocol": "ssh",
        "readonly": True,
        "pinned": True,
        "enabled": True,
        "sort_order": 1,
    }

    commands = render_slash_commands(context, ["linux_execute_command"], [override])
    labels = [item["label"] for item in commands]

    assert "/svc 企业服务巡检" in labels
    assert "/services 服务状态" not in labels


def test_disabled_builtin_override_hides_command_but_remains_manageable():
    context = {"asset_type": "linux", "protocol": "ssh", "host": "10.0.0.1"}
    override = {
        "id": "linux-services",
        "label": "/services 服务状态",
        "description": "disabled",
        "prompt_template": "disabled",
        "category": "操作系统",
        "scope_type": "asset_type",
        "asset_type": "linux",
        "protocol": "ssh",
        "readonly": True,
        "pinned": True,
        "enabled": False,
        "sort_order": 1,
    }

    commands = render_slash_commands(context, ["linux_execute_command"], [override])
    templates = render_builtin_templates(context, ["linux_execute_command"], [override])

    assert "/services 服务状态" not in {item["label"] for item in commands}
    service_template = next(item for item in templates if item["id"] == "linux-services")
    assert service_template["enabled"] is False
    assert service_template["source"] == "builtin_override"
