from core.session_profile import (
    _fallback_profile,
    _history_excerpt,
    _normalize_profile,
    profile_to_markdown,
    profile_to_system_prompt,
)


def test_fallback_profile_marks_database_focus_area():
    context = {
        "session_id": "sid-1",
        "asset_key": "oracle:oracle:10.0.0.1:1521",
        "host": "10.0.0.1",
        "port": 1521,
        "remark": "核心 Oracle",
        "asset_type": "oracle",
        "protocol": "oracle",
        "tags": ["数据库"],
    }
    inspection = {
        "summary": "数据库只读巡检完成。",
        "checks": [
            {"title": "数据库只读 SQL 探测", "status": "success", "output": '{"success": true}'}
        ],
    }

    profile = _fallback_profile("sid-1", context, inspection, "fallback")

    assert profile["role_category"] == "database"
    assert "数据库" in profile["role_label"]
    assert profile["risk_level"] == "normal"
    assert profile["focus_areas"][0]["priority"] == "P0"
    assert profile["relations"][0]["direction"] == "inbound"
    assert profile["relation_strategies"][0]["direction"] == "inbound"
    assert "v$session" in profile["relation_strategies"][0]["evidence"].lower()
    assert "数据库" in profile_to_markdown(profile)
    assert "互联采集策略" in profile_to_markdown(profile)


def test_fallback_profile_uses_catalog_domain_for_network_storage_and_middleware_ssh_assets():
    samples = [
        (
            "h3c_switch",
            "ssh",
            "network",
            "网络",
            "网络邻居与上下联",
        ),
        (
            "synology_nas",
            "ssh",
            "storage",
            "存储",
            "业务到存储的访问",
        ),
        (
            "kafka",
            "ssh",
            "middleware",
            "中间件",
            "业务到中间件的连接",
        ),
        (
            "process",
            "ssh",
            "middleware",
            "中间件",
            "业务到中间件的连接",
        ),
    ]

    for asset_type, protocol, role_category, role_text, strategy_title in samples:
        profile = _fallback_profile(
            f"sid-{asset_type}",
            {
                "session_id": f"sid-{asset_type}",
                "asset_key": f"{asset_type}:{protocol}:10.0.0.3:22",
                "host": "10.0.0.3",
                "port": 22,
                "asset_type": asset_type,
                "protocol": protocol,
                "tags": [],
            },
            {"checks": []},
            "fallback",
        )

        assert profile["role_category"] == role_category, asset_type
        assert role_text in profile["role_label"], asset_type
        assert profile["focus_areas"][0]["priority"] == "P0"
        assert profile["relation_strategies"][0]["title"] == strategy_title
        assert "Linux/Unix 主机" not in profile["role_label"]


def test_normalize_profile_corrects_stale_protocol_fallback_for_catalog_assets():
    context = {
        "session_id": "sid-h3c",
        "asset_key": "h3c_switch:ssh:10.0.0.3:22",
        "host": "10.0.0.3",
        "port": 22,
        "asset_type": "h3c_switch",
        "protocol": "ssh",
        "tags": [],
    }
    profile = _normalize_profile(
        {
            "role_label": "Linux/Unix 主机",
            "role_category": "linux",
            "purpose": "旧画像按 SSH 协议误判为 Linux 主机。",
            "relation_strategies": [
                {
                    "direction": "inbound",
                    "title": "业务/用户到主机的连接",
                    "method": "通过 ss/netstat 读取监听端口。",
                    "evidence": "ss -lntup",
                    "tool_hint": "ssh_execute_command",
                }
            ],
        },
        context,
    )

    assert profile["role_category"] == "network"
    assert "网络" in profile["role_label"]
    assert profile["relation_strategies"][0]["title"] == "网络邻居与上下联"
    assert "ssh_execute_command" not in profile["relation_strategies"][0]["tool_hint"]


def test_network_fallback_profile_extracts_neighbor_and_port_role_evidence():
    context = {
        "session_id": "sid-h3c",
        "asset_key": "h3c_switch:ssh:10.0.0.3:22",
        "host": "10.0.0.3",
        "port": 22,
        "asset_type": "h3c_switch",
        "protocol": "ssh",
        "tags": [],
    }
    inspection = {
        "checks": [
            {
                "name": "neighbors",
                "title": "LLDP 邻居",
                "status": "success",
                "command": "display lldp neighbor brief",
                "output": "GigabitEthernet1/0/48 Core-SW-01 Ten-GigabitEthernet1/0/1",
            },
            {
                "name": "mac_table",
                "title": "MAC 地址表",
                "status": "success",
                "command": "display mac-address",
                "output": "5489-98aa-bbcc 10 learned GigabitEthernet1/0/10",
            },
        ],
    }

    profile = _fallback_profile("sid-h3c", context, inspection, "fallback")

    assert profile["role_category"] == "network"
    assert profile["focus_areas"][0]["title"] == "接口、邻居和上下联"
    assert any(item["peer"] == "Core-SW-01" for item in profile["relations"])
    assert any("上联" in item["peer_role"] for item in profile["relations"])
    assert any("lldp" in item["protocol"] for item in profile["relations"])
    assert "VLAN/Trunk" in profile["relation_strategies"][0]["method"]


