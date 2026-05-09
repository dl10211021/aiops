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


def test_database_inspection_shortcuts_do_not_pollute_linux_sessions():
    labels = labels_for({"asset_type": "linux", "protocol": "ssh", "host": "10.0.0.1"})

    assert "/db-inspect 数据库巡检" not in labels
    assert "/db-slow 慢SQL分析" not in labels


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