def test_fallback_profile_raises_risk_for_multiple_failed_checks():
    context = {
        "session_id": "sid-2",
        "asset_key": "linux:ssh:10.0.0.2:22",
        "host": "10.0.0.2",
        "port": 22,
        "asset_type": "linux",
        "protocol": "ssh",
    }
    inspection = {
        "checks": [
            {"title": "内存", "status": "error", "output": "free failed"},
            {"title": "磁盘", "status": "error", "output": "df failed"},
            {"title": "服务", "status": "warning", "output": "failed units"},
        ],
    }

    profile = _fallback_profile("sid-2", context, inspection, "fallback")

    assert profile["role_category"] == "linux"
    assert profile["risk_level"] == "high"
    assert profile["confidence"] > 0


def test_profile_prompt_is_reused_without_manual_realtime_confirmation_wording():
    prompt = profile_to_system_prompt(
        {
            "profile_prompt": "这是核心 Linux 应用服务器，优先关注 Docker、SSH 和系统日志。",
        }
    )

    assert "不需要每轮人工确认" in prompt
    assert "实时工具结果验证" not in prompt


def test_history_excerpt_includes_tool_policy_and_evidence_for_profile_generation(monkeypatch):
    class FakeMemory:
        def get_messages(self, session_id: str, for_ui: bool = True):
            assert session_id == "sid-1"
            assert for_ui is True
            return [
                {"role": "user", "content": "检查数据库连接"},
                {
                    "role": "assistant",
                    "content": "数据库连接正常。",
                    "exec_trace": [
                        {
                            "tool": "db_execute_query",
                            "status": "done",
                            "args": "select 1 from dual",
                            "result": '{"success": true}',
                            "resultMeta": {
                                "tool_policy": {
                                    "operation_mode": "read_write",
                                    "approval_policy": "guarded_write",
                                    "evidence_family": "database",
                                }
                            },
                            "evidenceId": "tev-sid-1-call-1",
                        }
                    ],
                },
            ]

    monkeypatch.setattr("core.session_profile.memory_db", FakeMemory())

    excerpt = _history_excerpt("sid-1")

    assert "[工具轨迹]" in excerpt
    assert "tool=db_execute_query" in excerpt
    assert "policy=read_write/guarded_write/database" in excerpt
    assert "evidence=tev-sid-1-call-1" in excerpt
    assert "execute=select 1 from dual" in excerpt


def test_profile_to_system_prompt_synthesizes_from_structured_profile_when_prompt_missing():
    prompt = profile_to_system_prompt(
        {
            "role_label": "ISO27001 合规审计系统后端服务器",
            "purpose": "承载 ISO27001 合规审计平台的前后端容器服务。",
            "risk_level": "normal",
            "confidence": 92,
            "evidence": [
                {"label": "安全状态", "value": "UFW active, SSH active", "source": "session_service_health"}
            ],
            "focus_areas": [
                {
                    "priority": "P1",
                    "title": "SSH 访问控制",
                    "reason": "确认登录审计和密钥轮换策略。",
                }
            ],
            "relations": [
                {
                    "direction": "outbound",
                    "peer": "Oracle 数据库",
                    "endpoint": "172.17.8.150:1521",
                    "protocol": "oracle",
                    "evidence": "应用配置存在数据库连接。",
                    "confidence": 80,
                }
            ],
            "relation_strategies": [
                {
                    "direction": "inbound",
                    "title": "业务到 Oracle 的连接",
                    "method": "查询 v$session/v$process 汇总客户端来源。",
                    "evidence": "v$session、v$process",
                    "tool_hint": "database_execute_sql",
                }
            ],
        }
    )

    assert "ISO27001 合规审计系统后端服务器" in prompt
    assert "互联关系" in prompt
    assert "互联采集策略" in prompt
    assert "Oracle 数据库" in prompt
    assert "v$session" in prompt
    assert "UFW active" in prompt
    assert "SSH 访问控制" in prompt
    assert "不需要每轮人工确认" in prompt
